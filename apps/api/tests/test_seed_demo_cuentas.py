"""El generador de ranchos demo por cuenta (scripts/seed_demo_cuentas.py).

Lo que importa: que sea determinista (repetir no duplica), que todo lo que
genera pase las reglas reales de la API (#173), y que las cifras parezcan de
un rancho: ganancias de peso, precios y costos dentro de lo que se ve en campo.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fierro_api import dinero, hato
from fierro_api.dinero_models import MovementIn

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
HASTA = date(2026, 10, 30)
DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()


@pytest.fixture(scope="module")
def gen():
    sys.path.insert(0, str(SCRIPTS))
    ruta = SCRIPTS / "seed_demo_cuentas.py"
    spec = importlib.util.spec_from_file_location("seed_demo_cuentas", ruta)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _datos(gen, demo: str = "los-encinos-demo") -> dict[str, Any]:
    return gen.generar_cuenta(seed=2026, hasta=HASTA, semanas=14, demo=demo)


def test_determinista_y_sin_ids_repetidos(gen):
    uno, otro = _datos(gen), _datos(gen)
    assert uno == otro
    for lista, campo in (("readings", "event_id"), ("movimientos", "movement_id"),
                         ("diario", "entry_id")):
        ids = [x[campo] for x in uno[lista]]
        assert len(ids) == len(set(ids)), lista


def test_cuentas_distintas_no_comparten_ids(gen):
    a, b = _datos(gen, "a-demo"), _datos(gen, "b-demo")
    assert not {r["event_id"] for r in a["readings"]} & {r["event_id"] for r in b["readings"]}
    assert not {m["movement_id"] for m in a["movimientos"]} & {
        m["movement_id"] for m in b["movimientos"]}


def test_todo_el_dinero_pasa_las_reglas_de_la_api(gen):
    datos = _datos(gen)
    registrados = {f["tag_id"] for f in datos["fichas"]}
    for mov in datos["movimientos"]:
        MovementIn.model_validate({k: v for k, v in mov.items() if v is not None})
        assert set(mov.get("animals") or []) <= registrados
    tipos = {m["kind"] for m in datos["movimientos"]}
    assert tipos == {"compra", "venta", "gasto", "precio_mercado"}
    categorias = {m["category"] for m in datos["movimientos"] if m["kind"] == "gasto"}
    assert categorias == {"alimento", "sanidad", "mano_obra", "instalaciones", "transporte",
                          "otros"}


def test_una_compra_por_animal_y_venta_despues(gen):
    datos = _datos(gen)
    compras = {m["animals"][0]: m for m in datos["movimientos"] if m["kind"] == "compra"}
    ventas = [m for m in datos["movimientos"] if m["kind"] == "venta"]
    assert set(compras) == {f["tag_id"] for f in datos["fichas"]}
    assert len(ventas) == 4
    for venta in ventas:
        assert venta["occurred_on"] > compras[venta["animals"][0]]["occurred_on"]
        # Nadie se pesa despues de vendido.
        tag = venta["animals"][0]
        assert all(r["captured_at"][:10] < venta["occurred_on"]
                   for r in datos["readings"] if r["tag_id"] == tag)


def test_cifras_de_rancho(gen):
    datos = _datos(gen)
    for m in datos["movimientos"]:
        if m["kind"] in ("compra", "venta"):
            precio = Decimal(m["amount_mxn"]) / Decimal(m["weight_kg"])
            assert Decimal(50) < precio < Decimal(76), m
            assert Decimal(170) <= Decimal(m["weight_kg"]) <= Decimal(620), m
        if m["kind"] == "precio_mercado":
            assert Decimal(48) <= Decimal(m["precio_kg_mxn"]) <= Decimal(62)

    # Ganancia diaria de los que crecen normal: engorda ~0.8-1.3, recria ~0.5-0.7.
    for clave, tag in datos["aretes"].items():
        if not clave.startswith(("novillo-", "vaquilla-")):
            continue
        puntos = hato.puntos_tendencia(r for r in datos["readings"] if r["tag_id"] == tag)
        if len(puntos) < 2:
            continue
        dias = (puntos[-1]["_t"] - puntos[0]["_t"]).days
        ganancia = (puntos[-1]["weight_kg"] - puntos[0]["weight_kg"]) / dias
        limites = (0.7, 1.35) if clave.startswith("novillo") else (0.4, 0.8)
        assert limites[0] < ganancia < limites[1], (clave, ganancia)


def test_las_cuentas_de_174_salen_completas(gen):
    """Un novillo normal tiene valor, costo y ganancia: nada queda en None."""
    datos = _datos(gen)
    corral = {f["tag_id"]: {"corral": f["corral"]} for f in datos["fichas"]}
    movimientos = [{**m, "estado": "confirmado", "animals": m.get("animals") or [],
                    "amount_mxn": Decimal(m["amount_mxn"]) if m.get("amount_mxn") else None,
                    "precio_kg_mxn": Decimal(m["precio_kg_mxn"])
                    if m.get("precio_kg_mxn") else None,
                    "weight_kg": Decimal(m["weight_kg"]) if m.get("weight_kg") else None}
                   for m in datos["movimientos"]]
    tag = datos["aretes"]["pesado"]
    estado = dinero.estado_animal(tag, HASTA, datos["readings"], movimientos, corral)
    planos = [v for v in estado.values() if isinstance(v, dict) and "mxn" in v]
    assert planos and all(v["mxn"] is not None for v in planos), estado


# ---------------------------------------------------------------------------
# Contra la API real, con Postgres
# ---------------------------------------------------------------------------


class _ApiDePrueba:
    """Mismo contrato que `seed_demo_hato.Api`, sobre TestClient."""

    base = "testclient"

    def __init__(self, client, headers, error):
        self.client, self.headers, self.error = client, headers, error

    def __call__(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        resp = self.client.request(metodo, ruta, json=cuerpo, headers=self.headers)
        if resp.status_code >= 400:
            raise self.error(resp.status_code, str(resp.json().get("detail")))
        return resp.json()


@pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")
def test_siembra_repite_y_purga_contra_la_api(gen, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module
    from fierro_api.admin import crear_org
    from fierro_api.auth import create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.store_pg import PostgresReadingStore

    sufijo = uuid.uuid4().hex[:8]
    org, correo, su = f"cuenta-{sufijo}", f"u-{sufijo}@fierro.test", f"su-{sufijo}@fierro.test"
    apply_migrations(DSN)
    crear_org(DSN, slug=org, name="Rancho real")
    create_user(DSN, email=correo, password="clave-de-prueba", org_slug=org)
    create_user(DSN, email=su, password="clave-de-prueba", is_superuser=True)

    store = PostgresReadingStore(DSN)
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, dsn=DSN))
    monkeypatch.setattr(main_module, "store", store)
    try:
        client = TestClient(main_module.app)

        def entrar(c: str) -> dict[str, str]:
            r = client.post("/v1/auth/login", json={"email": c, "password": "clave-de-prueba"})
            return {"Authorization": f"Bearer {r.json()['api_key']}"}

        api = _ApiDePrueba(client, entrar(su), gen.ErrorApi)
        for _ in range(2):  # la segunda corrida no duplica nada
            gen.sembrar_cuenta(api, org, seed=2026, hasta=HASTA, semanas=14, rehacer=False)

        datos = _datos(gen, f"{org}-demo")
        usuario = entrar(correo)
        demo = client.get("/v1/auth/me", headers=usuario).json()["demo_org"]
        assert demo == f"{org}-demo"
        movs = client.get(f"/v1/dinero/movimientos?org={demo}&estado=todos", headers=usuario).json()
        assert len(movs["movements"]) == len(datos["movimientos"]) + len(datos["anulaciones"])
        animales = client.get(f"/v1/animals?org={demo}", headers=usuario).json()["animals"]
        assert len(animales) == len(datos["fichas"])
        # Su cuenta real sigue vacia.
        assert client.get("/v1/animals", headers=usuario).json()["animals"] == []
        assert client.get("/v1/dinero/movimientos", headers=usuario).json()["movements"] == []

        gen.sembrar_cuenta(api, org, seed=2026, hasta=date(2026, 11, 6), semanas=14,
                           rehacer=True)
        borrado = api("DELETE", f"/v1/orgs/{org}/demo")["borrado"]
        assert borrado["readings"] > 400 and borrado["money_movements"] > 50
    finally:
        store.close()
