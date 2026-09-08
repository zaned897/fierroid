from fierro_device.drivers.prototipo import PrototipoHardware, construir_prototipo
from fierro_device.hardware import (
    HardwareSample,
    MockHardware,
    build_hardware,
)
from fierro_device.main import Agent
from fierro_device.settings import Settings


class RelojFalso:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


class RfidFijo:
    def __init__(self, *muestras: HardwareSample) -> None:
        self._muestras = list(muestras)

    def read(self) -> HardwareSample:
        if self._muestras:
            return self._muestras.pop(0)
        return HardwareSample(None, None, False, "proto-rc522")


class RfidRepetitivo:
    def __init__(self, muestra: HardwareSample) -> None:
        self._muestra = muestra

    def read(self) -> HardwareSample:
        return self._muestra


class PesoFijo:
    def __init__(self, muestra: HardwareSample) -> None:
        self._muestra = muestra

    def read(self) -> HardwareSample:
        return self._muestra


class PesoSecuencia:
    def __init__(self, *muestras: HardwareSample) -> None:
        self._muestras = list(muestras)

    def read(self) -> HardwareSample:
        return self._muestras.pop(0)


TAG_SOLO = HardwareSample("proto:04A3B1C2", None, False, "proto-rc522")


def test_muestra_completa_del_micro_pasa_igual():
    completa = HardwareSample("proto:025854D3", 34.5, True, "proto-sim")
    hw = PrototipoHardware(RfidFijo(completa), PesoFijo(TAG_SOLO))

    assert hw.read() == completa


def test_tag_sin_peso_se_empareja_con_peso_estable():
    peso = HardwareSample(None, 412.0, True, "proto-fijo")
    hw = PrototipoHardware(RfidFijo(TAG_SOLO), PesoFijo(peso), clock=RelojFalso())

    muestra = hw.read()
    assert muestra.tag_id == "proto:04A3B1C2"
    assert muestra.weight_kg == 412.0
    assert muestra.stable is True
    assert muestra.source == "proto-fijo"


def test_ventana_vencida_sin_peso_estable_no_emite_nada(caplog):
    peso_inestable = HardwareSample(None, 512.0, False, "proto-aleatorio")
    reloj = RelojFalso()
    hw = PrototipoHardware(
        RfidRepetitivo(TAG_SOLO), PesoFijo(peso_inestable), clock=reloj
    )

    reloj.ahora = 2.0
    assert hw.read().tag_id is None
    reloj.ahora = 7.1
    vacia = hw.read()

    assert vacia.tag_id is None
    assert "ventana vencida" in caplog.text


def test_tag_distinto_dentro_de_la_ventana_reinicia():
    inestable = HardwareSample(None, 512.0, False, "proto-aleatorio")
    estable = HardwareSample(None, 412.0, True, "proto-fijo")
    reloj = RelojFalso()
    tag_b = HardwareSample("proto:05D4E3F2", None, False, "proto-rc522")
    hw = PrototipoHardware(
        RfidFijo(TAG_SOLO, tag_b, tag_b),
        PesoSecuencia(inestable, inestable, estable),
        clock=reloj,
    )

    reloj.ahora = 0.0
    assert hw.read().tag_id is None
    reloj.ahora = 4.5
    segunda = hw.read()
    reloj.ahora = 8.5
    emitido = hw.read()

    assert segunda.tag_id is None
    assert emitido.tag_id == "proto:05D4E3F2"
    assert emitido.weight_kg == 412.0


def test_sin_backend_de_peso_el_tag_solo_no_emite():
    hw = PrototipoHardware(RfidFijo(TAG_SOLO), None, clock=RelojFalso())

    assert hw.read().tag_id is None


def test_construir_prototipo_mock_usa_micro_simulado():
    hw = construir_prototipo(mock=True, rfid_port="COM9")

    muestra = hw.read()
    assert muestra.source == "proto-sim"
    assert muestra.tag_id is not None and muestra.tag_id.startswith("proto:")
    assert muestra.weight_kg is not None
    assert muestra.stable is True


def test_build_hardware_selecciona_prototipo_por_env(monkeypatch):
    monkeypatch.setenv("FIERRO_HW_BACKEND", "prototipo")
    prototipo = build_hardware(
        mock=True, scale_port="x", rfid_port="y", mock_interval_s=1
    )
    assert isinstance(prototipo, PrototipoHardware)

    monkeypatch.delenv("FIERRO_HW_BACKEND")
    mock = build_hardware(
        mock=True, scale_port="x", rfid_port="y", mock_interval_s=1
    )
    assert isinstance(mock, MockHardware)


def test_dod_main_produce_pesajes_en_la_outbox_sin_tocar_main(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("FIERRO_HW_BACKEND", "prototipo")
    monkeypatch.setenv("FIERRO_MOCK_HW", "1")
    monkeypatch.setenv("FIERRO_DB_PATH", str(tmp_path / "outbox.db"))
    monkeypatch.setenv("FIERRO_API_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("FIERRO_DEVICE_ID", "rpi-los-encinos-001")

    agente = Agent(Settings.from_env())
    lectura = agente.capture_once()

    assert lectura is not None
    assert lectura.tag_id.startswith("proto:")
    assert lectura.source == "proto-sim"
    assert agente.store.pending_count() == 1
