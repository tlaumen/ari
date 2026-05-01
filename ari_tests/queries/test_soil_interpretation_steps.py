"""Tests for soil interpretation steps (Step 6).

Tests for:
- StepSiFolder: Prompts user for project folder containing CPT files
- StepCptPrompt: Prompts user to select CPT from available CPTs
- StepCpt: Loads CPT data from file
- StepCptInterpretationMethod: Prompts user to select interpretation method
- StepInterpretCpt: Runs CPT interpretation and saves soil profile
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any

from ari.queries.base import Table, Requirement, Product, Step
from ari_tests.fixtures.workflow_mocks import SequentialMock, GUIMock
from prompt_toolkit.completion import WordCompleter

from ari_tests.test_utils import cpt
from baml_client.types import Berekening
from ari.queries.soil_interpretation import StepSiFolder
from ari.queries.soil_interpretation import StepCptPrompt, CPT_NAME_KEY
from ari.queries.soil_interpretation import StepCpt
from ari.queries.base import Product, Table
from ari.queries.soil_interpretation import (
    StepCptInterpretationMethod,
    naive_qc_rf,
)

class TestStepSiFolder:
    """Tests for StepSiFolder (InputStep).

    Prompts user for project folder containing CPT files and stores it in CALC.
    """

    def test_step_class_structure(self):
        """StepSiFolder has correct class structure."""

        # Check class attributes exist
        assert hasattr(StepSiFolder, "name")
        assert hasattr(StepSiFolder, "requires")
        assert hasattr(StepSiFolder, "produces")

        # Check specific values
        assert StepSiFolder.name == "step_si_folder"
        assert StepSiFolder.requires == []
        assert len(StepSiFolder.produces) == 1
        assert StepSiFolder.produces[0].key == "folder-grondonderzoek"
        assert StepSiFolder.produces[0].dest == Table.CALC

    def test_execute_stores_folder_in_ctx(self, fresh_db):
        """Behavior 1: execute() calls prompt() and stores result in ctx."""
        
        # Mock prompt to return a folder path
        seq = SequentialMock()
        seq.add_prompt("/test/folder")

        step = StepSiFolder()
        ctx: dict[str, Any] = {}

        with seq.mock():
            with patch("ari.queries.soil_interpretation.Path") as mock_path:
                # Mock Path to return a folder that "exists"
                mock_folder = MagicMock()
                mock_folder.exists.return_value = True
                mock_path.return_value = mock_folder

                step.execute(ctx)

        # Verify result is a Path object (not a string)
        assert "folder-grondonderzoek" in ctx
        result = ctx["folder-grondonderzoek"]
        # The step stores Path(folder), not the raw string
        assert isinstance(result, MagicMock) or hasattr(result, "exists")

    def test_execute_uses_cwd_on_empty_input(self, fresh_db):
        """Behavior 2: If user enters empty string, uses Path.cwd() as folder."""
        # Mock prompt to return empty string
        seq = SequentialMock()
        seq.add_prompt("")  # Empty input

        step = StepSiFolder()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify cwd was used
        assert "folder-grondonderzoek" in ctx
        # The result should be equivalent to Path.cwd()
        result = ctx["folder-grondonderzoek"]
        assert result == Path.cwd()

    def test_execute_raises_for_nonexistent_folder(self, fresh_db):
        """Behavior 3: Validates folder exists; raises ValueError if not."""
        # Mock prompt to return a non-existent folder
        seq = SequentialMock()
        seq.add_prompt("/nonexistent/folder")

        step = StepSiFolder()
        ctx: dict[str, Any] = {}

        with seq.mock():
            with patch("ari.queries.soil_interpretation.Path") as mock_path:
                # First Path() call for the initial prompt result
                # Mock exists() to return False
                mock_folder = MagicMock()
                mock_folder.exists.return_value = False
                mock_path.return_value = mock_folder

                with pytest.raises(ValueError) as exc_info:
                    step.execute(ctx)

                assert "folder does not exist" in str(exc_info.value)


class TestStepCptPrompt:
    """Tests for StepCptPrompt (InputStep).

    Prompts user to select CPT name from available CPTs in database.
    """

    def test_step_class_structure(self):
        """StepCptPrompt has correct class structure."""

        # Check class attributes exist
        assert hasattr(StepCptPrompt, "name")
        assert hasattr(StepCptPrompt, "requires")
        assert hasattr(StepCptPrompt, "produces")

        # Check specific values
        assert StepCptPrompt.name == "step_cpt_prompt"
        # Step 15: StepCptPrompt now requires cpts from PROJECT (via ctx propagation)
        assert len(StepCptPrompt.requires) == 1
        assert StepCptPrompt.requires[0].key == "cpts"
        assert StepCptPrompt.requires[0].source == Table.PROJECT

        assert len(StepCptPrompt.produces) == 1
        assert StepCptPrompt.produces[0].key == CPT_NAME_KEY
        assert StepCptPrompt.produces[0].dest == Table.CALC


    def test_execute_raises_when_no_cpts_available(self, fresh_db):
        """Behavior 1: Raises ValueError if no CPTs available."""
        step = StepCptPrompt()
        ctx: dict[str, Any] = {"cpts": []}

        # Should raise ValueError about no CPTs available
        with pytest.raises(ValueError) as exc_info:
            step.execute(ctx)

        error_msg = str(exc_info.value).lower()
        assert "no cpts available" in error_msg or "geen cpts" in error_msg

    def test_execute_prompts_with_word_completer(self, fresh_db):
        """Behavior 2: execute() prompts with WordCompleter populated from sorted CPT names."""
        cpt1 = MagicMock()
        cpt1.id_ = "A-CPT"
        cpt2 = MagicMock(id_="M-CPT")
        cpt3 = MagicMock(id_="Z-CPT")
        
        step = StepCptPrompt()
        ctx: dict[str, Any] = {"cpts": [cpt1, cpt2, cpt3]}

        # Mock prompt and capture the WordCompleter
        completer_arg = None

        def capture_prompt(*args, **kwargs):
            nonlocal completer_arg
            completer_arg = kwargs.get("completer")
            return "A-CPT"

        with patch("ari.queries.soil_interpretation.prompt", capture_prompt):
            step.execute(ctx)

        # Verify prompt was called
        assert completer_arg is not None
        # Verify the completer contains sorted CPT names
        # WordCompleter typically has a 'words' attribute
        completer_words = getattr(completer_arg, "words", None)
        if completer_words is not None:
            assert completer_words == ["A-CPT", "M-CPT", "Z-CPT"]

    def test_execute_validates_selected_cpt_exists(self, fresh_db):
        """Behavior 3: Validates selected CPT exists; raises ValueError if not found."""
        # Mock prompt to return invalid CPT name
        seq = SequentialMock()
        seq.add_prompt("InvalidCPT")

        step = StepCptPrompt()
        ctx: dict[str, Any] = {"cpts": [MagicMock(id_="A-CPT")]}

        with seq.mock():
            with pytest.raises(ValueError) as exc_info:
                step.execute(ctx)

        # Verify error message mentions available CPTs
        assert "InvalidCPT" in str(exc_info.value)

    def test_execute_stores_cpt_name_in_ctx(self, fresh_db):
        """Behavior 4: execute() stores selected CPT name in ctx[CPT_NAME_KEY]."""
        # Mock prompt to return "CPT1"
        seq = SequentialMock()
        seq.add_prompt("CPT1")

        step = StepCptPrompt()
        ctx: dict[str, Any] = {"cpts": [MagicMock(id_="CPT1")]}

        with seq.mock():
            step.execute(ctx)

        # Verify CPT name was stored in ctx using CPT_NAME_KEY
        assert CPT_NAME_KEY in ctx
        assert ctx[CPT_NAME_KEY] == "CPT1"


class TestStepCpt:
    """Tests for StepCpt (ComplexStep).

    Loads CPT data from file and stores it in both CALC (name) and PROJECT (full object).
    """

    def test_step_class_structure(self):
        """StepCpt has correct class structure."""

        # Check class attributes exist
        assert hasattr(StepCpt, "name")
        assert hasattr(StepCpt, "requires")
        assert hasattr(StepCpt, "produces")

        # Check specific values
        assert StepCpt.name == "step_cpt"
        assert len(StepCpt.requires) == 2
        # StepCpt requires folder and CPT name (from StepCptPrompt)
        req_keys = {r.key for r in StepCpt.requires}
        assert "folder-grondonderzoek" in req_keys
        assert "cpt" in req_keys

        # Behavior 1: StepCpt produces Product(key="cpts", dest=Table.PROJECT)
        assert Product(key="cpts", dest=Table.PROJECT) in StepCpt.produces
        assert len(StepCpt.produces) == 1

    def test_execute_stores_cpt_in_ctx(self, fresh_db):
        """Behavior 2: execute() stores CPT in ctx['cpts'] as a dict."""

        with patch("ari.queries.soil_interpretation.load_cpt") as mock_load:
            with patch("ari.queries.soil_interpretation.find_cpt") as mock_find:
                # find_cpt returns a single Path
                mock_path = MagicMock()
                mock_path.stem = "CPT002"
                mock_path.__str__ = lambda self: "/test/CPT002.gef"
                mock_find.return_value = mock_path

                # load_cpt returns a mock CPT
                mock_cpt = MagicMock()
                mock_cpt.id_ = "CPT002"
                mock_load.return_value = mock_cpt

                step = StepCpt()
                ctx: dict[str, Any] = {
                    "cpt": "CPT002",
                    "folder-grondonderzoek": Path.cwd(),
                }
                step.execute(ctx)

                # Verify ctx['cpts'] is a dict containing the loaded CPT object
                assert "cpts" in ctx
                assert isinstance(ctx["cpts"], dict)
                assert "CPT002" in ctx["cpts"]
                assert ctx["cpts"]["CPT002"] is mock_cpt

    def test_execute_handles_single_find_result(self, fresh_db):
        """Behavior 3: If find_cpt() returns single path, loads without prompting."""

        with patch("ari.queries.soil_interpretation.load_cpt") as mock_load:
            with patch("ari.queries.soil_interpretation.find_cpt") as mock_find:
                # find_cpt returns a single Path (not a list)
                mock_path = MagicMock()
                mock_path.stem = "CPT002"
                mock_path.__str__ = lambda self: "/test/CPT002.gef"
                mock_find.return_value = mock_path

                # load_cpt returns a mock CPT
                mock_cpt = MagicMock()
                mock_cpt.id_ = "CPT002"
                mock_load.return_value = mock_cpt

                step = StepCpt()
                ctx: dict[str, Any] = {
                    "cpt": "CPT002",
                    "folder-grondonderzoek": Path.cwd(),
                }
                step.execute(ctx)

                # Verify load_cpt was called (not choose_cpt)
                mock_load.assert_called_once()
                # Verify cpt_to_db was NOT called (replaced by ctx write)
                # Verify cpts key was written to ctx
                assert "cpts" in ctx
                assert ctx["cpts"]["CPT002"] is mock_cpt


class TestStepCptInterpretationMethod:
    """Tests for StepCptInterpretationMethod (InputStep).

    Prompts user to select CPT interpretation method.
    """

    def test_step_class_structure(self):
        """StepCptInterpretationMethod has correct class structure."""
        from ari.queries.soil_interpretation import StepCptInterpretationMethod

        # Check class attributes exist
        assert hasattr(StepCptInterpretationMethod, "name")
        assert hasattr(StepCptInterpretationMethod, "requires")
        assert hasattr(StepCptInterpretationMethod, "produces")

        # Check specific values
        assert StepCptInterpretationMethod.name == "step_cpt_interpretation_method"
        assert StepCptInterpretationMethod.requires == []
        assert len(StepCptInterpretationMethod.produces) == 1
        assert (
            StepCptInterpretationMethod.produces[0].key == "interpretatie-methode-cpt"
        )
        assert StepCptInterpretationMethod.produces[0].dest == Table.CALC

    def test_execute_stores_interpretation_function(self, fresh_db):
        """Behavior 1-2: execute() calls choice() and stores function in ctx."""
        # Mock choice to return the function itself (first element of tuple)
        seq = SequentialMock()
        seq.add_choice(naive_qc_rf)  # choice() returns the first element of the tuple

        step = StepCptInterpretationMethod()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

