"""Busqueda del Diario contra Postgres real, con corpus y permisos por organizacion."""
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter
from uuid import uuid4

import pytest
from fierro_api.migrate import MIGRATIONS_DIR, apply_migrations

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")
CORPUS = json.loads((Path(__file__).parent / "fixtures/journal_search.json").read_text("utf-8"))
MIGRATION = MIGRATIONS_DIR / "012_journal_search.sql"


@pytest.fixture
def world(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser, create_user

    apply_migrations(DSN)
    suffix = uuid4().hex[:12]
    orgs = [f"search147-{suffix}-{index}" for index in range(2)]
    emails = [f"{slug}@example.test" for slug in orgs]
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        for slug in orgs:
            cur.execute("INSERT INTO organizations(slug,name) VALUES (%s,%s)", (slug, slug))
    for email, org in zip(emails, orgs, strict=True):
        create_user(DSN, email=email, org_slug=org)
    ids = {}
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
            "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,),
        )
        users = [AuthUser(*row, False) for row in cur.fetchall()]
        for user in users:
            animal_ids = {}
            for tag in ("pinta", "colorada"):
                cur.execute(
                    "INSERT INTO animals(org_id,tag_id,alias) VALUES (%s,%s,%s) RETURNING id",
                    (user.org_id, tag, tag.title()),
                )
                animal_ids[tag] = cur.fetchone()[0]
            for note in CORPUS["entries"]:
                entry_id = uuid4()
                ids[user.org_slug, note["key"]] = str(entry_id)
                cur.execute(
                    "INSERT INTO journal_entries(entry_id,org_id,author_id,occurred_at,"
                    "category,body) VALUES (%s,%s,%s,%s,%s,%s)",
                    (entry_id, user.org_id, user.id, note["occurred_at"],
                     note["category"], note["body"]),
                )
                for tag in note["animals"]:
                    cur.execute(
                        "INSERT INTO journal_entry_animals(entry_id,animal_id,org_id) "
                        "VALUES (%s,%s,%s)", (entry_id, animal_ids[tag], user.org_id),
                    )
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    try:
        with TestClient(main.app) as client:
            yield client, users, ids
    finally:
        main.app.dependency_overrides.pop(main.current_user, None)
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            org_ids = [user.org_id for user in users]
            cur.execute("DELETE FROM journal_entries WHERE org_id=ANY(%s)", (org_ids,))
            cur.execute("DELETE FROM animals WHERE org_id=ANY(%s)", (org_ids,))
            cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))
            cur.execute("DELETE FROM organizations WHERE slug=ANY(%s)", (orgs,))


@pytest.mark.parametrize("example", CORPUS["questions"], ids=lambda case: case["query"])
def test_five_questions_find_expected_entry_in_top_three(world, example):
    client, users, ids = world
    response = client.get("/v1/journal/search", params={"q": example["query"]})
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert ids[users[0].org_slug, example["expected"]] in [
        entry["entry_id"] for entry in entries[:3]
    ]
    assert all(entry["author"] == users[0].email for entry in entries)
    assert all({"body", "excerpt", "category", "occurred_at", "animals"} <= entry.keys()
               for entry in entries)


@pytest.mark.parametrize(("query", "key"), [
    ("vacunó", "vacuna-brucelosis"), ("COJERA", "cojera-pinta"),
    ("DESPARASITACION", "desparasitacion"), ("reparacion bascula", "bascula-reparacion"),
])
def test_accents_case_and_spanish_stemming(world, query, key):
    client, users, ids = world
    response = client.get("/v1/journal/search", params={"q": query})
    assert response.status_code == 200
    assert ids[users[0].org_slug, key] in [
        entry["entry_id"] for entry in response.json()["entries"]
    ]


def test_tenant_scope_ignores_forged_org_and_admin_requires_one(world):
    from fierro_api import main

    client, users, ids = world
    for reader, other in [(users[0], users[1]), (users[1], users[0])]:
        main.app.dependency_overrides[main.current_user] = lambda reader=reader: reader
        response = client.get("/v1/journal/search", params={"q": "cojera", "org": other.org_slug})
        assert response.status_code == 200
        assert [entry["entry_id"] for entry in response.json()["entries"]] == [
            ids[reader.org_slug, "cojera-pinta"]
        ]
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get("/v1/journal/search?q=cojera").status_code == 400
    response = client.get("/v1/journal/search", params={"q": "cojera", "org": users[1].org_slug})
    assert response.status_code == 200
    assert response.json()["entries"][0]["entry_id"] == ids[users[1].org_slug, "cojera-pinta"]
    assert client.get("/v1/journal/search?q=cojera&org=inexistente").json()["entries"] == []
    main.app.dependency_overrides[main.current_user] = lambda: replace(
        users[0], org_id=None, org_slug=None,
    )
    assert client.get("/v1/journal/search?q=cojera").status_code == 403
    main.app.dependency_overrides.pop(main.current_user)
    assert client.get("/v1/journal/search?q=cojera").status_code == 401


def test_animal_time_filters_and_websearch_syntax(world):
    client, users, ids = world
    params = {"q": "vacuna", "tag": "colorada",
              "desde": "2026-11-02T02:00:00-06:00", "hasta": "2026-11-03T00:00:00Z"}
    response = client.get("/v1/journal/search", params=params)
    assert response.status_code == 200
    result = response.json()["entries"]
    assert [entry["entry_id"] for entry in result] == [ids[users[0].org_slug, "vacuna-brucelosis"]]
    assert result[0]["animals"] == ["colorada", "pinta"]
    assert "[[vacuna]]" in result[0]["excerpt"]
    assert client.get("/v1/journal/search", params={**params, "tag": "ausente"}).json() == {
        "entries": [],
    }
    assert client.get("/v1/journal/search", params={
        **params, "hasta": "2026-11-02T08:00:00Z",
    }).json()["entries"] == []
    query = '"sal mineral" OR "vacuna brucelosis"'
    result = client.get("/v1/journal/search", params={"q": query, "limit": 1}).json()["entries"]
    assert len(result) == 1
    assert result[0]["entry_id"] in {
        ids[users[0].org_slug, "vacuna-brucelosis"], ids[users[0].org_slug, "sal-mineral"],
    }
    assert client.get("/v1/journal/search?q=de%20la%20y").json()["entries"] == []
    response = client.get("/v1/journal/search", params={"q": "'; DROP TABLE users; --"})
    assert response.status_code == 200


@pytest.mark.parametrize("params", [
    {}, {"q": ""}, {"q": "   "}, {"q": "x" * 301},
    {"q": "cojera", "limit": 0}, {"q": "cojera", "limit": 101},
])
def test_invalid_search_parameters(world, params):
    client, _, _ = world
    assert client.get("/v1/journal/search", params=params).status_code == 422


def test_naive_dates_are_rejected(world):
    client, _, _ = world
    for field in ("desde", "hasta"):
        response = client.get("/v1/journal/search", params={
            "q": "cojera", field: "2026-11-02T08:00:00",
        })
        assert response.status_code == 400


def test_migration_twice_preserves_entries_and_populates_generated_index(world):
    import psycopg

    _, users, ids = world
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        for _ in range(2):
            cur.execute(MIGRATION.read_text("utf-8"))
        cur.execute(
            "SELECT body,search_text,search_tsv @@ websearch_to_tsquery("
            "'spanish',fierro_unaccent('VACUNO')) FROM journal_entries WHERE entry_id=%s",
            (ids[users[0].org_slug, "vacuna-brucelosis"],),
        )
        body, derived, matched = cur.fetchone()
        assert body == CORPUS["entries"][1]["body"]
        assert derived == ""
        assert matched
        cur.execute("SELECT count(*) FROM journal_entries WHERE org_id=%s", (users[0].org_id,))
        assert cur.fetchone()[0] == 30
        cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname='idx_journal_search'")
        assert "USING gin (search_tsv)" in cur.fetchone()[0]


def test_search_function_orders_relevance_then_event_date(world):
    import psycopg
    from fierro_api import journal

    _, users, ids = world
    later, relevant = uuid4(), uuid4()
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO journal_entries(entry_id,org_id,author_id,occurred_at,category,body) "
            "VALUES (%s,%s,%s,'2026-12-01T08:00:00Z','general',%s)",
            (later, users[0].org_id, users[0].id, CORPUS["entries"][1]["body"]),
        )
        cur.execute(
            "INSERT INTO journal_entries(entry_id,org_id,author_id,occurred_at,category,body) "
            "VALUES (%s,%s,%s,'2026-01-01T08:00:00Z','general','Vacuna vacuna vacuna vacuna.')",
            (relevant, users[0].org_id, users[0].id),
        )
    entries = journal.search(DSN, org=users[0].org_slug, query="vacuna")
    assert [entry["entry_id"] for entry in entries[:3]] == [
        str(relevant), str(later), ids[users[0].org_slug, "vacuna-brucelosis"],
    ]
    assert entries[1]["occurred_at"] == datetime(2026, 12, 1, 8, tzinfo=timezone.utc).isoformat()


def test_search_latency_with_ten_thousand_entries(world):
    import psycopg

    client, users, _ = world
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM journal_entries WHERE org_id=ANY(%s)",
                    ([user.org_id for user in users],))
        for user in users:
            cur.execute(
                "INSERT INTO journal_entries(entry_id,org_id,author_id,occurred_at,category,body) "
                "SELECT md5(%s || g)::uuid,%s,%s,"
                "'2026-01-01'::timestamptz + g * interval '1 minute',"
                "'observacion',CASE g %% 4 WHEN 0 THEN 'Revisión de la vacuna contra brucelosis.' "
                "WHEN 1 THEN 'Cojera de la pata trasera durante la revisión.' "
                "WHEN 2 THEN 'Llegaron costales de sal mineral para el corral.' "
                "ELSE 'Lluvia en el potrero norte durante la madrugada.' END "
                "FROM generate_series(1,5000) AS g",
                (user.org_slug, user.org_id, user.id),
            )
        cur.execute("ANALYZE journal_entries")
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
    durations = []
    for _ in range(10):
        for query in ("vacuna", "cojera", '"sal mineral"', "potrero", "inexistente"):
            started = perf_counter()
            response = client.get("/v1/journal/search", params={"q": query})
            durations.append((perf_counter() - started) * 1000)
            assert response.status_code == 200
            assert len(response.json()["entries"]) == (0 if query == "inexistente" else 10)
    p95 = quantiles(durations, n=100)[94]
    print(json.dumps({
        "postgres": version, "entries": 10000, "samples": len(durations),
        "median_ms": round(median(durations), 2), "p95_ms": round(p95, 2),
        "max_ms": round(max(durations), 2),
    }))
    assert p95 < 300
