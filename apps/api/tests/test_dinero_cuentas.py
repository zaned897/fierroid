"""Cuentas de dinero de #174: funciones puras, una prueba por criterio de aceptación."""

from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest
from fierro_api import dinero, hato

D0 = date(2026, 9, 1)


def mov(mid, kind, dia=D0, **extra):
    base = {
        "movement_id": mid,
        "kind": kind,
        "occurred_on": dia,
        "estado": "confirmado",
        "scope": "animales" if kind in ("compra", "venta") else "hato",
        "animals": [],
        "corral": None,
        "category": "alimento" if kind == "gasto" else None,
        "period_start": None,
        "period_end": None,
        "created_at": "2026-09-01T00:00:00Z",
    }
    return {**base, **extra}


def gasto(mid, monto, dia=D0, **extra):
    return mov(mid, "gasto", dia, amount_mxn=Decimal(monto), **extra)


def precio(mid, valor, dia=D0, **extra):
    return mov(mid, "precio_mercado", dia, precio_kg_mxn=Decimal(valor), **extra)


def pesaje(eid, dia, kg, tag="A", **extra):
    return {
        "event_id": eid,
        "tag_id": tag,
        "captured_at": f"{dia.isoformat()}T08:00:00Z",
        "weight_kg": kg,
        "stable": True,
        "source": "serial",
        **extra,
    }


def hato_de(*tags, corral=None):
    return {tag: {"corral": corral} for tag in tags}


# --- ganancia_diaria_reciente ---------------------------------------------


def test_ganancia_reciente_usa_los_dos_ultimos_con_un_dia_de_diferencia():
    puntos = hato.puntos_tendencia(
        [
            pesaje("a", D0, 400),
            pesaje("b", D0 + timedelta(days=10), 420),
            pesaje("c", D0 + timedelta(days=12), 423),
            {**pesaje("d", D0 + timedelta(days=12), 424), "captured_at": "2026-09-13T20:00:00Z"},
        ]
    )
    r = dinero.ganancia_diaria_reciente(puntos)
    # d y c están a 12 horas; el anterior válido de d es b, 2.5 días antes.
    assert r["anterior"]["event_id"] == "b"
    assert r["ultimo"]["event_id"] == "d"
    assert r["kg_dia"] == Fraction(4) / Fraction(5, 2)


def test_ganancia_reciente_sin_dos_pesajes_en_dias_distintos_es_none():
    assert dinero.ganancia_diaria_reciente([]) is None
    mismo_dia = hato.puntos_tendencia(
        [
            pesaje("a", D0, 400),
            {**pesaje("b", D0, 401), "captured_at": "2026-09-01T20:00:00Z"},
        ]
    )
    assert dinero.ganancia_diaria_reciente(mismo_dia) is None


# --- repartir ---------------------------------------------------------------


def test_hato_por_periodo_entre_diez_y_venta_a_media_ruta():
    vacas = [f"V{i}" for i in range(10)]
    g = gasto("g", "3000", period_start=D0, period_end=D0 + timedelta(days=29))
    fin = D0 + timedelta(days=29)

    activos = dinero.activos_por_dia(hato_de(*vacas), [], D0, fin)
    r = dinero.repartir(g, activos)
    assert all(parte == 10 for dia in r["por_dia"].values() for parte in dia.values())
    assert sum(sum(d.values()) for d in r["por_dia"].values()) == 3000

    # V0 se vende el día 15: carga 14 días y las otras 9 cargan los 16 restantes.
    venta = mov("v", "venta", D0 + timedelta(days=14), animals=["V0"], amount_mxn=Decimal(1))
    activos = dinero.activos_por_dia(hato_de(*vacas), [venta], D0, fin)
    r = dinero.repartir(g, activos)
    v0 = sum(d.get("V0", 0) for d in r["por_dia"].values())
    v1 = sum(d.get("V1", 0) for d in r["por_dia"].values())
    assert v0 == 140
    assert v1 == 140 + Fraction(1600, 9)
    assert v0 + 9 * v1 == 3000
    assert r["sin_asignar"] == {}


def test_gasto_sin_periodo_cae_el_dia_del_gasto_y_entre_nombrados():
    activos = dinero.activos_por_dia(hato_de("A", "B", "C"), [], D0, D0)
    r = dinero.repartir(gasto("g", "90", scope="animales", animals=["A", "B"]), activos)
    assert r["por_dia"] == {D0: {"A": 45, "B": 45}}


def test_nombrado_vendido_pasa_sus_dias_al_otro_nombrado():
    venta = mov("v", "venta", D0 + timedelta(days=1), animals=["A"], amount_mxn=Decimal(1))
    activos = dinero.activos_por_dia(hato_de("A", "B", "C"), [venta], D0, D0 + timedelta(days=1))
    g = gasto(
        "g",
        "100",
        scope="animales",
        animals=["A", "B"],
        period_start=D0,
        period_end=D0 + timedelta(days=1),
    )
    r = dinero.repartir(g, activos)
    assert r["por_dia"] == {D0: {"A": 25, "B": 25}, D0 + timedelta(days=1): {"B": 50}}


def test_corral_reparte_solo_entre_su_corral_y_lo_huerfano_queda_a_la_vista():
    h = {"A": {"corral": "2"}, "B": {"corral": "2"}, "C": {"corral": "1"}}
    activos = dinero.activos_por_dia(h, [], D0, D0)
    r = dinero.repartir(gasto("g", "50", scope="corral", corral="2"), activos)
    assert r["por_dia"] == {D0: {"A": 25, "B": 25}}
    vacio = dinero.repartir(gasto("g", "50", scope="corral", corral="9"), activos)
    assert vacio["por_dia"] == {} and vacio["sin_asignar"] == {D0: 50}


def test_compra_marca_alta_y_repartir_solo_acepta_gastos():
    compra = mov("c", "compra", D0 + timedelta(days=1), animals=["N"], amount_mxn=Decimal(1))
    activos = dinero.activos_por_dia(hato_de("A"), [compra], D0, D0 + timedelta(days=1))
    assert set(activos[D0]) == {"A"}
    assert set(activos[D0 + timedelta(days=1)]) == {"A", "N"}
    with pytest.raises(ValueError):
        dinero.repartir(compra, activos)


def test_dos_ventas_confirmadas_son_error_no_se_adivina():
    ventas = [mov(f"v{i}", "venta", animals=["A"], amount_mxn=Decimal(1)) for i in range(2)]
    with pytest.raises(ValueError):
        dinero.activos_por_dia(hato_de("A"), ventas, D0, D0)


# --- estado_animal ----------------------------------------------------------


def engorda(kg_dia, dias=10, tag="A", inicio=400.0):
    return [
        pesaje(f"{tag}{i}", D0 + timedelta(days=i * dias), inicio + kg_dia * dias * i, tag=tag)
        for i in range(2)
    ]


def costo_diario(monto, dias=10):
    return gasto("g", str(monto * dias), period_start=D0, period_end=D0 + timedelta(days=dias - 1))


@pytest.mark.parametrize(("kg_dia", "esperado"), [(1.1, "39.50"), (0.2, "-1.00")])
def test_ganancia_del_dia_engorda_por_precio_menos_costo(kg_dia, esperado):
    dia = D0 + timedelta(days=10)
    r = dinero.estado_animal(
        "A", dia, engorda(kg_dia), [precio("p", "45"), costo_diario(10)], hato_de("A")
    )
    g = r["ganancia_dia_mxn"]
    assert g["mxn"] == Decimal(esperado)
    assert g["motivo"] is None
    assert g["costo_dia_mxn"] == Decimal("10.00")
    assert [p["event_id"] for p in g["fuente"]["pesajes"]] == ["A0", "A1"]
    assert g["fuente"]["precio"]["movement_id"] == "p"
    assert g["fuente"]["movimientos"] == ["g"]


def test_sin_precio_las_cifras_de_valor_son_null_pero_los_costos_salen():
    compra = mov("c", "compra", animals=["A"], amount_mxn=Decimal("12000"))
    r = dinero.estado_animal(
        "A", D0 + timedelta(days=10), engorda(1.0), [compra, costo_diario(10)], hato_de("A")
    )
    for campo in ("valor_hoy", "resultado", "ganancia_dia_mxn"):
        assert r[campo]["mxn"] is None
        assert r[campo]["motivo"] == "falta_precio"
    assert (r["roi"]["valor"], r["roi"]["motivo"]) == (None, "falta_precio")
    assert r["roi"]["fuente"]["costo_acumulado"]["movimientos"] == ["c", "g"]
    assert r["costo_acumulado"]["mxn"] == Decimal("12100.00")
    assert r["costo_acumulado"]["por_categoria"] == {
        "alimento": Decimal("100.00"),
        "compra": Decimal("12000.00"),
    }
    assert r["costo_acumulado"]["fuente"]["movimientos"] == ["c", "g"]
    # El precio mínimo no necesita precio de mercado: lo metido entre el peso de hoy.
    assert r["precio_minimo_kg"]["mxn"] == Decimal("29.51")


def test_sin_dos_pesajes_limpios_en_dias_distintos_faltan_pesajes():
    pesajes = [pesaje("a", D0, 400), {**pesaje("b", D0, 401), "captured_at": "2026-09-01T20:00Z"}]
    r = dinero.estado_animal("A", D0, pesajes, [precio("p", "45")], hato_de("A"))
    assert r["ganancia_dia_mxn"]["mxn"] is None
    assert r["ganancia_dia_mxn"]["motivo"] == "faltan_pesajes"
    # Con un pesaje sí hay valor de hoy.
    assert r["valor_hoy"]["mxn"] == Decimal("18045.00")
    sin_pesajes = dinero.estado_animal("A", D0, [], [precio("p", "45")], hato_de("A"))
    assert sin_pesajes["valor_hoy"]["motivo"] == "faltan_pesajes"
    assert sin_pesajes["precio_minimo_kg"]["motivo"] == "faltan_pesajes"


def test_cambio_de_precio_a_media_ventana_sale_aparte_como_efecto_mercado():
    dia = D0 + timedelta(days=10)
    movimientos = [precio("p1", "40"), precio("p2", "45", D0 + timedelta(days=5)), costo_diario(10)]
    r = dinero.estado_animal("A", dia, engorda(1.1), movimientos, hato_de("A"))
    # La ganancia del día usa solo el precio de hoy: igual que con 45 fijo.
    assert r["ganancia_dia_mxn"]["mxn"] == Decimal("39.50")
    # 400 kg del pesaje anterior × (45 − 40).
    efecto = r["efecto_mercado_mxn"]
    assert efecto["mxn"] == Decimal("2000.00")
    assert efecto["fuente"]["precio_antes"]["movement_id"] == "p1"
    assert efecto["fuente"]["precio"]["movement_id"] == "p2"
    # Valor de hoy = 411 kg × 45.
    assert r["valor_hoy"]["mxn"] == Decimal("18495.00")


def test_anulados_y_propuestos_no_cuentan_pruebas_y_atipicos_tampoco():
    dia = D0 + timedelta(days=10)
    movimientos = [
        precio("p", "45"),
        precio("p_anulado", "90", D0 + timedelta(days=1), estado="anulado"),
        gasto("g_anulado", "500", estado="anulado"),
        gasto("g_reverso", "500", estado="anulacion", voids_movement_id="g_anulado"),
        gasto("g_propuesto", "700", estado="propuesto"),
    ]
    pesajes = [
        pesaje("a0", D0, 400),
        pesaje("a1", D0 + timedelta(days=1), 401),
        pesaje("a2", D0 + timedelta(days=2), 402),
        pesaje("atipico", D0 + timedelta(days=3), 600),
        pesaje("a4", D0 + timedelta(days=4), 404),
        pesaje("a5", D0 + timedelta(days=5), 405),
        pesaje("a6", D0 + timedelta(days=6), 406),
        pesaje("mock", D0 + timedelta(days=7), 900, source="mock"),
        pesaje("synthetic", D0 + timedelta(days=7), 900, source="synthetic"),
        pesaje("proto", D0 + timedelta(days=7), 900, source="proto-sim"),
    ]
    r = dinero.estado_animal("A", dia, pesajes, movimientos, hato_de("A"))
    assert r["costo_acumulado"]["mxn"] == Decimal("0.00")
    assert r["precio"]["movement_id"] == "p"
    assert r["valor_hoy"]["fuente"]["pesaje"]["event_id"] == "a6"
    assert r["valor_hoy"]["mxn"] == Decimal("18270.00")
    assert r["ganancia_dia_mxn"]["kg_dia"] == 1.0
    assert (r["roi"]["valor"], r["roi"]["motivo"]) == (None, "sin_costos")


def test_vendida_tiene_resultado_realizado_y_deja_de_cargar():
    dia = D0 + timedelta(days=20)
    movimientos = [
        precio("p", "45"),
        mov("c", "compra", animals=["A"], amount_mxn=Decimal("10000")),
        mov("v", "venta", D0 + timedelta(days=10), animals=["A"], amount_mxn=Decimal("12000")),
        gasto("g", "200", period_start=D0, period_end=D0 + timedelta(days=19)),
    ]
    r = dinero.estado_animal("A", dia, engorda(1.0), movimientos, hato_de("A", "B"))
    assert r["estado"] == "vendida"
    # Días 1 a 10 con B: 5 por día. Del 11 al 20 lo carga solo B.
    assert r["costo_acumulado"]["mxn"] == Decimal("10050.00")
    assert r["resultado"]["mxn"] == Decimal("1950.00")
    assert r["resultado"]["fuente"]["venta"] == "v"
    assert r["roi"]["valor"] == Decimal("0.1940")
    for campo in ("valor_hoy", "ganancia_dia_mxn", "efecto_mercado_mxn", "precio_minimo_kg"):
        assert r[campo]["motivo"] == "vendida"
    b = dinero.estado_animal("B", dia, [], movimientos, hato_de("A", "B"))
    assert b["costo_acumulado"]["mxn"] == Decimal("150.00")


def test_resultado_y_roi_si_se_vendiera_hoy():
    dia = D0 + timedelta(days=10)
    movimientos = [precio("p", "45"), mov("c", "compra", animals=["A"], amount_mxn=Decimal(18000))]
    r = dinero.estado_animal("A", dia, engorda(1.0), movimientos, hato_de("A"))
    # 410 kg × 45 = 18450; menos 18000 de compra.
    assert r["resultado"]["mxn"] == Decimal("450.00")
    assert r["roi"]["valor"] == Decimal("0.0250")
    assert r["precio_minimo_kg"]["mxn"] == Decimal("43.90")


def test_lo_posterior_al_dia_no_cuenta():
    movimientos = [
        precio("p", "45"),
        precio("futuro", "99", D0 + timedelta(days=30)),
        gasto("g", "300", period_start=D0, period_end=D0 + timedelta(days=29)),
    ]
    r = dinero.estado_animal(
        "A", D0 + timedelta(days=9), engorda(1.0, dias=5), movimientos, hato_de("A")
    )
    assert r["precio"]["movement_id"] == "p"
    assert r["costo_acumulado"]["mxn"] == Decimal("100.00")


def test_compra_posterior_al_dia_no_hace_activo_al_animal_antes_de_tiempo():
    movimientos = [
        gasto("g", "100"),
        mov("c", "compra", D0 + timedelta(days=5), animals=["B"], amount_mxn=Decimal(1)),
    ]
    r = dinero.estado_animal("A", D0, [], movimientos, hato_de("A", "B"))
    assert r["costo_acumulado"]["mxn"] == Decimal("100.00")


# --- hallazgos de la revisión adversaria -----------------------------------


def test_cuadre_a_centavos_del_caso_del_issue_suma_exacto():
    vacas = [f"V{i}" for i in range(10)]
    fin = D0 + timedelta(days=29)
    g = gasto("g", "3000", period_start=D0, period_end=fin)
    venta = mov("v", "venta", D0 + timedelta(days=14), animals=["V0"], amount_mxn=Decimal(1))
    activos = dinero.activos_por_dia(hato_de(*vacas), [venta], D0, fin)
    centavos = dinero.reparto_en_centavos(dinero.repartir(g, activos))
    assert sum(centavos.values()) == 300000
    assert centavos["V0"] == 14000
    assert sorted(set(centavos[v] for v in vacas[1:])) == [31777, 31778]
    # Y estado_animal da a cada vaca lo mismo que el cuadre.
    movimientos = [g, venta]
    total = sum(
        dinero.estado_animal(v, fin, [], movimientos, hato_de(*vacas))["costo_acumulado"]["mxn"]
        for v in vacas
    )
    assert total == Decimal("3000.00")


def test_categorias_suman_el_total_al_centavo():
    gastos = [
        gasto(f"g{i}", "10", category=c) for i, c in enumerate(("alimento", "sanidad", "otros"))
    ]
    r = dinero.estado_animal("A", D0, [], gastos, hato_de("A", "B", "C"))
    c = r["costo_acumulado"]
    assert sum(c["por_categoria"].values()) == c["mxn"]
    total = sum(
        dinero.estado_animal(t, D0, [], gastos, hato_de("A", "B", "C"))["costo_acumulado"]["mxn"]
        for t in "ABC"
    )
    assert total == Decimal("30.00")


@pytest.mark.parametrize(
    "cambio",
    [
        {"estado": "anulado"},
        {"estado": "propuesto"},
        {"amount_mxn": Decimal("-5")},
        {"scope": "lote"},
        {"scope": "corral", "corral": None},
        {"period_start": D0 + timedelta(days=2), "period_end": D0},
        {"period_end": D0},
        {"scope": "animales", "animals": []},
    ],
)
def test_repartir_rechaza_gastos_no_confirmados_o_mal_formados(cambio):
    activos = dinero.activos_por_dia(hato_de("A"), [], D0, D0 + timedelta(days=2))
    with pytest.raises(ValueError):
        dinero.repartir({**gasto("g", "10"), **cambio}, activos)


def test_horas_en_otra_zona_cuentan_en_utc_sin_dividir_entre_cero():
    pesajes = [
        {**pesaje("a", D0, 400), "captured_at": "2026-09-01T23:30:00-06:00"},
        {**pesaje("b", D0, 401.25), "captured_at": "2026-09-03T00:30:00-06:00"},
    ]
    r = dinero.estado_animal(
        "A", D0 + timedelta(days=5), pesajes, [precio("p", "40")], hato_de("A")
    )
    assert r["ganancia_dia_mxn"]["kg_dia"] == Decimal("1.200")
    assert r["ganancia_dia_mxn"]["mxn"] == Decimal("48.00")


def test_gasto_con_periodo_pagado_al_final_ya_carga_los_dias_corridos():
    g = gasto(
        "g", "300", D0 + timedelta(days=29), period_start=D0, period_end=D0 + timedelta(days=29)
    )
    r = dinero.estado_animal("A", D0 + timedelta(days=9), [], [g], hato_de("A"))
    assert r["costo_acumulado"]["mxn"] == Decimal("100.00")


def test_flete_del_dia_de_la_venta_lo_carga_la_vendida():
    dia = D0 + timedelta(days=3)
    movimientos = [
        mov("v", "venta", dia, animals=["A"], amount_mxn=Decimal("1000")),
        gasto("flete", "200", dia, scope="animales", animals=["A"], category="transporte"),
    ]
    r = dinero.estado_animal("A", dia, [], movimientos, hato_de("A", "B"))
    assert r["costo_acumulado"]["por_categoria"] == {"transporte": Decimal("200.00")}
    assert r["resultado"]["mxn"] == Decimal("800.00")


def test_compra_manda_sobre_desde_y_venta_futura_no_activa_antes():
    h = {"A": {"corral": None}, "B": {"corral": None, "desde": D0}}
    movimientos = [
        mov("c", "compra", D0 + timedelta(days=2), animals=["B"], amount_mxn=Decimal(1)),
        gasto("g", "100"),
    ]
    r = dinero.estado_animal("A", D0, [], movimientos, h)
    assert r["costo_acumulado"]["mxn"] == Decimal("100.00")


def test_errores_de_datos_en_compras_y_ventas_son_ruidosos():
    venta = mov("v", "venta", D0, animals=["A"], amount_mxn=Decimal(1))
    dos = [venta, {**venta, "movement_id": "v2"}]
    with pytest.raises(ValueError):
        dinero.estado_animal("A", D0, [], dos, hato_de("A"))  # sin gastos, igual se valida
    compra_tarde = mov("c", "compra", D0 + timedelta(days=1), animals=["A"], amount_mxn=Decimal(1))
    with pytest.raises(ValueError):
        dinero.activos_por_dia(hato_de("A"), [venta, compra_tarde], D0, D0)
    with pytest.raises(ValueError):
        dinero.activos_por_dia(hato_de("A"), [{**venta, "animals": ["A", "B"]}], D0, D0)
    with pytest.raises(ValueError):
        dinero.activos_por_dia(hato_de("A"), [], D0 + timedelta(days=1), D0)
    with pytest.raises(ValueError):
        dinero.estado_animal("X", D0, [], [], hato_de("A"))


def test_compra_y_venta_anuladas_no_cuentan():
    movimientos = [
        mov("c", "compra", animals=["A"], amount_mxn=Decimal("9000"), estado="anulado"),
        mov("v", "venta", animals=["A"], amount_mxn=Decimal("9500"), estado="anulado"),
    ]
    r = dinero.estado_animal("A", D0, [], movimientos, hato_de("A"))
    assert r["estado"] == "activa"
    assert r["costo_acumulado"]["mxn"] == Decimal("0.00")


def test_pesajes_de_otro_arete_o_posteriores_al_dia_no_cuentan():
    dia = D0 + timedelta(days=10)
    pesajes = [
        *engorda(1.0),
        pesaje("B0", dia, 900, tag="B"),
        pesaje("futuro", dia + timedelta(days=1), 700),
    ]
    r = dinero.estado_animal("A", dia, pesajes, [precio("p", "45")], hato_de("A", "B"))
    assert r["valor_hoy"]["fuente"]["pesaje"]["event_id"] == "A1"
    assert r["valor_hoy"]["mxn"] == Decimal("18450.00")


def test_atipico_como_ultimo_pesaje_usa_el_anterior_limpio():
    pesajes = [pesaje(f"a{i}", D0 + timedelta(days=i), 400 + i) for i in range(6)]
    pesajes.append(pesaje("raro", D0 + timedelta(days=6), 520))
    r = dinero.estado_animal(
        "A", D0 + timedelta(days=6), pesajes, [precio("p", "45")], hato_de("A")
    )
    assert r["valor_hoy"]["fuente"]["pesaje"]["event_id"] == "a5"


def test_peso_cero_no_valua_al_animal():
    r = dinero.estado_animal("A", D0, [pesaje("a", D0, 0)], [precio("p", "45")], hato_de("A"))
    assert r["valor_hoy"]["motivo"] == "faltan_pesajes"
    assert r["precio_minimo_kg"]["motivo"] == "faltan_pesajes"


def test_ventana_de_la_ganancia_solo_toma_gastos_entre_los_dos_pesajes():
    dia = D0 + timedelta(days=20)
    pesajes = [pesaje("a", D0 + timedelta(days=10), 400), pesaje("b", dia, 410)]
    movimientos = [
        precio("p", "45"),
        gasto("antes", "1000", D0 + timedelta(days=5)),  # fuera de la ventana
        gasto("dentro", "50", D0 + timedelta(days=12)),
        gasto("ese_dia", "70", dia),  # el día del último pesaje ya no es de la ventana
    ]
    r = dinero.estado_animal("A", dia, pesajes, movimientos, hato_de("A"))
    g = r["ganancia_dia_mxn"]
    assert g["costo_dia_mxn"] == Decimal("5.00")
    assert g["fuente"]["movimientos"] == ["dentro"]
    assert g["mxn"] == Decimal("40.00")


def test_desempate_de_precio_por_instante_de_registro_en_utc():
    viejo = precio("viejo", "40", created_at="2026-09-01T10:00:00-06:00")  # 16:00 UTC
    nuevo = precio("nuevo", "41", created_at="2026-09-01T12:00:00+00:00")
    assert dinero.precio_vigente([nuevo, viejo], D0)["movement_id"] == "viejo"


def test_efecto_mercado_negativo_y_sin_precio_anterior():
    dia = D0 + timedelta(days=10)
    baja = [precio("p1", "45"), precio("p2", "40", D0 + timedelta(days=5))]
    r = dinero.estado_animal("A", dia, engorda(1.0), baja, hato_de("A"))
    assert r["efecto_mercado_mxn"]["mxn"] == Decimal("-2000.00")
    tarde = [precio("p2", "40", D0 + timedelta(days=5))]
    r = dinero.estado_animal("A", dia, engorda(1.0), tarde, hato_de("A"))
    assert r["efecto_mercado_mxn"]["motivo"] == "falta_precio_anterior"
