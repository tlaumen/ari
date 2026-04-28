import math
import pytest
import matplotlib.pyplot as plt

from pathlib import Path

from ceniac.soil_investigation.cpt import load_cpt, plot_cpt
from ceniac.soil_investigation.cpt import Cpt


@pytest.mark.auto
def test_read_cpt():
    cpt_path = Path(__file__).parent / "CPT002.xml"
    cpt = load_cpt(cpt_path)
    assert isinstance(cpt, Cpt)


@pytest.mark.auto
def test_plot_cpt():
    cpt_path = Path(__file__).parent / "CPT002.xml"
    cpt = load_cpt(cpt_path)
    fig, ax_qc, ax_fr = plot_cpt(cpt)
    assert isinstance(fig, plt.Figure)  # pyright: ignore
    assert isinstance(ax_qc, plt.Axes)  # pyright: ignore
    assert isinstance(ax_fr, plt.Axes)  # pyright: ignore


@pytest.mark.auto
def test_get_idx_level():
    cpt_path = Path(__file__).parent / "CPT002.xml"
    cpt = load_cpt(cpt_path)
    assert cpt._get_idx_level(-15.0) == 748
    assert cpt._get_idx_level(-32.6) == 1628


@pytest.mark.auto
def test_calculate_average_qc():
    cpt_path = Path(__file__).parent / "CPT002.xml"
    cpt = load_cpt(cpt_path)

    # Approximate guess of average qc over interval
    top_level = -15.0  # m+NAP
    bottom_level = -32.6  # m+NAP
    qc_avg_approx = 16  # MPa, guesstimate of what the value should be
    assert math.isclose(
        cpt.calculate_average_qc(top=top_level, bottom=bottom_level),
        qc_avg_approx,
        abs_tol=1,
    )  # within 2 MPa
