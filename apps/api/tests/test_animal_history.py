"""Contrato del historial: organización obligatoria y paginación validada."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from fierro_api import main
from fierro_api.auth import AuthUser


@pytest.fixture
def history(monkeypatch):
    store = Mock()
    store.list_readings.return_value = []
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "_require_postgres", lambda: "test-only")
    user = AuthUser(1, "normal@example.test", 1, "own-org", False)
    main.app.dependency_overrides[main.current_user] = lambda: user
    yield TestClient(main.app), store
    main.app.dependency_overrides.pop(main.current_user, None)


def test_normal_user_cannot_select_another_organization(history):
    client, store = history
    response = client.get("/v1/animals/same-tag/readings?org=other-org")
    assert response.status_code == 200
    assert store.list_readings.call_args.kwargs["org_slug"] == "own-org"
    assert store.list_readings.call_args.kwargs["tag_id"] == "same-tag"


def test_superuser_must_select_organization(history):
    client, store = history
    main.app.dependency_overrides[main.current_user] = lambda: AuthUser(
        2, "admin@example.test", None, None, True
    )
    assert client.get("/v1/animals/same-tag/readings").status_code == 400
    store.list_readings.assert_not_called()
    assert client.get("/v1/animals/same-tag/readings?org=chosen").status_code == 200
    assert store.list_readings.call_args.kwargs["org_slug"] == "chosen"


def test_history_validates_and_passes_cursor(history):
    client, store = history
    store.list_readings.return_value = [{
        "event_id": "evt-1", "captured_at": "2026-09-27T00:00:00+00:00",
    }]
    body = client.get("/v1/animals/tag/readings?limit=1").json()
    assert body["next_cursor"]
    response = client.get("/v1/animals/tag/readings", params={"cursor": body["next_cursor"]})
    assert response.status_code == 200
    assert store.list_readings.call_args.kwargs["cursor"] == (
        "2026-09-27T00:00:00+00:00", "evt-1"
    )
    assert client.get("/v1/animals/tag/readings?cursor=invalid").status_code == 400
    assert client.get("/v1/animals/tag/readings?limit=201").status_code == 422
