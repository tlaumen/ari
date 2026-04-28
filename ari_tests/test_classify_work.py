from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock, patch, MagicMock

import pytest

from baml_client.types import TypeOfWork
from baml_client.types import VerzoekVerduidelijking, Berekening

from ari.classify_work import route_prompt, route_workflows, run_call_chain
from ari.workflows.derive_params import query_pile_foundation_soil_params
from ari.report.pile import query_foundation_report
from ari.classify_work import request_clarification
from ari.queries.soil_interpretation import SOIL_INTERPRETATION_STEPS
from ari.queries.derive_params import DERIVE_PARAMS_STEPS
from ari.queries.pile_calc import PILE_CALC_STEPS
from ari.queries.pile_report import PILE_REPORTING_STEPS
from ari.queries.base import Table, StepRunner
from ari.db.db import db
from ari_tests.fixtures.workflow_mocks import SequentialMock


# Tests for Step 12: Compose PAALFUNDERING_STEPS in classify_work.py


class TestPAALFUNDERINGStepsConstant:
    """Tests for Behavior 1: PAALFUNDERING_STEPS constant exists and concatenates workflow lists."""

    def test_paalfundering_steps_exists(self):
        """PAALFUNDERING_STEPS should be importable from classify_work module."""
        from ari.classify_work import PAALFUNDERING_STEPS

        assert PAALFUNDERING_STEPS is not None

    def test_paalfundering_steps_length(self):
        """PAALFUNDERING_STEPS should have correct length (5 + 1 + 12 + 7 = 25 steps).

        Updated in Step 21: PILE_CALC_STEPS now includes all 12 pile calc steps.
        """
        from ari.classify_work import PAALFUNDERING_STEPS

        assert len(PAALFUNDERING_STEPS) == 25

    def test_paalfundering_steps_equals_concatenation(self):
        """PAALFUNDERING_STEPS should equal concatenation of three workflow step lists."""
        from ari.classify_work import PAALFUNDERING_STEPS

        expected = SOIL_INTERPRETATION_STEPS + DERIVE_PARAMS_STEPS + PILE_CALC_STEPS + PILE_REPORTING_STEPS
        assert PAALFUNDERING_STEPS == expected


class TestRouteWorkflowsBehavior:
    """Tests for route_workflows() function behaviors."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance."""
        return Mock()

    @pytest.mark.auto
    def test_route_workflows_accepts_db_parameter(self, mock_db):
        """route_workflows() should accept db: Database parameter."""
        from ari.classify_work import PAALFUNDERING_STEPS

        # This should not raise TypeError for missing db argument
        with patch("ari.classify_work.StepRunner") as mock_runner:
            mock_runner_instance = Mock()
            mock_runner_instance.run.return_value = {}
            mock_runner.return_value = mock_runner_instance

            # Call with db parameter - should not raise TypeError
            route_workflows(response=Berekening.PAALFUNDERING, db=mock_db)

    @pytest.mark.auto
    def test_route_workflows_calls_step_runner_run(self, mock_db):
        """route_workflows() should call StepRunner(PAALFUNDERING_STEPS).run(db) for PAALFUNDERING."""
        from ari.classify_work import PAALFUNDERING_STEPS

        with patch("ari.classify_work.StepRunner") as mock_runner:
            mock_runner_instance = Mock()
            mock_runner_instance.run.return_value = {}
            mock_runner.return_value = mock_runner_instance

            route_workflows(response=Berekening.PAALFUNDERING, db=mock_db)

            # Verify StepRunner was instantiated with PAALFUNDERING_STEPS
            mock_runner.assert_called_once_with(PAALFUNDERING_STEPS)
            # Verify run() was called with db
            mock_runner_instance.run.assert_called_once_with(mock_db)

    @pytest.mark.auto
    def test_route_workflows_returns_query_foundation_report(self, mock_db):
        """route_workflows() should return list containing query_foundation_report."""
        with patch("ari.classify_work.StepRunner") as mock_runner:
            mock_runner_instance = Mock()
            mock_runner_instance.run.return_value = {}
            mock_runner.return_value = mock_runner_instance

            result = route_workflows(response=Berekening.PAALFUNDERING, db=mock_db)

            # Result should be a list containing query_foundation_report
            assert isinstance(result, list)
            assert query_foundation_report in result
            assert len(result) == 1  # Only query_foundation_report in the returned list

    @pytest.mark.auto
    def test_route_workflows_raises_not_implemented_for_non_paalfundering(
        self, mock_db
    ):
        """route_workflows() should raise NotImplementedError for non-PAALFUNDERING Berekening."""
        with pytest.raises(NotImplementedError):
            route_workflows(response=Berekening.STABILITEIT, db=mock_db)


class TestRoutePromptIntegration:
    """Tests for route_prompt() integration with route_workflows()."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance."""
        return Mock()

    @pytest.mark.auto
    def test_route_prompt_passes_db_to_route_workflows(self, mock_db):
        """route_prompt() should pass db parameter to route_workflows()."""
        with patch("ari.classify_work.route_workflows") as mock_route_workflows:
            mock_route_workflows.return_value = [query_foundation_report]

            # Initialize a calculation session first (required by current implementation)
            with patch.object(mock_db, "calc"):
                route_prompt(response=Berekening.PAALFUNDERING)

            # Verify route_workflows was called with db parameter
            mock_route_workflows.assert_called_once()
            # Check that db was passed as second argument
            _, kwargs = mock_route_workflows.call_args
            assert "db" in kwargs or len(mock_route_workflows.call_args[0]) >= 2


# Legacy tests (to be updated when old workflow functions are deprecated)


@pytest.mark.auto
def test_route_workflows_legacy():
    """Legacy test for old behavior - to be updated when StepRunner is fully integrated."""
    from ari.classify_work import PAALFUNDERING_STEPS

    # This test checks the old behavior for backward compatibility during transition
    mock_db = Mock()
    with patch("ari.classify_work.StepRunner") as mock_runner:
        mock_runner_instance = Mock()
        mock_runner_instance.run.return_value = {}
        mock_runner.return_value = mock_runner_instance

        call_chain: list[Callable] = route_workflows(
            response=Berekening.PAALFUNDERING, db=mock_db
        )
    # Old behavior returned the full query chain, new behavior returns only query_foundation_report
    # This test documents the expected change
    assert query_foundation_report in call_chain

    with pytest.raises(NotImplementedError):
        _ = route_workflows(response=Berekening.STABILITEIT, db=mock_db)


@pytest.mark.auto
def test_route_prompt_berekening():
    """Test route_prompt for Berekening.PAALFUNDERING with StepRunner mocked."""
    # Mock StepRunner to avoid actual step execution (which requires user prompts)
    with patch("ari.classify_work.StepRunner") as mock_runner:
        mock_runner_instance = Mock()
        mock_runner_instance.run.return_value = {}
        mock_runner.return_value = mock_runner_instance

        call_chain: list[Callable] = route_prompt(response=Berekening.PAALFUNDERING)

        # With StepRunner integrated, route_prompt should return [query_foundation_report]
        # as the final step after StepRunner completes
        assert call_chain == [query_foundation_report]


@pytest.mark.auto
def test_route_prompt_verduidelijking():
    call_chain: list[Callable] = route_prompt(
        response=VerzoekVerduidelijking(
            intentie="Geef meer informatie",
            verzoek_tot_verduidelijking="Ik snap niet wat je vraagt. Zou je duidelijker kunnen uitleggen wat voor berekening je wil maken?",
        )
    )
    assert call_chain == [request_clarification]


@pytest.mark.auto
def test_route_prompt_error():
    # Provide a wrong type, which is not implemented!
    # These are only Berekening and VerzoekVerduidelijking
    with pytest.raises(ValueError):
        _ = route_prompt(response=TypeOfWork)


# Tests for Step 22: PAALFUNDERING_STEPS validation + full workflow integration


class TestPaalfunderingWorkflowIntegration22:
    """Integration tests for composed PAALFUNDERING workflow (Step 22).

    Tests the full 18-step workflow:
    - SOIL_INTERPRETATION_STEPS (5 steps): SI folder → CPT → CPT name →
      interpretation method → interpret CPT
    - DERIVE_PARAMS_STEPS (1 step): Prompt for soil params
    - PILE_CALC_STEPS (12 steps): Loads, pile type, dimensions, location,
      tip level, work order, phreatic level, structure rigidity, future
      ground level, skin friction, run calc
    """

    def test_paalfundering_steps_validates(self):
        """Behavior 1: StepRunner.validate() passes for PAALFUNDERING_STEPS."""
        from ari.classify_work import PAALFUNDERING_STEPS

        runner = StepRunner(PAALFUNDERING_STEPS)
        runner.validate()  # Should not raise
