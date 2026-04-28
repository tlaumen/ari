import pytest

from ceniac.soil_investigation.borehole import load_borehole

from pathlib import Path


@pytest.mark.auto
def test_read_borehole():
    path = Path(__file__).parent / "B37F2316.gef"
    load_borehole(path)
