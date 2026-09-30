import os
from dataclasses import replace
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="PostgreSQL local requerido")


def test_waitlist_persistence_permissions_and_validation(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser
    from fierro_api.migrate import apply_migrations

    apply_migrations(DSN)
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    email = f"waitlist-{uuid4().hex}@example.test"
    body = {"name": "Prueba local", "email": email, "stations": 2, "consent": True}
    client = TestClient(main.app)
    try:
        for bad in [{"consent": False}, {"stations": 0}, {"email": "bad"},
                    {"name": "   "}, {"website": "spam"}]:
            assert client.post("/v1/waitlist", json={**body, **bad}).status_code == 422
        assert client.get("/v1/admin/waitlist").status_code == 401
        assert client.post("/v1/waitlist", json=body).status_code == 202
        assert client.post("/v1/waitlist", json={**body, "email": email.upper(),
                                               "name": "No sobrescribir"}).status_code == 202
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("SELECT name,stations FROM waitlist WHERE email=%s", (email,))
            assert cur.fetchall() == [("Prueba local", 2)]
        user = AuthUser(1, "local@example.test", 1, "los-encinos", False)
        main.app.dependency_overrides[main.current_user] = lambda: user
        assert client.get("/v1/admin/waitlist").status_code == 403
        user = replace(user, is_superuser=True)
        result = client.get("/v1/admin/waitlist").json()
        assert any(r["email"] == email for r in result["entries"])
    finally:
        main.app.dependency_overrides.pop(main.current_user, None)
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM waitlist WHERE email=%s", (email,))
