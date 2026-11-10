"""Pruebas del rancho demo del asistente (scripts/seed_demo_hato.py).

Lo que importa no es que el script corra, sino que la historia que promete
sea la que el asistente encuentra: si una herramienta de `hato.py` deja de
ver al enfermo o al que no se pesa, la demo en vivo falla frente a alguien.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fierro_api import hato

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "seed_demo_hato.py"


@pytest.fixture(scope="module")
def demo():
    spec = importlib.util.spec_from_file_location("seed_demo_hato", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HASTA = date(2026, 10, 30)


def _ahora(hasta: date) -> datetime:
    return datetime(hasta.year, hasta.month, hasta.day, tzinfo=UTC) + timedelta(days=1, hours=18)


def _claves(datos: dict[str, Any], filas: list[dict[str, Any]]) -> set[str]:
    inverso = {tag: clave for clave, tag in datos["aretes"].items()}
    return {inverso[f["tag_id"]] for f in filas}


def test_misma_fecha_mismos_ids(demo):
    """Repetir la siembra no duplica: pesajes y bitacora con las mismas claves."""
    uno = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    otro = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    assert uno == otro
    ids = [r["event_id"] for r in uno["readings"]]
    assert len(ids) == len(set(ids))
    entradas = [e["entry_id"] for e in uno["bitacora"]]
    assert len(entradas) == len(set(entradas))


def test_los_pesajes_cuentan_para_el_asistente(demo):
    """Con source synthetic el asistente no veria nada: es la razon del script."""
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    assert not any(hato.es_prueba(r) for r in datos["readings"])


def test_ningun_pesaje_despues_de_la_ultima_jornada(demo):
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    limite = datetime(2026, 10, 31, 6, tzinfo=UTC)  # medianoche en Zacatecas
    assert all(datetime.fromisoformat(r["captured_at"]) < limite for r in datos["readings"])
    assert all(round(r["weight_kg"] * 2) == r["weight_kg"] * 2 for r in datos["readings"])


def test_resumen_dice_quien_queda_fuera(demo):
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    resumen = hato.resumen_hato(datos["readings"], datos["fichas"])
    assert resumen["animales_registrados"] == len(datos["aretes"])
    assert set(resumen["con_ficha_sin_pesaje"]) == {
        datos["aretes"]["nuevo"],
        datos["aretes"]["nuevo2"],
    }
    assert resumen["fuera_por_ultimo_pesaje_atipico"] == [datos["aretes"]["atipico"]]
    assert resumen["fuera_por_no_tener_pesaje_estable"] == [datos["aretes"]["nervioso"]]


@pytest.mark.parametrize("dias", range(0, 120, 3))
def test_la_historia_aguanta_cualquier_fecha(demo, dias):
    """El ruido cambia con --hasta; la historia no debe cambiar con el."""
    hasta = date(2026, 6, 1) + timedelta(days=dias)
    datos = demo.generar(seed=2026, hasta=hasta, semanas=14)
    revision = hato.animales_a_revisar(datos["readings"], ahora=_ahora(hasta))
    assert _claves(datos, revision["sin_ganar_peso"]) == {"enfermo", "coja"}
    assert _claves(datos, revision["ultimo_pesaje_atipico"]) == {"atipico"}
    assert _claves(datos, revision["sin_pesar"]) == {"potrero", "potrero2"}
    assert _claves(datos, [revision["ganancia_mas_baja"]]) == {"coja"}


def test_hay_animales_listos_para_venta(demo):
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    pesados = hato.buscar_animales(datos["readings"], datos["fichas"], peso_min_kg=450)
    assert pesados["total"] >= 2
    assert all(450 <= a["ultimo"]["weight_kg"] < 600 for a in pesados["animales"])


def test_ficha_con_atipico_viejo_y_bitacora(demo):
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    ficha = hato.ficha_animal(datos["readings"], datos["fichas"], datos["aretes"]["estrella"])
    assert ficha["alias"] == "El Güero"
    assert sum(p["atipico"] for p in ficha["pesajes_estables"]) == 1
    assert any(e["tag_id"] == datos["aretes"]["enfermo"] for e in datos["bitacora"])


class _ApiFalsa:
    def __init__(self, env: str, email: str = "admin@fierro.mx") -> None:
        self.base = "http://falsa"
        self.env = env
        self.email = email
        self.llamadas: list[tuple[str, str]] = []
        self.orgs: list[dict[str, Any]] = []

    def __call__(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        self.llamadas.append((metodo, ruta))
        if ruta == "/health":
            return {"env": self.env}
        if ruta == "/v1/auth/me":
            return {"email": self.email, "is_superuser": True}
        if ruta == "/v1/orgs":
            return {"orgs": self.orgs}
        raise AssertionError(f"no deberia llegar a {metodo} {ruta}")


def test_production_se_niega_sin_permiso(demo):
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    api = _ApiFalsa("production")
    with pytest.raises(SystemExit, match="production"):
        demo.sembrar(
            api, datos, org="demo", org_nombre="Demo", usuario=None, permitir_produccion=False
        )
    assert api.llamadas == [("GET", "/health")]


def test_no_te_quita_el_superusuario(demo):
    """create_user es upsert por correo: darte de alta en el rancho te degradaria."""
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14)
    with pytest.raises(SystemExit, match="superusuario"):
        demo.sembrar(
            _ApiFalsa("stage"), datos, org="demo", org_nombre="Demo",
            usuario="Admin@Fierro.mx", permitir_produccion=False,
        )


def test_no_mueve_una_estacion_de_otro_rancho(demo):
    """Mover una estacion arrastra sus pesajes: eso se detiene antes del PUT."""
    datos = demo.generar(seed=2026, hasta=HASTA, semanas=14, org="demo")
    api = _ApiFalsa("stage")
    ajena = {"device_id": demo.estaciones("demo")[0], "readings": 50}
    api.orgs = [
        {"slug": "demo", "ranches": [{"slug": "el-mezquite", "devices": []}]},
        {"slug": "otro", "ranches": [{"slug": "x", "devices": [ajena]}]},
    ]
    with pytest.raises(SystemExit, match="otro"):
        demo.sembrar(
            api, datos, org="demo", org_nombre="Demo", usuario=None, permitir_produccion=False
        )
    assert not any(metodo == "PUT" for metodo, _ in api.llamadas)
