from __future__ import annotations

import logging

import pytest
from fierro_device.drivers.estabilidad import FiltroEstable
from fierro_device.drivers.estacion import (
    FUENTE_ESTACION_SIM,
    EstacionHardware,
    construir_estacion,
)
from fierro_device.hardware import HardwareSample, build_hardware
from fierro_device.main import Agent
from fierro_device.settings import (
    DEFAULT_CERO_KG,
    DEFAULT_ESTABLE_BANDA_KG,
    DEFAULT_ESTABLE_VENTANA_S,
    DEFAULT_PESO_MIN_KG,
    DEFAULT_VENTANA_TAG_S,
    Settings,
)


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora


class RfidGuion:
    def __init__(
        self,
        tags: list[str | None],
        *,
        repetir_ultimo: bool = False,
        fuente: str = "rfid-test",
    ) -> None:
        self._tags = list(tags)
        self._repetir_ultimo = repetir_ultimo
        self._ultimo: str | None = None
        self._fuente = fuente

    def encolar(self, *tags: str | None) -> None:
        self._tags.extend(tags)

    def read(self) -> HardwareSample:
        if self._tags:
            self._ultimo = self._tags.pop(0)
            tag = self._ultimo
        else:
            tag = self._ultimo if self._repetir_ultimo else None
        return HardwareSample(tag, None, False, self._fuente)


class BasculaGuion:
    def __init__(
        self,
        pesos: list[float | None],
        *,
        repetir_ultimo: bool = False,
        fuente: str = "bascula-test",
    ) -> None:
        self._pesos = list(pesos)
        self._repetir_ultimo = repetir_ultimo
        self._ultimo: float | None = None
        self._fuente = fuente

    def encolar(self, *pesos: float | None) -> None:
        self._pesos.extend(pesos)

    def read(self) -> HardwareSample:
        if self._pesos:
            self._ultimo = self._pesos.pop(0)
            kg = self._ultimo
        else:
            kg = self._ultimo if self._repetir_ultimo else None
        return HardwareSample(None, kg, False, self._fuente)


def test_filtro_estable_exige_banda_y_ventana():
    reloj = RelojFalso()
    filtro = FiltroEstable(banda_kg=0.5, ventana_s=1.0, clock=reloj)

    assert filtro.evaluar(400.0) is False
    reloj.ahora = 0.5
    assert filtro.evaluar(400.4) is False
    reloj.ahora = 1.0
    assert filtro.evaluar(399.6) is True

    reloj.ahora = 1.5
    assert filtro.evaluar(401.0) is False
    reloj.ahora = 2.5
    assert filtro.evaluar(401.0) is True

    filtro.reiniciar()
    reloj.ahora = 2.6
    assert filtro.evaluar(401.0) is False


def test_animal_normal_emite_un_pesaje_estable():
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111"], repetir_ultimo=True)
    bascula = BasculaGuion([0.0, 320.0, 450.0, 450.3, 450.1], repetir_ultimo=True)
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        peso_min_kg=30.0,
        cero_kg=20.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    reloj.ahora = 0.0
    assert hw.read().tag_id is None
    reloj.ahora = 0.5
    assert hw.read().tag_id is None
    reloj.ahora = 1.0
    assert hw.read().tag_id is None
    reloj.ahora = 1.5
    assert hw.read().tag_id is None
    reloj.ahora = 2.0
    muestra = hw.read()

    assert muestra.tag_id == "982000111111111"
    assert muestra.weight_kg == 450.1
    assert muestra.stable is True
    assert muestra.source == "bascula-test"


def test_animal_parado_60s_produce_un_solo_pesaje_y_rearma_al_bajar_a_cero(caplog):
    caplog.set_level(logging.INFO, logger="fierro_device")
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111"], repetir_ultimo=True)
    bascula = BasculaGuion([480.0], repetir_ultimo=True)
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        peso_min_kg=30.0,
        cero_kg=20.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    emitidos: list[HardwareSample] = []
    for paso in range(121):
        reloj.ahora = paso * 0.5
        muestra = hw.read()
        if muestra.tag_id is not None:
            emitidos.append(muestra)

    assert len(emitidos) == 1
    assert emitidos[0].tag_id == "982000111111111"
    assert emitidos[0].weight_kg == 480.0
    assert emitidos[0].stable is True
    assert "sin regreso a cero" in caplog.text

    # El animal sale (baja de cero_kg) y entra el siguiente.
    rfid.encolar(None, "982000222222222", "982000222222222", "982000222222222")
    bascula.encolar(5.0, 410.0, 410.0, 410.0)

    reloj.ahora = 61.0
    assert hw.read().tag_id is None
    reloj.ahora = 62.0
    assert hw.read().tag_id is None
    reloj.ahora = 62.5
    assert hw.read().tag_id is None
    reloj.ahora = 63.0
    segundo = hw.read()

    assert segundo.tag_id == "982000222222222"
    assert segundo.weight_kg == 410.0
    assert segundo.stable is True


def test_dos_aretes_en_ventana_anula_y_registra_motivo(caplog):
    caplog.set_level(logging.WARNING, logger="fierro_device")
    reloj = RelojFalso()
    rfid = RfidGuion(
        ["982000111111111", "982000222222222", "982000222222222", "982000222222222", None]
    )
    bascula = BasculaGuion([430.0], repetir_ultimo=True)
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    emitidos: list[HardwareSample] = []
    for t in (0.0, 0.5, 1.5, 2.5, 4.0):
        reloj.ahora = t
        muestra = hw.read()
        if muestra.tag_id is not None:
            emitidos.append(muestra)

    assert emitidos == []
    assert "dos aretes en ventana" in caplog.text


def test_peso_que_nunca_se_estabiliza_vence_ventana_sin_emitir(caplog):
    caplog.set_level(logging.WARNING, logger="fierro_device")
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111"], repetir_ultimo=True)
    bascula = BasculaGuion(
        [400.0, 412.0, 398.0, 415.0, 401.0, 418.0, 395.0, 410.0, 402.0, 416.0, 399.0]
    )
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    for paso in range(11):
        reloj.ahora = paso * 0.5
        muestra = hw.read()
        assert muestra.tag_id is None
        assert muestra.stable is False

    assert "ventana vencida" in caplog.text


def test_peso_bajo_minimo_no_emite_y_registra_motivo(caplog):
    caplog.set_level(logging.WARNING, logger="fierro_device")
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111"], repetir_ultimo=True)
    bascula = BasculaGuion([12.0], repetir_ultimo=True)
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        peso_min_kg=30.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    for t in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
        reloj.ahora = t
        muestra = hw.read()
        assert muestra.tag_id is None
        assert muestra.stable is False

    assert "bajo minimo" in caplog.text


def test_peso_bajo_minimo_al_inicio_no_impide_pesar_al_subir_animal():
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111"], repetir_ultimo=True)
    bascula = BasculaGuion([0.0, 0.0, 420.0, 420.0], repetir_ultimo=True)
    hw = EstacionHardware(
        rfid,
        bascula,
        banda_kg=0.5,
        ventana_estable_s=1.0,
        peso_min_kg=30.0,
        ventana_tag_s=5.0,
        clock=reloj,
    )

    reloj.ahora = 0.0
    assert hw.read().tag_id is None
    reloj.ahora = 1.0
    assert hw.read().tag_id is None
    reloj.ahora = 1.5
    assert hw.read().tag_id is None
    reloj.ahora = 2.5
    muestra = hw.read()

    assert muestra.tag_id == "982000111111111"
    assert muestra.weight_kg == 420.0
    assert muestra.stable is True


def test_arete_sin_peso_no_emite_y_vence_ventana(caplog):
    caplog.set_level(logging.WARNING, logger="fierro_device")
    reloj = RelojFalso()
    rfid = RfidGuion(["982000111111111", None, None, None])
    bascula = BasculaGuion([None], repetir_ultimo=True)
    hw = EstacionHardware(rfid, bascula, ventana_tag_s=5.0, clock=reloj)

    for t in (0.0, 1.0, 3.0, 5.0):
        reloj.ahora = t
        muestra = hw.read()
        assert muestra.tag_id is None
        assert muestra.stable is False

    assert "ventana vencida" in caplog.text


def test_peso_sin_arete_no_emite():
    reloj = RelojFalso()
    rfid = RfidGuion([None], repetir_ultimo=True)
    bascula = BasculaGuion([450.0], repetir_ultimo=True)
    hw = EstacionHardware(rfid, bascula, ventana_estable_s=1.0, clock=reloj)

    for t in (0.0, 0.5, 1.0, 2.0, 5.0):
        reloj.ahora = t
        muestra = hw.read()
        assert muestra.tag_id is None
        assert muestra.stable is False


def test_settings_lee_parametros_de_estacion_y_tiene_defaults(monkeypatch):
    for var in (
        "FIERRO_ESTABLE_BANDA_KG",
        "FIERRO_ESTABLE_VENTANA_S",
        "FIERRO_PESO_MIN_KG",
        "FIERRO_CERO_KG",
        "FIERRO_VENTANA_TAG_S",
    ):
        monkeypatch.delenv(var, raising=False)

    por_defecto = Settings.from_env()
    assert por_defecto.estable_banda_kg == DEFAULT_ESTABLE_BANDA_KG
    assert por_defecto.estable_ventana_s == DEFAULT_ESTABLE_VENTANA_S
    assert por_defecto.peso_min_kg == DEFAULT_PESO_MIN_KG
    assert por_defecto.cero_kg == DEFAULT_CERO_KG
    assert por_defecto.ventana_tag_s == DEFAULT_VENTANA_TAG_S

    monkeypatch.setenv("FIERRO_ESTABLE_BANDA_KG", "1.5")
    monkeypatch.setenv("FIERRO_ESTABLE_VENTANA_S", "2.0")
    monkeypatch.setenv("FIERRO_PESO_MIN_KG", "80.0")
    monkeypatch.setenv("FIERRO_CERO_KG", "15.0")
    monkeypatch.setenv("FIERRO_VENTANA_TAG_S", "7.5")

    custom = Settings.from_env()
    assert custom.estable_banda_kg == 1.5
    assert custom.estable_ventana_s == 2.0
    assert custom.peso_min_kg == 80.0
    assert custom.cero_kg == 15.0
    assert custom.ventana_tag_s == 7.5


def test_build_hardware_estacion_mock_usa_estacion_sim_y_rearma(monkeypatch):
    for var in (
        "FIERRO_ESTABLE_BANDA_KG",
        "FIERRO_ESTABLE_VENTANA_S",
        "FIERRO_PESO_MIN_KG",
        "FIERRO_CERO_KG",
        "FIERRO_VENTANA_TAG_S",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FIERRO_HW_BACKEND", "estacion")
    construido = build_hardware(
        mock=True, scale_port="COM1", rfid_port="COM2", mock_interval_s=3.0
    )
    assert isinstance(construido, EstacionHardware)

    reloj = RelojFalso()
    hw = construir_estacion(
        mock=True,
        scale_port="COM1",
        rfid_port="COM2",
        mock_interval_s=3.0,
        clock=reloj,
    )

    emitidos: list[HardwareSample] = []
    for paso in range(15):
        reloj.ahora = paso * 0.5
        muestra = hw.read()
        assert muestra.source == FUENTE_ESTACION_SIM
        assert muestra.source != "scale"
        if muestra.tag_id is not None:
            emitidos.append(muestra)

    assert len(emitidos) >= 2
    assert emitidos[0].tag_id != emitidos[1].tag_id
    for m in emitidos:
        assert m.stable is True
        assert m.weight_kg is not None and m.weight_kg >= DEFAULT_PESO_MIN_KG


def test_build_hardware_estacion_sin_mock_falla_ruidoso(monkeypatch):
    monkeypatch.setenv("FIERRO_HW_BACKEND", "estacion")
    hw = build_hardware(
        mock=False,
        scale_port="/dev/ttyUSB0",
        rfid_port="/dev/ttyUSB1",
        mock_interval_s=3.0,
    )
    assert isinstance(hw, EstacionHardware)
    with pytest.raises(NotImplementedError):
        hw.read()


def test_agent_con_backend_estacion_guarda_en_outbox_sin_tocar_main(
    monkeypatch, tmp_path
):
    for var in (
        "FIERRO_ESTABLE_BANDA_KG",
        "FIERRO_PESO_MIN_KG",
        "FIERRO_CERO_KG",
        "FIERRO_VENTANA_TAG_S",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FIERRO_HW_BACKEND", "estacion")
    monkeypatch.setenv("FIERRO_MOCK_HW", "1")
    monkeypatch.setenv("FIERRO_ESTABLE_VENTANA_S", "0")
    monkeypatch.setenv("FIERRO_DB_PATH", str(tmp_path / "outbox.db"))
    monkeypatch.setenv("FIERRO_API_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("FIERRO_DEVICE_ID", "rpi-estacion-001")

    agente = Agent(Settings.from_env())
    lectura = agente.capture_once()

    assert lectura is not None
    assert lectura.source == FUENTE_ESTACION_SIM
    assert lectura.source != "scale"
    assert lectura.stable is True
    assert lectura.weight_kg >= DEFAULT_PESO_MIN_KG
    assert agente.store.pending_count() == 1
    # Sigue desarmada mientras no regrese a cero.
    assert agente.capture_once() is None
