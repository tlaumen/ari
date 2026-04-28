"""Soil interpretation workflow steps.

This module contains the Step classes for the soil interpretation workflow:
- StepSiFolder: Prompts user for project folder containing CPT files
- StepCptPrompt: Prompts user to select CPT from available CPTs
- StepCpt: Loads CPT data from file
- StepCptInterpretationMethod: Prompts user to select interpretation method
- StepInterpretCpt: Runs CPT interpretation and saves soil profile

Key constants:
- CPT_FILE_EXTENSIONS: Valid CPT file extensions
- INTERPRETATION_NAME_MAP: Maps method names to functions
- SI_FOLDER_KEY: Context key for soil investigation folder
- CPT_NAME_KEY: Context key for CPT name
- CPT_INTERPRETATION_METHOD_KEY: Context key for interpretation method
"""

from pathlib import Path
from typing import Any, Callable

from prompt_toolkit.shortcuts import prompt, choice
from prompt_toolkit.completion import WordCompleter

from ceniac.soil_investigation.cpt import Cpt, load_cpt
from ceniac.soil_profile.soil_profile import SoilProfile
from ceniac.soil_investigation.interpret import naive_qc_rf, run_interpreter

from ari.queries.base import Step, Requirement, Product, Table
from ari.workflows.soil_interpretation import find_cpt, choose_cpt


# Constants
CPT_FILE_EXTENSIONS = (".xml", ".XML", ".gef", ".GEF")
INTERPRETATION_NAME_MAP = {"Qc Rf interpretatie": naive_qc_rf}

# Context keys
SI_FOLDER_KEY = "folder-grondonderzoek"
CPT_NAME_KEY = "cpt"
CPT_INTERPRETATION_METHOD_KEY = "interpretatie-methode-cpt"


class StepSiFolder(Step):
    """Prompts user for the project folder containing CPT files.

    This step is an InputStep that prompts the user for the folder where
    CPT files are located. The folder is stored in the CALC table.

    Attributes:
        name: Unique step name
        requires: No inputs required (first step in workflow)
        produces: Produces SI_FOLDER_KEY to CALC table

    Behavior:
        1. Prompts user for folder path with default of Path.cwd()
        2. If user enters empty string, uses Path.cwd()
        3. Validates folder exists; raises ValueError if not
    """

    name = "step_si_folder"
    requires: list[Requirement] = []
    produces: list[Product] = [Product(key=SI_FOLDER_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user for folder and validate it exists.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the folder path
        """
        # Prompt for folder with cwd as default
        folder = prompt(f"Wat is de projectfolder? [Standaard: {Path.cwd()}]")

        # If empty, use cwd
        if folder == "":
            top_level_folder = Path.cwd()
        else:
            top_level_folder = Path(folder)

        # Validate folder exists
        if not top_level_folder.exists():
            raise ValueError(
                f"De opgegeven folder bestaat niet: {folder}. folder does not exist"
            )

        ctx[SI_FOLDER_KEY] = top_level_folder


class StepCptPrompt(Step):
    """Prompts user to select CPT name from available CPTs.

    This step is an InputStep that:
    1. Reads available CPTs from ctx["cpts"] (populated by StepCpt via StepRunner)
    2. Raises ValueError if no CPTs available
    3. Prompts user with WordCompleter populated from sorted CPT names
    4. Validates selected CPT exists in available CPTs
    5. Stores selected CPT name in ctx[CPT_NAME_KEY]

    Attributes:
        name: Unique step name
        requires: cpts from PROJECT (via ctx → Step.run())
        produces: Produces CPT_NAME_KEY to CALC table
    """

    name = "step_cpt_prompt"
    requires: list[Requirement] = [
        Requirement(key="cpts", source=Table.PROJECT),
    ]
    produces: list[Product] = [Product(key=CPT_NAME_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user to select CPT from available CPTs.

        Args:
            db: Database instance for fallback CPT lookup
            ctx: Context dictionary with cpts from PROJECT and for storing selected CPT name

        Raises:
            ValueError: If no CPTs available or selected CPT not found
        """
        # Get available CPTs from ctx["cpts"] (populated by StepCpt via StepRunner)
        available_cpts = ctx["cpts"]

        # Validate: must have at least one cpt_names
        if not available_cpts:
            raise ValueError("No CPTs available. Please load a CPT file first.")

        # Get sorted CPT names for WordCompleter
        cpt_names = sorted(cpt.id_ for cpt in available_cpts)
        
        # Prompt user with WordCompleter
        completer = WordCompleter(cpt_names)
        selected_cpt = prompt("Welke CPT wil je gebruiken? ", completer=completer)
        
        # Validate: selected CPT must exist
        if selected_cpt not in cpt_names:
            raise ValueError(
                f"CPT '{selected_cpt}' not found. "
                f"Available CPTs: {[cpt.id_ for cpt in available_cpts]}"
            )

        # Store selected CPT name in ctx
        ctx[CPT_NAME_KEY] = selected_cpt


class StepCpt(Step):
    """Loads CPT data from file and stores it in the database.

    This step is a ComplexStep that:
    1. Reads the folder from ctx (SI_FOLDER_KEY)
    2. Reads the CPT name from ctx (user-provided, may have extension)
    3. Strips file extension if present (.xml, .XML, .gef, .GEF)
    4. Uses find_cpt() to locate the file (handles typos via Levenshtein)
    5. If multiple matches, prompts user to choose via choose_cpt()
    6. Loads the CPT and stores it in PROJECT via cpt_to_db()

    Attributes:
        name: Unique step name
        requires: SI_FOLDER_KEY from CALC table, CPT_NAME_KEY from ctx
        produces: None (CPT object written to PROJECT via cpt_to_db())
    """

    name = "step_cpt"
    requires: list[Requirement] = [
        Requirement(key=SI_FOLDER_KEY, source=Table.CALC),
        Requirement(key=CPT_NAME_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [
        # cpts written to PROJECT via ctx → Step.run() → db.add();
        # complex step writes to ctx, StepRunner.run() handles write-back.
        Product(key="cpts", dest=Table.PROJECT),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Load CPT from file and store in database.

        Args:
            db: Database instance for storing CPT
            ctx: Context dictionary with folder and CPT name

        Raises:
            ValueError: If folder doesn't exist or CPT cannot be found
        """

        # Get folder from ctx
        top_level_folder = ctx[SI_FOLDER_KEY]

        # Get CPT name from ctx (user provided via prompt or context)
        cpt_name = ctx.get(CPT_NAME_KEY)
        if not cpt_name:
            raise ValueError("No CPT name provided in context")

        # Strip file extension if present
        for ext in CPT_FILE_EXTENSIONS:
            if cpt_name.endswith(ext):
                cpt_name = cpt_name[: -len(ext)]
                break

        # Find CPT file
        cpt_path = find_cpt(name=cpt_name, top_level_folder=top_level_folder)

        # Handle multiple matches: let user choose
        if isinstance(cpt_path, list):
            cpt_path = choose_cpt(cpt_path)

        # Extract actual file name (may differ due to typo correction)
        cpt_name = cpt_path.stem

        # Load CPT
        cpt = load_cpt(cpt_path)

        # Store CPT name in ctx (for subsequent steps)
        ctx[CPT_NAME_KEY] = cpt_name

        # Check if CPT id matches file name
        if cpt.id_ != cpt_name:
            print(
                f"The cpt name: {cpt_name} and the id of the saved cpt: {cpt.id_} "
                "are not the same. Please note the cpt is referred to by the filename!"
            )

        # Store CPT in PROJECT via ctx → Step.run() → db.add(Table.PROJECT, "cpts", ...)
        ctx["cpts"] = {cpt_name: cpt}


class StepCptInterpretationMethod(Step):
    """Prompts user to select CPT interpretation method.

    This step is an InputStep that shows available interpretation methods
    and stores the selected function in ctx.

    Attributes:
        name: Unique step name
        requires: No inputs required
        produces: CPT_INTERPRETATION_METHOD_KEY to CALC table

    Supported methods:
        - "Qc Rf interpretatie" -> naive_qc_rf
    """

    name = "step_cpt_interpretation_method"
    requires: list[Requirement] = []
    produces: list[Product] = [
        Product(key=CPT_INTERPRETATION_METHOD_KEY, dest=Table.CALC)
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Prompt user to select interpretation method.

        Args:
            db: Database instance (unused, but required by Step interface)
            ctx: Context dictionary to store the selected function
        """
        # Prompt user to select interpretation function
        interpretation_function = choice(
            message="Welke cpt interpretatie methode wil je gebruiken?",
            options=[
                (function, name) for name, function in INTERPRETATION_NAME_MAP.items()
            ],
        )

        ctx[CPT_INTERPRETATION_METHOD_KEY] = interpretation_function


class StepInterpretCpt(Step):
    """Runs CPT interpretation and writes SoilProfile to ctx.

    This step is a ComplexStep that:
    1. Reads CPT object from ctx["cpts"][ctx["cpt"]] (populated by StepCpt)
    2. Reads interpretation function from ctx["interpretatie-methode-cpt"]
    3. Calls interpret_cpt() to get SoilProfile object
    4. Sets soil_profile.based_on = cpt_name (in-place mutation)
    5. Writes SoilProfile to ctx["soilprofiles"] for downstream steps

    Attributes:
        name: Unique step name
        requires: cpts from PROJECT (via ctx), cpt name from CALC, interpretation method from CALC
        produces: soilprofiles to PROJECT (via ctx → Step.run() → db.add())
    """

    name = "step_interpret_cpt"
    requires: list[Requirement] = [
        Requirement(key="cpts", source=Table.PROJECT),
        Requirement(key="cpt", source=Table.CALC),
        Requirement(key=CPT_INTERPRETATION_METHOD_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [
        # soilprofiles written to PROJECT via ctx → Step.run() → db.add(Table.PROJECT, "soilprofiles", ...)
        # ComplexStep pattern: explicit Product declaration for StepRunner.validate()
        Product(key="soilprofiles", dest=Table.PROJECT),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute: Interpret CPT and write SoilProfile to ctx.

        Args:
            db: Database instance (unused for reading, required by Step interface)
            ctx: Context dictionary with CPT name, CPT object dict, and interpretation function

        Raises:
            ValueError: If CPT name not found in ctx["cpts"] keys
        """
        from ari.workflows.soil_interpretation import interpret_cpt

        # Get CPT name from ctx
        cpt_name = ctx[CPT_NAME_KEY]

        # Get CPT object from ctx["cpts"] dict (populated by StepCpt via ctx propagation)
        cpts = ctx["cpts"]
        if cpt_name not in cpts:
            raise ValueError(
                f"CPT '{cpt_name}' not found in ctx. "
                f"Available CPTs: {list(cpts.keys())}"
            )
        cpt = cpts[cpt_name]

        # Get interpretation function from ctx
        interpretation_function = ctx[CPT_INTERPRETATION_METHOD_KEY]

        # Run interpretation
        soil_profile = interpret_cpt(
            cpt=cpt,
            interpretation_function=interpretation_function,
        )

        # Set based_on tracking before placing in ctx
        soil_profile.based_on = cpt_name

        # Write SoilProfile to ctx for downstream steps (via Step.run() → db.add())
        ctx["soilprofiles"] = soil_profile


# Workflow constant: List of all steps in the soil interpretation workflow
SOIL_INTERPRETATION_STEPS = [
    StepSiFolder,
    StepCptPrompt,
    StepCpt,
    StepCptInterpretationMethod,
    StepInterpretCpt,
]
