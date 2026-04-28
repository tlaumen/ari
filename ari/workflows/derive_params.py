import math

from prompt_toolkit.shortcuts import print_formatted_text, prompt
from prompt_toolkit.validation import ValidationError
from prompt_toolkit.completion import WordCompleter

from ceniac.parameters.model import PileFoundationParams

from ari.cli_utils import yes_no_validator
from ari.cli_utils import bool_validator
from ari.cli_utils import number_validator
from ari.db.db import get_all_soil_profiles
from ari.db.database import Table
from ari.db.db import db


def query_pile_foundation_soil_params():
    # Get all soils from interpreted soil profiles
    soils = get_all_soils()
    soils.sort()

    # Query for parameter values
    for soil in soils:
        _query_single_foundation_soil_params(soil=soil)


def _query_single_foundation_soil_params(soil: str):
    # Query single soil params
    print_formatted_text(
        "\n\n" + "+" * 50 + f"\n\nVoer de grondparameters in: \nNaam: {soil}"
    )
    gamma_nat = prompt(
        "Natuurlijk volumiek gewicht [kN/m3]: ", validator=number_validator
    )
    gamma_sat = prompt(
        "Verzadigd volumiek gewicht [kN/m3]: ", validator=number_validator
    )
    friction_angle = float(
        prompt("Wat is de wrijvingshoek [graden]: ", validator=number_validator)
    )
    K0 = 1 - math.sin(
        math.radians(friction_angle)
    )  # in accordance with Jaky TODO: assess if correct/good enough
    bool_completer = WordCompleter(["true", "false"])
    _compressible = prompt(
        "Is de grondsoort samendrukbaar [true/false]: ",
        completer=bool_completer,
        validator=bool_validator,
    )
    if _compressible.strip().lower() == "true":
        compressible = True
    elif _compressible.strip().lower() == "false":
        compressible = False
    else:
        raise ValidationError(
            message="The input for 'compressible' should be 'true' or 'false'."
        )
    if compressible:
        undrained_shear_strength = float(
            prompt(
                "Wat is de ongedraineerde schuifsterkte [kPa]: ",
                validator=number_validator,
            )
        )
    else:
        undrained_shear_strength = 100  # kPa, randomly chosen large value TODO: assess if correct towards future
    params = PileFoundationParams(
        soil=soil,
        K0=float(K0),
        gamma_nat=float(gamma_nat),
        gamma_sat=float(gamma_sat),
        compressible=compressible,
        undrained_shear_strength=undrained_shear_strength,
        friction_angle=friction_angle,
    )
    db.add(Table.PROJECT, "params", params)


def get_all_soils():
    """Get all soils interpreted in the cpts"""
    soil_profiles = get_all_soil_profiles()
    print("soil profiles", soil_profiles)
    soils = {s for soil_profile in soil_profiles for s in soil_profile.soils}
    return list(soils)
