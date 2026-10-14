import os
from dataclasses import replace
from urllib.parse import parse_qs, urlparse
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
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, dsn=DSN, env="dev", smtp_host="", smtp_from=""),
    )
    email = f"waitlist-{uuid4().hex}@example.test"
    body = {
        "name": "Prueba local",
        "email": email,
        "state": "Jalisco",
        "stations": 2,
        "consent": True,
    }
    client = TestClient(main.app)
    try:
        for bad in [{"consent": False}, {"stations": 0}, {"email": "bad"},
                    {"name": "   "}, {"website": "spam"}]:
            assert client.post("/v1/waitlist", json={**body, **bad}).status_code == 422
        assert client.get("/v1/admin/waitlist").status_code == 401
        created = client.post("/v1/waitlist", json=body)
        assert created.status_code == 202
        created_body = created.json()
        assert created_body["accepted"] is True
        assert created_body["confirmed"] is False
        assert created_body["email_sent"] is False
        assert created_body["confirmation_url"]
        duplicate = client.post("/v1/waitlist", json={**body, "email": email.upper(),
                                                    "name": "No sobrescribir"})
        assert duplicate.status_code == 202
        duplicate_body = duplicate.json()
        assert duplicate_body["confirmed"] is False
        token = parse_qs(urlparse(duplicate_body["confirmation_url"]).query)["token"][0]
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT name,state,stations,confirmation_token_hash,confirmed_at
                FROM waitlist
                WHERE email=%s
                """,
                (email,),
            )
            row = cur.fetchone()
            assert row[0] == "Prueba local"
            assert row[1] == "Jalisco"
            assert row[2] == 2
            assert row[3]
            assert row[4] is None
        confirmed = client.get(f"/v1/waitlist/confirm?token={token}")
        assert confirmed.status_code == 200
        assert "Correo confirmado" in confirmed.text
        already_confirmed = client.post("/v1/waitlist", json=body)
        assert already_confirmed.status_code == 202
        assert already_confirmed.json()["confirmed"] is True
        assert "confirmation_url" not in already_confirmed.json()
        user = AuthUser(1, "local@example.test", 1, "los-encinos", False)
        main.app.dependency_overrides[main.current_user] = lambda: user
        assert client.get("/v1/admin/waitlist").status_code == 403
        user = replace(user, is_superuser=True)
        result = client.get("/v1/admin/waitlist").json()
        entry = next(r for r in result["entries"] if r["email"] == email)
        assert entry["state"] == "Jalisco"
        assert entry["confirmed_at"]
        export = client.get("/v1/admin/waitlist.xlsx")
        assert export.status_code == 200
        assert export.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    finally:
        main.app.dependency_overrides.pop(main.current_user, None)
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM waitlist WHERE email=%s", (email,))
