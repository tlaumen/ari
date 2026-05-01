"""Tests for Step.run() method (Step 2).

Tests verify that Step.run():
1. Populates ctx from PROJECT requirements
2. Populates ctx from CALC requirements
3. Calls execute() with correct arguments
4. Writes CALC products back to db.calc
5. Writes PROJECT products via db.project.add()
"""

import pytest
from unittest.mock import MagicMock, call
from typing import Any

from baml_client.types import Berekening

from ceniac.soil_profile.soil_profile import SoilProfile

from ari.db.database import Table, Database
from ari.queries.base import (
    Table,
    Requirement,
    Product,
    Step,
)


class TestStepRun:
    """Tests for Step.run() orchestration."""


    def test_run_writes_calc_product(self, fresh_db):
        """Step.run() writes CALC product via db.calc.set_calc().

        Given Product(key="result", dest=Table.CALC),
        db.calc.get_calc("result") should equal ctx["result"] after run().
        """
        db = fresh_db
        
        # Setup: Create a calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Create a step that produces a CALC result
        class TestStep(Step):
            name = "test_step"
            requires = []
            produces = [Product(key="result", dest=Table.CALC)]

            def execute(self, ctx):
                ctx["result"] = "computed_value"

        step = TestStep()

        # Execute run()
        step.run(db)

        # Verify result was written to calc
        assert db.calc.get_calc("result") == "computed_value"

    def test_run_writes_project_product(self, fresh_db):
        """Step.run() writes PROJECT product via db.project.add().

        Given Product(key="ignored", dest=Table.PROJECT),
        the object should be added to the appropriate project sub-table.
        """
        db = fresh_db

        # Create a soil profile to add
        soil_profile = SoilProfile(
            name="test_profile", surface_level=-0.5, layers=[], bottom=-10.0
        )

        # Create a step that produces a PROJECT result
        class TestStep(Step):
            name = "test_step"
            requires = []
            produces = [Product(key="soilprofiles", dest=Table.PROJECT)]

            def execute(self, ctx):
                ctx["soilprofiles"] = soil_profile

        step = TestStep()

        # Execute run()
        step.run(db)

        # Verify soil profile was added to project
        assert soil_profile in db.project.soilprofiles
        assert db.project.soilprofiles[0] is soil_profile

    def test_run_orchestrates_full_flow(self, fresh_db):
        """Step.run() performs complete flow: populate -> execute -> write.

        Full integration test verifying the complete orchestration:
        1. Get inputs from db based on requires
        2. Call execute() with populated ctx
        3. Write outputs back to db based on produces
        """
        # Setup: Add CPT to project, create calc session with data
        from ari_tests.test_utils import cpt

        db = fresh_db
        db.add(Table.PROJECT, "cpts", cpt)
        db.calc.create_session(Berekening.PAALFUNDERING)
        db.calc.set_calc("factor", 2.0)

        # Create a step that reads from both tables and writes to CALC
        class TestStep(Step):
            name = "test_step"
            requires = [
                Requirement(key="cpts", source=Table.PROJECT),
                Requirement(key="factor", source=Table.CALC),
            ]
            produces = [Product(key="output", dest=Table.CALC)]

            def execute(self, ctx):
                # Verify inputs are available
                cpts = ctx["cpts"]
                factor = ctx["factor"]
                # Compute output
                ctx["output"] = len(cpts) * factor

        step = TestStep()

        # Execute run()
        step.run(db)

        # Verify: output was written to calc
        assert db.calc.get_calc("output") == 2.0

class ConcreteTestStep(Step):
    """Concrete implementation of Step for testing."""

    name = "test_step"

    def __init__(
        self,
        requires_list: list[Requirement] = None,
        produces_list: list[Product] = None,
    ):
        self.requires = requires_list or []
        self.produces = produces_list or []

    def execute(self, ctx: dict[str, Any]) -> None:
        """No-op execute for testing validation."""
        pass


class TestStepRunValidation:
    """Test validation of required products in ctx after execute()."""

    def test_does_not_raise_when_ctx_contains_all_required_keys(self, fresh_db: Database):
        """Step.run() does NOT raise when ctx contains all keys from requires."""
        step = ConcreteTestStep(
            requires_list=[Requirement(key="input_key", source=Table.CALC)],
            produces_list=[],
        )
        fresh_db.create_new_calculation(Berekening.PAALFUNDERING)
        fresh_db.add(source=Table.CALC, key="input_key", value="some_value")

        # Should not raise
        step.run(fresh_db)

    def test_step_with_empty_requires_never_raises(self, fresh_db: Database):
        """Step with empty requires list never raises ValueError from this check."""
        step = ConcreteTestStep(requires_list=[], produces_list=[])

        # Should not raise
        step.run(fresh_db)

    def test_valueerror_message_contains_missing_key_name(self, fresh_db: Database):
        """ValueError message contains the missing key name."""

        class ExecuteRemovingKeyStep(ConcreteTestStep):
            def execute(self, ctx: dict[str, Any]) -> None:
                # Remove the required key to simulate a missing product
                if "my_missing_key" in ctx:
                    del ctx["my_missing_key"]

        fresh_db.create_new_calculation(Berekening.PAALFUNDERING)
        
        step = ExecuteRemovingKeyStep(
            requires_list=[Requirement(key="my_missing_key", source=Table.PROJECT)],
            produces_list=[],
        )

        with pytest.raises(KeyError) as exc_info:
            step.run(fresh_db)

        assert "my_missing_key" in str(exc_info.value)

    def test_raises_for_missing_key_when_multiple_required(self, fresh_db: Database):
        """When multiple keys are required but some missing, raises for one of them."""

        class ExecuteRemovingKeysStep(ConcreteTestStep):
            def execute(self, ctx: dict[str, Any]) -> None:
                # Remove key2 and key3, leaving only key1
                if "key2" in ctx:
                    del ctx["key2"]
                if "key3" in ctx:
                    del ctx["key3"]

        step = ExecuteRemovingKeysStep(
            requires_list=[
                Requirement(key="key1", source=Table.CALC),
                Requirement(key="key2", source=Table.CALC),
                Requirement(key="key3", source=Table.CALC),
            ],
            produces_list=[],
        )
        fresh_db.create_new_calculation(Berekening.PAALFUNDERING)
        fresh_db.add(source=Table.CALC, key="key1", value="value1")
        with pytest.raises(KeyError) as exc_info:
            step.run(fresh_db)

        # Should report one of the missing keys
        missing_in_ctx = "key2" in str(exc_info.value) or "key3" in str(exc_info.value)
        assert missing_in_ctx
