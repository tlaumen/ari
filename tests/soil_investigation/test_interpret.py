import pytest

from pathlib import Path

from ceniac.soil_investigation.cpt import load_cpt
from ceniac.soil_investigation.interpret import NaiveQcRfCorrelation, run_interpreter
from ceniac.soil_investigation.interpret import group_layers
from ceniac.soil_profile.soil_profile import Layer


@pytest.mark.auto
def test_group_layers():
    layers = [
        Layer("zand", top=top / 100, bottom=bottom / 100)
        for top, bottom in zip(range(0, -1000, -2), range(-2, -1002, -2))
    ]
    layers = group_layers(layers)
    assert layers == [Layer("zand", top=0, bottom=-10)]


@pytest.mark.auto
def test_group_layers2():
    layers = [
        Layer("zand", top=top / 100, bottom=bottom / 100)
        for top, bottom in zip(range(0, -1000, -2), range(-2, -1002, -2))
    ]
    layers += [
        Layer("klei", top=top / 100, bottom=bottom / 100)
        for top, bottom in zip(range(-1000, -1500, -2), range(-1002, -1502, -2))
    ]
    layers += [
        Layer("zand", top=top / 100, bottom=bottom / 100)
        for top, bottom in zip(range(-1500, -1700, -2), range(-1504, -1702, -2))
    ]
    layers = group_layers(layers)
    assert layers == [
        Layer("zand", top=0, bottom=-10),
        Layer("klei", top=-10, bottom=-15),
        Layer("zand", top=-15, bottom=-17),
    ]


@pytest.mark.auto
def test_classify():
    cpt_path = Path(__file__).parent / "CPT002.xml"
    cpt = load_cpt(cpt_path)
    sp = NaiveQcRfCorrelation().classify(cpt, min_layer_thickness=0.5)
