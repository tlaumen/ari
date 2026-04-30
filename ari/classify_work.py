from typing import Any
from typing import Callable

from prompt_toolkit.shortcuts import prompt, print_formatted_text

from baml_client.sync_client import b
from baml_client.types import (
    TypeOfWork,
    ClarificationRequest,
    Berekening,
    VerzoekVerduidelijking,
)

from ari.queries.base import Step, StepRunner
from ari.queries.soil_interpretation import SOIL_INTERPRETATION_STEPS
from ari.queries.derive_params import DERIVE_PARAMS_STEPS
from ari.queries.pile_calc import PILE_CALC_STEPS
from ari.queries.pile_report import PILE_REPORTING_STEPS
from ari.db.db import create_new_calculation_table, initialize_db, Database


# Compose PAALFUNDERING_STEPS by concatenating all workflow step lists
PAALFUNDERING_STEPS: list[type[Step]] = (
    SOIL_INTERPRETATION_STEPS + DERIVE_PARAMS_STEPS + PILE_CALC_STEPS + PILE_REPORTING_STEPS
)



def route_prompt(response: Berekening | VerzoekVerduidelijking) -> list[Callable]:
    db = Database()

    call_chain: list[Callable] = []
    if isinstance(response, VerzoekVerduidelijking):
        print_formatted_text(
            f"Je prompt was onduidelijk: {response.verzoek_tot_verduidelijking}"
        )
        call_chain.append(request_clarification)

    elif isinstance(response, Berekening):
        call_chain.extend(route_workflows(response, db))
    else:
        raise ValueError(f"There is no logic implemented for reponse: {response}")
    return call_chain


def request_clarification():
    return prompt("Kun je beter uitleggen wat je bedoelt?")


def route_workflows(response: Berekening, db: Database) -> list[Callable]:
    """Route to the appropriate workflow based on Berekening type.

    For PAALFUNDERING:
    - Runs StepRunner with PAALFUNDERING_STEPS (concatenation of SOIL_INTERPRETATION_STEPS +
      DERIVE_PARAMS_STEPS + PILE_CALC_STEPS)
    - Returns [query_foundation_report] as the final step to be executed

    Args:
        response: The Berekening type to route
        db: Database instance for StepRunner

    Returns:
        List of Callable steps to execute

    Raises:
        NotImplementedError: For Berekening types other than PAALFUNDERING
    """
    if response == Berekening.PAALFUNDERING:
        # Run StepRunner with composed step list, ignore the returned ctx dict
        StepRunner(PAALFUNDERING_STEPS).run(db)
    else:
        raise NotImplementedError("Unfortunately, this workflow is not yet implemented")



