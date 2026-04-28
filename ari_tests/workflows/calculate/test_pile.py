from pathlib import Path

import pytest
from geolib.models.dfoundations import piles
import tkinter as tk

from baml_client.types import Berekening
from ari.workflows.calculate.pile import (
    PileType,
    pile_location_selector,
    PILE_LOCATION_KEY,
)
from ari.db.db import (
    load_db,
    write_calc_data,
)
from ari.workflows.calculate.pile import combine_soil_profiles_cpts
from ari.workflows.calculate.pile import create_pile
from ari.map_selector import MapPointSelector

from ari_tests.test_utils import DB_DUMP_FOLDER, DB_PATH, cpt, sp


@pytest.mark.auto
def test_combine_soil_profiles_cpts(workflow_db):
    cpts = [cpt]
    soil_profiles = [sp]
    cpt_sp_map = combine_soil_profiles_cpts(
        cpts=cpts,
        soil_profiles=soil_profiles,
        sp_cpt_mapping={sp.name: cpt.id_},
    )
    assert cpt_sp_map[0][0] == cpt
    assert cpt_sp_map[0][1] == sp


@pytest.mark.auto
def test_combine_soil_profiles_cpts_error_cpt(workflow_db):
    cpts = [cpt]
    soil_profiles = [sp]
    with pytest.raises(ValueError):
        _ = combine_soil_profiles_cpts(
            cpts=cpts,
            soil_profiles=soil_profiles,
            sp_cpt_mapping={sp.name: cpt.id_, sp.name: "cpt666"},
        )


@pytest.mark.auto
def test_combine_soil_profiles_cpts_error_soil_profile(workflow_db):
    cpts = [cpt]
    soil_profiles = [sp]
    with pytest.raises(ValueError):
        _ = combine_soil_profiles_cpts(
            cpts=cpts,
            soil_profiles=soil_profiles,
            sp_cpt_mapping={sp.name: cpt.id_, "sp666": cpt.id_},
        )


@pytest.mark.auto
def test_create_pile():
    pile = create_pile(pile_type=PileType.VIBROPAAL, dimensions=(400, 450))
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)

    pile = create_pile(pile_type=PileType.SCHROEFPAAL, dimensions=650)
    assert isinstance(pile, piles.BearingRoundPile)

    pile = create_pile(pile_type=PileType.PREFAB_HEIPAAL, dimensions=450)
    assert isinstance(pile, piles.BearingRectangularPile)

    pile = create_pile(pile_type=PileType.BUISSCHROEFPAAL, dimensions=(400, 450))
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)

    pile = create_pile(
        pile_type=PileType.BUISSCHROEFPAAL_VERLOREN_CASING, dimensions=(400, 450)
    )
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)


@pytest.mark.parametrize(
    "pile_type,dimensions,expected_class",
    [
        (PileType.PREFAB_HEIPAAL, 450, piles.BearingRectangularPile),
        (PileType.VIBROPAAL, (400, 450), piles.BearingRoundPileWithLostTip),
        (PileType.SCHROEFPAAL, 650, piles.BearingRoundPile),
        (PileType.BUISSCHROEFPAAL, (400, 450), piles.BearingRoundPileWithLostTip),
        (
            PileType.BUISSCHROEFPAAL_VERLOREN_CASING,
            (400, 450),
            piles.BearingRoundPileWithLostTip,
        ),
    ],
)
def test_create_pile_returns_valid_dgeolib_object(
    pile_type, dimensions, expected_class
):
    """Test that create_pile produces a valid d-geolib object that passes schema validation."""
    pile = create_pile(pile_type=pile_type, dimensions=dimensions)
    assert isinstance(pile, expected_class)
    pile.model_dump()


@pytest.mark.parametrize(
    "pile_type,wrong_dimensions",
    [
        (PileType.PREFAB_HEIPAAL, (400, 450)),
        (PileType.SCHROEFPAAL, (400, 450)),
        (PileType.VIBROPAAL, 450),
        (PileType.BUISSCHROEFPAAL, 450),
    ],
)
def test_create_pile_raises_on_invalid_dimensions(pile_type, wrong_dimensions):
    """Test that invalid dimension types raise ValueError."""
    with pytest.raises(ValueError):
        create_pile(pile_type=pile_type, dimensions=wrong_dimensions)


def test_create_pile_uses_correct_dgeolib_parameter_names():
    """Verify create_pile uses correct clay/silt/peat naming (not clay/loam/peat)."""
    pile = create_pile(PileType.SCHROEFPAAL, 650)
    params = pile.model_dump()
    assert "pile_class_factor_shaft_clay_silt_peat" in params
    assert "pile_class_factor_shaft_clay_loam_peat" not in str(params)
