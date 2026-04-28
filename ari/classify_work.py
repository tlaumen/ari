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
from ari.workflows.soil_interpretation import SOIL_INTERPRETATION_QUERIES
from ari.workflows.derive_params import query_pile_foundation_soil_params
from ari.report.pile import query_foundation_report
from ari.db.db import create_new_calculation_table, initialize_db, Database


# Compose PAALFUNDERING_STEPS by concatenating all workflow step lists
PAALFUNDERING_STEPS: list[type[Step]] = (
    SOIL_INTERPRETATION_STEPS + DERIVE_PARAMS_STEPS + PILE_CALC_STEPS + PILE_REPORTING_STEPS
)


def route_work_type(response: ClarificationRequest | TypeOfWork, msg: str) -> Any:
    """Based on the message of a user, routes to the correct workflow"""
    if isinstance(response, ClarificationRequest):
        clarification: str = str(input(response.message))
        new_msg: str = msg + "\n" + clarification
        response = query_work_type_router(
            new_msg
        )  # TODO: improve callflow, can result in infinite recursion
        return route_work_type(response, new_msg)
    elif isinstance(response, TypeOfWork):
        match response:
            case TypeOfWork.CALCULATE:
                return query_pile_calc
            case TypeOfWork.DERIVE_SOIL_PARAMETERS:
                return query_pile_foundation_soil_params
            case TypeOfWork.INTERPRET_SOIL_INVESTIGATION:
                return SOIL_INTERPRETATION_QUERIES
            case TypeOfWork.REPORT:
                return query_foundation_report
            case _:
                raise NotImplementedError(
                    "Currently, the cases implemented are: CALCULATE, DERIVE_SOIL_PARAMETER, INTERPRET_SOIL_INVESTIGATION and REPORT."
                )
    else:
        raise NotImplementedError(
            f"A reponse of TypeOfWork or ClarificationRequest is expected, not: {response}"
        )


def query_work_type_router(msg: str) -> ClarificationRequest | TypeOfWork:
    return b.ClassifyWork(msg)


def route_prompt(response: Berekening | VerzoekVerduidelijking) -> list[Callable]:
    # Get the database singleton for passing to route_workflows
    from ari.db.db import db

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
        # Return query_foundation_report as final step to be called by run_call_chain
        return [query_foundation_report]
    else:
        raise NotImplementedError("Unfortunately, this workflow is not yet implemented")


def run_call_chain(call_chain: list[Callable]):
    for tool in call_chain:
        # try:
        tool()
    # except Exception as e:
    #     print(f"Function: {tool.__name__} failed.") # TODO replace with logging
    #     raise e


def agent_loop():
    initialize_db()
    while True:
        msg = prompt("Wat gaan we nu weer berekenen?")
        response = b.ChooseWorkflow(input=msg)
        if isinstance(response, Berekening):
            create_new_calculation_table(
                calc_type=response
            )  # HAndle that a new calculation starts --> asses how to improve if workflows become smaller
            call_chain = route_prompt(response=response)
            run_call_chain(call_chain)
