"""Diario del rancho (#149): entradas sin animal o con varios, migración y Notas."""
import os
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fierro_api.migrate import MIGRATIONS_DIR

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")

MIGRACION = MIGRATIONS_DIR / "011_journal_entries.sql"


@pytest.fixture
def world(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser, create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    suffix = uuid4().hex[:12]
    emails = [f"diario-{suffix}-{n}@example.test" for n in range(2)]
    for email, org in zip(emails, ["los-encinos", "valle-verde"], strict=True):
        create_user(DSN, email=email, org_slug=org)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
                    "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,))
        users = [AuthUser(*row, False) for row in cur.fetchall()]
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    prefix = f"d{suffix}"
    yield TestClient(main.app), users, prefix
    main.app.dependency_overrides.pop(main.current_user, None)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        like = prefix + "%"
        cur.execute(
            "DELETE FROM journal_entries WHERE author_id=ANY(%s) OR entry_id IN ("
            "SELECT ea.entry_id FROM journal_entry_animals ea JOIN animals a "
            "ON a.id=ea.animal_id WHERE a.tag_id LIKE %s)", ([u.id for u in users], like),
        )
        cur.execute("DELETE FROM animal_journal WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM animals WHERE tag_id LIKE %s", (like,))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


def entry(**overrides):
    return {"entry_id": str(uuid4()), "occurred_at": "2026-11-10T12:00:00Z",
            "category": "clima", "body": "Llovió 30 mm", **overrides}


def test_entry_without_animal_and_with_three(world):
    client, users, prefix = world
    sola = entry()
    first = client.post("/v1/journal", json=sola)
    assert first.status_code == 200
    assert first.json()["animals"] == []
    assert first.json()["author"] == users[0].email
    # Reintento con el mismo entry_id: misma respuesta, sin duplicar.
    assert client.post("/v1/journal", json=sola).json() == first.json()

    tags = [f"{prefix}-c", f"{prefix}-a", f"{prefix}-b"]
    varias = entry(category="manejo", body="Desparasitación de tres", animals=tags)
    second = client.post("/v1/journal", json=varias)
    assert second.status_code == 200
    assert second.json()["animals"] == sorted(tags)
    assert client.post("/v1/journal", json={**varias, "animals": list(reversed(tags))}).json() \
        == second.json()
    # Mismo id con otro conjunto de animales es otra anotación.
    assert client.post("/v1/journal", json={**varias, "animals": tags[:2]}).status_code == 409

    ids = [e["entry_id"] for e in client.get("/v1/journal").json()["entries"]]
    assert ids.count(sola["entry_id"]) == 1
    assert ids.count(varias["entry_id"]) == 1
    # La entrada con varios animales aparece en la ficha de cada uno.
    for tag in tags:
        por_animal = client.get(f"/v1/animals/{tag}/journal").json()["entries"]
        assert [e["entry_id"] for e in por_animal] == [varias["entry_id"]]
        assert client.get("/v1/journal", params={"tag": tag}).json()["entries"][0]["entry_id"] \
            == varias["entry_id"]


def test_filters_and_pagination(world):
    client, _, prefix = world
    tag = f"{prefix}-filtro"
    for day in (8, 9, 10):
        assert client.post("/v1/journal", json=entry(
            occurred_at=f"2026-11-{day:02d}T12:00:00Z", animals=[tag],
        )).status_code == 200
    rango = {"tag": tag, "desde": "2026-11-09T00:00:00Z", "hasta": "2026-11-10T00:00:00Z"}
    assert [e["occurred_at"][:10] for e in client.get("/v1/journal", params=rango)
            .json()["entries"]] == ["2026-11-09"]
    first = client.get("/v1/journal", params={"tag": tag, "limit": 2}).json()
    second = client.get("/v1/journal", params={
        "tag": tag, "limit": 2, "cursor": first["next_cursor"]}).json()
    assert len(first["entries"]) == 2 and len(second["entries"]) == 1
    assert second["next_cursor"] is None
    assert client.get("/v1/journal", params={"desde": "2026-11-09T00:00:00"}).status_code == 400
    assert client.get("/v1/journal", params={"cursor": "bad"}).status_code == 400


@pytest.mark.parametrize("invalid", [
    {"category": "otra"}, {"body": " "}, {"animals": [""]}, {"animals": ["x" * 65]},
    {"occurred_at": "2026-11-10T12:00:00"},
])
def test_validation(world, invalid):
    client, _, _ = world
    assert client.post("/v1/journal", json=entry(**invalid)).status_code == 422


def test_new_categories_on_animal_route(world):
    client, _, prefix = world
    for category in ("clima", "insumos", "equipo", "general"):
        response = client.post(f"/v1/animals/{prefix}-cat/journal", json=entry(category=category))
        assert response.status_code == 200
        assert response.json()["animals"] == [f"{prefix}-cat"]


def test_organization_isolation(world):
    from fierro_api import main

    client, users, prefix = world
    tag = f"{prefix}-aislado"
    payload = entry(animals=[tag], body="Nota de Los Encinos")
    assert client.post("/v1/journal?org=valle-verde", json=payload).status_code == 200
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    # ?org= de otra organización se ignora para usuarios normales.
    vistas = client.get("/v1/journal?org=los-encinos").json()["entries"]
    assert payload["entry_id"] not in {e["entry_id"] for e in vistas}
    assert client.get("/v1/journal", params={"tag": tag}).json()["entries"] == []
    assert client.get(f"/v1/animals/{tag}/journal").json()["entries"] == []
    # El mismo entry_id desde otra organización no pisa ni revela la nota.
    conflicto = client.post("/v1/journal", json=payload)
    assert conflicto.status_code == 409
    assert "Los Encinos" not in conflicto.text

    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get("/v1/journal").status_code == 400
    assert client.post("/v1/journal", json=entry()).status_code == 400
    assert payload["entry_id"] in {
        e["entry_id"] for e in client.get("/v1/journal?org=los-encinos&limit=100")
        .json()["entries"]
    }


def test_migration_copies_journal_and_notes_once(world):
    """La migración conserva entry_id, autor y fechas, y es idempotente."""
    import psycopg

    _, users, prefix = world
    sql = MIGRACION.read_text(encoding="utf-8")
    viejo = uuid4()
    occurred = datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)
    created = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO animals(org_id, tag_id, notes) VALUES (%s,%s,%s), (%s,%s,NULL) "
            "RETURNING id",
            (users[0].org_id, f"{prefix}-vieja", "Cojea de la pata trasera",
             users[0].org_id, f"{prefix}-sin-notas"),
        )
        animal_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO animal_journal(entry_id, animal_id, author_id, occurred_at, "
            "created_at, category, body) VALUES (%s,%s,%s,%s,%s,'salud','Vacuna aplicada')",
            (viejo, animal_id, users[0].id, occurred, created),
        )
        conn.commit()
        for _ in range(2):
            cur.execute(sql)
            conn.commit()
        cur.execute(
            "SELECT e.org_id, e.author_id, e.occurred_at, e.created_at, e.category, e.body, "
            "array_agg(ea.animal_id) FROM journal_entries e JOIN journal_entry_animals ea "
            "ON ea.entry_id=e.entry_id WHERE e.entry_id=%s GROUP BY e.entry_id", (viejo,),
        )
        assert cur.fetchone() == (users[0].org_id, users[0].id, occurred, created, "salud",
                                  "Vacuna aplicada", [animal_id])
        cur.execute(
            "SELECT e.entry_id, e.category, e.source, e.author_id, e.body "
            "FROM journal_entries e JOIN journal_entry_animals ea ON ea.entry_id=e.entry_id "
            "JOIN animals a ON a.id=ea.animal_id WHERE a.tag_id LIKE %s AND e.source='ficha'",
            (prefix + "%",),
        )
        notas = cur.fetchall()
    assert len(notas) == 1
    assert isinstance(notas[0][0], UUID)
    assert notas[0][1:] == ("general", "ficha", None, "Cojea de la pata trasera")


def test_notes_field_writes_journal_entries(world):
    import psycopg

    client, users, prefix = world
    tag = f"{prefix}-notas"
    ruta = f"/v1/animals/{tag}"
    guardada = client.put(ruta, json={"alias": "Pinta", "notes": "Brava en la manga"})
    assert guardada.status_code == 200
    assert guardada.json()["notes"] == "Brava en la manga"
    # La web reenvía la ficha completa al cambiar el alias: no duplica la nota.
    assert client.put(ruta, json={"alias": "La Pinta", "notes": "Brava en la manga"}) \
        .json()["notes"] == "Brava en la manga"
    assert client.put(ruta, json={"alias": "La Pinta", "notes": "Ya se calmó"}) \
        .json()["notes"] == "Ya se calmó"
    assert client.get(ruta).json()["notes"] == "Ya se calmó"
    entradas = client.get(ruta + "/journal").json()["entries"]
    assert [(e["category"], e["body"]) for e in entradas] == [
        ("general", "Ya se calmó"), ("general", "Brava en la manga"),
    ]
    assert all(e["author"] == users[0].email for e in entradas)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT notes FROM animals WHERE tag_id=%s", (tag,))
        assert cur.fetchone() == (None,)
