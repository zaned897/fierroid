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
    _limpiar_limites()
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


# ---------------------------------------------------------------------------
# #74: limite por cliente, concurrencia y paginacion
# ---------------------------------------------------------------------------


def _limpiar_limites():
    import psycopg
    from fierro_api.migrate import apply_migrations

    apply_migrations(DSN)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM waitlist_rate")


@pytest.fixture
def api(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main

    _limpiar_limites()
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN, edge_secret="s3creto"))
    correos: list[str] = []
    yield TestClient(main.app), correos
    main.app.dependency_overrides.pop(main.current_user, None)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM waitlist WHERE email = ANY(%s)", (correos,))
        cur.execute("DELETE FROM waitlist_rate")


def _alta(client, correos, headers):
    email = f"limite-{uuid4().hex}@example.test"
    correos.append(email)
    body = {"name": "Rancho", "email": email, "stations": 1, "consent": True}
    return client.post("/v1/waitlist", json=body, headers=headers)


def test_un_cliente_se_limita_y_otro_sigue_entrando(api):
    from fierro_api.waitlist import CLIENT_LIMIT

    client, correos = api
    abusivo = {"x-forwarded-for": "198.51.100.7"}
    for _ in range(CLIENT_LIMIT):
        assert _alta(client, correos, abusivo).status_code == 202
    bloqueado = _alta(client, correos, abusivo)
    assert bloqueado.status_code == 429
    assert bloqueado.headers["retry-after"] == "3600"

    assert _alta(client, correos, {"x-forwarded-for": "203.0.113.9"}).status_code == 202


def test_reintentar_un_correo_existente_tambien_gasta_cupo(api):
    from fierro_api.waitlist import CLIENT_LIMIT

    client, correos = api
    h = {"x-forwarded-for": "198.51.100.8"}
    email = f"repite-{uuid4().hex}@example.test"
    correos.append(email)
    body = {"name": "Rancho", "email": email, "stations": 1, "consent": True}
    codigos = [client.post("/v1/waitlist", json=body, headers=h).status_code
               for _ in range(CLIENT_LIMIT + 1)]
    assert codigos == [202] * CLIENT_LIMIT + [429]


def test_solo_la_ultima_ip_reenviada_cuenta(api):
    """Inventar entradas a la izquierda de X-Forwarded-For no cambia de cliente."""
    from fierro_api.waitlist import CLIENT_LIMIT

    client, correos = api
    for i in range(CLIENT_LIMIT):
        h = {"x-forwarded-for": f"10.0.0.{i}, 198.51.100.9"}
        assert _alta(client, correos, h).status_code == 202
    assert _alta(client, correos, {"x-forwarded-for": "10.9.9.9, 198.51.100.9"}).status_code == 429


def test_la_ip_firmada_por_vercel_solo_vale_con_el_secreto(api):
    from fierro_api.waitlist import CLIENT_LIMIT

    client, correos = api
    # Por Vercel: todos llegan desde la misma IP de salida, pero firmados.
    vercel = {"x-forwarded-for": "76.76.21.1"}
    for i in range(CLIENT_LIMIT + 2):
        h = {**vercel, "x-fierro-edge": "s3creto", "x-fierro-client-ip": f"192.0.2.{i}"}
        assert _alta(client, correos, h).status_code == 202

    # Sin el secreto el encabezado se ignora y cuenta la IP que se conecto.
    falso = {"x-forwarded-for": "198.51.100.10", "x-fierro-edge": "adivinado"}
    codigos = [
        _alta(client, correos, {**falso, "x-fierro-client-ip": f"192.0.2.{100 + i}"}).status_code
        for i in range(CLIENT_LIMIT + 1)
    ]
    assert codigos[-1] == 429


def test_la_ip_no_se_guarda_en_claro(api):
    import psycopg

    client, correos = api
    _alta(client, correos, {"x-forwarded-for": "198.51.100.11"})
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT client FROM waitlist_rate")
        assert all("198.51" not in r[0] for r in cur.fetchall())


def test_reintentos_concurrentes_del_mismo_correo_crean_una_fila(api):
    from concurrent.futures import ThreadPoolExecutor

    import psycopg
    from fierro_api import waitlist

    _, correos = api
    email = f"concurrente-{uuid4().hex}@example.test"
    correos.append(email)

    def alta(i):
        waitlist.register(DSN, name=f"Intento {i}", email=email, stations=1, client=f"c{i}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(alta, range(16)))
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM waitlist WHERE email=%s", (email,))
        assert cur.fetchone()[0] == 1


def test_la_paginacion_no_repite_ni_omite(api):
    from fierro_api import main, waitlist
    from fierro_api.auth import AuthUser

    client, correos = api
    for i in range(23):
        email = f"pagina-{i:02d}-{uuid4().hex}@example.test"
        correos.append(email)
        waitlist.register(DSN, name="Rancho", email=email, stations=1)

    main.app.dependency_overrides[main.current_user] = lambda: AuthUser(
        1, "su@example.test", None, None, True)
    vistos: list[int] = []
    cursor = None
    while True:
        url = "/v1/admin/waitlist?limit=10" + (f"&before={cursor}" if cursor else "")
        body = client.get(url).json()
        vistos += [e["id"] for e in body["entries"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(vistos) == len(set(vistos))
    assert vistos == sorted(vistos, reverse=True)
    emails = set()
    for i in range(0, len(vistos), 100):
        emails |= {e["email"] for e in client.get(
            f"/v1/admin/waitlist?limit=100&before={vistos[i] + 1}").json()["entries"]}
    assert set(correos) <= emails


def test_sin_secreto_no_hay_limite_por_cliente(api, monkeypatch):
    """Sin secreto, todo Vercel compartiria una IP: el limite bloquearia a todos."""
    from fierro_api import main
    from fierro_api.waitlist import CLIENT_LIMIT

    client, correos = api
    monkeypatch.setattr(main, "settings", replace(main.settings, edge_secret=""))
    vercel = {"x-forwarded-for": "76.76.21.1"}
    for _ in range(CLIENT_LIMIT + 2):
        assert _alta(client, correos, vercel).status_code == 202
