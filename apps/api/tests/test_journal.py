"""Persistencia real, alcance y reintentos de anotaciones."""
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")


@pytest.fixture
def world(monkeypatch):
    if not DSN:
        pytest.skip("FIERRO_TEST_PG_DSN no definido")
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
        cur.execute("DELETE FROM animals WHERE tag_id=ANY(%s)", ([tag, tag + "-2", tag + "-3"],))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


@pytest.fixture
def validation_client(monkeypatch):
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser

    # Estas peticiones se rechazan antes de abrir una conexión.
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn="postgresql://unused"))
    main.app.dependency_overrides[main.current_user] = lambda: AuthUser(
        1, "validation@example.test", 1, "los-encinos", False,
    )
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.pop(main.current_user, None)


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


def test_ranch_entries_and_animal_views(world):
    client, _, tag = world
    tags = [tag, tag + '-2', tag + '-3']
    rain = entry(category='clima', body='Llovió 30 mm')
    group = entry(tags=tags, category='insumos')
    for payload in (rain, group):
        first = client.post('/v1/journal', json=payload)
        assert first.status_code == 200
        assert client.post('/v1/journal', json=payload).json() == first.json()
    retry = client.post('/v1/journal', json={**group, 'tags': list(reversed(tags)) + [tag]})
    assert retry.status_code == 200
    assert client.post('/v1/journal', json={**group, 'tags': tags[:2]}).status_code == 409
    ids = {e['entry_id'] for e in client.get('/v1/journal').json()['entries']}
    assert ids == {rain['entry_id'], group['entry_id']}
    for animal in tags:
        rows = client.get(f'/v1/animals/{animal}/journal').json()['entries']
        assert [e['entry_id'] for e in rows] == [group['entry_id']]
        filtered = client.get('/v1/journal', params={'tag': animal}).json()['entries']
        assert filtered == rows


def test_ranch_scope_filters_and_pagination(world):
    from fierro_api import main

    client, users, tag = world
    payloads = [entry(tags=[tag], occurred_at=f'2026-09-{day}T12:00:00Z')
                for day in (25, 26, 27)]
    for payload in payloads:
        assert client.post('/v1/journal?org=valle-verde', json=payload).status_code == 200
    query = {'desde': '2026-09-26T12:00:00Z', 'hasta': '2026-09-27T12:00:00Z', 'limit': 1}
    first = client.get('/v1/journal', params=query).json()
    second = client.get('/v1/journal', params={**query, 'cursor': first['next_cursor']}).json()
    assert first['entries'][0]['entry_id'] == payloads[2]['entry_id']
    assert second['entries'][0]['entry_id'] == payloads[1]['entry_id']
    assert client.get('/v1/journal', params={'desde': query['hasta'],
                                           'hasta': query['desde']}).status_code == 400
    assert client.get('/v1/journal?desde=2026-09-27T12:00:00').status_code == 422
    assert client.get('/v1/journal?cursor=bad').status_code == 400
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    assert client.get('/v1/journal?org=los-encinos').json()['entries'] == []
    assert client.post('/v1/journal', json=payloads[0]).status_code == 409
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get('/v1/journal').status_code == 400
    assert client.post('/v1/journal', json=entry()).status_code == 400
    assert client.get('/v1/journal?org=valle-verde').json()['entries'] == []
    assert len(client.get('/v1/journal?org=los-encinos').json()['entries']) == 3


def test_profile_notes_append_without_overwriting_column(world):
    import psycopg

    client, users, tag = world
    path = f'/v1/animals/{tag}'
    for text in ('Primera nota', 'Primera nota', 'Segunda nota'):
        response = client.put(path, json={'alias': 'Pinta', 'notes': text})
        assert response.status_code == 200
        assert response.json()['notes'] == text
    assert client.get(path).json()['notes'] == 'Segunda nota'
    rows = client.get(path + '/journal').json()['entries']
    assert [e['body'] for e in rows] == ['Segunda nota', 'Primera nota']
    assert all(e['category'] == 'general' and e['author'] == users[0].email for e in rows)
    assert client.put(path, json={'alias': 'Nuevo alias'}).json()['notes'] == 'Segunda nota'
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute('SELECT notes FROM animals WHERE tag_id=%s', (tag,))
        assert cur.fetchone() == (None,)


@pytest.mark.parametrize('tags_count', [0, 3])
def test_concurrent_ranch_retry_commits_once(world, tags_count):
    from fierro_api.journal import add_entry, list_entries

    _, users, tag = world
    tags = [tag, tag + '-2', tag + '-3'][:tags_count]
    args = dict(org='los-encinos', tags=tags, author_id=users[0].id, entry_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                category='equipo', body='Revisión de báscula')
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: add_entry(DSN, **args), range(2)))
    assert results[0] == results[1]
    assert len(list_entries(DSN, org='los-encinos', limit=20)) == 1


def test_profile_note_concurrent_retry_and_validation(world):
    from fierro_api.animals import upsert_animal

    client, users, tag = world
    args = dict(org_slug='los-encinos', tag_id=tag, notes='Nota de la ficha', author_id=users[0].id)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: upsert_animal(DSN, **args), range(2)))
    assert all(result['notes'] == args['notes'] for result in results)
    path = f'/v1/animals/{tag}'
    assert len(client.get(path + '/journal').json()['entries']) == 1
    assert client.put(path, json={'notes': 'x' * 4001}).status_code == 400
    assert client.put(path, json={'notes': '   '}).status_code == 400
    assert len(client.get(path + '/journal').json()['entries']) == 1


@pytest.mark.parametrize('invalid', [
    {'tags': ['']}, {'tags': ['  ']}, {'tags': ['x'] * 101}, {'tags': [123]},
    {'body': ' '}, {'body': 'x' * 4001}, {'category': 'unknown'},
    {'occurred_at': '2026-09-27T12:00:00'}, {'entry_id': 'bad'},
])
def test_ranch_validation(validation_client, invalid):
    assert validation_client.post('/v1/journal', json=entry(**invalid)).status_code == 422


def test_ranch_requires_credentials(validation_client):
    from fierro_api import main

    client = validation_client
    main.app.dependency_overrides.pop(main.current_user)
    assert client.get('/v1/journal').status_code == 401
    assert client.post('/v1/journal', json=entry()).status_code == 401
