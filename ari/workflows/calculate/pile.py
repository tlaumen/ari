from enum import StrEnum
import tkinter as tk

from geolib.models.dfoundations import piles

from ceniac.soil_investigation.cpt import Cpt
from ceniac.calculate.pile import TimeOrderType
from ceniac.soil_profile.soil_profile import SoilProfile

from ari.map_selector import MapPointSelector


TIME_ORDER_QUERY_MAP = [
    (TimeOrderType.CPT_EXCAVATION_INSTALL, "cpt -> excavate -> install"),
    (TimeOrderType.INSTALL_CPT_EXCAVATION, "install pile -> cpt -> excavate"),
    (TimeOrderType.EXCAVATION_CPT_INSTALL, "excavate -> cpt -> install pile"),
    (TimeOrderType.EXCAVATION_INSTALL_CPT, "excavate -> install pile -> cpt"),
    (TimeOrderType.INSTALL_EXCAVATION_CPT, "install pile -> excavate -> cpt"),
    (TimeOrderType.CPT_INSTALL_EXCAVATION, "cpt -> install pile -> excavate"),
    (TimeOrderType.CPT_BEFORE_AND_AFTER_INSTALL, "cpt -> install -> cpt"),
]


class PileType(StrEnum):
    PREFAB_HEIPAAL = "Prefab heipaal"
    VIBROPAAL = "Vibropaal"
    SCHROEFPAAL = "Schroefpaal"
    BUISSCHROEFPAAL = "Buisschroefpaal"
    BUISSCHROEFPAAL_VERLOREN_CASING = "Schroefpaal met verloren casing"


SLS_LOAD_KEY = "bgt-verticale-belasting"
ULS_LOAD_KEY = "ugt-verticale-belasting"
PILE_TYPE_KEY = "paaltype"
PILE_DIMENSIONS_KEY = "paalafmetingen"
PILE_LOCATION_KEY = "coordinaten-paal"
SOIL_INVESTIGATION_TOPVIEW_IMAGE = "bovenaanzicht-grondonderzoek"
PILE_TIP_LEVEL_KEY = "paalpuntniveau"
WORK_ORDER_KEY = "cpt-uitvoering-werkvolgorde"
PHREATIC_LEVEL_KEY = "grondwaterniveau"
STRUCTURE_RIGIDITY_KEY = "constructie-stijf?"
FUTURE_GROUND_LEVEL_KEY = "toekomstig-maaiveld-niveau"
CALCULATION_RESULTS_KEY = "berekeningsresultaten"
SKIN_FRICTION_RANGES_KEY = "negatieve-positieve-kleef-trajecten"


# ----------------- LOGIC --------------------------


def combine_soil_profiles_cpts(
    cpts: list[Cpt], soil_profiles: list[SoilProfile], sp_cpt_mapping: dict[str, str]
) -> list[tuple[Cpt, SoilProfile]]:
    cpt_sp_map: list[tuple[Cpt, SoilProfile]] = []
    for soil_profile_name, cpt_id in sp_cpt_mapping.items():
        for cpt in cpts:
            if cpt.id_ == cpt_id:
                break
        else:
            print()
            raise ValueError(
                f"The cpt in the mapping: {cpt_id} is not present in the list of cpts."
            )

        for soil_profile in soil_profiles:
            if soil_profile.name == soil_profile_name:
                break
        else:
            raise ValueError(
                f"The soil profile in the mapping: {soil_profile_name} is not present in the list of soil profiles."
            )
        cpt_sp_map.append((cpt, soil_profile))
    return cpt_sp_map


def pile_location_selector(cpts: list[Cpt]) -> MapPointSelector:
    """UI element to select location on map"""
    root = tk.Tk()
    selector = MapPointSelector(root, cpts)

    return selector


def create_pile(
    pile_type: PileType, dimensions: float | tuple[float, float]
) -> piles.BearingPile:
    """Dimensions are filled in in mm"""
    # return None #TODO: implement properly!
    youngs_modulus = 25e6  # kPa --> not cracked, 10e6 if cracked #TODO: chekc how cracking can be implemented
    match pile_type:
        case PileType.SCHROEFPAAL:
            if not isinstance(dimensions, float | int):
                raise ValueError(
                    f"The dimensions for a 'SCHROEFPAAL' should only be the diameter, not: {dimensions}"
                )
            return piles.BearingRoundPile(
                diameter=dimensions / 1000,
                pile_name=f"{pile_type.name}_{dimensions}",
                pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,  # TODO: check if correct! only USER DEFINED allowed for this pile
                pile_class_factor_tip=0.3,  # alpha_p -> TODO: check if correct
                pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
                preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
                overrule_pile_tip_shape_factor=False,
                characteristic_adhesion=10,  # TODO: check what does and if correct!
                load_settlement_curve=piles.LoadSettlementCurve.THREE,
                elasticity_modulus=youngs_modulus,
                use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
                user_defined_pile_type_as_prefab=False,
                overrule_pile_tip_cross_section_factors=False,
            )
        case PileType.PREFAB_HEIPAAL:
            if not isinstance(dimensions, float | int):
                raise ValueError(
                    f"The dimensions for a 'PREFAB_HEIPAAL' should only be the diameter, not: {dimensions}"
                )
            return piles.BearingRectangularPile(
                base_width=dimensions / 1000,
                base_length=dimensions / 1000,
                pile_name=f"{pile_type.name}_{dimensions}",
                pile_type=piles.PileType.USER_DEFINED_VIBRATING,  # TODO: check if correct type!
                pile_class_factor_tip=0.7,  # alpha_p -> TODO: check if correct
                pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
                preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
                overrule_pile_tip_shape_factor=False,
                characteristic_adhesion=10,  # TODO: check what does and if correct!
                load_settlement_curve=piles.LoadSettlementCurve.ONE,
                elasticity_modulus=youngs_modulus,
                use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
                user_defined_pile_type_as_prefab=False,
                overrule_pile_tip_cross_section_factors=False,
            )
        case PileType.BUISSCHROEFPAAL:
            if not isinstance(dimensions, tuple) or len(dimensions) != 2:
                raise ValueError(
                    f"The dimensions for a 'PREFAB_HEIPAAL' should be both the diameter of the shaft and tip, not: {dimensions}"
                )
            return piles.BearingRoundPileWithLostTip(
                base_diameter=dimensions[0]
                / 1000,  # TODO: check the first argument is the base diameter
                pile_diameter=dimensions[1]
                / 1000,  # TODO: check the second argument is the base diameter
                pile_name=f"{pile_type.name}_{dimensions[0]}",
                pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,
                pile_class_factor_tip=0.63,  # alpha_p -> TODO: check if correct
                pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
                preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
                overrule_pile_tip_shape_factor=False,
                characteristic_adhesion=10,  # TODO: check what does and if correct!
                load_settlement_curve=piles.LoadSettlementCurve.ONE,
                elasticity_modulus=youngs_modulus,
                use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
                user_defined_pile_type_as_prefab=False,
                overrule_pile_tip_cross_section_factors=False,
            )
        case PileType.BUISSCHROEFPAAL_VERLOREN_CASING:
            if not isinstance(dimensions, tuple) or len(dimensions) != 2:
                raise ValueError(
                    f"The dimensions for a 'PREFAB_HEIPAAL' should be both the diameter of the shaft and tip, not: {dimensions}"
                )
            return piles.BearingRoundPileWithLostTip(
                base_diameter=dimensions[0]
                / 1000,  # TODO: check the first argument is the base diameter
                pile_diameter=dimensions[1]
                / 1000,  # TODO: check the second argument is the base diameter
                pile_name=f"{pile_type.name}_{dimensions[0]}",
                pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,
                pile_class_factor_tip=0.63,  # alpha_p -> TODO: check if correct
                pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
                preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
                overrule_pile_tip_shape_factor=False,
                characteristic_adhesion=10,  # TODO: check what does and if correct!
                load_settlement_curve=piles.LoadSettlementCurve.ONE,
                elasticity_modulus=youngs_modulus,
                use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
                user_defined_pile_type_as_prefab=False,
                overrule_pile_tip_cross_section_factors=False,
            )
        case PileType.VIBROPAAL:
            if not isinstance(dimensions, tuple) or len(dimensions) != 2:
                raise ValueError(
                    f"The dimensions for a 'PREFAB_HEIPAAL' should be both the diameter of the shaft and tip, not: {dimensions}"
                )
            return piles.BearingRoundPileWithLostTip(
                base_diameter=dimensions[0]
                / 1000,  # TODO: check the first argument is the base diameter
                pile_diameter=dimensions[1]
                / 1000,  # TODO: check the second argument is the base diameter
                pile_name=f"{pile_type.name}_{dimensions[0]}",
                pile_type=piles.PileType.USER_DEFINED_VIBRATING,  # TODO: USER_DEFINED piles.PileType required, assess if correct!
                pile_class_factor_tip=0.8,  # alpha_p -> TODO: check if correct
                pile_class_factor_shaft_sand_gravel=0.012,  # alpha_s -> TODO: check if correct
                preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
                overrule_pile_tip_shape_factor=False,
                characteristic_adhesion=10,  # TODO: check what does and if correct!
                load_settlement_curve=piles.LoadSettlementCurve.ONE,
                elasticity_modulus=youngs_modulus,
                use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
                user_defined_pile_type_as_prefab=False,
                overrule_pile_tip_cross_section_factors=False,
            )
