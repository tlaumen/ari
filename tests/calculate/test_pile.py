import numpy as np
import math
from pathlib import Path
from copy import deepcopy

from geolib.models.dfoundations import piles
import pytest
import matplotlib.pyplot as plt

from ceniac.calculate.pile import (
    PileBearingCapacityCalc,
    PileResult,
    PileResults,
    SkinFrictionRanges,
    approx_skin_friction_ranges,
    contributes_to_negative_skin_friction,
    cpts_cover_foundation_all_sides,
    plot_bearing_capacity,
    select_cpts,
    _get_equivalent_diameter,
)
from ceniac.parameters.model import PileFoundationParams
from ceniac.soil_investigation.cpt import Cpt, load_cpt, plot_cpt
from ceniac.calculate.pile import _map_params_to_soils
from ceniac.soil_profile.soil_profile import Layer, SoilProfile, calculate_stresses
from ceniac.calculate.pile import _get_angle_horizontal
from ceniac.calculate.pile import _sort_cpts_counter_clockwise
from ceniac.soil_profile.soil_profile import Layer
from ceniac.calculate.pile import TimeOrderType
from ceniac.calculate.pile import _calculate_mock_negative_skin_friction

zand_params = PileFoundationParams(
    soil="zand",
    K0=0.4,
    gamma_nat=18,
    gamma_sat=20,
    compressible=False,
    friction_angle=30,
    undrained_shear_strength=200,
)
klei_params = PileFoundationParams(
    soil="klei",
    K0=0.5,
    gamma_nat=15,
    gamma_sat=15,
    friction_angle=25,
    undrained_shear_strength=20,
    compressible=True,
)


@pytest.fixture
def setup():
    print("Removing earlier created files")
    fp = Path(__file__).parent / "calc1.fid"
    if fp.exists():
        fp.unlink()


@pytest.mark.auto
def test_map_params_to_soils():
    map_ = _map_params_to_soils(
        soils=["zand", "klei"], soil_params=[zand_params, klei_params]
    )
    assert map_ == {"klei": klei_params, "zand": zand_params}


@pytest.mark.auto
def test_map_params_to_soils_exception():
    with pytest.raises(ValueError):
        _ = _map_params_to_soils(
            soils=["zand", "klei", "veen"], soil_params=[zand_params, klei_params]
        )


@pytest.mark.auto
def test_contributes_to_negative_skin_friction_not_compressible():
    params_map = _map_params_to_soils(
        soils=["zand", "klei"], soil_params=[zand_params, klei_params]
    )

    assert not contributes_to_negative_skin_friction(
        layer=Layer(
            soil="zand",
            top=0,
            bottom=-1,
        ),
        soil_param_map=params_map,
        pile_tip_level=-5,
    )


@pytest.mark.auto
def test_contributes_to_negative_skin_friction_not_thick_enough():
    params_map = _map_params_to_soils(
        soils=["zand", "klei"], soil_params=[zand_params, klei_params]
    )

    assert not contributes_to_negative_skin_friction(
        layer=Layer(
            soil="zand",
            top=0,
            bottom=-0.3,
        ),
        soil_param_map=params_map,
        pile_tip_level=-5,
    )


@pytest.mark.auto
def test_contributes_to_negative_skin_friction_below_pile_tip():
    params_map = _map_params_to_soils(
        soils=["zand", "klei"], soil_params=[zand_params, klei_params]
    )

    assert not contributes_to_negative_skin_friction(
        layer=Layer(
            soil="zand",
            top=-5.5,
            bottom=--8,
        ),
        soil_param_map=params_map,
        pile_tip_level=-5,
    )


@pytest.mark.auto
def test_contributes_to_negative_skin_friction():
    params_map = _map_params_to_soils(
        soils=["zand", "klei"], soil_params=[zand_params, klei_params]
    )

    assert contributes_to_negative_skin_friction(
        layer=Layer(
            soil="klei",
            top=-2,
            bottom=-3,
        ),
        soil_param_map=params_map,
        pile_tip_level=-5,
    )


@pytest.mark.auto
def test_approx_skin_friction_ranges():
    clay_layer = Layer(soil="klei", top=0, bottom=-5)
    sand_layer = Layer(soil="zand", top=-5, bottom=-15)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="", surface_level=0, layers=[clay_layer, sand_layer], bottom=-15
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-7,
    )
    assert skin_friction_ranges == SkinFrictionRanges(
        bottom_negative_skin_friction=-5, top_positive_skin_friction=-5
    )


@pytest.mark.auto
def test_approx_skin_friction_ranges_2():
    clay_layer = Layer(soil="klei", top=0, bottom=-5)
    sand_layer = Layer(soil="zand", top=-5, bottom=-15)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="", surface_level=0, layers=[clay_layer, sand_layer], bottom=-15
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-7,
    )
    assert skin_friction_ranges == SkinFrictionRanges(
        top_positive_skin_friction=-5, bottom_negative_skin_friction=-5
    )


@pytest.mark.auto
def test_approx_skin_friction_ranges_3():
    sand_layer = Layer(soil="zand", top=0, bottom=-15)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="", surface_level=0, layers=[sand_layer], bottom=-15
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-7,
    )
    assert skin_friction_ranges == SkinFrictionRanges(top_positive_skin_friction=0)


@pytest.mark.auto
def test_approx_skin_friction_ranges_4():
    clay_layer = Layer(soil="klei", top=0, bottom=-15)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="", surface_level=0, layers=[clay_layer], bottom=-15
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-7,
    )
    assert skin_friction_ranges == SkinFrictionRanges(
        top_positive_skin_friction=-15, bottom_negative_skin_friction=-15
    )


@pytest.mark.auto
def test_approx_skin_friction_ranges_5():
    # Case with more varying soil profile
    sand1 = Layer("zand", 0, -2)
    clay1 = Layer("klei", -2, -4)
    sand2 = Layer("zand", -4, -6)
    clay2 = Layer("klei", -6, -8)
    sand3 = Layer("zand", -8, -10)
    clay3 = Layer("klei", -10, -12)
    sand4 = Layer("zand", -12, -20)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="",
            surface_level=0,
            layers=[sand1, clay1, sand2, clay2, sand3, clay3, sand4],
            bottom=-20,
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-15,
    )
    assert skin_friction_ranges == SkinFrictionRanges(
        top_positive_skin_friction=-12, bottom_negative_skin_friction=-12
    )


@pytest.mark.auto
def test_approx_skin_friction_ranges_6():
    # Case in which bottom of negative skin friction is below the pile tip level
    # Hence the bottom of nsf and top of psf should be equal to pile tip level
    sand1 = Layer("zand", 0, -2)
    clay1 = Layer("klei", -2, -4)
    sand2 = Layer("zand", -4, -6)
    clay2 = Layer("klei", -6, -8)
    sand3 = Layer("zand", -8, -10)
    clay3 = Layer("klei", -10, -12)
    sand4 = Layer("zand", -12, -20)

    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=SoilProfile(
            name="",
            surface_level=0,
            layers=[sand1, clay1, sand2, clay2, sand3, clay3, sand4],
            bottom=-20,
        ),
        soil_params=[zand_params, klei_params],
        pile_tip_level=-7,
    )
    assert skin_friction_ranges == SkinFrictionRanges(
        top_positive_skin_friction=-7, bottom_negative_skin_friction=-7
    )


@pytest.mark.auto
def test_get_angle_horizontal():
    assert _get_angle_horizontal(
        x=-math.sqrt(2) / 2, y=-math.sqrt(2) / 2, x_center=0, y_center=0
    ) == (math.pi * 5 / 4)
    assert _get_angle_horizontal(
        x=math.sqrt(2) / 2, y=math.sqrt(2) / 2, x_center=0, y_center=0
    ) == (math.pi / 4)
    assert _get_angle_horizontal(x=0, y=1, x_center=0, y_center=0) == (math.pi / 2)
    assert _get_angle_horizontal(x=0, y=-1, x_center=0, y_center=0) == (math.pi * 3 / 2)
    assert _get_angle_horizontal(x=0, y=0, x_center=0, y_center=0) == 0
    assert _get_angle_horizontal(x=-1, y=0, x_center=0, y_center=0) == math.pi


@pytest.mark.auto
def test_sort_cpts_counter_clockwise():
    cpt_0_degrees = Cpt(
        id_="0",
        x=1,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_90_degrees = Cpt(
        id_="0",
        x=0,
        y=1,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_180_degrees = Cpt(
        id_="0",
        x=-1,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_270_degrees = Cpt(
        id_="0",
        x=0,
        y=-1,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpts = _sort_cpts_counter_clockwise(
        cpts=[cpt_180_degrees, cpt_90_degrees, cpt_0_degrees, cpt_270_degrees],
        x_pile=0,
        y_pile=0,
    )
    assert cpts == [cpt_0_degrees, cpt_90_degrees, cpt_180_degrees, cpt_270_degrees]


@pytest.mark.auto
def test_cpts_cover_foundation_all_sides():
    cpt_0_degrees = Cpt(
        id_="0",
        x=1,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_90_degrees = Cpt(
        id_="90",
        x=0,
        y=1,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_180_degrees = Cpt(
        id_="180",
        x=-1,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_270_degrees = Cpt(
        id_="270",
        x=0,
        y=-1,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    assert cpts_cover_foundation_all_sides(
        cpts=[cpt_0_degrees, cpt_180_degrees, cpt_90_degrees, cpt_270_degrees],
        x_pile=0,
        y_pile=0,
    )
    _ = cpts_cover_foundation_all_sides(
        cpts=[cpt_0_degrees, cpt_270_degrees, cpt_180_degrees, cpt_90_degrees],
        x_pile=0,
        y_pile=0,
    )
    assert not cpts_cover_foundation_all_sides(
        cpts=[cpt_0_degrees, cpt_180_degrees, cpt_270_degrees],
        x_pile=0,
        y_pile=0,
    )


@pytest.mark.auto
def test_select_cpts():
    cpt_0_degrees = Cpt(
        id_="0",
        x=1,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_90_degrees = Cpt(
        id_="90",
        x=0,
        y=51,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_180_degrees = Cpt(
        id_="180",
        x=-10,
        y=0,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpt_270_degrees = Cpt(
        id_="270",
        x=0,
        y=-15,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=np.array([]),
        qc=np.array([]),
        fs=np.array([]),
    )
    cpts = [
        cpt_0_degrees,
        cpt_90_degrees,
        cpt_180_degrees,
        cpt_270_degrees,
    ]  # order of input matters for assertion below
    assert select_cpts(cpts=cpts, x_pile=0, y_pile=0) == [
        cpt_0_degrees,
        cpt_180_degrees,
        cpt_270_degrees,
    ]
    assert select_cpts(cpts=cpts, x_pile=0, y_pile=0, max_distance=10) == [
        cpt_0_degrees,
        cpt_180_degrees,
    ]


@pytest.mark.auto
def test_pile_bearing_capacity_calc(setup):
    depths = np.arange(0, -10, -0.02)
    qc = np.full_like(depths, 10)
    cpt = Cpt(
        id_="cpt1",
        x=1,
        y=1,
        surface_level=0,
        predrill_depth=0,
        a_cone=0.8,
        depths=depths,
        qc=qc,
        fs=qc * 0.5 / 100,
    )
    soil_profile = SoilProfile(
        name="", surface_level=0, layers=[Layer("zand", 0, -10)], bottom=-10
    )
    cpt_sp_map = [(cpt, soil_profile)]
    zand = PileFoundationParams(
        soil="zand",
        K0=0.3,
        gamma_nat=18,
        gamma_sat=20,
        friction_angle=30,
        compressible=False,
        undrained_shear_strength=300,
    )
    pile = piles.BearingRoundPile(
        diameter=0.3,
        pile_name="pile1",
        pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,  # TODO: check if correct! only USER DEFINED allowed for this pile
        pile_class_factor_tip=0.3,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.THREE,
        elasticity_modulus=20e3,  # MPA? TODO: check if correct order of magnitude in terms of units
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )

    # ValueError raised because no soil with name 'zand2' is provided
    with pytest.raises(ValueError):
        zand2 = PileFoundationParams(
            soil="",
            K0=0.3,
            gamma_nat=18,
            gamma_sat=20,
            friction_angle=30,
            compressible=False,
            undrained_shear_strength=300,
        )
        soil_profile2 = SoilProfile(
            name="", surface_level=0, layers=[Layer("zand2", 0, -10)], bottom=-10
        )
        cpt_sp_map2 = [(cpt, soil_profile2)]
        pbcc = PileBearingCapacityCalc(
            file_path=Path(__file__).parent / "calc1.fid",
            cpt_soil_profile_map=cpt_sp_map2,
            rigid_construction=False,
            piletip_levels=[-6],
            time_order=TimeOrderType.CPT_INSTALL_EXCAVATION,
            phreatic_level=-1,
            additional_soils=[zand2],
            pile=pile,
            pile_location=(0, 0),
            pile_head_level=0,
            skin_friction_ranges={
                cpt_sp_map2[0][0].id_: SkinFrictionRanges(
                    top_positive_skin_friction=-2, bottom_negative_skin_friction=-2
                )
            },
            future_surface_level=0,
        )
        pbcc._validate_soils()

    pbcc = PileBearingCapacityCalc(
        file_path=Path(__file__).parent / "calc1.fid",
        cpt_soil_profile_map=cpt_sp_map,
        rigid_construction=False,
        piletip_levels=[-6],
        time_order=TimeOrderType.CPT_INSTALL_EXCAVATION,
        phreatic_level=-1,
        additional_soils=[zand],
        pile=pile,
        pile_location=(0, 0),
        skin_friction_ranges={
            cpt_sp_map[0][0].id_: SkinFrictionRanges(
                top_positive_skin_friction=-2, bottom_negative_skin_friction=-2
            )
        },
        future_surface_level=0,
        pile_head_level=0,
    )
    pbcc.build_calculation()
    # pbcc.calculate()


def test_get_equivalent_diameter_round():
    pile = piles.BearingRoundPile(
        diameter=0.3,
        pile_name="pile1",
        pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,  # TODO: check if correct! only USER DEFINED allowed for this pile
        pile_class_factor_tip=0.3,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.THREE,
        elasticity_modulus=20e3,  # MPA? TODO: check if correct order of magnitude in terms of units
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )
    assert _get_equivalent_diameter(pile) == (0.3, 0.3)


def test_get_equivalent_diameter_round_lost_tip():
    pile = piles.BearingRoundPileWithLostTip(
        base_diameter=630 / 1000,  # TODO: check the first argument is the base diameter
        pile_diameter=570
        / 1000,  # TODO: check the second argument is the base diameter
        pile_name="pile1",
        pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,
        pile_class_factor_tip=0.63,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.ONE,
        elasticity_modulus=20e3,
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )
    assert _get_equivalent_diameter(pile) == (0.63, 0.57)


def test_get_equivalent_diameter_rectangular():
    pile = piles.BearingRectangularPile(
        base_width=450 / 1000,
        base_length=450 / 1000,
        pile_name="heipaal1",
        pile_type=piles.PileType.USER_DEFINED_VIBRATING,  # TODO: check if correct type!
        pile_class_factor_tip=0.7,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.ONE,
        elasticity_modulus=20e3,
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )
    equivalent_diameter = math.sqrt((0.45**2) * 4 / math.pi)
    assert _get_equivalent_diameter(pile) == (equivalent_diameter, equivalent_diameter)


def test_get_equivalent_diamteter_not_implemented():
    # Test random object type --> should return NotImplementError
    with pytest.raises(NotImplementedError):
        _ = _get_equivalent_diameter(pile=(...))  # pyright: ignore


def test_calculate_mock_negative_skin_friction():
    zand = PileFoundationParams(
        soil="zand",
        K0=0.3,
        gamma_nat=18,
        gamma_sat=20,
        friction_angle=32,
        compressible=False,
        undrained_shear_strength=300,
    )
    klei = PileFoundationParams(
        soil="klei",
        K0=0.6,
        gamma_nat=16,
        gamma_sat=16,
        friction_angle=25,
        compressible=True,
        undrained_shear_strength=30,
    )

    soil_profile = SoilProfile(
        name="sp1",
        surface_level=0,
        layers=[Layer("zand", 0, -5), Layer("klei", -5, -15), Layer("zand", -15, -52)],
        bottom=-52,
    )
    if not soil_profile.validate:
        raise ValueError(
            f"Something has gone wrong with creating the soil profile: {soil_profile}. The input is invalid"
        )
    stresses = calculate_stresses(
        soil_profile=soil_profile,
        water_level=-1,
        soil_weights={
            zand.soil: (zand.gamma_nat, zand.gamma_sat),
            klei.soil: (klei.gamma_nat, klei.gamma_sat),
        },
    )

    # Test on nsf mock calc until layer separation
    nsf = _calculate_mock_negative_skin_friction(
        soil_profile=soil_profile, stresses=stresses, params=[klei, zand], bottom=-15
    )
    assert math.isclose(
        nsf, 342.2, abs_tol=0.1
    )  # TODO: manual calculation to assess correct!

    # Test on nsf mock calc until somewhere in layer separation
    nsf = _calculate_mock_negative_skin_friction(
        soil_profile=soil_profile, stresses=stresses, params=[klei, zand], bottom=-14
    )
    assert math.isclose(
        nsf, 314.5, abs_tol=0.1
    )  # TODO: manual calculation to assess correct!

    # Test on nsf mock calc until somewhere in layer separation of first layer
    nsf = _calculate_mock_negative_skin_friction(
        soil_profile=soil_profile, stresses=stresses, params=[klei, zand], bottom=-0.5
    )
    assert math.isclose(
        nsf, 1.3, abs_tol=0.1
    )  # TODO: manual calculation to assess correct!

    # Test value error bottom nsf range > surface level
    with pytest.raises(ValueError):
        _ = _calculate_mock_negative_skin_friction(
            soil_profile=soil_profile,
            stresses=stresses,
            params=[klei, zand],
            bottom=2,
        )
    # Test value error bottom nsf range < bottom of soil profile
    with pytest.raises(ValueError):
        _ = _calculate_mock_negative_skin_friction(
            soil_profile=soil_profile,
            stresses=stresses,
            params=[klei, zand],
            bottom=-60,
        )


def test_pile_bearing_capacity_calc_mock_calculate():
    surface_level = 0
    pile_tip_level = -25
    pile = piles.BearingRectangularPile(
        base_width=450 / 1000,
        base_length=450 / 1000,
        pile_name="heipaal1",
        pile_type=piles.PileType.USER_DEFINED_VIBRATING,  # TODO: check if correct type!
        pile_class_factor_tip=0.7,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.ONE,
        elasticity_modulus=20e3,
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )

    zand = PileFoundationParams(
        soil="zand",
        K0=0.3,
        gamma_nat=18,
        gamma_sat=20,
        friction_angle=32,
        compressible=False,
        undrained_shear_strength=300,
    )
    klei = PileFoundationParams(
        soil="klei",
        K0=0.6,
        gamma_nat=16,
        gamma_sat=16,
        friction_angle=25,
        compressible=True,
        undrained_shear_strength=30,
    )

    soil_profile = SoilProfile(
        name="sp1",
        surface_level=surface_level,
        layers=[Layer("zand", 0, -5), Layer("klei", -5, -15), Layer("zand", -15, -52)],
        bottom=-52,
    )

    cpt = load_cpt(Path(__file__).parent.parent / "soil_investigation" / "CPT002.xml")
    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=soil_profile,
        soil_params=[klei, zand],
        pile_tip_level=pile_tip_level,
    )
    cpt_sp_map = [(cpt, soil_profile)]

    # Calculation with only 1 cpt
    pbcc = PileBearingCapacityCalc(
        file_path=Path(__file__).parent / "calc1.fid",
        cpt_soil_profile_map=cpt_sp_map,
        rigid_construction=False,
        piletip_levels=np.arange(pile_tip_level - 2, pile_tip_level + 2, 0.5).tolist(),
        time_order=TimeOrderType.CPT_INSTALL_EXCAVATION,
        phreatic_level=-1,
        additional_soils=[zand, klei],
        pile=pile,
        pile_location=(0, 0),
        skin_friction_ranges={cpt_sp_map[0][0].id_: skin_friction_ranges},
        future_surface_level=surface_level,
        pile_head_level=surface_level,
    )
    pbcc._mock_calculate()
    if pbcc.results is None:
        raise AssertionError(
            "Test failed, the results attribute of the PileBearingCapacityCalc should not be None"
        )
    result1 = pbcc.results.results[0]
    assert (
        result1.rep_bearing_capacity
        == result1.bc_shaft_rep + result1.bc_tip_rep - result1.nsf_rep
    )

    # Calculate the design value
    filtered_results = [
        res for res in pbcc.results.results if res.tip_level == pile_tip_level
    ]
    if len(filtered_results) != 1:
        raise ValueError(
            f"The pile tip level: {pile_tip_level} is not in the results. This should be the case, the implementation of the test in this fashion is invalid"
        )
    result2 = filtered_results[0]
    design_bearing_capacity = pbcc.calculate_design_bearing_capacity(
        pile_tip_level=pile_tip_level
    )
    assert (
        design_bearing_capacity == result2.rep_bearing_capacity / 1.39
    )  # TODO: assess if correct for 1 CPT in a non-rigid structure

    # If the wrong tip level is requested -> raise ValueError
    with pytest.raises(ValueError):
        _ = pbcc.calculate_design_bearing_capacity(pile_tip_level=pile_tip_level - 5)

    # Calculation with multiple cpts
    cpt2 = deepcopy(cpt)
    name = "CPT2"
    cpt2.id_ = name

    soil_profile2 = SoilProfile(
        name="sp2",
        surface_level=cpt.surface_level,
        layers=[Layer("zand", cpt2.surface_level, cpt.bottom)],
        bottom=cpt.bottom,
    )
    cpt_sp_map.append((cpt2, soil_profile2))
    pbcc = PileBearingCapacityCalc(
        file_path=Path(__file__).parent / "calc1.fid",
        cpt_soil_profile_map=cpt_sp_map,
        rigid_construction=False,
        piletip_levels=np.arange(pile_tip_level - 2, pile_tip_level + 2, 0.5).tolist(),
        time_order=TimeOrderType.CPT_INSTALL_EXCAVATION,
        phreatic_level=-1,
        additional_soils=[zand, klei],
        pile=pile,
        pile_location=(0, 0),
        skin_friction_ranges={
            cpt_sp_map[0][0].id_: skin_friction_ranges,
            cpt_sp_map[1][0].id_: skin_friction_ranges,
        },
        future_surface_level=surface_level,
        pile_head_level=surface_level,
    )
    pbcc._mock_calculate()


@pytest.mark.auto
def test_plot_bearing_capacity():
    pile = piles.BearingRectangularPile(
        base_width=450 / 1000,
        base_length=450 / 1000,
        pile_name="heipaal1",
        pile_type=piles.PileType.USER_DEFINED_VIBRATING,  # TODO: check if correct type!
        pile_class_factor_tip=0.7,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.ONE,
        elasticity_modulus=20e3,
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )
    cpt = load_cpt(Path(__file__).parent.parent / "soil_investigation" / "CPT002.xml")

    top_tip_level = -20
    bc_shaft_top = 1000
    bc_tip_top = 1500
    nsf_top = 200
    results = PileResults(
        pile=pile,
        results=[
            PileResult(
                cpt=cpt,
                tip_level=top_tip_level,
                bc_shaft_rep=bc_shaft_top,
                bc_tip_rep=bc_tip_top,
                nsf_rep=nsf_top,
                design_bearing_capacity=bc_shaft_top + bc_tip_top - nsf_top,
            ),
            PileResult(
                cpt=cpt,
                tip_level=top_tip_level - 1,
                bc_shaft_rep=bc_shaft_top + 100,
                bc_tip_rep=bc_tip_top + 200,
                nsf_rep=nsf_top,
                design_bearing_capacity=bc_shaft_top + 100 + bc_tip_top + 200 - nsf_top,
            ),
            PileResult(
                cpt=cpt,
                tip_level=top_tip_level - 2,
                bc_shaft_rep=bc_shaft_top + 200,
                bc_tip_rep=bc_tip_top + 500,
                nsf_rep=nsf_top,
                design_bearing_capacity=bc_shaft_top + 200 + bc_tip_top + 500 - nsf_top,
            ),
            PileResult(
                cpt=cpt,
                tip_level=top_tip_level - 3,
                bc_shaft_rep=bc_shaft_top + 300,
                bc_tip_rep=bc_tip_top + 700,
                nsf_rep=nsf_top,
                design_bearing_capacity=bc_shaft_top + 300 + bc_tip_top + 700 - nsf_top,
            ),
            PileResult(
                cpt=cpt,
                tip_level=top_tip_level - 4,
                bc_shaft_rep=bc_shaft_top + 500,
                bc_tip_rep=bc_tip_top + 400,
                nsf_rep=nsf_top,
                design_bearing_capacity=bc_shaft_top + 500 + bc_tip_top + 400 - nsf_top,
            ),
        ],
    )

    fig, ax = plot_bearing_capacity(
        calculation_name="Heipaal vierkant 450", results=results
    )
    assert isinstance(fig, plt.Figure)  # pyright: ignore
    assert isinstance(ax, plt.Axes)  # pyright: ignore
