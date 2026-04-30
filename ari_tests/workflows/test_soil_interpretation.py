from pathlib import Path
import colorsys

from matplotlib.colors import rgb2hex
import pytest

from ari.queries.soil_interpretation import find_cpt, interpret_cpt, load_cpt
from ari.queries.soil_interpretation import _is_word_in_string
from ceniac.soil_investigation.interpret import naive_qc_rf


@pytest.mark.auto
def test_find_cpt_non_existant_folder():
    top_level_folder_non_existant = Path(__file__).parent.parent / "tests" / "calculate"

    # Top level folder does not exist
    with pytest.raises(ValueError):
        _ = find_cpt(name="cpt001", top_level_folder=top_level_folder_non_existant)


@pytest.mark.auto
def test_find_cpt_no_si():
    top_level_folder_no_si = Path(__file__).parent.parent.parent / "tests" / "calculate"

    # Top level folder does not exist
    with pytest.raises(ValueError):
        _ = find_cpt(name="cpt001", top_level_folder=top_level_folder_no_si)


@pytest.mark.auto
def test_find_cpt_exact():
    top_level_folder = (
        Path(__file__).parent.parent.parent / "tests" / "soil_investigation"
    )
    cpt_path = find_cpt(name="CPT002", top_level_folder=top_level_folder)
    assert cpt_path == (top_level_folder / "CPT002.xml")


@pytest.mark.auto
def test_find_cpt_approximate():
    top_level_folder = (
        Path(__file__).parent.parent.parent / "tests" / "soil_investigation"
    )
    cpt_path = find_cpt(name="CP002", top_level_folder=top_level_folder)
    assert cpt_path == [
        top_level_folder / "CPT002.xml",
        top_level_folder / "CPT003.xml",
    ]

    cpt_path = find_cpt(name="CPT0", top_level_folder=top_level_folder)
    assert cpt_path == [
        top_level_folder / "CPT002.xml",
        top_level_folder / "CPT003.xml",
    ]


@pytest.mark.auto
def test_not_find_cpt_approximate():
    top_level_folder = (
        Path(__file__).parent.parent.parent / "tests" / "soil_investigation"
    )
    with pytest.raises(ValueError):
        _ = find_cpt(name="C02", top_level_folder=top_level_folder)


@pytest.mark.auto
def test_is_word_in_string():
    assert _is_word_in_string("klei", "klei, zandig")
    assert not _is_word_in_string("klei", "kleiig zand")
    assert not _is_word_in_string("silt", "siltig zand")
    assert _is_word_in_string("Klei", "klei, zandig")
    assert _is_word_in_string("klei", "Klei, zandig")


@pytest.mark.auto
def test_hsl_to_hex():
    rgb = colorsys.hls_to_rgb(h=300 / 360, s=80 / 100, l=50 / 100)

    # Checked with https://colorpicker.dev/#e619e5, very small deviation due to rounding errors
    assert rgb2hex(rgb) == "#e619e5"
