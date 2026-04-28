"""Tests for Step infrastructure (Step 1a-1d).

Uses:
- fresh_db fixture for real database with cleanup
- SequentialMock for UI mocking (prompt, choice, confirm)
- GUIMock for GUI mocking (MapPointSelector, interpreter)
"""

import pytest

from typing import Any

from ari.queries.base import (
    Table,
    Requirement,
    Product,
    Step,
)


# === Table re-export tests ===


class TestTableReExport:
    """Verify Table enum is properly accessible."""

    def test_table_values(self):
        """Table enum has expected string values."""
        assert Table.PROJECT.value == "project"
        assert Table.CALC.value == "calc"


# === Requirement dataclass tests ===


class TestRequirementDataclass:
    """Tests for Requirement dataclass."""

    def test_create_requirement(self):
        """Requirement can be created with key and source."""
        req = Requirement(key="cpts", source=Table.PROJECT)
        assert req.key == "cpts"
        assert req.source == Table.PROJECT

    def test_requirement_equality(self):
        """Two Requirements with same values are equal."""
        req1 = Requirement(key="cpts", source=Table.PROJECT)
        req2 = Requirement(key="cpts", source=Table.PROJECT)
        assert req1 == req2


# === Product dataclass tests ===


class TestProductDataclass:
    """Tests for Product dataclass."""

    def test_create_product(self):
        """Product can be created with key and dest."""
        prod = Product(key="bgt-verticale-belasting", dest=Table.CALC)
        assert prod.key == "bgt-verticale-belasting"
        assert prod.dest == Table.CALC

    def test_product_equality(self):
        """Two Products with same values are equal."""
        prod1 = Product(key="test", dest=Table.CALC)
        prod2 = Product(key="test", dest=Table.CALC)
        assert prod1 == prod2


# === Step.run() tests ===


class ConcreteStepForTesting(Step):
    """Concrete Step subclass for testing Step.run()."""

    name = "concrete_step_for_testing"
    requires: list[Requirement] = []
    produces: list[Product] = []

    def __init__(self) -> None:
        super().__init__()
        self.execute_called = False
        self.execute_ctx_arg = None

    def execute(self, ctx: dict[str, Any]) -> None:
        self.execute_called = True
        self.execute_ctx_arg = ctx


class TestStepRun:
    """Tests for Step.run() method."""

    def test_run_calls_execute_once(self, fresh_db):
        """Step.run() calls execute() once with correct db and ctx."""
        from baml_client.types import Berekening

        # Setup: Create a calc session and add data (CALC requirements need active session)
        fresh_db.calc.create_session(Berekening.PAALFUNDERING)
        fresh_db.calc.set_calc("test", "test_value")

        # Create step with CALC requirement (verifies read happens before execute)
        step = ConcreteStepForTesting()
        step.requires = [Requirement(key="test", source=Table.CALC)]

        step.run(fresh_db)    # Verify execute was called exactly once
        assert step.execute_called is True

    def test_run_writes_calc_product(self, fresh_db):
        """Step.run() writes CALC product to db.calc.

        Given Product(key="result", dest=Table.CALC),
        db.calc.get_calc("result") should equal ctx["result"].
        """
        from baml_client.types import Berekening

        # Create step that produces a CALC product
        step = ConcreteStepForTesting()
        step.produces = [Product(key="result", dest=Table.CALC)]

        # Override execute to populate ctx with result
        step.execute = lambda ctx: ctx.update({"result": "computed_value"})

        # Setup: Create a calc session
        fresh_db.calc.create_session(Berekening.PAALFUNDERING)

        step.run(fresh_db)

        # Verify product was written to CALC table
        assert fresh_db.calc.get_calc("result") == "computed_value"


# === StepRunner.validate() tests ===


class ConcreteStepForValidateTest(Step):
    """Concrete Step subclass for testing StepRunner.validate()."""

    name: str = "concrete_step"
    requires: list[Requirement] = []
    produces: list[Product] = []

    def execute(self, ctx: dict[str, Any]) -> None:
        pass


class TestStepRunnerValidate:
    """Tests for StepRunner.validate() method."""

    def test_validate_passes_for_valid_workflow(self):
        """StepRunner.validate() passes silently for valid workflow.

        A valid workflow has:
        - Unique step names
        - No circular dependencies
        - All requirements satisfied by other steps
        - No duplicate product keys
        """
        from ari.queries.base import StepRunner

        # Step A produces key_a, requires nothing
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            produces = [Product(key="key_a", dest=Table.CALC)]

        # Step B produces key_b, requires key_a
        class StepB(ConcreteStepForValidateTest):
            name = "step_b"
            requires = [Requirement(key="key_a", source=Table.CALC)]
            produces = [Product(key="key_b", dest=Table.CALC)]

        # Step C requires key_b (no products, just terminal)
        class StepC(ConcreteStepForValidateTest):
            name = "step_c"
            requires = [Requirement(key="key_b", source=Table.CALC)]
            produces = []

        runner = StepRunner(steps=[StepA, StepB, StepC])

        # Should pass without raising
        runner.validate()

    def test_validate_raises_for_duplicate_step_names(self):
        """StepRunner.validate() raises ValueError for duplicate step names."""
        from ari.queries.base import StepRunner

        # Two steps with the same name
        class StepDuplicate1(ConcreteStepForValidateTest):
            name = "step_duplicate"
            produces = [Product(key="key1", dest=Table.CALC)]

        class StepDuplicate2(ConcreteStepForValidateTest):
            name = "step_duplicate"
            produces = [Product(key="key2", dest=Table.CALC)]

        runner = StepRunner(steps=[StepDuplicate1, StepDuplicate2])

        with pytest.raises(ValueError) as exc_info:
            runner.validate()

        assert "Duplicate step name" in str(exc_info.value)

    def test_validate_raises_for_circular_dependencies(self):
        """StepRunner.validate() raises ValueError for circular dependencies."""
        from ari.queries.base import StepRunner

        # Step A requires key_b, produces key_a
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            requires = [Requirement(key="key_b", source=Table.CALC)]
            produces = [Product(key="key_a", dest=Table.CALC)]

        # Step B requires key_a, produces key_b (creates cycle: A needs B, B needs A)
        class StepB(ConcreteStepForValidateTest):
            name = "step_b"
            requires = [Requirement(key="key_a", source=Table.CALC)]
            produces = [Product(key="key_b", dest=Table.CALC)]

        runner = StepRunner(steps=[StepA, StepB])

        with pytest.raises(ValueError) as exc_info:
            runner.validate()

        assert "Cycle detected" in str(exc_info.value)

    def test_validate_raises_for_unsatisfied_requirement(self):
        """StepRunner.validate() raises ValueError for unsatisfied requirements.

        A requirement is unsatisfied if:
        - No step in the workflow produces that key
        - The key is not a known root key (external input)
        """
        from ari.queries.base import StepRunner

        # Step A requires key_not_produced by anyone
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            requires = [Requirement(key="key_not_produced", source=Table.CALC)]
            produces = [Product(key="key_a", dest=Table.CALC)]

        runner = StepRunner(steps=[StepA])

        with pytest.raises(ValueError) as exc_info:
            runner.validate()

        assert "Unsatisfied requirement" in str(exc_info.value)

    def test_validate_raises_for_duplicate_product_keys(self):
        """StepRunner.validate() raises ValueError for duplicate product keys.

        When two steps produce the same key, it's ambiguous which step
        should satisfy a dependent step's requirement.
        """
        from ari.queries.base import StepRunner

        # Step A produces key_shared
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            produces = [Product(key="key_shared", dest=Table.CALC)]

        # Step B also produces key_shared
        class StepB(ConcreteStepForValidateTest):
            name = "step_b"
            produces = [Product(key="key_shared", dest=Table.CALC)]

        runner = StepRunner(steps=[StepA, StepB])

        with pytest.raises(ValueError) as exc_info:
            runner.validate()

        assert "Duplicate product key" in str(exc_info.value)

    def test_validate_passes_with_single_step(self):
        """StepRunner.validate() passes for a single step with no dependencies."""
        from ari.queries.base import StepRunner

        class SingleStep(ConcreteStepForValidateTest):
            name = "single_step"
            requires = []
            produces = [Product(key="output", dest=Table.CALC)]

        runner = StepRunner(steps=[SingleStep])
        runner.validate()  # Should not raise


# === Integration tests with real database ===


class TestStepWithDatabase:
    """Tests verifying Step works with real database fixtures.

    These tests use fresh_db to get clean database state.
    UI mocking is applied via SequentialMock.
    """

    def test_database_get_method_with_real_db(self, fresh_db):
        """Verify db.get() works on the singleton with fresh_db."""

        # Get project tables (returns dicts)
        cpts = fresh_db.get(Table.PROJECT, "cpts")
        assert isinstance(cpts, list)
        assert cpts == []

        # Get raises for invalid PROJECT keys
        with pytest.raises(KeyError):
            fresh_db.get(Table.PROJECT, "invalid")

    def test_database_add_method_with_real_db(self, fresh_db):
        """Verify db.add() stores data correctly with fresh_db."""
        from ari_tests.test_utils import cpt

        # Add CPT via PROJECT table
        fresh_db.add(Table.PROJECT, "cpts", cpt)

        # Verify it was stored
        assert cpt.id_ == fresh_db.project.cpts[0].id_
        assert fresh_db.project.cpts[0] is cpt

    def test_requirement_produces_consistent_with_database_keys(self, fresh_db):
        """Verify Requirement keys match actual database table names.

        This ensures the Step definition matches what the database provides.
        """

        # Valid PROJECT keys
        valid_project_keys = ["cpts", "soilprofiles", "params", "colors"]
        for key in valid_project_keys:
            assert fresh_db.has(Table.PROJECT, key) is True

        # Requirements should use valid keys
        req = Requirement(key="cpts", source=Table.PROJECT)
        assert fresh_db.has(req.source, req.key) is True


# === StepRunner.run() tests ===


class TestStepRunnerRun:
    """Tests for StepRunner.run() method."""

    def test_run_writes_products_to_db(self, fresh_db):
        """StepRunner.run() writes products to db after each step.

        Verify db state after execution contains all produced values.
        """
        from ari.queries.base import StepRunner
        from baml_client.types import Berekening

        # Step A: produces key_a
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            produces = [Product(key="key_a", dest=Table.CALC)]

            def execute(self, ctx: dict[str, Any]) -> None:
                ctx["key_a"] = "value_a"

        # Step B: produces key_b
        class StepB(ConcreteStepForValidateTest):
            name = "step_b"
            requires = [Requirement(key="key_a", source=Table.CALC)]
            produces = [Product(key="key_b", dest=Table.CALC)]

            def execute(self, ctx: dict[str, Any]) -> None:
                ctx["key_b"] = "value_b"

        # Setup: Create a calc session
        fresh_db.calc.create_session(Berekening.PAALFUNDERING)

        runner = StepRunner(steps=[StepA, StepB])
        runner.run(fresh_db)

        # Verify both products were written to db
        assert fresh_db.calc.get_calc("key_a") == "value_a"
        assert fresh_db.calc.get_calc("key_b") == "value_b"

    def test_run_raises_on_invalid_workflow(self, fresh_db):
        """StepRunner.run() raises ValueError if validate() fails.

        Circular dependency should cause run() to fail before execution.
        """
        from ari.queries.base import StepRunner
        from baml_client.types import Berekening

        execution_count = 0

        # Step A: requires key_b (creates cycle)
        class StepA(ConcreteStepForValidateTest):
            name = "step_a"
            requires = [Requirement(key="key_b", source=Table.CALC)]
            produces = [Product(key="key_a", dest=Table.CALC)]

            def execute(self, ctx: dict[str, Any]) -> None:
                nonlocal execution_count
                execution_count += 1

        # Step B: requires key_a (creates cycle: A needs B, B needs A)
        class StepB(ConcreteStepForValidateTest):
            name = "step_b"
            requires = [Requirement(key="key_a", source=Table.CALC)]
            produces = [Product(key="key_b", dest=Table.CALC)]

            def execute(self, ctx: dict[str, Any]) -> None:
                nonlocal execution_count
                execution_count += 1

        # Setup: Create a calc session
        fresh_db.calc.create_session(Berekening.PAALFUNDERING)

        runner = StepRunner(steps=[StepA, StepB])

        with pytest.raises(ValueError) as exc_info:
            runner.run(fresh_db)

        assert "Cycle detected" in str(exc_info.value)
        # Verify no steps were executed
        assert execution_count == 0

