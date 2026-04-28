from copy import deepcopy

from geolib.soils import soil
import pytest

from ceniac.soil_profile.soil_profile import (
    SoilProfile,
    SoilStresses,
    calculate_stresses,
)
from ceniac.soil_profile.soil_profile import Layer

SURFACE_LEVEL = 0
BOTTOM_PROFILE = -10
CLAY_LAYER = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-3)
SAND_LAYER = Layer(soil="sand", top=-3, bottom=BOTTOM_PROFILE)


@pytest.fixture
def soil_profile():
    clay_layer = deepcopy(CLAY_LAYER)
    sand_layer = deepcopy(SAND_LAYER)
    return SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )


CLAY_LAYER2 = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-4)
SILT_LAYER2 = Layer(soil="silt", top=-4, bottom=-8)
SAND_LAYER2 = Layer(soil="sand", top=-8, bottom=BOTTOM_PROFILE)


@pytest.fixture
def soil_profile2():
    clay_layer2 = deepcopy(CLAY_LAYER2)
    silt_layer2 = deepcopy(SILT_LAYER2)
    sand_layer2 = deepcopy(SAND_LAYER2)

    return SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer2, silt_layer2, sand_layer2],
        bottom=BOTTOM_PROFILE,
    )


@pytest.mark.auto
def test_validate_soil_profile(soil_profile):
    assert soil_profile.validate()


@pytest.mark.auto
def test_validate_soil_profile_holes():
    clay_layer = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-3)
    sand_layer = Layer(soil="sand", top=-4, bottom=BOTTOM_PROFILE)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_no_holes()
    assert not sp.validate()


@pytest.mark.auto
def test_validate_soil_profile_surface_level():
    clay_layer = Layer(soil="clay", top=-1, bottom=-3)
    sand_layer = Layer(soil="sand", top=-3, bottom=BOTTOM_PROFILE)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_no_holes()
    assert not sp.validate()


@pytest.mark.auto
def test_validate_soil_profile_bottom():
    clay_layer = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-3)
    sand_layer = Layer(soil="sand", top=-3, bottom=-9)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_no_holes()
    assert not sp.validate()


@pytest.mark.auto
def test_validate_soil_profile_inverted_bounds_layer():
    clay_layer = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-3)
    silt_layer = Layer(soil="silt", top=-6, bottom=-3)
    sand_layer = Layer(soil="sand", top=-6, bottom=BOTTOM_PROFILE)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, silt_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_correct_layers()
    assert not sp.validate()


@pytest.mark.auto
def test_validate_soil_profile_empty_layer():
    clay_layer = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-6)
    silt_layer = Layer(soil="silt", top=-6, bottom=-6)
    sand_layer = Layer(soil="sand", top=-6, bottom=BOTTOM_PROFILE)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[clay_layer, silt_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_correct_layers()
    assert not sp.validate()


@pytest.mark.auto
def test_validate_soil_profile_sorting():
    clay_layer = Layer(soil="clay", top=SURFACE_LEVEL, bottom=-3)
    silt_layer = Layer(soil="silt", top=-3, bottom=-6)
    sand_layer = Layer(soil="sand", top=-6, bottom=BOTTOM_PROFILE)
    sp = SoilProfile(
        name="",
        surface_level=SURFACE_LEVEL,
        layers=[silt_layer, clay_layer, sand_layer],
        bottom=BOTTOM_PROFILE,
    )
    assert not sp._validate_sorting()
    assert not sp.validate()


@pytest.mark.auto
def test_get_idx(soil_profile):
    idx = soil_profile._get_layer_idx(CLAY_LAYER)
    assert idx == 0
    idx = soil_profile._get_layer_idx(SAND_LAYER)
    assert idx == 1


@pytest.mark.auto
def test_change_layer_top(soil_profile):
    soil_profile.change_layer(CLAY_LAYER, new_bottom=-6)
    assert soil_profile.validate()


@pytest.mark.auto
def test_change_layer_bottom(soil_profile):
    soil_profile.change_layer(SAND_LAYER, new_top=-2, new_bottom=-8)
    assert not soil_profile.validate()


@pytest.mark.auto
def test_change_layer_middle(soil_profile2):
    soil_profile2.change_layer(SILT_LAYER2, new_top=-2, new_bottom=-6)
    assert soil_profile2.validate()


@pytest.mark.auto
def test_remove_layer_fill_middle(soil_profile2):
    soil_profile2.remove_layer(SILT_LAYER2, fill=True)
    assert soil_profile2.validate()


@pytest.mark.auto
def test_remove_layer_no_fill(soil_profile2):
    soil_profile2.remove_layer(SILT_LAYER2, fill=False)
    assert not soil_profile2.validate()


@pytest.mark.auto
def test_remove_layer_top(soil_profile2):
    soil_profile2.remove_layer(CLAY_LAYER2)
    assert soil_profile2.validate()


@pytest.mark.auto
def test_remove_layer_bottom(soil_profile2):
    soil_profile2.remove_layer(SAND_LAYER2)
    assert soil_profile2.validate()


@pytest.mark.auto
def test_add_layer(soil_profile, soil_profile2):
    soil_profile.add_layer(SILT_LAYER2)
    assert soil_profile.validate()
    assert soil_profile == soil_profile2


@pytest.mark.auto
def test_soil_stresses_at_boundary():
    # Soil profile:
    #   - clay: 0 - -5 m+NAP
    #   - sand: -5 - -10 m+NAP
    #   - phreatic surface: -1 m+NAP

    stresses = SoilStresses(
        phreatic_level=-1,
        levels=[0, -1, -5, -10],
        total_stresses=[0, 15, 75, 175],
        pore_water_pressure=[0, 0, 40, 90],
        effective_stresses=[0, 15, 35, 85],
    )

    # Get stress on layer boundary
    # Check top works
    sigv, pwp, sigv_eff = stresses.get_stresses_at_level(level=0)
    assert sigv == 0
    assert pwp == 0
    assert sigv_eff == 0

    # Check a boundary works
    sigv, pwp, sigv_eff = stresses.get_stresses_at_level(level=-5)
    assert sigv == 75
    assert pwp == 40
    assert sigv_eff == 35

    # Check bottom works
    sigv, pwp, sigv_eff = stresses.get_stresses_at_level(level=-10)
    assert sigv == 175
    assert pwp == 90
    assert sigv_eff == 85


@pytest.mark.auto
def test_soil_stresses_interpolated():
    # Soil profile:
    #   - clay: 0 - -5 m+NAP
    #   - sand: -5 - -10 m+NAP
    #   - phreatic surface: -1 m+NAP

    stresses = SoilStresses(
        phreatic_level=-1,
        levels=[0, -1, -5, -10],
        total_stresses=[0, 15, 75, 175],
        pore_water_pressure=[0, 0, 40, 90],
        effective_stresses=[0, 15, 35, 85],
    )

    # Get stress interpolated
    # Above phreatic surface
    sigv, pwp, sigv_eff = stresses.get_stresses_at_level(level=-0.5)
    assert sigv == 7.5
    assert pwp == 0
    assert sigv_eff == 7.5

    # Below phreatic surface
    sigv, pwp, sigv_eff = stresses.get_stresses_at_level(level=-7.5)
    assert sigv == 125
    assert pwp == 65
    assert sigv_eff == 60


@pytest.mark.auto
def test_soil_stresses_wrong_order():
    # Test layers are in order
    with pytest.raises(ValueError):
        _ = SoilStresses(
            phreatic_level=-1,
            levels=[0, -5, -1, -10],
            total_stresses=[0, 15, 75, 175],
            pore_water_pressure=[0, 0, 40, 90],
            effective_stresses=[0, 15, 35, 85],
        )


@pytest.mark.auto
def test_soil_stresses_above_surface():
    # Soil profile:
    #   - clay: 0 - -5 m+NAP
    #   - sand: -5 - -10 m+NAP
    #   - phreatic surface: -1 m+NAP
    stresses = SoilStresses(
        phreatic_level=-1,
        levels=[0, -1, -5, -10],
        total_stresses=[0, 15, 75, 175],
        pore_water_pressure=[0, 0, 40, 90],
        effective_stresses=[0, 15, 35, 85],
    )

    # Get raused errors
    # Above surface level
    with pytest.raises(ValueError):
        _ = stresses.get_stresses_at_level(level=2)


@pytest.mark.auto
def test_soil_stresses_below_bottom():
    # Soil profile:
    #   - clay: 0 - -5 m+NAP
    #   - sand: -5 - -10 m+NAP
    #   - phreatic surface: -1 m+NAP
    stresses = SoilStresses(
        phreatic_level=-1,
        levels=[0, -1, -5, -10],
        total_stresses=[0, 15, 75, 175],
        pore_water_pressure=[0, 0, 40, 90],
        effective_stresses=[0, 15, 35, 85],
    )

    # Get raused errors
    # Above surface level
    with pytest.raises(ValueError):
        _ = stresses.get_stresses_at_level(level=-11)


@pytest.mark.auto
def test_calculate_stresses_water_level_in_layer():
    soil_profile = SoilProfile(
        name="sp1",
        surface_level=5,  # m+NAP
        layers=[
            Layer(soil="klei", top=5, bottom=-5),
            Layer("zand", top=-5, bottom=-10),
        ],
        bottom=-10,
    )

    stresses = calculate_stresses(
        soil_profile=soil_profile,
        water_level=0,
        soil_weights={"klei": (15, 15), "zand": (18, 20)},
    )

    assert stresses == SoilStresses(
        phreatic_level=0,
        levels=[5, 0, -5, -10],
        total_stresses=[0, 75, 150, 250],
        pore_water_pressure=[0, 0, 50, 100],
        effective_stresses=[0, 75, 100, 150],
    )


@pytest.mark.auto
def test_calculate_stresses_water_level_on_layer_separation():
    soil_profile = SoilProfile(
        name="sp1",
        surface_level=5,  # m+NAP
        layers=[
            Layer(soil="klei", top=5, bottom=-5),
            Layer("zand", top=-5, bottom=-10),
        ],
        bottom=-10,
    )

    stresses = calculate_stresses(
        soil_profile=soil_profile,
        water_level=-5,
        soil_weights={
            "klei": (
                15,
                20,
            ),  # meant to be different numbers to differentiate volumetric weight
            "zand": (18, 20),
        },
    )

    assert stresses == SoilStresses(
        phreatic_level=-5,
        levels=[5, -5, -10],
        total_stresses=[0, 150, 250],
        pore_water_pressure=[0, 0, 50],
        effective_stresses=[0, 150, 200],
    )


@pytest.mark.auto
def test_calculate_stresses_water_level_above_surface():
    soil_profile = SoilProfile(
        name="sp1",
        surface_level=0,  # m+NAP
        layers=[
            Layer(soil="klei", top=0, bottom=-5),
            Layer("zand", top=-5, bottom=-10),
        ],
        bottom=-10,
    )

    stresses = calculate_stresses(
        soil_profile=soil_profile,
        water_level=5,
        soil_weights={"klei": (15, 15), "zand": (18, 20)},
    )

    assert stresses == SoilStresses(
        phreatic_level=5,
        levels=[0, -5, -10],
        total_stresses=[50, 125, 225],
        pore_water_pressure=[50, 100, 150],
        effective_stresses=[0, 25, 75],
    )


@pytest.mark.auto
def test_soil_profile_get_soil_at_level():
    soil_profile = SoilProfile(
        name="sp1",
        surface_level=0,  # m+NAP
        layers=[
            Layer(soil="klei", top=0, bottom=-5),
            Layer("zand", top=-5, bottom=-10),
        ],
        bottom=-10,
    )

    assert soil_profile.get_soil_at_level(-3) == "klei"
    assert soil_profile.get_soil_at_level(-7) == "zand"

    # Request above surface level
    with pytest.raises(ValueError):
        _ = soil_profile.get_soil_at_level(3)
    # Request below bottom
    with pytest.raises(ValueError):
        _ = soil_profile.get_soil_at_level(12)
