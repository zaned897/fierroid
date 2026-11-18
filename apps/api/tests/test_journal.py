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
        cur.execute("DELETE FROM journal_entries WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM animal_journal WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM animals WHERE tag_id LIKE %s", (tag + "%",))
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


def test_ranch_entries_with_zero_or_three_animals(world):
    client, _, tag = world
    rain = entry(category="clima", body="Llovió 30 mm")
    first = client.post("/v1/journal", json=rain)
    assert first.status_code == 200
    assert first.json()["tags"] == []
    assert client.post("/v1/journal", json=rain).json() == first.json()

    tags = [tag, tag + "-2", tag + "-3"]
    feeding = entry(category="insumos", tags=tags)
    second = client.post("/v1/journal", json=feeding)
    assert second.status_code == 200
    assert second.json()["tags"] == sorted(tags)
    assert client.post("/v1/journal", json={
        **feeding, "tags": [*reversed(tags), tag],
    }).json() == second.json()
    assert {e["entry_id"] for e in client.get("/v1/journal").json()["entries"]} == {
        rain["entry_id"], feeding["entry_id"],
    }
    for animal in tags:
        assert client.get(f"/v1/animals/{animal}/journal").json()["entries"] == [second.json()]
    assert client.post("/v1/journal", json={**feeding, "tags": tags[:2]}).status_code == 409
    assert client.post("/v1/journal", json={**feeding, "tags": []}).status_code == 409


@pytest.mark.parametrize("category", ["clima", "insumos", "equipo", "general"])
def test_new_categories_work_on_both_routes(world, category):
    client, _, tag = world
    assert client.post("/v1/journal", json=entry(category=category)).status_code == 200
    response = client.post(f"/v1/animals/{tag}/journal", json=entry(category=category))
    assert response.status_code == 200


def test_ranch_scope_and_legacy_view_share_the_journal(world):
    from fierro_api import main

    client, users, tag = world
    payload = entry(tags=[tag])
    first = client.post("/v1/journal?org=valle-verde", json=payload)
    assert first.status_code == 200
    legacy = {key: value for key, value in payload.items() if key != "tags"}
    assert client.post(f"/v1/animals/{tag}/journal", json=legacy).json() == first.json()
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    for params in ({}, {"org": "los-encinos"}, {"tag": tag, "org": "los-encinos"}):
        assert client.get("/v1/journal", params=params).json()["entries"] == []
    assert client.post("/v1/journal?org=los-encinos", json=payload).status_code == 409
    other = entry(tags=[tag], body="Otro rancho")
    assert client.post("/v1/journal?org=los-encinos", json=other).status_code == 200
    assert [e["entry_id"] for e in client.get("/v1/journal").json()["entries"]] == [
        other["entry_id"],
    ]
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get("/v1/journal").status_code == 400
    assert client.post("/v1/journal", json=entry()).status_code == 400
    for org, expected in (("los-encinos", payload), ("valle-verde", other)):
        assert [e["entry_id"] for e in client.get(
            "/v1/journal", params={"org": org, "tag": tag},
        ).json()["entries"]] == [expected["entry_id"]]
    main.app.dependency_overrides.pop(main.current_user)
    assert client.get("/v1/journal").status_code == 401
    assert client.post("/v1/journal", json=entry()).status_code == 401


def test_ranch_date_filters_and_cursor(world):
    client, _, tag = world
    for hour in (11, 12, 12, 13):
        assert client.post("/v1/journal", json=entry(
            tags=[tag], occurred_at=f"2026-09-27T{hour}:00:00Z",
        )).status_code == 200
    filters = {"desde": "2026-09-27T06:00:00-06:00", "hasta": "2026-09-27T13:00:00Z",
               "tag": tag, "limit": 1}
    page = client.get("/v1/journal", params=filters).json()
    following = client.get("/v1/journal", params={
        **filters, "cursor": page["next_cursor"],
    }).json()
    assert len(page["entries"]) == len(following["entries"]) == 1
    assert page["entries"][0]["entry_id"] != following["entries"][0]["entry_id"]
    assert client.get("/v1/journal", params={
        **filters, "cursor": following["next_cursor"],
    }).json()["entries"] == []
    assert client.get("/v1/journal", params={"tag": tag + "-missing"}).json()["entries"] == []
    assert len(client.get("/v1/journal", params={
        "desde": "2026-09-27T13:00:00Z",
    }).json()["entries"]) == 1
    assert len(client.get("/v1/journal", params={
        "hasta": "2026-09-27T12:00:00Z",
    }).json()["entries"]) == 1
    assert client.get("/v1/journal?desde=2026-09-27T12:00:00").status_code == 422
    assert client.get("/v1/journal?cursor=bad").status_code == 400
    assert client.get("/v1/journal", params={
        "desde": "2026-09-28T00:00:00Z", "hasta": "2026-09-27T00:00:00Z",
    }).status_code == 400


@pytest.mark.parametrize("invalid", [
    {"body": "  "}, {"body": "x" * 4001}, {"occurred_at": "2026-09-27T12:00:00"},
    {"category": "unknown"}, {"entry_id": "bad"}, {"tags": [""]}, {"tags": ["  "]},
])
def test_ranch_validation(world, invalid):
    client, _, _ = world
    assert client.post("/v1/journal", json=entry(**invalid)).status_code == 422


def test_profile_notes_are_append_only_and_retries_do_not_duplicate(world):
    import psycopg

    client, users, tag = world
    path = f"/v1/animals/{tag}"
    for text in ("Primera nota", "Primera nota", "Segunda nota"):
        response = client.put(path, json={"notes": text, "alias": "Pinta"})
        assert response.status_code == 200
        assert response.json()["notes"] == text
        assert client.get(path).json()["notes"] == text
    history = client.get(path + "/journal").json()["entries"]
    assert {e["body"] for e in history} == {"Primera nota", "Segunda nota"}
    assert len(history) == 2
    assert all(e["author"] == users[0].email and e["source"] == "ficha" for e in history)
    for payload in ({"alias": "Nueva"}, {"notes": None}, {"notes": "  "}):
        assert client.put(path, json=payload).status_code == 200
        assert client.get(path).json()["notes"] == "Segunda nota"
    assert len(client.get(path + "/journal").json()["entries"]) == 2
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT notes FROM animals WHERE tag_id=%s", (tag,))
        assert cur.fetchone() == (None,)
        cur.execute("SELECT count(*) FROM animal_journal WHERE author_id=%s", (users[0].id,))
        assert cur.fetchone() == (0,)


def test_concurrent_ranch_and_profile_retries(world):
    from fierro_api.animals import upsert_animal
    from fierro_api.journal import add_ranch_entry, list_entries

    _, users, tag = world
    args = dict(org="los-encinos", tags=[tag, tag + "-2", tag + "-3"], author_id=users[0].id,
                entry_id=uuid4(), occurred_at=datetime.now(timezone.utc),
                category="manejo", body="Manejo del lote")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: add_ranch_entry(DSN, **args), range(2)))
    assert results[0] == results[1]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: upsert_animal(
            DSN, org_slug="los-encinos", tag_id=tag, notes="Nota de ficha", author_id=users[0].id,
        ), range(2)))
    assert len(list_entries(DSN, org="los-encinos", tag=tag, limit=20)) == 2


def test_migration_preserves_history_and_notes_twice(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser
    from fierro_api.migrate import discover
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    schema = "journal_migration_" + uuid4().hex
    scoped_dsn = make_conninfo(DSN, options=f"-csearch_path={schema}")
    with psycopg.connect(DSN) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        with psycopg.connect(scoped_dsn) as conn, conn.cursor() as cur:
            paths = discover()
            for path in paths:
                if path.name < "011":
                    cur.execute(path.read_text())
            cur.execute("SELECT id FROM organizations WHERE slug='demo'")
            org_id = cur.fetchone()[0]
            cur.execute("INSERT INTO organizations(slug,name) "
                        "VALUES ('other','Other') RETURNING id")
            other_org = cur.fetchone()[0]
            cur.execute("INSERT INTO users(email,password_hash,org_id) VALUES "
                        "('migration@example.test','unused',%s) RETURNING id", (org_id,))
            author_id = cur.fetchone()[0]
            stamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
            text = "Nota histórica larga " * 300
            cur.execute("INSERT INTO animals(org_id,tag_id,notes,updated_at) "
                        "VALUES (%s,'old',%s,%s) RETURNING id", (org_id, text, stamp))
            animal_id = cur.fetchone()[0]
            cur.execute("INSERT INTO animals(org_id,tag_id,notes) VALUES "
                        "(%s,'blank','  '),(%s,'empty',NULL),(%s,'old','Otra org')",
                        (org_id, org_id, other_org))
            cur.execute("SELECT id FROM animals WHERE org_id=%s AND tag_id='old'", (other_org,))
            other_animal = cur.fetchone()[0]
            original = uuid4()
            cur.execute("INSERT INTO animal_journal(entry_id,animal_id,author_id,occurred_at,"
                        "created_at,category,body) VALUES (%s,%s,%s,%s,%s,'salud','Original')",
                        (original, animal_id, author_id, stamp, stamp))
            migration = next(p for p in paths if p.name.startswith("011"))
            cur.execute(migration.read_text())
            cur.execute("SELECT * FROM journal_entries ORDER BY entry_id")
            once = cur.fetchall()
            cur.execute(migration.read_text())
            cur.execute("SELECT * FROM journal_entries ORDER BY entry_id")
            assert cur.fetchall() == once
            cur.execute("SELECT count(*) FROM journal_entry_animals")
            assert cur.fetchone() == (3,)
            cur.execute("SELECT org_id,author_id,occurred_at,created_at,body "
                        "FROM journal_entries WHERE entry_id=%s", (original,))
            assert cur.fetchone() == (org_id, author_id, stamp, stamp, "Original")
            # La base impide unir una entrada con un animal de otra organización.
            for invalid_org in (org_id, other_org):
                with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
                    cur.execute("INSERT INTO journal_entry_animals VALUES (%s,%s,%s)",
                                (original, other_animal, invalid_org))
        user = AuthUser(author_id, "migration@example.test", org_id, "demo", False)
        monkeypatch.setattr(main, "settings", replace(main.settings, dsn=scoped_dsn))
        main.app.dependency_overrides[main.current_user] = lambda: user
        client = TestClient(main.app)
        history = client.get("/v1/animals/old/journal").json()["entries"]
        assert len(history) == 2
        legacy = next(e for e in history if e["entry_id"] == str(original))
        assert legacy["author"] == user.email
        assert datetime.fromisoformat(legacy["occurred_at"]) == stamp
        retry = client.post("/v1/animals/old/journal", json={
            "entry_id": str(original), "occurred_at": stamp.isoformat(),
            "category": "salud", "body": "Original",
        })
        assert retry.status_code == 200
        assert retry.json() == legacy
        note = next(e for e in history if e["source"] == "ficha")
        assert note["body"] == text
        assert note["author"] == "Notas de la ficha"
        assert datetime.fromisoformat(note["created_at"]) == stamp
        assert client.get("/v1/animals/old").json()["notes"] == text
        assert client.put("/v1/animals/old", json={"notes": text}).status_code == 200
        assert len(client.get("/v1/animals/old/journal").json()["entries"]) == 2
    finally:
        main.app.dependency_overrides.pop(main.current_user, None)
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
