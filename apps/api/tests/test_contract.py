"""El contrato de la API es un archivo versionado, no una consecuencia.

Sin esto, un agente puede agregar, renombrar o quitar un campo y nadie se
entera hasta que el front deja de funcionar. Con esto, cambiar la superficie de
la API obliga a actualizar el contrato en el mismo commit, donde se revisa.

Regenerar tras un cambio deliberado:

    python -m fierro_api.contract
"""

from __future__ import annotations

import json
from pathlib import Path

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contracts" / "openapi.json"


def _vivo() -> dict:
    from fierro_api.contract import build_spec

    return build_spec()


def _guardado() -> dict:
    return json.loads(CONTRATO.read_text(encoding="utf-8"))


def test_las_rutas_coinciden_con_el_contrato():
    vivas = set(_vivo()["paths"])
    guardadas = set(_guardado()["paths"])

    assert vivas == guardadas, (
        "La superficie de la API cambio sin actualizar el contrato.\n"
        f"  nuevas:      {sorted(vivas - guardadas)}\n"
        f"  eliminadas:  {sorted(guardadas - vivas)}\n"
        "Si el cambio es deliberado: python -m fierro_api.contract"
    )


def test_los_metodos_de_cada_ruta_coinciden():
    vivo, guardado = _vivo()["paths"], _guardado()["paths"]

    for ruta in sorted(set(vivo) & set(guardado)):
        assert set(vivo[ruta]) == set(guardado[ruta]), (
            f"Cambiaron los metodos de {ruta} sin actualizar el contrato"
        )


def test_los_esquemas_coinciden():
    """Un campo agregado o quitado en un modelo rompe al consumidor."""
    vivos = _vivo().get("components", {}).get("schemas", {})
    guardados = _guardado().get("components", {}).get("schemas", {})

    assert set(vivos) == set(guardados), "Se agrego o quito un modelo sin actualizar el contrato"

    for nombre in sorted(vivos):
        campos_vivos = set(vivos[nombre].get("properties", {}))
        campos_guardados = set(guardados[nombre].get("properties", {}))
        assert campos_vivos == campos_guardados, (
            f"Cambiaron los campos de {nombre}.\n"
            f"  nuevos:     {sorted(campos_vivos - campos_guardados)}\n"
            f"  eliminados: {sorted(campos_guardados - campos_vivos)}"
        )


def test_el_contrato_esta_ordenado_y_es_estable():
    """Ordenado por llave: si no, cada regeneracion produce un diff falso."""
    crudo = CONTRATO.read_text(encoding="utf-8")
    normalizado = json.dumps(json.loads(crudo), indent=2, ensure_ascii=False, sort_keys=True)
    assert crudo == normalizado + "\n"
