"""Regresiones del registro de dinero sin una conexión a Postgres."""
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from fierro_api import dinero_store, main
from fierro_api.auth import AuthUser
from fierro_api.dinero_models import MovementIn


def test_animals_accept_database_order_different_from_python():
    cursor = Mock()
    cursor.fetchall.return_value = [{"id": 2, "tag_id": "a"}, {"id": 1, "tag_id": "Z"}]

    assert dinero_store._animals(cursor, 1, sorted(["a", "Z"])) == [2, 1]


def test_animals_report_missing_tags_even_with_same_row_count():
    cursor = Mock()
    cursor.fetchall.return_value = [{"id": 1, "tag_id": "Z"}, {"id": 1, "tag_id": "Z"}]

    with pytest.raises(ValueError, match="no está registrado.*: a$"):
        dinero_store._animals(cursor, 1, ["Z", "a"])


@pytest.fixture
def registration(monkeypatch):
    import psycopg

    cursor = MagicMock()
    cursor.fetchone.side_effect = [{"id": 1}, None]
    cursor.fetchall.side_effect = [[{"id": 7, "tag_id": "MX-1"}], []]
    connect = MagicMock()
    connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(psycopg, "connect", connect)
    inserted = Mock(side_effect=lambda cur, data, org_id, author_id, animal_ids: {
        **data, "author_id": author_id, "author": "test@example.test",
        "status": "confirmado", "estado": "confirmado", "voids_movement_id": None,
        "created_at": datetime.now(UTC),
    })
    monkeypatch.setattr(dinero_store, "_insert", inserted)
    monkeypatch.setattr(main, "_require_postgres", lambda: "test-only")
    user = AuthUser(1, "test@example.test", 1, "own-org", False)
    main.app.dependency_overrides[main.current_user] = lambda: user
    yield TestClient(main.app), cursor, inserted
    main.app.dependency_overrides.pop(main.current_user, None)


@pytest.mark.parametrize(("previo", "kind", "day", "message"), [
    ("compra", "compra", "2026-11-02", "ya tiene una compra vigente"),
    ("compra", "venta", "2026-10-31", "anterior a la compra"),
    ("venta", "venta", "2026-11-02", "ya tiene una venta vigente"),
    ("venta", "compra", "2026-11-02", "posterior a la venta"),
])
def test_existing_purchase_conflicts_return_409_without_insert(
    registration, previo, kind, day, message,
):
    client, cursor, inserted = registration
    cursor.fetchall.side_effect = [
        [{"id": 7, "tag_id": "MX-1"}], [{"kind": previo, "occurred_on": date(2026, 11, 1)}],
    ]
    response = client.post("/v1/dinero/movimientos", json={
        "movement_id": str(uuid4()), "kind": kind, "amount_mxn": "100",
        "occurred_on": day, "scope": "animales", "animals": ["MX-1"],
    })

    assert response.status_code == 409, response.text
    assert message in response.json()["detail"]
    inserted.assert_not_called()


@pytest.mark.parametrize("day", ["2026-11-01", "2026-11-02"])
def test_sale_on_or_after_purchase_is_allowed(registration, day):
    client, cursor, inserted = registration
    cursor.fetchall.side_effect = [
        [{"id": 7, "tag_id": "MX-1"}], [{"kind": "compra", "occurred_on": date(2026, 11, 1)}],
    ]
    response = client.post("/v1/dinero/movimientos", json={
        "movement_id": str(uuid4()), "kind": "venta", "amount_mxn": "100",
        "occurred_on": day, "scope": "animales", "animals": ["MX-1"],
    })

    assert response.status_code == 200, response.text
    inserted.assert_called_once()


@pytest.mark.parametrize("kind", ["compra", "venta"])
def test_registration_without_current_purchase_is_allowed(registration, kind):
    client, _, inserted = registration
    response = client.post("/v1/dinero/movimientos", json={
        "movement_id": str(uuid4()), "kind": kind, "amount_mxn": "100",
        "occurred_on": "2026-11-01", "scope": "animales", "animals": ["MX-1"],
    })

    assert response.status_code == 200, response.text
    inserted.assert_called_once()


def test_retry_compares_animal_sets(registration):
    _, cursor, inserted = registration
    movement = MovementIn(movement_id=uuid4(), kind="gasto", category="alimento",
                          amount_mxn="100", occurred_on="2026-11-01", scope="animales",
                          animals=["a", "Z"])
    existing = {**movement.model_dump(), "org_id": 1, "author_id": 1,
                "voids_movement_id": None, "animals": ["a", "Z"]}
    cursor.fetchone.side_effect = [{"id": 1}, existing]

    result = dinero_store.add("test-only", org="own-org", author_id=1, movement=movement)

    assert result["movement_id"] == movement.movement_id
    inserted.assert_not_called()
