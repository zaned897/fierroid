from pathlib import Path

import pytest
from fierro_device.drivers.micro_simulado import MicroSimulado
from fierro_device.drivers.rc522_serie import PuertoSerie, Rc522Serie

CAPTURA_RUIDO = (
    Path(__file__).resolve().parents[3]
    / "hardware"
    / "test-fixtures"
    / "rfid-mfrc522"
    / "captura-20260906-223853.bin"
)


class TransporteGuiado:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)
        self.aperturas = 0

    def abrir(self) -> None:
        self.aperturas += 1

    def cerrar(self) -> None: ...

    def leer(self, n: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class TransporteQueFalla(TransporteGuiado):
    def __init__(self, chunks: list[bytes]) -> None:
        super().__init__(chunks)
        self.fallar = True

    def leer(self, n: int) -> bytes:
        if self.fallar:
            self.fallar = False
            raise RuntimeError("puerto murio")
        return super().leer(n)


def driver(chunks: list[bytes], fuente: str = "proto-rc522") -> Rc522Serie:
    return Rc522Serie(TransporteGuiado(chunks), fuente=fuente)


def test_banner_del_transcript_se_consumo_sin_producir_datos():
    hw = driver(
        [
            b"== Fierro proto == pesaje por evento ==\r\n",
            b"lineas: W,<uid>,<adc> | H,<millis> | # diagnostico\r\n",
            b"RC522 version: 0x92\r\n",
            b"cfg estable_ms=800\r\n",
            b"Listo. Presenta una tarjeta...\r\n",
        ]
    )
    muestra = hw.read()
    assert muestra.tag_id is None
    assert muestra.weight_kg is None
    assert hw.eventos == 0


def test_lectura_limpia_del_transcript():
    hw = driver([b"W,025854D3,5\r\n", b"H,110041\r\n"])
    muestra = hw.read()
    assert muestra.tag_id == "proto:025854D3"
    assert muestra.weight_kg == 34.5
    assert muestra.stable is True
    assert muestra.source == "proto-rc522"
    assert hw.eventos == 1
    assert hw.latidos == 1


def test_dos_tags_del_transcript_en_orden():
    hw = driver(
        [
            b"# sesion 025854D3 esperando peso...\r\n",
            b"W,025854D3,5\r\n",
            b"# sesion BEDE50D3 esperando peso...\r\n",
            b"W,BEDE50D3,4\r\n",
        ]
    )
    primera = hw.read()
    segunda = hw.read()
    assert primera.tag_id == "proto:025854D3"
    assert segunda.tag_id == "proto:BEDE50D3"
    assert segunda.weight_kg == 33.5


def test_timeout_marca_estable_false():
    hw = driver([b"W,BEDE50D3,4\r\n", b"# emitido por timeout: no estabilizo\r\n"])
    muestra = hw.read()
    assert muestra.tag_id == "proto:BEDE50D3"
    assert muestra.weight_kg == 33.5
    assert muestra.stable is False


def test_linea_partida_entre_chunks():
    hw = driver([b"W,025854", b"D3,512\r\n", b"H,1\r\n"])
    muestra = hw.read()
    assert muestra.tag_id == "proto:025854D3"
    assert muestra.weight_kg == 465.5


def test_captura_bin_de_ruido_no_produce_datos():
    hw = driver([CAPTURA_RUIDO.read_bytes()])
    muestra = hw.read()
    assert muestra.tag_id is None
    assert hw.eventos == 0
    assert hw.latidos == 1
    assert hw.lineas_descartadas > 0


def test_linea_malformada_se_descarta_contada():
    hw = driver([b"W,solo-dos\r\n", b"W,UID,abc\r\n", b"W,UID,1023\r\n", b"H,5\r\n"])
    muestra = hw.read()
    assert muestra.tag_id == "proto:UID"
    assert muestra.weight_kg == 900.0
    assert hw.lineas_descartadas == 2


def test_adc_extremos_mapean_al_rango():
    hw = driver([b"W,AA,0\r\n", b"H,1\r\n", b"W,BB,1023\r\n", b"H,2\r\n"])
    bajo = hw.read()
    alto = hw.read()
    assert bajo.weight_kg == 30.0
    assert alto.weight_kg == 900.0


def test_puerto_que_falla_se_reabre_en_la_siguiente_lectura():
    transporte = TransporteQueFalla([b"W,025854D3,5\r\n", b"H,1\r\n"])
    hw = Rc522Serie(transporte)
    with pytest.raises(RuntimeError, match="puerto murio"):
        hw.read()
    muestra = hw.read()
    assert muestra.tag_id == "proto:025854D3"
    assert transporte.aperturas == 2


def test_puerto_serie_sin_abrir_falla_ruidoso():
    puerto = PuertoSerie("COM99")
    with pytest.raises(RuntimeError, match="no abierto"):
        puerto.leer(1)


def test_micro_simulado_emite_banner_y_presentaciones():
    micro = MicroSimulado()
    hw = Rc522Serie(micro, fuente="proto-sim")
    vacia = hw.read()
    assert vacia.tag_id is None

    micro.presentar("025854D3", 1023)
    muestra = hw.read()
    assert muestra.tag_id == "proto:025854D3"
    assert muestra.weight_kg == 900.0
    assert muestra.stable is True
    assert muestra.source == "proto-sim"


def test_micro_simulado_timeout_y_sin_abrir():
    micro = MicroSimulado()
    with pytest.raises(RuntimeError, match="no abierto"):
        micro.presentar("AA", 5)

    hw = Rc522Serie(micro)
    hw.read()
    micro.presentar("BEDE50D3", 4, estable=False)
    muestra = hw.read()
    assert muestra.stable is False


def test_micro_simulado_heartbeat_respeta_intervalo():
    reloj = {"ahora": 0.0}
    micro = MicroSimulado(clock=lambda: reloj["ahora"])
    micro.abrir()
    while micro.leer(4096):
        pass
    reloj["ahora"] = 5.0
    assert micro.leer(4096) == b""
    reloj["ahora"] = 10.0
    assert micro.leer(4096).startswith(b"H,")
