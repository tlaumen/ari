"""Tests for StepInterpretCpt ctx-write migration (Step 15).

These tests verify that StepInterpretCpt:
1. Reads CPT from ctx["cpts"] instead of db.project.cpts
2. Writes SoilProfile to ctx["soilprofiles"] instead of calling soil_profile_to_db()
3. Sets soil_profile.based_on = cpt_name
4. Only produces Product(key="soilprofiles", dest=Table.PROJECT)
5. Does not import or call soil_profile_to_db
"""

import pytest
import sys
from unittest.mock import MagicMock, patch
from typing import Any

from ari.queries.base import Table, Requirement, Product


class TestStepInterpretCptRequires:
    """Tests for Behavior 1: StepInterpretCpt.requires includes cpts Requirement."""

    def test_cpts_requirement_declared(self):
        """Behavior 1: Requirement(key="cpts", source=Table.PROJECT) is in requires."""
        from ari.queries.soil_interpretation import StepInterpretCpt

        req_keys = {r.key for r in StepInterpretCpt.requires}
        assert "cpts" in req_keys

    def test_requires_has_three_entries(self):
        """Behavior 1: StepInterpretCpt.requires has exactly 3 entries."""
        from ari.queries.soil_interpretation import StepInterpretCpt

        assert len(StepInterpretCpt.requires) == 3

    def test_cpts_requirement_has_correct_source(self):
        """Behavior 1: cpts Requirement has source=Table.PROJECT."""
        from ari.queries.soil_interpretation import StepInterpretCpt

        cpts_req = next((r for r in StepInterpretCpt.requires if r.key == "cpts"), None)
        assert cpts_req is not None
        assert cpts_req.source == Table.PROJECT


class TestStepInterpretCptProduces:
    """Tests for Behavior 6: StepInterpretCpt.produces contains only soilprofiles."""

    def test_produces_has_single_entry(self):
        """Behavior 6: StepInterpretCpt.produces has exactly 1 entry."""
        from ari.queries.soil_interpretation import StepInterpretCpt

        assert len(StepInterpretCpt.produces) == 1

    def test_produces_soilprofiles_to_project(self):
        """Behavior 6: Produces Product(key="soilprofiles", dest=Table.PROJECT)."""
        from ari.queries.soil_interpretation import StepInterpretCpt

        assert (
            Product(key="soilprofiles", dest=Table.PROJECT) in StepInterpretCpt.produces
        )


class TestStepInterpretCptExecuteReadsFromCtx:
    """Tests for Behavior 2: execute() reads CPT from ctx["cpts"]."""

    def test_execute_reads_cpt_from_ctx_cpts(self, fresh_db):
        """Behavior 2: execute() obtains CPT from ctx["cpts"][cpt_name]."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Create a CPT dict to put in ctx
        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,  # CPT stored in ctx
            }
            step.execute(ctx)

            # Verify interpret_cpt was called with the CPT from ctx["cpts"]
            mock_interpret.assert_called_once()
            call_args = mock_interpret.call_args
            assert call_args.kwargs["cpt"] is cpt

    def test_execute_cpt_not_in_db_but_in_ctx_succeeds(self, fresh_db):
        """Behavior 2: CPT NOT in db.project.cpts but present in ctx["cpts"] → step succeeds."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # CPT is NOT in db.project.cpts, only in ctx["cpts"]
        assert cpt.id_ not in db.project.cpts

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Should succeed (CPT found in ctx)
            mock_interpret.assert_called_once()

    def test_execute_raises_when_cpt_missing_from_ctx(self, fresh_db):
        """Behavior 2: Raises ValueError when cpt_name not in ctx["cpts"] keys."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # ctx has cpts dict but not the CPT we're looking for
        step = StepInterpretCpt()
        ctx: dict[str, Any] = {
            "cpt": "NONEXISTENT_CPT",
            "interpretatie-methode-cpt": MagicMock(),
            "cpts": {},  # Empty dict - no CPTs available
        }

        with pytest.raises(ValueError) as exc_info:
            step.execute(ctx)

        assert "NONEXISTENT_CPT" in str(exc_info.value)

    def test_error_message_includes_available_cp_ts(self, fresh_db):
        """Behavior 2: Error message includes available CPTs for debugging."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        step = StepInterpretCpt()
        ctx: dict[str, Any] = {
            "cpt": "MISSING_CPT",
            "interpretatie-methode-cpt": MagicMock(),
            "cpts": {"CPT1": MagicMock(), "CPT2": MagicMock()},
        }

        with pytest.raises(ValueError) as exc_info:
            step.execute(ctx)

        error_msg = str(exc_info.value)
        assert (
            "not found in ctx" in error_msg.lower() or "not in ctx" in error_msg.lower()
        )
        # Should list available CPTs
        assert "CPT1" in error_msg and "CPT2" in error_msg


class TestStepInterpretCptExecuteCallsInterpretCpt:
    """Tests for Behavior 3: execute() calls interpret_cpt from workflows module."""

    def test_interpret_cpt_called_with_cpt_from_ctx(self, fresh_db):
        """Behavior 3: interpret_cpt is called once with the CPT object from ctx["cpts"]."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}
        mock_interp_func = MagicMock()

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": mock_interp_func,
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify interpret_cpt was called with correct args
            mock_interpret.assert_called_once()
            call_args = mock_interpret.call_args
            assert call_args.kwargs["cpt"] is cpt
            assert call_args.kwargs["interpretation_function"] is mock_interp_func

    def test_interpret_cpt_function_in_workflows_module(self):
        """Behavior 3: interpret_cpt is available in ari.workflows.soil_interpretation."""
        from ari.workflows import soil_interpretation as si_mod

        assert hasattr(si_mod, "interpret_cpt")
        assert callable(si_mod.interpret_cpt)

    def test_soil_profile_to_db_not_imported_in_queries_module(self):
        """Behavior 3: soil_profile_to_db is NOT imported in ari.queries.soil_interpretation.

        StepInterpretCpt only imports interpret_cpt from workflows module.
        The workflows module may still have soil_profile_to_db (used by legacy query_* functions),
        but the queries module (which contains the Step class) should not import it.
        """
        import ari.queries.soil_interpretation as qsi_mod
        import ari.workflows.soil_interpretation as wsi_mod

        # Verify soil_profile_to_db is NOT in the queries module (Step location)
        assert not hasattr(qsi_mod, "soil_profile_to_db"), (
            "soil_profile_to_db should not be imported in ari.queries.soil_interpretation"
        )

        # Verify interpret_cpt IS available in workflows module (Step's dependency)
        assert hasattr(wsi_mod, "interpret_cpt"), (
            "interpret_cpt should be available in ari.workflows.soil_interpretation"
        )


class TestStepInterpretCptExecuteSetsBasedOn:
    """Tests for Behavior 4: execute() sets soil_profile.based_on = cpt_name."""

    def test_based_on_set_before_writing_to_ctx(self, fresh_db):
        """Behavior 4: After execute(), ctx["soilprofiles"].based_on == cpt_name."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            # Create a mock soil profile that we can inspect
            mock_soil_profile = MagicMock()
            mock_soil_profile.based_on = None
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify based_on was set to the CPT name
            assert mock_soil_profile.based_on == cpt.id_

    def test_based_on_is_set_via_mutation(self, fresh_db):
        """Behavior 4: based_on is set via in-place mutation (not copy)."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt, sp
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            # Use real SoilProfile from test_utils fixture
            mock_interpret.return_value = sp

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify based_on is set on the same object in ctx
            assert ctx["soilprofiles"].based_on == cpt.id_
            assert ctx["soilprofiles"] is sp  # Same object, not copied


class TestStepInterpretCptExecuteWritesToCtx:
    """Tests for Behavior 5: execute() writes SoilProfile to ctx["soilprofiles"]."""

    def test_soilprofiles_key_in_ctx_after_execute(self, fresh_db):
        """Behavior 5: After execute(), "soilprofiles" is in ctx."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            assert "soilprofiles" in ctx

    def test_soilprofiles_is_same_object_as_returned_by_interpret_cpt(self, fresh_db):
        """Behavior 5: ctx["soilprofiles"] is the same object returned by interpret_cpt."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify it's the same object, not a copy
            assert ctx["soilprofiles"] is mock_soil_profile

    def test_soil_profile_to_db_not_called_in_step(self, fresh_db):
        """Behavior 5: StepInterpretCpt does NOT call soil_profile_to_db.

        The step only imports interpret_cpt from workflows module.
        soil_profile_to_db may still exist in workflows module (used by legacy query_* functions)
        but is NOT imported or called by StepInterpretCpt.
        """
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify step wrote to ctx, not to db directly
            assert "soilprofiles" in ctx

        # Verify soil_profile_to_db is NOT imported in ari.queries.soil_interpretation
        import ari.queries.soil_interpretation as qsi_mod

        assert not hasattr(qsi_mod, "soil_profile_to_db"), (
            "soil_profile_to_db should not be imported in ari.queries.soil_interpretation"
        )


class TestStepInterpretCptExecuteNoRegression:
    """Regression tests: existing behavior preserved."""

    def test_interpretation_function_from_ctx(self, fresh_db):
        """Interpretation function comes from ctx["interpretatie-methode-cpt"]."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        cpt_dict = {cpt.id_: cpt}
        mock_interp_func = MagicMock()

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": cpt.id_,
                "interpretatie-methode-cpt": mock_interp_func,
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Verify interpret_cpt was called with the function from ctx
            call_args = mock_interpret.call_args
            assert call_args.kwargs["interpretation_function"] is mock_interp_func

    def test_cpt_name_from_ctx_cpt_key(self, fresh_db):
        """CPT name comes from ctx["cpt"], used to index ctx["cpts"]."""
        from ari.queries.soil_interpretation import StepInterpretCpt
        from ari.db.db import db
        from ari_tests.test_utils import cpt
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Use a different key for ctx["cpt"] than cpt.id_ to verify lookup
        cpt_dict = {"MY-CPT-NAME": cpt}

        with patch(
            "ari.workflows.soil_interpretation.interpret_cpt"
        ) as mock_interpret:
            mock_soil_profile = MagicMock()
            mock_interpret.return_value = mock_soil_profile

            step = StepInterpretCpt()
            ctx: dict[str, Any] = {
                "cpt": "MY-CPT-NAME",  # Different key
                "interpretatie-methode-cpt": MagicMock(),
                "cpts": cpt_dict,
            }
            step.execute(ctx)

            # Should use "MY-CPT-NAME" to look up CPT
            mock_interpret.assert_called_once()
            assert mock_interpret.call_args.kwargs["cpt"] is cpt
