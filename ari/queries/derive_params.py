"""Derive params workflow steps.

This module contains the Step classes for the derive params workflow:
- StepPileFoundationSoilParams: Prompts user for pile foundation soil parameters

Key constants:
- PILE_FOUNDATION_PARAMS_KEY: Context key for pile foundation params
- DERIVE_PARAMS_STEPS: List of Step classes for the derive params workflow
"""

import math
from typing import Any

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.completion import WordCompleter

from ceniac.parameters.model import PileFoundationParams
from ceniac.soil_profile.soil_profile import SoilProfile

from ari.queries.base import Step, Requirement, Product, Table
from ari.cli_utils import bool_validator, number_validator


# Context keys
PILE_FOUNDATION_PARAMS_KEY = "pile-foundation-params"

def get_all_soils(soil_profiles: list[SoilProfile]) -> list[str]:
    """Get all soils interpreted in the cpts"""
    # Implemented with nested loop to get a determinstically ordered list top to bottom
    # With a set and list, this does not happen and this is unpredictable for user and testing
    soils: list[str] = [] 
    for sp in soil_profiles:
        for soil in sp.soils:
            if soil in soils:
                continue
            soils.append(soil)
    return soils

class StepPileFoundationSoilParams(Step):
    """Prompts user for pile foundation soil parameters for each soil type.

    This step is an InputStep that:
    1. Reads soil names from ctx["soils"] (populated by Step.run() from db.project.soils)
    2. For each soil type, prompts for gamma_nat, gamma_sat, friction_angle
    3. Calculates K0 from friction_angle using Jaky's formula
    4. Prompts for compressible, and undrained_shear_strength (if compressible)
    5. Creates PileFoundationParams and stores in ctx["params"]

    Attributes:
        name: Unique step name
        requires: soils list from PROJECT (pre-populated via ctx)
        produces: params dict to PROJECT (written by Step.run() via db.add())
    """

    name = "step_pile_foundation_soil_params"
    requires: list[Requirement] = [
        Requirement(key="soilprofiles", source=Table.PROJECT),
    ]
    produces: list[Product] = [
        Product(key="params", dest=Table.PROJECT),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for soil params and store in ctx.

        Args:
            ctx: Context dictionary with 'soils' input and 'params' output
        """
        # Get soil names from ctx (populated by Step.run() from db.project.soilprofiles)
        soil_profiles = ctx["soilprofiles"]
        soils = get_all_soils(soil_profiles=soil_profiles)
    
        # Collect params for each soil
        params_dict: dict[str, PileFoundationParams] = {}
        for soil in soils:
            params_dict[soil] = _query_single_soil_params(soil)

        # Store in ctx for write-back via Step.run() -> db.add()
        ctx["params"] = params_dict


def _query_single_soil_params(soil: str) -> PileFoundationParams:
    """Query parameters for a single soil type.

    Args:
        soil: Soil type name

    Returns:
        PileFoundationParams object for the soil
    """
    # Prompt for gamma_nat
    gamma_nat = prompt(
        "Natuurlijk volumiek gewicht [kN/m3]: ",
        validator=number_validator,
    )

    # Prompt for gamma_sat
    gamma_sat = prompt(
        "Verzadigd volumiek gewicht [kN/m3]: ",
        validator=number_validator,
    )

    # Prompt for friction_angle
    friction_angle = float(
        prompt(
            "Wat is de wrijvingshoek [graden]: ",
            validator=number_validator,
        )
    )

    # Calculate K0 using Jaky's formula
    K0 = 1 - math.sin(math.radians(friction_angle))

    # Prompt for compressible
    bool_completer = WordCompleter(["true", "false"])
    compressible_input = prompt(
        "Is de grondsoort samendrukbaar [true/false]: ",
        completer=bool_completer,
        validator=bool_validator,
    )
    compressible = compressible_input.strip().lower() == "true"

    # Prompt for undrained_shear_strength if compressible
    if compressible:
        undrained_shear_strength = float(
            prompt(
                "Wat is de ongedraineerde schuifsterkte [kPa]: ",
                validator=number_validator,
            )
        )
    else:
        undrained_shear_strength = 100.0  # kPa, default for non-compressible

    # Create and return PileFoundationParams object
    return PileFoundationParams(
        soil=soil,
        K0=float(K0),
        gamma_nat=float(gamma_nat),
        gamma_sat=float(gamma_sat),
        friction_angle=friction_angle,
        compressible=compressible,
        undrained_shear_strength=undrained_shear_strength,
    )


# Derive params workflow steps list (Step 8)
DERIVE_PARAMS_STEPS: list[type[Step]] = [
    StepPileFoundationSoilParams,
]
