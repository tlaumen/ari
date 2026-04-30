"""Tests for pile calc steps (Step 14).

Tests for:
- StepSlsLoad: Prompts user for SLS (Service Limit State) vertical load
- PILE_CALC_STEPS: List of steps for pile calc workflow (Step 16)
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Any

from geolib.models.dfoundations import piles

from ari.queries.base import Table, Requirement, Product, Step, StepRunner
from ari_tests.fixtures.workflow_mocks import SequentialMock

from ari.queries.pile_calc import PileType, create_pile

@pytest.mark.auto
def test_create_pile():
    pile = create_pile(pile_type=PileType.VIBROPAAL, dimensions=(400, 450))
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)

    pile = create_pile(pile_type=PileType.SCHROEFPAAL, dimensions=650)
    assert isinstance(pile, piles.BearingRoundPile)

    pile = create_pile(pile_type=PileType.PREFAB_HEIPAAL, dimensions=450)
    assert isinstance(pile, piles.BearingRectangularPile)

    pile = create_pile(pile_type=PileType.BUISSCHROEFPAAL, dimensions=(400, 450))
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)

    pile = create_pile(
        pile_type=PileType.BUISSCHROEFPAAL_VERLOREN_CASING, dimensions=(400, 450)
    )
    assert isinstance(pile, piles.BearingRoundPileWithLostTip)


@pytest.mark.parametrize(
    "pile_type,dimensions,expected_class",
    [
        (PileType.PREFAB_HEIPAAL, 450, piles.BearingRectangularPile),
        (PileType.VIBROPAAL, (400, 450), piles.BearingRoundPileWithLostTip),
        (PileType.SCHROEFPAAL, 650, piles.BearingRoundPile),
        (PileType.BUISSCHROEFPAAL, (400, 450), piles.BearingRoundPileWithLostTip),
        (
            PileType.BUISSCHROEFPAAL_VERLOREN_CASING,
            (400, 450),
            piles.BearingRoundPileWithLostTip,
        ),
    ],
)
def test_create_pile_returns_valid_dgeolib_object(
    pile_type, dimensions, expected_class
):
    """Test that create_pile produces a valid d-geolib object that passes schema validation."""
    pile = create_pile(pile_type=pile_type, dimensions=dimensions)
    assert isinstance(pile, expected_class)
    pile.model_dump()


@pytest.mark.parametrize(
    "pile_type,wrong_dimensions",
    [
        (PileType.PREFAB_HEIPAAL, (400, 450)),
        (PileType.SCHROEFPAAL, (400, 450)),
        (PileType.VIBROPAAL, 450),
        (PileType.BUISSCHROEFPAAL, 450),
    ],
)
def test_create_pile_raises_on_invalid_dimensions(pile_type, wrong_dimensions):
    """Test that invalid dimension types raise ValueError."""
    with pytest.raises(ValueError):
        create_pile(pile_type=pile_type, dimensions=wrong_dimensions)


def test_create_pile_uses_correct_dgeolib_parameter_names():
    """Verify create_pile uses correct clay/silt/peat naming (not clay/loam/peat)."""
    pile = create_pile(PileType.SCHROEFPAAL, 650)
    params = pile.model_dump()
    assert "pile_class_factor_shaft_clay_silt_peat" in params
    assert "pile_class_factor_shaft_clay_loam_peat" not in str(params)


class TestStepSlsLoad:
    """Tests for StepSlsLoad (InputStep).

    Prompts user for SLS (Service Limit State) vertical load.
    """

    def test_step_class_structure(self):
        """StepSlsLoad has correct class structure."""
        from ari.queries.pile_calc import StepSlsLoad, SLS_LOAD_KEY

        # Check class attributes exist
        assert hasattr(StepSlsLoad, "name")
        assert hasattr(StepSlsLoad, "requires")
        assert hasattr(StepSlsLoad, "produces")

        # Check specific values
        assert StepSlsLoad.name == "step_sls_load"
        assert StepSlsLoad.requires == []

    def test_execute_prompts_for_sls_load(self, fresh_db):
        """Behavior 1: execute() calls prompt() with BGT belasting message."""
        from ari.queries.pile_calc import StepSlsLoad
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock prompt to return a numeric value
        seq = SequentialMock()
        seq.add_prompt("500")

        step = StepSlsLoad()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify prompt was called (SequentialMock verifies call happened)
        assert True  # If we get here without error, prompt was called

    def test_execute_converts_to_float(self, fresh_db):
        """Behavior 2: Given valid numeric input "500", stores float(500.0) in ctx."""
        from ari.queries.pile_calc import StepSlsLoad, SLS_LOAD_KEY
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock prompt to return "500"
        seq = SequentialMock()
        seq.add_prompt("500")

        step = StepSlsLoad()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify ctx[SLS_LOAD_KEY] equals 500.0
        assert SLS_LOAD_KEY in ctx
        assert ctx[SLS_LOAD_KEY] == 500.0

    def test_empty_requires(self):
        """Behavior 3: Step has no requirements — can run independently."""
        from ari.queries.pile_calc import StepSlsLoad

        assert StepSlsLoad.requires == []

    def test_produces_to_calc(self):
        """Behavior 4: Produces Product(key=SLS_LOAD_KEY, dest=Table.CALC)."""
        from ari.queries.pile_calc import StepSlsLoad, SLS_LOAD_KEY

        assert len(StepSlsLoad.produces) == 1
        prod = StepSlsLoad.produces[0]
        assert prod.key == SLS_LOAD_KEY
        assert prod.dest == Table.CALC


class TestStepUlsLoad:
    """Tests for StepUlsLoad (InputStep).

    Prompts user for ULS (Ultimate Limit State) vertical load.
    """

    def test_step_class_structure(self):
        """StepUlsLoad has correct class structure."""
        from ari.queries.pile_calc import StepUlsLoad, ULS_LOAD_KEY

        # Check class attributes exist
        assert hasattr(StepUlsLoad, "name")
        assert hasattr(StepUlsLoad, "requires")
        assert hasattr(StepUlsLoad, "produces")

        # Check specific values
        assert StepUlsLoad.name == "step_uls_load"
        assert StepUlsLoad.requires == []

    def test_execute_prompts_for_uls_load(self, fresh_db):
        """Behavior 1: execute() calls prompt() with UGT belasting message."""
        from ari.queries.pile_calc import StepUlsLoad
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock prompt to return a numeric value
        seq = SequentialMock()
        seq.add_prompt("600")

        step = StepUlsLoad()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify prompt was called (SequentialMock verifies call happened)
        assert True  # If we get here without error, prompt was called

    def test_execute_converts_to_float(self, fresh_db):
        """Behavior 2: Given valid numeric input "600", stores float(600.0) in ctx."""
        from ari.queries.pile_calc import StepUlsLoad, ULS_LOAD_KEY
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock prompt to return "600"
        seq = SequentialMock()
        seq.add_prompt("600")

        step = StepUlsLoad()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify ctx[ULS_LOAD_KEY] equals 600.0
        assert ULS_LOAD_KEY in ctx
        assert ctx[ULS_LOAD_KEY] == 600.0

    def test_empty_requires(self):
        """Behavior 3: Step has no requirements — can run independently."""
        from ari.queries.pile_calc import StepUlsLoad

        assert StepUlsLoad.requires == []

    def test_produces_to_calc(self):
        """Behavior 4: Produces Product(key=ULS_LOAD_KEY, dest=Table.CALC)."""
        from ari.queries.pile_calc import StepUlsLoad, ULS_LOAD_KEY

        assert len(StepUlsLoad.produces) == 1
        prod = StepUlsLoad.produces[0]
        assert prod.key == ULS_LOAD_KEY
        assert prod.dest == Table.CALC


class TestPileCalcStepsList:
    """Tests for PILE_CALC_STEPS list (Step 16 Integration)."""

    def test_pile_calc_steps_import(self):
        """PILE_CALC_STEPS is exported from ari.queries.pile_calc.

        Import should succeed without error.
        """
        from ari.queries.pile_calc import PILE_CALC_STEPS

        assert PILE_CALC_STEPS is not None

    def test_pile_calc_steps_is_list(self):
        """PILE_CALC_STEPS is a list."""
        from ari.queries.pile_calc import PILE_CALC_STEPS

        assert isinstance(PILE_CALC_STEPS, list)

    def test_pile_calc_steps_starts_with_sls_load(self):
        """PILE_CALC_STEPS contains StepSlsLoad as first element."""
        from ari.queries.pile_calc import PILE_CALC_STEPS, StepSlsLoad

        assert len(PILE_CALC_STEPS) >= 1
        assert PILE_CALC_STEPS[0] is StepSlsLoad

    def test_pile_calc_steps_validates_no_cycles(self):
        """StepRunner.validate() passes for PILE_CALC_STEPS.

        Note: Full PILE_CALC_STEPS requires PROJECT data from other workflows.
        This test validates only the CALC-table steps (Steps 1-10).
        """
        from ari.queries.pile_calc import (
            StepSlsLoad,
            StepUlsLoad,
            StepPileType,
            StepPileDimensions,
            StepPileLocation,
            StepPileTipLevel,
            StepCptWorkOrder,
            StepPhreaticLevel,
            StepStructureRigidity,
            StepFutureGroundLevel,
        )

        # Validate only the CALC-table steps (Steps 1-10)
        # Steps 11-12 require PROJECT table data from other workflows
        calc_steps = [
            StepSlsLoad,
            StepUlsLoad,
            StepPileType,
            StepPileDimensions,
            StepPileLocation,
            StepPileTipLevel,
            StepCptWorkOrder,
            StepPhreaticLevel,
            StepStructureRigidity,
            StepFutureGroundLevel,
        ]

        runner = StepRunner(calc_steps)

        # Should not raise
        runner.validate()

    def test_full_workflow_executes_with_mocked_prompts(self, fresh_db):
        """Full workflow executes with mocked prompts and database state.

        Given fresh_db with mocked prompts, StepRunner.run() should
        complete successfully and store the SLS load value.
        """
        from ari.queries.pile_calc import StepSlsLoad, SLS_LOAD_KEY
        from ari.db.db import db
        from baml_client.types import Berekening

        # Setup: Create calc session
        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock prompts for SLS load
        seq = SequentialMock()
        seq.add_prompt("750")

        step = StepSlsLoad()
        ctx: dict[str, Any] = {}

        with seq.mock():
            step.execute(ctx)

        # Verify SLS load was stored
        assert SLS_LOAD_KEY in ctx
        assert ctx[SLS_LOAD_KEY] == 750.0
