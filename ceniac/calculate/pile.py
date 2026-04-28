from dataclasses import dataclass, field
from itertools import pairwise
import math
from pathlib import Path
import re
import statistics

from geolib.models.dfoundations import profiles
from geolib.models.dfoundations.profiles import TimeOrderType
from geolib.models.dfoundations.dfoundations_model import DFoundationsModel
import geolib as gl
from geolib.soils import Soil
from geolib.models.dfoundations import piles
from geolib.models.dfoundations.piles import BearingPile
import matplotlib.pyplot as plt
import numpy as np

from ceniac.soil_profile.soil_profile import (
    SoilProfile,
    SoilStresses,
    calculate_stresses,
)
from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import Layer
from ceniac.parameters.model import PileFoundationParams
from ceniac.parameters.model import Color

from .base import Calculation

MIN_THICKNESS_NEGATIVE_SF = (
    0.5  # assuming 10% strain, less than 0.5 m does not contribute significantly
)


@dataclass
class SkinFrictionRanges:
    """Class that defines the ranges of skin friction over the depth of a soil profile"""

    top_positive_skin_friction: float  # m+NAP
    bottom_negative_skin_friction: float | None = None  # m+NAP


def _map_params_to_soils(
    soils: list[str], soil_params: list[PileFoundationParams]
) -> dict[str, PileFoundationParams]:
    """Private function to map the provided soil parameters to the provided soil based on the names"""
    _soils = set(soils)  # remove duplicate soils
    soil_param_map: dict[str, PileFoundationParams] = {}
    for soil in _soils:
        for params in soil_params:
            if soil == params.soil:
                soil_param_map[soil] = params
                break
        else:
            raise ValueError(
                f"Soil: {soil} not defined in the parameters. Please make sure all soils are defined in the parameters!"
            )
    return soil_param_map


def contributes_to_negative_skin_friction(
    layer: Layer, soil_param_map: dict[str, PileFoundationParams], pile_tip_level: float
) -> bool:
    """Check if a layer contributes to the negative skin friction based on the parameters of the present soil and its thickness"""
    if not soil_param_map[layer.soil].compressible:
        return False
    if layer.thickness < MIN_THICKNESS_NEGATIVE_SF:
        return False
    if layer.top <= pile_tip_level:
        return False
    return True


def approx_skin_friction_ranges(
    soil_profile: SoilProfile,
    soil_params: list[PileFoundationParams],
    pile_tip_level: float,
) -> SkinFrictionRanges:
    """Automatically makes a naive approximation of the skin friction ranges based on material parameters"""
    soil_param_map = _map_params_to_soils(
        soils=[l.soil for l in soil_profile.layers], soil_params=soil_params
    )
    layer_negative_skin_friction_map: list[bool] = [
        contributes_to_negative_skin_friction(
            layer=layer, soil_param_map=soil_param_map, pile_tip_level=pile_tip_level
        )
        for layer in soil_profile.layers
    ]
    if not any(layer_negative_skin_friction_map):
        return SkinFrictionRanges(top_positive_skin_friction=soil_profile.surface_level)
    if all(layer_negative_skin_friction_map):
        # TODO: add logging warning here that probably something will go wrong in the calculation
        return SkinFrictionRanges(
            top_positive_skin_friction=soil_profile.bottom,
            bottom_negative_skin_friction=soil_profile.bottom,
        )

    bottom_nsf: float = soil_profile.surface_level
    for i, layer in enumerate(soil_profile.layers):
        if any(layer_negative_skin_friction_map[i + 1 :]):
            continue
        bottom_nsf = layer.bottom
        break

    # TODO: assess if necessary for D-Foundation calculations
    # Prevents top positive skin friction being below pile tip level
    if bottom_nsf < pile_tip_level:
        bottom_nsf = pile_tip_level
    return SkinFrictionRanges(
        top_positive_skin_friction=bottom_nsf, bottom_negative_skin_friction=bottom_nsf
    )


def select_skin_friction_areas(
    cpt: Cpt,
    soil_profile: SoilProfile,
    soil_params: list[PileFoundationParams],
    pile_tip_level: float,
    soil_colors: list[Color],
) -> SkinFrictionRanges:
    """
    Select the depth ranges where the positive and negative skin friction is applied.
        - step 1: an automatic, naive approximation is made
        - step 2: the ranges can be adapted based on user input
    """

    # 0. TODO: Validate input(?)
    # assess if Almere rules apply based on coordinates
    # if so --> logging message!

    # 1. Make an automated guess
    skin_friction_ranges = approx_skin_friction_ranges(
        soil_profile=soil_profile,
        soil_params=soil_params,
        pile_tip_level=pile_tip_level,
    )
    return skin_friction_ranges
    # TODO: for future, add human interpretation on top of automatic!
    # 2. show the manual interpretation
    # skin_friction_ranges = manual_range_check(
    #     skin_friction_ranges=skin_friction_ranges,
    #     cpt=cpt,
    #     soil_profile=soil_profile,
    #     soil_color_map=soil_color_map,
    #     pile_tip_level=pile_tip_level,
    # )
    # return skin_friction_ranges


def _get_angle_horizontal(
    x: float, y: float, x_center: float, y_center: float
) -> float:
    """
    Get the angle of the cpt with the pile relative to the horizontal.
    Analoguous to the unit circle:
        - horizontal on the right/East side is 0 degrees
        - vertical on the top/North side is 90 degrees
        - horizontal on the left/West side is 180 degrees
        - vertical on the bottom/South side is 270 degrees
    """
    # Determine angle with horizontal in radians from inverse of tangent
    # tan(theta) = dy / dx
    # theta = tan-1(dy/dx) (in radians)
    theta = math.atan2(y - y_center, x - x_center)
    if (
        theta < 0
    ):  # from negative radians to positive radians to sort counter clockwise from horizontal
        theta += 2 * math.pi
    return theta


def _sort_cpts_counter_clockwise(cpts: list[Cpt], x_pile: float, y_pile: float):
    """Sort all cpts rotated around the pile counterclockwise"""
    cpt_angle_map: list[tuple[Cpt, float]] = [
        (cpt, _get_angle_horizontal(x=cpt.x, y=cpt.y, x_center=x_pile, y_center=y_pile))
        for cpt in cpts
    ]
    cpt_angle_map.sort(key=lambda x: x[1])
    return [cpt for cpt, _ in cpt_angle_map]


def cpts_cover_foundation_all_sides(
    cpts: list[Cpt], x_pile: float, y_pile: float, max_angle: int = 110
):
    """Assess that the cpts cover a pile in all directions"""
    # Sort cpts counterclockwise
    cpts = _sort_cpts_counter_clockwise(cpts, x_pile, y_pile)
    angles = [
        _get_angle_horizontal(x=cpt.x, y=cpt.y, x_center=x_pile, y_center=y_pile)
        for cpt in cpts
    ]

    # Check all angles conform the norm
    for angle1, angle2, cpt1, cpt2 in zip(angles[:-1], angles[1:], cpts[:-1], cpts[1:]):
        angle = (angle2 - angle1) * 360 / (2 * math.pi)
        print(angle)
        if angle < 0:
            raise ValueError(
                "Cpt's are not sorted correctly, angle between adjacent cpts should be positive"
            )
        if angle > max_angle:
            print(
                f"The angle between {cpt1.id_} and {cpt2.id_} is {round(angle, 1)}. This is larger than the allowed: {max_angle} to comply with NEN9997-1"
            )  # TODO: setup logging correctly
            return False
    return True


def select_cpts(
    cpts: list[Cpt], x_pile: float, y_pile: float, max_distance: int = 25
) -> list[Cpt]:
    """
    Select cpts within a maximum distance of the pile and then check they cover the pile as required conform the eurocode NEN9997-1
    The variables x_pile and y_pile are the coordinates of the pile in the RD coordinate system
    """
    # 0. Check the cpts are within the required maximum distance
    cpts_filtered_distance: list[Cpt] = []
    for cpt in cpts:
        distance = ((cpt.x - x_pile) ** 2 + (cpt.y - y_pile) ** 2) ** 0.5
        if distance <= max_distance:
            cpts_filtered_distance.append(cpt)

    if len(cpts_filtered_distance) == 0:
        raise ValueError(
            f"Of cpts: {[cpt.id_ for cpt in cpts]}, none are within {max_distance} m of the pile, at: ({x_pile}, {y_pile}) (RD coordinates)"
        )

    # 1. Check the cpts cover the Pile adequantely
    # if not --> log warning --> does not comply with NEN9997-1
    cpts_cover_foundation_all_sides(cpts_filtered_distance, x_pile, y_pile)
    return cpts_filtered_distance


def extract_name(s: str):
    """
    Extract the value between 'name=' and ',' using regex.

    Args:
        s (str): The input string to search

    Returns:
        str: The extracted value, or None if pattern not found
    """
    match = re.search(r"name=([^,]*)", s)
    return match.group(1) if match else None


@dataclass
class PileResult:
    """Stores result of a single calculation"""

    cpt: Cpt
    tip_level: float  # m+NAP
    bc_shaft_rep: float  # kN
    bc_tip_rep: float  # kN
    nsf_rep: float  # kN
    design_bearing_capacity: float  # kN

    @property
    def rep_bearing_capacity(self) -> float:
        if self.nsf_rep < 0:
            raise ValueError("It is assumed the negative skin friction is positive")
        return self.bc_shaft_rep + self.bc_tip_rep - self.nsf_rep


@dataclass
class PileResults:
    """Stores the bearing capacity results for a pile for every pile tip level calculated and for every cpt taken into account"""

    pile: BearingPile
    results: list[PileResult]


@dataclass
class PileBearingCapacityCalc(Calculation):
    """Class that makes a vertical pile bearing capacity calculation using the Deltares series sofware API geolib"""

    file_path: Path
    cpt_soil_profile_map: list[tuple[Cpt, SoilProfile]]
    rigid_construction: bool
    piletip_levels: list[float]  # m+NAP
    time_order: TimeOrderType
    phreatic_level: float  # m+NAP
    additional_soils: list[PileFoundationParams]
    pile: BearingPile
    pile_location: tuple[float, float]  # x coord and y coord in RD coords
    pile_head_level: float  # level of the top of the pile in m+NAP, can differ from future surface level in case of pile cap
    future_surface_level: float
    skin_friction_ranges: dict[
        str, SkinFrictionRanges
    ]  # dictionary {cpt_name: <skin friction range object>, ...}
    _model: DFoundationsModel = field(default_factory=DFoundationsModel)
    _pile_n: int = 0
    results: PileResults | None = None  # only there after making calculation

    def get_results(self) -> "PileResults | None":
        """Gets results from the pile bearing capacity calculation.

        Returns:
            PileResults: The results of the bearing capacity calculation,
                        or None if calculate() was called but not _mock_calculate().
        """
        return self.results

    def _validate_soils(self):
        """Validates all soils in the soil profiles are either part of the default"""
        # TODO: add checks that the following attributes are in the additional_soils:
        #    - name
        #    - mohr_coulomb_parameters.friction_angle
        #    - undrained_parameters.undrained_shear_strength
        # for soil in self.additional_soils:
        #     if soil.soil is None:
        #         raise ValueError(
        #             "The attribute `name` should be set on the Soil object"
        #         )

        #     if soil.mohr_coulomb_parameters.friction_angle is None:
        #         raise ValueError(
        #             "The attribute `mohr_coulom_parameters.friction_angle` should be set on the Soil object"
        #         )

        #     if soil.undrained_parameters.undrained_shear_strength is None:
        #         raise ValueError(
        #             "The attribute `undrained_parameters.undrained_shear_strength` should be set on the Soil object"
        #         )

        # Validate all soils required are actually added
        default_soils: list[str] = []
        for s in self._model.soils:
            for soil in s[1]:
                default_soils.append(soil.name)

        # default_soils: list[str] = [soil[1].name for soil in self._model.soils[0]]
        soils_in_profiles: set[str] = {
            layer.soil
            for _, profile in self.cpt_soil_profile_map
            for layer in profile.layers
        }
        soils_to_add: list[str] = [
            soil for soil in soils_in_profiles if soil not in default_soils
        ]
        # Check only the soils in the soil profile that are non-default soils
        _names_soils_to_add: list[str] = [soil.soil for soil in self.additional_soils]
        print(_names_soils_to_add)
        for soil in soils_to_add:
            if soil not in _names_soils_to_add:
                raise ValueError(
                    f"The soil: {soil} is in one of the soil profiles but not a default soil and not included in the additional soils to add! It should be added to the additonal_soils argument"
                )

    def _set_model_options(self):
        """Sets model and calculation options, boilerplate stuff to configure the model"""
        model_options = gl.models.dfoundations.dfoundations_model.BearingPilesModel(
            is_rigid=self.rigid_construction,  # pyright: ignore
            factor_xi3=self._calc_ksi3(len(self.cpt_soil_profile_map)),
        )

        # From pile tip levels -> get top, bottom and interval for calculation (needs to be in this format for the indicative calculation)
        if len(self.piletip_levels) == 1:
            top_tip_level = self.piletip_levels[0]
            bottom_tip_level = self.piletip_levels[0]
            interval = 1  # randomly chosen
        elif len(self.piletip_levels) > 1:
            if self.piletip_levels[0] != max(self.piletip_levels):  # max = top level
                raise ValueError("The first pile tip level should be the top level")
            if self.piletip_levels[-1] != min(
                self.piletip_levels
            ):  # min = bottom level
                raise ValueError("The last pile tip level should be the bottom level")
            top_tip_level = self.piletip_levels[0]
            bottom_tip_level = self.piletip_levels[-1]
            interval = self.piletip_levels[0] - self.piletip_levels[1]
            if any(
                math.isclose(ptl_0 - ptl_1, interval, abs_tol=1e-2)
                for ptl_0, ptl_1 in pairwise(self.piletip_levels)
            ):
                raise ValueError(
                    f"Not all pile tip levels have in the same interval! This should be the case. Current input: {self.piletip_levels}"
                )
        else:
            raise ValueError("The number of piletip levels should be at least 1")

        # Creat the calculation options object
        calculation_options = gl.models.dfoundations.dfoundations_model.CalculationOptions(
            calculationtype=gl.models.dfoundations.dfoundations_model.CalculationType.INDICATION_BEARING_CAPACITY,
            trajectory_begin=top_tip_level,
            trajectory_end=bottom_tip_level,
            trajectory_interval=interval,
        )
        self._model.set_model(model_options, calculation_options)

    def _create_gl_soil(self, params: PileFoundationParams) -> Soil:
        # At the minimum, the following parameters should be set
        #    - name
        #    - mohr_coulomb_parameters.friction_angle
        #    - undrained_parameters.undrained_shear_strength
        soil = Soil()
        soil.name = params.soil
        soil.soil_weight_parameters.unsaturated_weight = params.gamma_nat  # pyright: ignore
        soil.soil_weight_parameters.saturated_weight = params.gamma_sat  # pyright: ignore
        soil.mohr_coulomb_parameters.friction_angle = params.friction_angle  # pyright: ignore
        soil.undrained_parameters.undrained_shear_strength = (
            params.undrained_shear_strength
        )  # pyright: ignore
        return soil

    def _add_soils(self):
        """
        Add soils that are present in the model but not yet present in the DFoundationModel
        These soil should have the following attributes:
            - name
            - mohr_coulomb_parameters.friction_angle
            - undrained_parameters.undrained_shear_strength
        """
        self._validate_soils()  # validates all soils present in the soil profiles are actually provided in the parameters
        for soil in self.additional_soils:  # pyright: ignore
            soil: Soil = self._create_gl_soil(soil)  # pyright: ignore
            self._model.add_soil(soil)

    def _calc_ksi3(self, n_cpts: int):
        return calc_ksi3(rigid_construction=self.rigid_construction, n_cpts=n_cpts)

    def _calc_ksi4(self, n_cpts: int):
        return calc_ksi4(rigid_construction=self.rigid_construction, n_cpts=n_cpts)

    def _add_cpt_soil_profile_couple(self, cpt: Cpt, soil_profile: SoilProfile):
        # Create cpt geolib cpt object
        cpt_gl = profiles.CPT(
            cptname=cpt.id_,
            groundlevel=cpt.surface_level,
            measured_data=[{"z": z, "qc": qc} for z, qc in zip(cpt.levels, cpt.qc)],
            timeorder_type=self.time_order,
        )

        excavation = profiles.Excavation(excavation_level=self.future_surface_level)

        # Create a soil profile based on the created cpt and the excavation
        layers: list[dict[str, str | float]] = []
        for layer in soil_profile.layers:
            layers.append(
                {
                    "material": layer.soil,
                    "top_level": layer.top,
                    "excess_pore_pressure_top": 0.0,
                    "excess_pore_pressure_bottom": 0.0,
                    "ocr_value": 1.0,
                    "reduction_cone_resistance": 0,
                }
            )
        for pile_tip_level in self.piletip_levels:
            soil_profile_gl = profiles.Profile(
                name=f"{cpt.id_}_{round(pile_tip_level, 1)}",
                location=profiles.Point(x=cpt.x, y=cpt.y),
                phreatic_level=self.phreatic_level,
                pile_tip_level=pile_tip_level,
                cpt=cpt_gl,
                layers=layers,
                excavation=excavation,
            )
            self._model.add_profile(soil_profile_gl)

    def _add_pile(self):
        pile_name = f"pile{self._pile_n}"
        # Add Bearing Pile
        location = piles.BearingPileLocation(
            pile_name=pile_name,
            point=profiles.Point(x=self.pile_location[0], y=self.pile_location[1]),
            pile_head_level=self.pile_head_level,
            surcharge=0,  # TODO: check what this is!
            limit_state_str=1,  # TODO: check what this is, probably load ULS
            limit_state_service=1,  # TODO: check what this is, probably load SLS
        )
        self._model.add_pile_if_unique(self.pile, location)

    def build_calculation(self):
        # 0. Setup model and calculation options
        self._set_model_options()

        # 1. Add non-default soils
        self._add_soils()

        # 2. Add cpts and soil profiles
        for cpt, soil_profile in self.cpt_soil_profile_map:
            self._add_cpt_soil_profile_couple(cpt=cpt, soil_profile=soil_profile)

        # 3. Add Pile
        self._add_pile()

        # 4. Dump model
        if self.file_path.exists():
            raise ValueError(f"Calculation file on: {self.file_path} already exists!")
        self._model.serialize(self.file_path)

    def calculate(self):
        if not self.file_path.exists():
            raise ValueError(
                "The calculation file was not yet build. Please first run the 'build_calculation' method!"
            )
        self._model.execute()

        # TODO: add logic to set results

    def calculate_design_bearing_capacity(
        self, pile_tip_level: float, cpts_to_use: list[str] | None = None
    ):
        """
        Takes the representative results and calculates the design value taking into account the uncertainty.
        Note that the `calculate` method should be run before this can be run.
        If not all cpts should be used, due to (too) high variance, the cpts to be used can be provided
        """
        if self.results is None:
            raise ValueError(
                "The bearing capacities should be performed before the design value can be determined"
            )

        if not any(
            math.isclose(res.tip_level, pile_tip_level, abs_tol=1e-2)
            for res in self.results.results
        ):
            raise ValueError(
                f"Pile tip level: {pile_tip_level} is not present in the results: {set([res.tip_level for res in self.results.results])}"
            )

        # Set `cpts_to_use` in case of default value
        if cpts_to_use is None:
            cpts_to_use = [
                r.cpt.id_ for r in self.results.results
            ]  # TODO: check the cpt id_ is correct use

        relevant_results = [
            res
            for res in self.results.results
            if math.isclose(res.tip_level, pile_tip_level, abs_tol=1e-2)
        ]

        # In case of only 1 cpt, the statistics cannot be determined
        if len(relevant_results) == 1:
            print(
                "A pile calculation is never valid in accordance with the NEN9997-1 with only 1 cpt. It should be covert from all directions"
            )  # TODO: add to logging
            return (
                relevant_results[0].rep_bearing_capacity / self._calc_ksi3(1)
            )  # TODO: check NEN9997-1 for other partial factor are required to calculate the design value

        avg_bc = statistics.mean(
            [
                r.rep_bearing_capacity
                for r in relevant_results
                if r.cpt.id_ in cpts_to_use
            ]
        )
        std_bc = statistics.stdev(
            [
                r.rep_bearing_capacity
                for r in relevant_results
                if r.cpt.id_ in cpts_to_use
            ]
        )

        # Assess the statistics of the variation
        if std_bc / avg_bc > 0.12:
            print(
                "To reduce the variance:\n\t1. Check if cpt's with lower bearing capacity are covered by others\n\t2. Remove the cpt's with too high bearing capacity\n\t3. Make multiple areas in case of a 'field of piles' foundation"
            )  # TODO: add to logging
            # TODO: when this happens -> plot image with pile, the cpt's and their respective bearing capacities
            raise ValueError(
                "The coefficient of variation of all used bearing capacities should be below 12%"
            )  # TODO: this is not complete, higher variance is allowed for distance cpt - pile < 25 m

        return (
            avg_bc / self._calc_ksi3(n_cpts=len(cpts_to_use))
        )  # TODO: check NEN9997-1 for other partial factor are required to calculate the design value

    def _mock_calculate(self):
        """Mock implementation that roughly calculates bearing capacity in compression for development purposes"""
        results: list[PileResult] = []
        for pile_tip_level in self.piletip_levels:
            for cpt, soil_profile in self.cpt_soil_profile_map:
                # Get skin friction ranges
                skin_friction_range = self.skin_friction_ranges[cpt.id_]
                if skin_friction_range.bottom_negative_skin_friction is not None:
                    if (
                        skin_friction_range.bottom_negative_skin_friction
                        < pile_tip_level
                    ):
                        raise ValueError(
                            "The bottom of the negative skin friction range is below the pile tip level!"
                        )
                    bottom_nsf = skin_friction_range.bottom_negative_skin_friction
                else:
                    bottom_nsf = soil_profile.surface_level

                # Get pile diameters
                tip_diameter, shaft_diameter = _get_equivalent_diameter(self.pile)

                # Calculate bearing capacity shaft
                top_level = min(
                    self.future_surface_level, cpt.surface_level
                )  # the bearing capacity can only be calculated on the interval where the cpt has measured
                qc_avg_shaft = (
                    cpt.calculate_average_qc(top=top_level, bottom=pile_tip_level)
                    * 1000
                )  # MPa -> kPa
                bc_shaft = (
                    qc_avg_shaft
                    * shaft_diameter
                    * math.pi
                    * (top_level - pile_tip_level)
                    * self.pile.pile_class_factor_shaft_sand_gravel
                )

                # Calculate bearing capacity tip
                qc_avg_tip = (
                    cpt.calculate_average_qc(
                        top=pile_tip_level + (4 * tip_diameter),
                        bottom=pile_tip_level - (0.8 * tip_diameter),
                    )
                    * 1000
                )  # MPa -> kPa
                bc_tip = (
                    qc_avg_tip
                    * (((tip_diameter**2) / 4) * math.pi)
                    * self.pile.pile_class_factor_tip
                )

                # Calculate negative skin friction
                stresses = calculate_stresses(
                    soil_profile=soil_profile,
                    water_level=self.phreatic_level,
                    soil_weights={
                        s.soil: (s.gamma_nat, s.gamma_sat)
                        for s in self.additional_soils
                    },
                )
                bottom_nsf: float | None = (
                    skin_friction_range.bottom_negative_skin_friction
                )
                if bottom_nsf is None:
                    bottom_nsf = soil_profile.surface_level
                nsf = (
                    shaft_diameter
                    * math.pi
                    * _calculate_mock_negative_skin_friction(
                        soil_profile=soil_profile,
                        stresses=stresses,
                        params=self.additional_soils,
                        bottom=bottom_nsf,
                    )
                )  # TODO: bottom of neagtive skin friction currently not set?

                # collect data
                results.append(
                    PileResult(
                        cpt=cpt,
                        tip_level=pile_tip_level,
                        bc_shaft_rep=bc_shaft,
                        bc_tip_rep=bc_tip,
                        nsf_rep=nsf,
                        design_bearing_capacity=(bc_shaft + bc_tip + nsf)
                        / self._calc_ksi3(
                            n_cpts=len(self.cpt_soil_profile_map)
                        ),  # TODO: currently incorrect, make in accordance with norm!
                    )
                )
        self.results = PileResults(
            pile=self.pile,
            results=results,
        )


def calc_ksi3(rigid_construction: bool, n_cpts: int):
    if rigid_construction:
        ksi3_n_cpt_map: dict[int, float] = {
            1: 1.39,
            2: 1.39,
            3: 1.39,
            4: 1.39,
            5: 1.39,
            6: 1.39,
            7: 1.39,
            8: 1.39,
        }  # TODO: fill in real values
    else:
        ksi3_n_cpt_map: dict[int, float] = {
            1: 1.39,
            2: 1.39,
            3: 1.39,
            4: 1.39,
            5: 1.39,
            6: 1.39,
            7: 1.39,
            8: 1.39,
        }  # TODO: fill in real values
    return ksi3_n_cpt_map[n_cpts]


def calc_ksi4(rigid_construction: bool, n_cpts: int):
    if rigid_construction:
        ksi4_n_cpt_map: dict[int, float] = {
            1: 1.39,
            2: 1.39,
            3: 1.39,
            4: 1.39,
            5: 1.39,
            6: 1.39,
            7: 1.39,
            8: 1.39,
        }  # TODO: fill in real values
    else:
        ksi4_n_cpt_map: dict[int, float] = {
            1: 1.39,
            2: 1.39,
            3: 1.39,
            4: 1.39,
            5: 1.39,
            6: 1.39,
            7: 1.39,
            8: 1.39,
        }  # TODO: fill in real values
    return ksi4_n_cpt_map[n_cpts]


def _get_equivalent_diameter(pile: BearingPile) -> tuple[float, float]:
    """Gets the (equivalent) diameter of a pile. Returns respectively the tip and shaft diameter"""
    if isinstance(pile, piles.BearingRoundPile):
        return pile.diameter, pile.diameter
    elif isinstance(pile, piles.BearingRoundPileWithLostTip):
        return pile.base_diameter, pile.pile_diameter
    elif isinstance(pile, piles.BearingRectangularPile):
        pile_tip_area = pile.base_length * pile.base_width
        equivalent_diameter = math.sqrt((pile_tip_area * 4) / math.pi)
        return equivalent_diameter, equivalent_diameter
    else:
        raise NotImplementedError(f"A pile of type: {type(pile)} is not implemented")


def _get_friction_angle_from_soil(
    soil: str, params: list[PileFoundationParams]
) -> float:
    for soil_params in params:
        if soil_params.soil == soil:
            return soil_params.friction_angle
    raise ValueError(f"The soil: {soil} is not present in the params: {params}")


def _calculate_mock_negative_skin_friction(
    soil_profile: SoilProfile,
    stresses: SoilStresses,
    params: list[PileFoundationParams],
    bottom: float,
) -> float:
    """Calculates the negative skin friction of the soil, not taking into account the circumference of the pile"""
    if bottom > soil_profile.surface_level:
        raise ValueError(
            "The bottom of the negative skin friction range should be at surface level or below"
        )

    if bottom < soil_profile.bottom:
        raise ValueError(
            "The bottom of the negative skin friction range should be higher or equal to the bottom of the soil profile"
        )

    # When bottom of negative skin friction range, the negative skin friction is equal to zero
    if bottom == soil_profile.surface_level:
        return 0

    # Calculate negative skin friction over depth of soil profile until bottom of negative skin friction range
    nsf: float = 0
    for (level_top, level_bottom), (sig_eff_top, sig_eff_bottom) in zip(
        pairwise(stresses.levels), pairwise(stresses.effective_stresses)
    ):
        # Break out of the loop when the bottom of nsf range is equal to the top of the new layer
        if level_top == bottom:
            break

        # Break out of the loop when the bottom of nsf range is above the top of the new layer
        if level_top < bottom:
            break

        # Change the bottom of the layer when the bottom of nsf range is above the bottom of the new layer
        if level_bottom < bottom:
            level_bottom = bottom

        # Get soil of layer (can also be part of layer if water level splits up layer)
        soil_top = soil_profile.get_soil_at_level(level_top - 0.01)
        soil_bottom = soil_profile.get_soil_at_level(level_bottom + 0.01)
        if soil_top != soil_bottom:
            raise ValueError(
                f"Something has gone wrong, the soil at the top: {soil_top} at level: {level_top - 0.01} is not the same as the soil at the bottom of the layer: {soil_bottom} at level: {level_bottom + 0.01}"
            )
        else:
            soil = soil_top

        # Get friction angle
        friction_angle = _get_friction_angle_from_soil(soil=soil, params=params)

        # Get horizontal stress
        K0 = 1 - math.sin(math.radians(friction_angle))  # in accordance with Jaky

        # Calculate horizontal force
        height = level_top - level_bottom
        sig_h_top = sig_eff_top * K0
        sig_h_bottom = sig_eff_bottom * K0
        F_horizontal = (sig_h_top + sig_h_bottom) * height / 2

        # Calculate frictional force portion
        nsf += F_horizontal * math.tan(math.radians(friction_angle))
    return nsf


def plot_bearing_capacity(
    results: PileResults, calculation_name: str
) -> tuple[plt.Figure, plt.Axes]:  # pyright: ignore
    fig, ax = plt.subplots()
    ax.set_title(calculation_name)
    pile_tip_levels, bearing_capacities = zip(
        *[(res.tip_level, res.rep_bearing_capacity) for res in results.results]
    )
    ax.plot(bearing_capacities, pile_tip_levels, marker="o", color="k", linestyle="--")
    ax.set_xlabel("Draagkracht (rep) [kN]")
    ax.set_ylabel("Niveau [m+NAP]")
    ax.set_yticks(np.arange(min(pile_tip_levels), max(pile_tip_levels) + 0.5, 0.5))
    ax.grid()
    return fig, ax
