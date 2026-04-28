"""Pile calc workflow steps.

This module contains the Step classes for the pile calc workflow:
- StepSlsLoad: Prompts user for SLS (Service Limit State) vertical load
- StepUlsLoad: Prompts user for ULS (Ultimate Limit State) vertical load

Key constants:
- SLS_LOAD_KEY: Context key for SLS load value
- ULS_LOAD_KEY: Context key for ULS load value
- PILE_CALC_STEPS: List of Step classes for the pile calc workflow
"""

from typing import Any

from prompt_toolkit.shortcuts import prompt, choice, confirm

from ari.queries.base import Step, Requirement, Product, Table
from ari.workflows.calculate.pile import (
    PileType,
    pile_location_selector,
    create_pile,
)
from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import SoilProfile
from geolib.models.dfoundations.profiles import TimeOrderType
from ari.cli_utils import number_validator
from ceniac.calculate.pile import (
    PileBearingCapacityCalc,
    SkinFrictionRanges,
    select_skin_friction_areas,
)


# Context keys
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
SKIN_FRICTION_RANGES_KEY = "negatieve-positieve-kleef-trajecten"
CALCULATION_RESULTS_KEY = "berekeningsresultaten"

TIME_ORDER_OPTIONS = [
    (TimeOrderType.CPT_EXCAVATION_INSTALL, "cpt -> excavate -> install"),
    (TimeOrderType.INSTALL_CPT_EXCAVATION, "install pile -> cpt -> excavate"),
    (TimeOrderType.EXCAVATION_CPT_INSTALL, "excavate -> cpt -> install pile"),
    (TimeOrderType.EXCAVATION_INSTALL_CPT, "excavate -> install pile -> cpt"),
    (TimeOrderType.INSTALL_EXCAVATION_CPT, "install pile -> excavate -> cpt"),
    (TimeOrderType.CPT_INSTALL_EXCAVATION, "cpt -> install pile -> excavate"),
    (TimeOrderType.CPT_BEFORE_AND_AFTER_INSTALL, "cpt -> install -> cpt"),
]


class StepSlsLoad(Step):
    """Prompts user for SLS (Service Limit State) vertical load.

    This step is an InputStep that:
    1. Prompts user for vertical BGT belasting (Service Limit State load)
    2. Validates input using number_validator
    3. Converts to float and stores in ctx[SLS_LOAD_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (first step in pile calc workflow)
        produces: Produces SLS_LOAD_KEY to CALC table

    Behavior:
        1. Prompts user "Wat is de verticale BGT belasting? "
        2. Validates input using number_validator
        3. Stores float value in ctx[SLS_LOAD_KEY]
    """

    name = "step_sls_load"
    requires: list[Requirement] = []  # No requirements — first step
    produces: list[Product] = [Product(key=SLS_LOAD_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for SLS load and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the SLS load value
        """
        # Prompt for SLS load with number validator
        sls_load = prompt(
            "Wat is de verticale BGT belasting? ",
            validator=number_validator,
        )

        # Convert to float and store in ctx
        ctx[SLS_LOAD_KEY] = float(sls_load)


class StepUlsLoad(Step):
    """Prompts user for ULS (Ultimate Limit State) vertical load.

    This step is an InputStep that:
    1. Prompts user for vertical UGT belasting (Ultimate Limit State load)
    2. Validates input using number_validator
    3. Converts to float and stores in ctx[ULS_LOAD_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces ULS_LOAD_KEY to CALC table

    Behavior:
        1. Prompts user "Wat is de verticale UGT belasting? "
        2. Validates input using number_validator
        3. Stores float value in ctx[ULS_LOAD_KEY]
    """

    name = "step_uls_load"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=ULS_LOAD_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for ULS load and store in ctx.

        db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the ULS load value
        """
        # Prompt for ULS load with number validator
        uls_load = prompt(
            "Wat is de verticale UGT belasting? ",
            validator=number_validator,
        )

        # Convert to float and store in ctx
        ctx[ULS_LOAD_KEY] = float(uls_load)


class StepPileType(Step):
    """Prompts user to select a pile type from the PileType enum.

    This step is an InputStep that:
    1. Presents user with choice of pile types using prompt_toolkit choice()
    2. Stores the selected PileType enum value in ctx[PILE_TYPE_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces PILE_TYPE_KEY to CALC table

    Behavior:
        1. Calls choice() with message "Selecteer de gewenste paal: "
           and options [(pt, pt.value) for pt in PileType]
        2. Stores the returned PileType value in ctx[PILE_TYPE_KEY]
    """

    name = "step_pile_type"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=PILE_TYPE_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for pile type selection and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the pile type selection
        """
        # Prompt for pile type selection using choice
        pile_type = choice(
            message="Selecteer de gewenste paal: ",
            options=[(pt, pt.value) for pt in PileType],
        )

        # Store the selected PileType in ctx
        ctx[PILE_TYPE_KEY] = pile_type


class StepPileDimensions(Step):
    """Prompts user for pile dimensions based on pile type.

    This step is an InputStep that:
    1. Reads pile type from ctx[PILE_TYPE_KEY]
    2. Prompts for dimensions based on pile type:
       - PREFAB_HEIPAAL / SCHROEFPAAL: single prompt for width/diameter
       - VIBROPAAL / BUISSCHROEFPAAL / BUISSCHROEFPAAL_VERLOREN_CASING:
         two prompts for shaft and foot diameters
    3. Stores dimensions as float or tuple[float, float] in ctx[PILE_DIMENSIONS_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (reads ctx directly)
        produces: Produces PILE_DIMENSIONS_KEY to CALC table
    """

    name = "step_pile_dimensions"
    requires: list[Requirement] = []  # No requirements — reads ctx directly
    produces: list[Product] = [Product(key=PILE_DIMENSIONS_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for pile dimensions and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary with pile type, to store dimensions
        """
        # Read pile type from ctx
        pile_type = ctx[PILE_TYPE_KEY]

        # Prompt for dimensions based on pile type
        match pile_type:
            case PileType.PREFAB_HEIPAAL:
                # Single dimension (width) for prefab pile
                dimensions = float(
                    prompt(
                        "Wat is de breedte van de prefab paal?",
                        validator=number_validator,
                    )
                )
            case PileType.SCHROEFPAAL:
                # Single dimension (diameter) for schroefpaal
                dimensions = float(
                    prompt(
                        "Wat is de diameter van de paal?",
                        validator=number_validator,
                    )
                )
            case (
                PileType.VIBROPAAL
                | PileType.BUISSCHROEFPAAL
                | PileType.BUISSCHROEFPAAL_VERLOREN_CASING
            ):
                # Two dimensions (shaft and foot diameter)
                diameter_shaft = prompt(
                    "Wat is de diameter van de schacht?",
                    validator=number_validator,
                )
                diameter_foot = prompt(
                    "Wat is de diameter van de punt?",
                    validator=number_validator,
                )
                dimensions = (float(diameter_shaft), float(diameter_foot))
            case _:
                raise ValueError(
                    f"Unsupported pile type: {pile_type}. "
                    "Supported types: PREFAB_HEIPAAL, SCHROEFPAAL, VIBROPAAL, "
                    "BUISSCHROEFPAAL, BUISSCHROEFPAAL_VERLOREN_CASING"
                )

        # Store dimensions in ctx
        ctx[PILE_DIMENSIONS_KEY] = dimensions


class StepPileLocation(Step):
    """Opens GUI to select pile location on map, stores coordinates and top-view image.

    This step is an InputStep that:
    1. Calls pile_location_selector() with list of CPTs from database
    2. Gets selected point coordinates via selector.get_point()
    3. Stores coordinates tuple in ctx[PILE_LOCATION_KEY]
    4. Stores top_view_image in ctx[SOIL_INVESTIGATION_TOPVIEW_IMAGE]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces PILE_LOCATION_KEY and SOIL_INVESTIGATION_TOPVIEW_IMAGE to CALC table
    """

    name = "step_pile_location"
    requires: list[Requirement] = [Requirement(key="cpts", source=Table.PROJECT)]
    produces: list[Product] = [
        Product(key=PILE_LOCATION_KEY, dest=Table.CALC),
        Product(key=SOIL_INVESTIGATION_TOPVIEW_IMAGE, dest=Table.CALC),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Open GUI map selector and store coordinates + image in ctx.

        Args:
            db: Database instance (used to get CPTs for map markers)
            ctx: Context dictionary to store the pile location and image
        """
        # Open GUI map selector
        selector = pile_location_selector(ctx["cpts"])

        # Extract point coordinates (RD) and store in ctx
        point = selector.get_point()
        ctx[PILE_LOCATION_KEY] = point

        # Extract top view image and store in ctx
        ctx[SOIL_INVESTIGATION_TOPVIEW_IMAGE] = selector.top_view_image


class StepCptWorkOrder(Step):
    """Prompts user to select CPT/pile/excavation time order.

    This step is an InputStep that:
    1. Presents user with choice of time orders using prompt_toolkit choice()
    2. Stores the selected TimeOrderType enum value in ctx[WORK_ORDER_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces WORK_ORDER_KEY to CALC table
    """

    name = "step_cpt_work_order"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=WORK_ORDER_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for time order selection and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the time order selection
        """
        # Prompt for time order selection using choice
        work_order = choice(
            message="Wat is de cpt-bouw-paalinstallatie volgorde?",
            options=TIME_ORDER_OPTIONS,
        )

        # Store the selected TimeOrderType in ctx
        ctx[WORK_ORDER_KEY] = work_order


class StepPileTipLevel(Step):
    """Prompts user for pile tip level (paalpuntniveau) in meters +NAP.

    This step is an InputStep that:
    1. Prompts user for pile tip level using prompt_toolkit
    2. Validates input using number_validator
    3. Converts to float and stores in ctx[PILE_TIP_LEVEL_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces PILE_TIP_LEVEL_KEY to CALC table

    Behavior:
        1. Prompts user "Wat is het paalpuntniveau? [m+NAP]"
        2. Validates input using number_validator
        3. Stores float value in ctx[PILE_TIP_LEVEL_KEY]
    """

    name = "step_pile_tip_level"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=PILE_TIP_LEVEL_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for pile tip level and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the pile tip level value
        """
        # Prompt for pile tip level with number validator
        pile_tip_level = prompt(
            "Wat is het paalpuntniveau? [m+NAP]",
            validator=number_validator,
        )

        # Convert to float and store in ctx
        ctx[PILE_TIP_LEVEL_KEY] = float(pile_tip_level)


class StepPhreaticLevel(Step):
    """Prompts user for phreatic (groundwater) level in meters +NAP.

    This step is an InputStep that:
    1. Prompts user for phreatic groundwater level
    2. Validates input using number_validator
    3. Converts to float and stores in ctx[PHREATIC_LEVEL_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces PHREATIC_LEVEL_KEY to CALC table

    Behavior:
        1. Prompts user "Wat is de freatische grondwaterstand ter plaatse van de cpt? [m+NAP]"
        2. Validates input using number_validator
        3. Stores float value in ctx[PHREATIC_LEVEL_KEY]
    """

    name = "step_phreatic_level"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=PHREATIC_LEVEL_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for phreatic level and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the phreatic level value
        """
        # Prompt for phreatic level with number validator
        phreatic_level = prompt(
            "Wat is de freatische grondwaterstand ter plaatse van de cpt? [m+NAP]",
            validator=number_validator,
        )

        # Convert to float and store in ctx
        ctx[PHREATIC_LEVEL_KEY] = float(phreatic_level)


class StepStructureRigidity(Step):
    """Prompts user for structure rigidity (stijve constructie) using yes/no confirmation.

    This step is an InputStep that:
    1. Asks user if it's a stiff structure (stijve constructie)
    2. Uses confirm() for yes/no prompt
    3. Stores boolean in ctx[STRUCTURE_RIGIDITY_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces STRUCTURE_RIGIDITY_KEY to CALC table

    Behavior:
        1. Calls confirm() with "Is het een stijve constructie?"
        2. Stores bool value in ctx[STRUCTURE_RIGIDITY_KEY]
    """

    name = "step_structure_rigidity"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=STRUCTURE_RIGIDITY_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for structure rigidity and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the structure rigidity value
        """
        # Prompt for structure rigidity confirmation
        is_stiff = confirm("Is het een stijve constructie?")

        # Store the boolean in ctx
        ctx[STRUCTURE_RIGIDITY_KEY] = bool(is_stiff)


class StepFutureGroundLevel(Step):
    """Prompts user for future ground level (maaiveldniveau) in meters +NAP.

    This step is an InputStep that:
    1. Prompts user for future ground level
    2. Validates input using number_validator
    3. Converts to float and stores in ctx[FUTURE_GROUND_LEVEL_KEY]

    Attributes:
        name: Unique step name
        requires: No inputs required (can run independently)
        produces: Produces FUTURE_GROUND_LEVEL_KEY to CALC table

    Behavior:
        1. Prompts user "Wat is het toekomstige maaiveldniveau? [m+NAP] "
        2. Validates input using number_validator
        3. Stores float value in ctx[FUTURE_GROUND_LEVEL_KEY]
    """

    name = "step_future_ground_level"
    requires: list[Requirement] = []  # No requirements — can run independently
    produces: list[Product] = [Product(key=FUTURE_GROUND_LEVEL_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for future ground level and store in ctx.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the future ground level value
        """
        # TODO: give pointers on current groundlevel of cpts as a reference
        # Prompt for future ground level with number validator
        future_ground_level = prompt(
            "Wat is het toekomstige maaiveldniveau? [m+NAP] ",
            validator=number_validator,
        )

        # Convert to float and store in ctx
        ctx[FUTURE_GROUND_LEVEL_KEY] = float(future_ground_level)


class StepSkinFrictionRanges(Step):
    """Computes skin friction ranges from CPTs, soil profiles, parameters, and pile tip level.

    This step is a ComputationStep that:
    1. Gets CPTs, soil profiles, profile maps from db (via Step.run() populating ctx)
    2. Calls combine_soil_profiles_cpts() to get cpt/soil_profile mapping
    3. Calls select_skin_friction_areas() for each (cpt, soil_profile) pair
    4. Stores resulting dict[cpt_id -> SkinFrictionRanges] in ctx[SKIN_FRICTION_RANGES_KEY]

    Attributes:
        name: Unique step name
        requires: cpts, soilprofiles, params, colors from PROJECT; paalpuntniveau from CALC
        produces: Produces SKIN_FRICTION_RANGES_KEY to CALC table
    """

    name = "step_skin_friction_ranges"
    requires: list[Requirement] = [
        Requirement(key="cpts", source=Table.PROJECT),
        Requirement(key="soilprofiles", source=Table.PROJECT),
        Requirement(key="params", source=Table.PROJECT),
        Requirement(key="colors", source=Table.PROJECT),
        Requirement(key=PILE_TIP_LEVEL_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [Product(key=SKIN_FRICTION_RANGES_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Compute skin friction ranges and store in ctx.

        Derives CPT-to-profile mapping by reading sp.based_on from each
        SoilProfile in ctx["soilprofiles"].values(), then looking up the
        CPT from ctx["cpts"][sp.based_on]. Does NOT use combine_soil_profiles_cpts()
        or profilemap.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the skin friction ranges
        """
        # Get data from ctx (populated by Step.run() from db)
        cpts = ctx["cpts"]
        soil_profiles = ctx["soilprofiles"]
        soil_params = ctx["params"]
        soil_colors = ctx["colors"]
        pile_tip_level = ctx[PILE_TIP_LEVEL_KEY]

        # Build cpt_soil_profile_map by reading based_on from each SoilProfile.
        # ctx["soilprofiles"] is a dict of SoilProfile objects keyed by name.
        cpt_id_map: dict[str, Cpt] = {cpt.id_:cpt for cpt in cpts}
        cpt_soil_profile_map: list[tuple[Cpt, SoilProfile]] = []
        for sp in soil_profiles:
            based_on_cpt_id = sp.based_on
            if based_on_cpt_id and based_on_cpt_id in cpt_id_map:
                cpt_soil_profile_map.append((cpt_id_map[based_on_cpt_id], sp))

        # Calculate skin friction ranges for each CPT/soil profile pair
        skin_friction_ranges: dict[str, SkinFrictionRanges] = {}
        for cpt, soil_profile in cpt_soil_profile_map:
            sfr = select_skin_friction_areas(
                cpt=cpt,
                soil_profile=soil_profile,
                soil_params=soil_params,
                pile_tip_level=pile_tip_level,
                soil_colors=soil_colors,
            )
            skin_friction_ranges[cpt.id_] = sfr

        # Store results in ctx
        ctx[SKIN_FRICTION_RANGES_KEY] = skin_friction_ranges


class StepRunPileCalc(Step):
    """Runs the pile bearing capacity calculation.

    This step is a ComputationStep that:
    1. Reads all required data from ctx
    2. Calls combine_soil_profiles_cpts() to get cpt/soil_profile mapping
    3. Creates PileBearingCapacityCalc with all required parameters
    4. Calls build_calculation() then _mock_calculate()
    5. Stores calc.get_results() in ctx[CALCULATION_RESULTS_KEY]

    Attributes:
        name: Unique step name
        requires: All keys from CALC table (pile_tip_level, structure_rigidity, work_order, etc.)
        produces: Produces CALCULATION_RESULTS_KEY to CALC table
    """

    name = "step_run_pile_calc"
    requires: list[Requirement] = [
        Requirement(key="cpts", source=Table.PROJECT),
        Requirement(key="soilprofiles", source=Table.PROJECT),
        Requirement(key="params", source=Table.PROJECT),
        Requirement(key=PILE_TIP_LEVEL_KEY, source=Table.CALC),
        Requirement(key=STRUCTURE_RIGIDITY_KEY, source=Table.CALC),
        Requirement(key=WORK_ORDER_KEY, source=Table.CALC),
        Requirement(key=PHREATIC_LEVEL_KEY, source=Table.CALC),
        Requirement(key=PILE_TYPE_KEY, source=Table.CALC),
        Requirement(key=PILE_DIMENSIONS_KEY, source=Table.CALC),
        Requirement(key=FUTURE_GROUND_LEVEL_KEY, source=Table.CALC),
        Requirement(key=PILE_LOCATION_KEY, source=Table.CALC),
        Requirement(key=SKIN_FRICTION_RANGES_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [Product(key=CALCULATION_RESULTS_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Run pile bearing capacity calculation and store results.

        Derives CPT-to-profile mapping by reading sp.based_on from each
        SoilProfile in ctx["soilprofiles"].values(), then looking up the
        CPT from ctx["cpts"][sp.based_on]. Does NOT use combine_soil_profiles_cpts()
        or profilemap.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary with all required parameters
        """
        # Get data from ctx (populated by Step.run() from db)
        cpts = ctx["cpts"]
        soil_profiles = ctx["soilprofiles"]
        additional_soils = ctx["params"]

        # Build cpt_soil_profile_map by reading based_on from each SoilProfile.
        # ctx["soilprofiles"] is a dict of SoilProfile objects keyed by name.
        cpt_soil_profile_map: list[tuple[Cpt, SoilProfile]] = []
        for sp in soil_profiles.values():
            based_on_cpt_id = sp.based_on
            if based_on_cpt_id and based_on_cpt_id in cpts:
                cpt_soil_profile_map.append((cpts[based_on_cpt_id], sp))

        # Get other parameters from ctx
        pile_tip_level = ctx[PILE_TIP_LEVEL_KEY]
        rigid = ctx[STRUCTURE_RIGIDITY_KEY]
        work_order = ctx[WORK_ORDER_KEY]
        phreatic_level = ctx[PHREATIC_LEVEL_KEY]
        pile_type = ctx[PILE_TYPE_KEY]
        pile_dimensions = ctx[PILE_DIMENSIONS_KEY]
        future_surface_level = ctx[FUTURE_GROUND_LEVEL_KEY]
        pile_location = ctx[PILE_LOCATION_KEY]
        skin_friction_ranges = ctx[SKIN_FRICTION_RANGES_KEY]

        # Create pile object
        pile = create_pile(pile_type=pile_type, dimensions=pile_dimensions)

        # Create and run calculation
        calc = PileBearingCapacityCalc(
            file_path=None,  # Will be set by build_calculation
            cpt_soil_profile_map=cpt_soil_profile_map,
            rigid_construction=rigid,
            piletip_levels=[pile_tip_level],
            time_order=work_order,
            phreatic_level=phreatic_level,
            additional_soils=additional_soils,
            pile_location=pile_location,
            pile_head_level=future_surface_level,
            pile=pile,
            skin_friction_ranges=skin_friction_ranges,
            future_surface_level=future_surface_level,
        )

        # Build and calculate
        calc.build_calculation()
        calc._mock_calculate()

        # Store results in ctx
        ctx[CALCULATION_RESULTS_KEY] = calc.get_results()


# Pile calc workflow steps list (Step 21 — final integration)
PILE_CALC_STEPS: list[type[Step]] = [
    StepSlsLoad,
    StepUlsLoad,
    StepPileType,
    StepPileDimensions,
    StepPileLocation,
    StepPileTipLevel,
    StepCptWorkOrder,
    StepPhreaticLevel,
    StepStructureRigidity,
    StepFutureGroundLevel,
    StepSkinFrictionRanges,
    StepRunPileCalc,
]
