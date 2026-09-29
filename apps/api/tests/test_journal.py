"""Persistencia real, alcance y reintentos de anotaciones."""
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


@pytest.fixture
def world(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser, create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    assert apply_migrations(DSN) == []
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    suffix = uuid4().hex
    emails = [f"journal-{suffix}-{n}@example.test" for n in range(2)]
    for email, org in zip(emails, ["los-encinos", "valle-verde"], strict=True):
        create_user(DSN, email=email, org_slug=org)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
                    "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,))
        users = [AuthUser(*row, False) for row in cur.fetchall()]
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    tag = f"journal-{suffix}"
    yield TestClient(main.app), users, tag
    main.app.dependency_overrides.pop(main.current_user, None)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM animal_journal WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM animals WHERE tag_id=%s", (tag,))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


def entry(**overrides):
    return {"entry_id": str(uuid4()), "occurred_at": "2026-09-27T12:00:00Z",
            "category": "observacion", "body": "Observación del animal", **overrides}


def test_note_author_scope_and_retry(world):
    from fierro_api import main

    client, users, tag = world
    path = f"/v1/animals/{tag}/journal"
    payload = entry()
    first = client.post(path + "?org=valle-verde", json=payload)
    assert first.status_code == 200
    assert first.json()["author"] == users[0].email
    assert client.post(path, json=payload).json() == first.json()
    assert len(client.get(path).json()["entries"]) == 1
    assert client.post(path, json={**payload, "body": "Otro texto"}).status_code == 409
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    assert client.get(path + "?org=los-encinos").json()["entries"] == []
    assert client.post(path, json=payload).status_code == 409
    assert client.post(path, json=entry(body="Otra organización")).status_code == 200
    assert len(client.get(path).json()["entries"]) == 1


def test_admin_scope_and_pagination(world):
    from fierro_api import main

    client, users, tag = world
    path = f"/v1/animals/{tag}/journal"
    for _ in range(3):
        assert client.post(path, json=entry()).status_code == 200
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get(path).status_code == 400
    assert client.post(path, json=entry()).status_code == 400
    first = client.get(path, params={"org": "los-encinos", "limit": 2}).json()
    second = client.get(path, params={
        "org": "los-encinos", "limit": 2, "cursor": first["next_cursor"],
    }).json()
    assert len(first["entries"]) == 2
    assert len(second["entries"]) == 1
    assert second["next_cursor"] is None
    assert {e["entry_id"] for e in first["entries"]}.isdisjoint(
        e["entry_id"] for e in second["entries"]
    )
    assert client.get(path + "?org=valle-verde").json()["entries"] == []
    assert client.get(path + "?org=los-encinos&cursor=bad").status_code == 400


@pytest.mark.parametrize("invalid", [
    {"body": "   "}, {"body": "x" * 4001}, {"occurred_at": "2026-09-27T12:00:00"},
    {"entry_id": "bad"}, {"category": "unknown"},
])
def test_validation(world, invalid):
    client, _, tag = world
    assert client.post(f"/v1/animals/{tag}/journal", json=entry(**invalid)).status_code == 422


def test_concurrent_retry_commits_once(world):
    from fierro_api.journal import add_entry, list_entries

    _, users, tag = world
    args = dict(org="los-encinos", tag=tag, author_id=users[0].id, entry_id=uuid4(),
                occurred_at=datetime.now(timezone.utc), category="manejo", body="Manejo del animal")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: add_entry(DSN, **args), range(2)))
    assert results[0] == results[1]
    assert len(list_entries(DSN, org="los-encinos", tag=tag, limit=20)) == 1
