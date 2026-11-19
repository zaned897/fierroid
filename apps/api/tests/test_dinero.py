"""Dinero real en Postgres, alcance, reintentos y anulaciones append-only."""
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from fierro_api.dinero_models import MovementIn

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
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    prefix = "money" + uuid4().hex[:10]
    emails = [f"{prefix}-{index}@example.test" for index in range(2)]
    for email, org in zip(emails, ["los-encinos", "valle-verde"], strict=True):
        create_user(DSN, email=email, org_slug=org)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
                    "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,))
        users = [AuthUser(*row, False) for row in cur.fetchall()]
        for user in users:
            for suffix in ("a", "b"):
                cur.execute("INSERT INTO animals(org_id,tag_id) VALUES (%s,%s)",
                            (user.org_id, prefix + suffix))
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    with TestClient(main.app) as client:
        yield client, users, prefix
    main.app.dependency_overrides.pop(main.current_user, None)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        for condition in ["AND voids_movement_id IS NOT NULL", ""]:
            cur.execute("DELETE FROM money_movements WHERE author_id=ANY(%s) " + condition,
                        ([u.id for u in users],))
        cur.execute("DELETE FROM journal_entries WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM animals WHERE tag_id LIKE %s", (prefix + "%",))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


def movement(tag=None, **overrides):
    return {"movement_id": str(uuid4()), "kind": "compra", "amount_mxn": "12345.67",
            "occurred_on": "2026-11-01", "scope": "animales",
            "animals": [tag] if tag else [], **overrides}


def post(client, data):
    return client.post("/v1/dinero/movimientos", json=data)


def test_idempotent_exact_decimal_and_concurrent_retry(world):
    from fierro_api.dinero_store import add

    client, users, prefix = world
    data = movement(prefix + "a", weight_kg="381.25")
    first = post(client, data)
    assert first.status_code == 200, first.text
    assert first.json()["amount_mxn"] == "12345.67"
    assert first.json()["author_id"] == users[0].id
    assert first.json()["estado"] == "confirmado"
    assert post(client, data).json() == first.json()
    assert post(client, {**data, "amount_mxn": "12345.68"}).status_code == 409
    assert post(client, {**data, "animals": [prefix + "b"]}).status_code == 409
    other = MovementIn(**movement(prefix + "a", kind="venta"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(executor.map(lambda _: add(DSN, org=users[0].org_slug,
                                               author_id=users[0].id, movement=other), range(2)))
    assert rows[0] == rows[1]
    ids = [row["movement_id"] for row in client.get("/v1/dinero/movimientos").json()["movements"]]
    assert ids.count(data["movement_id"]) == 1
    assert ids.count(str(other.movement_id)) == 1


@pytest.mark.parametrize("invalid", [
    {"animals": []}, {"animals": ["{a}", "{b}"]},
    {"amount_mxn": "0"}, {"amount_mxn": "-1"}, {"amount_mxn": "1.001"},
    {"amount_mxn": "10000000000"}, {"amount_mxn": "NaN"}, {"amount_mxn": "Infinity"},
    {"category": "alimento"}, {"precio_kg_mxn": "50"}, {"scope": "hato"},
    {"status": "confirmado"}, {"author_id": 999}, {"org_id": 999},
    {"period_start": "2026-11-02", "period_end": "2026-11-01"},
])
def test_invalid_purchase(world, invalid):
    client, _, prefix = world
    if "animals" in invalid:
        invalid = {**invalid, "animals": [v.format(a=prefix + "a", b=prefix + "b")
                                         for v in invalid["animals"]]}
    assert post(client, movement(prefix + "a", **invalid)).status_code == 422


def test_expense_validation_scopes_source_and_dates(world):
    from fierro_api import main

    client, users, prefix = world
    expense = movement(kind="gasto", scope="hato", category="alimento")
    assert post(client, {**expense, "category": None}).status_code == 422
    assert post(client, {**expense, "weight_kg": "20"}).status_code == 422
    assert post(client, {**expense, "period_start": "2026-11-01"}).status_code == 422
    note = str(uuid4())
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    assert client.post("/v1/journal", json={"entry_id": note, "category": "insumos",
                       "body": "Compra de alimento", "occurred_at": "2026-11-01T12:00:00Z"}) \
        .status_code == 200
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    assert post(client, {**expense, "source_entry_id": note}).status_code == 422
    assert post(client, {**expense, "source_entry_id": str(uuid4())}).status_code == 422
    for scope, fields in [("hato", {}), ("corral", {"corral": " Norte "}),
                          ("animales", {"animals": [prefix + "b", prefix + "a"]})]:
        data = {**expense, "movement_id": str(uuid4()), "scope": scope, **fields,
                "period_start": "2026-11-01", "period_end": "2026-11-01"}
        response = post(client, data)
        assert response.status_code == 200, response.text
        if scope == "corral":
            assert response.json()["corral"] == "Norte"
    assert post(client, {**expense, "scope": "corral"}).status_code == 422
    assert post(client, {**expense, "corral": "Norte"}).status_code == 422
    assert post(client, movement(prefix + "desconocido")).status_code == 422


def test_append_only_void_retry_filters_and_double_void(world):
    import psycopg

    client, users, prefix = world
    data = movement(prefix + "a")
    first = post(client, data).json()
    operation = {"movement_id": str(uuid4()), "occurred_on": "2026-11-02"}
    path = f"/v1/dinero/movimientos/{data['movement_id']}/anular"
    result = client.post(path, json=operation)
    assert result.status_code == 200, result.text
    assert result.json()["voids_movement_id"] == data["movement_id"]
    assert result.json()["estado"] == "anulacion"
    assert client.post(path, json=operation).json() == result.json()
    assert client.post(path, json={**operation, "movement_id": str(uuid4())}).status_code == 409
    assert client.post(path, json={**operation, "occurred_on": "2026-11-03"}).status_code == 409
    assert client.post(f"/v1/dinero/movimientos/{operation['movement_id']}/anular",
                       json={**operation, "movement_id": str(uuid4())}).status_code == 409
    assert data["movement_id"] not in {row["movement_id"] for row in
        client.get("/v1/dinero/movimientos?estado=vigente").json()["movements"]}
    all_rows = client.get("/v1/dinero/movimientos?estado=todos").json()["movements"]
    original = next(row for row in all_rows if row["movement_id"] == data["movement_id"])
    assert original == {**first, "estado": "anulado"}
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT status,count(*) OVER() FROM money_movements WHERE author_id=%s",
                    (users[0].id,))
        assert cur.fetchall() == [("confirmado", 2), ("confirmado", 2)]
    assert post(client, data).json()["estado"] == "anulado"


def test_concurrent_double_void_has_single_reversal(world):
    from fierro_api.dinero_models import VoidIn
    from fierro_api.dinero_store import MovementConflict, void

    client, users, prefix = world
    data = movement(prefix + "a")
    assert post(client, data).status_code == 200

    def attempt(_):
        try:
            return void(DSN, org=users[0].org_slug, author_id=users[0].id,
                        original_id=UUID(data["movement_id"]),
                        operation=VoidIn(movement_id=uuid4(), occurred_on="2026-11-02"))
        except MovementConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, range(2)))
    assert sum(row is not None for row in results) == 1


def test_filters_and_price_current_history(world):
    client, _, prefix = world
    for day in (1, 2, 3):
        assert post(client, movement(prefix + "a", occurred_on=f"2026-11-0{day}")) \
            .status_code == 200
    filtered = client.get("/v1/dinero/movimientos", params={"animal": prefix + "a",
                          "desde": "2026-11-02", "hasta": "2026-11-02", "kind": "compra"})
    assert [row["occurred_on"] for row in filtered.json()["movements"]] == ["2026-11-02"]
    assert client.get("/v1/dinero/movimientos?desde=2026-11-03&hasta=2026-11-01") \
        .status_code == 422
    assert client.get("/v1/dinero/movimientos?estado=otro").status_code == 422
    empty = client.get("/v1/dinero/precio").json()
    assert empty == {"current": None, "history": []}
    ids = []
    for day, amount in [("2026-11-01", "50"), ("2026-11-02", "51.25"),
                        ("2099-01-01", "99")]:
        data = movement(kind="precio_mercado", scope="hato", amount_mxn=None,
                        precio_kg_mxn=amount, occurred_on=day)
        ids.append(data["movement_id"])
        assert post(client, data).status_code == 200
    assert post(client, movement(prefix + "a", kind="precio_mercado", scope="hato",
                                 amount_mxn=None, precio_kg_mxn="50")).status_code == 422
    price = client.get("/v1/dinero/precio").json()
    assert price["current"]["movement_id"] == ids[1]
    assert len(price["history"]) == 3
    assert price["current"]["precio_kg_mxn"] == "51.25"
    assert client.post(f"/v1/dinero/movimientos/{ids[1]}/anular", json={
        "movement_id": str(uuid4()), "occurred_on": "2026-11-03"}).status_code == 200
    assert client.get("/v1/dinero/precio").json()["current"]["movement_id"] == ids[0]


def test_organization_isolation_and_superuser_scope(world):
    from fierro_api import main

    client, users, prefix = world
    data = movement(prefix + "a")
    first = client.post("/v1/dinero/movimientos?org=valle-verde", json=data)
    assert first.status_code == 200
    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    assert client.get("/v1/dinero/movimientos?org=los-encinos").json()["movements"] == []
    assert post(client, data).status_code == 409
    assert client.post(f"/v1/dinero/movimientos/{data['movement_id']}/anular?org=los-encinos",
                       json={"movement_id": str(uuid4()), "occurred_on": "2026-11-02"}) \
        .status_code == 404
    own = {**data, "movement_id": str(uuid4())}
    assert client.post("/v1/dinero/movimientos?org=los-encinos", json=own).status_code == 200
    main.app.dependency_overrides[main.current_user] = lambda: replace(users[0], is_superuser=True)
    assert client.get("/v1/dinero/movimientos").status_code == 400
    assert client.get("/v1/dinero/precio").status_code == 400
    assert post(client, movement(prefix + "a")).status_code == 400
    assert client.post(f"/v1/dinero/movimientos/{data['movement_id']}/anular", json={
        "movement_id": str(uuid4()), "occurred_on": "2026-11-02"}).status_code == 400
    rows = client.get("/v1/dinero/movimientos?org=los-encinos").json()["movements"]
    assert data["movement_id"] in {row["movement_id"] for row in rows}
    assert own["movement_id"] not in {row["movement_id"] for row in rows}


def test_database_rejects_bad_cardinality(world):
    import psycopg

    _, users, _ = world
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
            cur.execute("INSERT INTO money_movements(movement_id,org_id,author_id,kind,"
                        "amount_mxn,occurred_on,scope) VALUES (%s,%s,%s,'compra',10,"
                        "'2026-11-01','animales')", (uuid4(), users[0].org_id, users[0].id))
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_database_rejects_nonfinite_money(world):
    import psycopg

    _, users, _ = world
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
            cur.execute("INSERT INTO money_movements(movement_id,org_id,author_id,kind,"
                        "category,amount_mxn,occurred_on,scope) VALUES "
                        "(%s,%s,%s,'gasto','otros','NaN','2026-11-01','hato')",
                        (uuid4(), users[0].org_id, users[0].id))


def test_migration_idempotent_and_composite_foreign_keys(world):
    import psycopg
    from fierro_api.migrate import MIGRATIONS_DIR

    client, users, prefix = world
    original = movement(prefix + "a")
    assert post(client, original).status_code == 200
    sql = (MIGRATIONS_DIR / "014_dinero.sql").read_text(encoding="utf-8")
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        for _ in range(2):
            cur.execute(sql)
            conn.commit()
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            cur.execute("SELECT id FROM animals WHERE org_id=%s AND tag_id=%s",
                        (users[1].org_id, prefix + "b"))
            other_animal = cur.fetchone()[0]
            cur.execute("INSERT INTO money_movement_animals(movement_id,animal_id,org_id) "
                        "VALUES (%s,%s,%s)",
                        (original["movement_id"], other_animal, users[0].org_id))
        foreign_note = uuid4()
        cur.execute("INSERT INTO journal_entries(entry_id,org_id,author_id,occurred_at,"
                    "category,body) VALUES (%s,%s,%s,now(),'insumos','Nota de otra org')",
                    (foreign_note, users[1].org_id, users[1].id))
        conn.commit()
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            cur.execute("INSERT INTO money_movements(movement_id,org_id,author_id,kind,"
                        "category,amount_mxn,occurred_on,scope,source_entry_id) VALUES "
                        "(%s,%s,%s,'gasto','otros',10,'2026-11-01','hato',%s)",
                        (uuid4(), users[0].org_id, users[0].id, foreign_note))
    assert post(client, original).status_code == 200
