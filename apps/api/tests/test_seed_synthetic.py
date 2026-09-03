"""Pruebas del generador de datos sinteticos.

Vive en apps/api/tests porque es el testpath que ya corre CI; el script en si
esta en scripts/ y no es parte de ningun paquete instalable.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "seed_synthetic.py"


@pytest.fixture(scope="module")
def seed_module():
    spec = importlib.util.spec_from_file_location("seed_synthetic", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # @dataclass con anotaciones diferidas resuelve tipos via sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def now():
    return datetime(2026, 9, 1, tzinfo=timezone.utc)


def build(seed_module, now, *, animals=10, days=60, seed=99):
    rng = random.Random(seed)
    herd = seed_module.build_herd(rng, animals, seed_module.DEFAULT_COUNTRY_CODE, now)
    events = seed_module.generate_events(
        rng=rng,
        herd=herd,
        devices=["rpi-a", "rpi-b"],
        days=days,
        interval_days=7,
        now=now,
    )
    return herd, events


def test_misma_semilla_mismos_event_id(seed_module, now):
    """Re-sembrar no debe duplicar: los event_id tienen que repetirse exactos."""
    _, first = build(seed_module, now)
    _, second = build(seed_module, now)

    assert [e["event_id"] for e in first] == [e["event_id"] for e in second]
    assert [e["weight_kg"] for e in first] == [e["weight_kg"] for e in second]


def test_semillas_distintas_generan_hatos_distintos(seed_module, now):
    _, a = build(seed_module, now, seed=1)
    _, b = build(seed_module, now, seed=2)
    assert [e["event_id"] for e in a] != [e["event_id"] for e in b]


def test_event_id_unico_por_lectura(seed_module, now):
    _, events = build(seed_module, now, animals=25, days=120)
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids))


def test_arete_cumple_formato_iso_11784(seed_module, now):
    herd, _ = build(seed_module, now, animals=30)
    for animal in herd:
        assert len(animal.tag_id) == 15
        assert animal.tag_id.isdigit()
        assert animal.tag_id.startswith("484")  # codigo de pais Mexico


def test_pesos_en_rango_bovino_real(seed_module, now):
    _, events = build(seed_module, now, animals=40, days=180)
    weights = [e["weight_kg"] for e in events]
    assert weights, "el generador no produjo eventos"
    assert min(weights) > 30.0
    assert max(weights) < 1300.0
    # Division del indicador: 0.5 kg (OIML R76).
    assert all(round(w * 2) == w * 2 for w in weights)


def test_el_animal_gana_peso_con_el_tiempo(seed_module, now):
    """La curva de Gompertz debe crecer; si no, la grafica de la PWA miente."""
    rng = random.Random(7)
    herd = seed_module.build_herd(rng, 5, seed_module.DEFAULT_COUNTRY_CODE, now)
    for animal in herd:
        early = seed_module.weight_at(animal, animal.birth + timedelta(days=120))
        later = seed_module.weight_at(animal, animal.birth + timedelta(days=600))
        assert later > early


def test_no_se_pesan_animales_antes_de_nacer(seed_module, now):
    herd, events = build(seed_module, now, animals=20, days=365)
    birth_by_tag = {a.tag_id: a.birth for a in herd}
    for event in events:
        captured = datetime.fromisoformat(event["captured_at"])
        assert captured >= birth_by_tag[event["tag_id"]]


def test_ningun_pesaje_en_el_futuro(seed_module, now):
    """La ultima jornada esta a medias: no se inventan pesajes que no ocurrieron."""
    _, events = build(seed_module, now, animals=30, days=45)
    for event in events:
        assert datetime.fromisoformat(event["captured_at"]) <= now


def test_hatos_de_semillas_distintas_no_comparten_aretes(seed_module, now):
    """La base de "usuarios de prueba con datos distintos".

    Si dos organizaciones sembradas con semillas distintas comparten un arete,
    el mismo animal aparece en dos ranchos y la separacion multi-cliente es
    mentira, aunque el filtrado por tenant funcione perfecto.
    """
    herd_a, _ = build(seed_module, now, animals=40, seed=1130)
    herd_b, _ = build(seed_module, now, animals=40, seed=1111)
    herd_c, _ = build(seed_module, now, animals=40, seed=1012)

    aretes = [{a.tag_id for a in h} for h in (herd_a, herd_b, herd_c)]
    for i, uno in enumerate(aretes):
        for otro in aretes[i + 1 :]:
            assert not (uno & otro)


def test_eventos_ordenados_por_fecha(seed_module, now):
    _, events = build(seed_module, now, animals=15, days=90)
    stamps = [e["captured_at"] for e in events]
    assert stamps == sorted(stamps)


def test_contrato_de_campos(seed_module, now):
    _, events = build(seed_module, now, animals=5, days=30)
    expected = {"event_id", "device_id", "tag_id", "weight_kg", "captured_at", "stable", "source"}
    for event in events:
        assert set(event) == expected
        assert event["source"] == "synthetic"
        assert isinstance(event["stable"], bool)


def test_cli_exige_destino(seed_module):
    assert seed_module.main([]) == 2


def test_cli_escribe_json(seed_module, tmp_path):
    out = tmp_path / "fixtures.json"
    assert seed_module.main(["--out", str(out), "--animals", "4", "--days", "14"]) == 0

    import json

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["herd"]) == 4
    assert payload["readings"]
