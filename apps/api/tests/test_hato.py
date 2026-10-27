"""Paridad con animalTrend.test.mjs y cuentas del hato sin datos inventados."""

from datetime import UTC, datetime

import pytest
from fierro_api import hato


def row(event_id, captured_at, **extra):
    return {
        "event_id": event_id,
        "captured_at": captured_at,
        "tag_id": "A",
        "weight_kg": 400,
        "stable": True,
        "source": "serial",
        **extra,
    }


def series(weights, tag="A"):
    return [
        row(f"{tag}{i}", f"2026-09-{i + 1:02d}", weight_kg=weight, tag_id=tag)
        for i, weight in enumerate(weights)
    ]


def test_tendencia_excluye_pruebas_inestables_pesos_y_fechas_invalidos():
    readings = [
        row("real", "2026-09-01"),
        *[
            row(source, "2026-09-02", source=source)
            for source in ("mock", "synthetic", "proto-rc522", "proto-sim")
        ],
        row("unstable", "2026-09-03", stable=False),
        row("missing", "2026-09-04", weight_kg=None),
        row("date", "bad"),
        row("negative", "2026-09-04", weight_kg=-1),
        row("infinite", "2026-09-04", weight_kg=float("inf")),
        row("nan", "2026-09-04", weight_kg=float("nan")),
    ]
    assert [p["event_id"] for p in hato.puntos_tendencia(readings)] == ["real"]


def test_tendencia_ordena_por_captura_deduplica_y_conserva_mismo_dia():
    first = row("a", "2026-09-01")
    late = row("b", "2026-08-31", received_at="2026-09-05")
    points = hato.puntos_tendencia([first, late, first, row("c", "2026-09-01")])
    assert [p["event_id"] for p in points] == ["b", "a", "c"]


def test_ganancia_diaria_entre_primero_y_ultimo():
    assert hato.ganancia_diaria(hato.puntos_tendencia([row("a", "2026-09-01")])) is None
    points = hato.puntos_tendencia([
        row("a", "2026-09-01T00:00:00Z"),
        row("b", "2026-09-11T00:00:00Z", weight_kg=412),
    ])
    assert hato.ganancia_diaria(points) == pytest.approx(1.2)
    same_day = hato.puntos_tendencia([
        row("a", "2026-09-01T08:00:00Z"),
        row("b", "2026-09-01T12:00:00Z", weight_kg=401),
    ])
    assert hato.ganancia_diaria(same_day) is None


def test_atipicos_senala_p3_sin_borrar_pesajes():
    points = hato.puntos_tendencia(series([400, 405, 410, 480, 420, 425, 430], "p"))
    assert hato.ids_atipicos(points) == {"p3"}
    assert len(points) == 7
    assert hato.ids_atipicos(points[:3]) == set()


def test_crecimiento_rapido_no_es_atipico():
    points = hato.puntos_tendencia(series([200, 215, 230, 245, 260, 275]))
    assert hato.ids_atipicos(points) == set()


def test_resumen_suma_solo_ultimo_estable_y_explica_exclusiones():
    readings = [
        *series([400, 410], "A"),
        row("unstable", "2026-09-03", weight_kg=900, stable=False),
        row("test", "2026-09-04", weight_kg=999, source="mock"),
        *series([200, 205], "B"),
        *series([400, 405, 410, 480], "C"),
        row("D0", "2026-09-01", tag_id="D", stable=False),
    ]
    result = hato.resumen_hato(readings, [{"tag_id": "A"}, {"tag_id": "E"}], truncado=True)
    assert result["peso_total_kg"] == 615
    assert result["animales_en_el_total"] == 2
    assert result["animales_registrados"] == 5
    assert result["animales_pesados"] == 4
    assert result["con_ficha_sin_pesaje"] == ["E"]
    assert result["fuera_por_ultimo_pesaje_atipico"] == ["C"]
    assert result["fuera_por_no_tener_pesaje_estable"] == ["D"]
    assert result["pesaje_mas_viejo_en_el_total"] == "2026-09-02"
    assert result["pesajes_revisados"] == len(readings)
    assert result["lectura_incompleta"] is True


def test_rezagado_requiere_dos_intervalos_con_ganancia_hasta_un_kg():
    readings = [
        *series([400, 401, 402], "rezagado"),
        *series([400, 401], "un-intervalo"),
        *series([400, 401, 403], "recuperado"),
    ]
    result = hato.animales_a_revisar(readings, ahora=datetime(2026, 9, 4, tzinfo=UTC))
    assert [a["tag_id"] for a in result["sin_ganar_peso"]] == ["rezagado"]
    assert result["sin_ganar_peso"][0]["pesajes_sin_ganar"] == 2
    assert result["sin_ganar_peso"][0]["kg_en_esos_pesajes"] == 2


def test_revision_cuenta_solo_ultimo_pesaje_de_cada_dia():
    readings = [
        row("a", "2026-09-01T08:00:00Z", weight_kg=400),
        row("b", "2026-09-01T12:00:00Z", weight_kg=401),
        row("c", "2026-09-02T08:00:00Z", weight_kg=402),
    ]
    now = datetime(2026, 9, 4, tzinfo=UTC)
    assert hato.animales_a_revisar(readings, ahora=now)["sin_ganar_peso"] == []
    readings.append(row("d", "2026-09-03T08:00:00Z", weight_kg=403))
    result = hato.animales_a_revisar(readings, ahora=now)["sin_ganar_peso"]
    assert len(result) == 1
    assert result[0]["pesajes_sin_ganar"] == 2
    assert result[0]["kg_en_esos_pesajes"] == 2


def test_sin_pesar_exige_mas_de_treinta_dias():
    readings = [
        row("old", "2026-08-31", tag_id="viejo"),
        row("boundary", "2026-09-01", tag_id="limite"),
        row("new", "2026-09-02", tag_id="reciente"),
        row("mock", "2026-09-30", tag_id="viejo", source="mock"),
    ]
    result = hato.animales_a_revisar(readings, ahora=datetime(2026, 10, 1, tzinfo=UTC))
    assert result["sin_pesar"] == [{"tag_id": "viejo", "ultimo_pesaje": "2026-08-31"}]


@pytest.fixture
def search_data():
    return (
        [*series([400, 405, 410, 480], "A"), *series([200, 205], "B")],
        [{"tag_id": "A", "alias": "Luna"}, {"tag_id": "C", "alias": "Lucero"}],
    )


@pytest.mark.parametrize(("text", "tags"), [("lu", ["A", "C"]), ("b", ["B"]), ("x", [])])
def test_buscar_por_alias_o_arete_sin_distinguir_mayusculas(search_data, text, tags):
    result = hato.buscar_animales(*search_data, texto=text)
    assert [a["tag_id"] for a in result["animales"]] == tags
    assert result["total"] == len(tags)


def test_buscar_rango_inclusivo_usa_ultimo_limpio_y_excluye_sin_peso(search_data):
    result = hato.buscar_animales(*search_data, peso_min_kg=205, peso_max_kg=410)
    assert [a["tag_id"] for a in result["animales"]] == ["A", "B"]
    assert [a["ultimo"]["weight_kg"] for a in result["animales"]] == [410, 205]
    assert hato.buscar_animales(*search_data, peso_min_kg=411)["animales"] == []
    assert hato.buscar_animales(*search_data, peso_max_kg=204)["animales"] == []


def test_buscar_limita_resultados_conservando_total_y_fichas_sin_peso(search_data):
    result = hato.buscar_animales(*search_data, limite=2)
    assert [a["tag_id"] for a in result["animales"]] == ["A", "B"]
    assert result["total"] == 3
    assert result["recortado"] is True
    full = hato.buscar_animales(*search_data)
    assert full["recortado"] is False
    assert full["animales"][-1] == {"tag_id": "C", "alias": "Lucero", "ultimo": None}
