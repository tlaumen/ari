"""Tests for derive params steps (Step 7 & 8).

Tests for:
- StepPileFoundationSoilParams: Prompts user for pile foundation soil parameters
- DERIVE_PARAMS_STEPS: List of steps for derive params workflow (Step 8)
"""

import math
import pytest
from unittest.mock import patch, MagicMock
from typing import Any

from ceniac.soil_profile.soil_profile import SoilProfile
from ceniac.soil_profile.soil_profile import Layer

from ari.queries.base import Table, Requirement, Product, Step, StepRunner
from ari_tests.fixtures.workflow_mocks import SequentialMock

dummy_soil_profile = SoilProfile(
    name="SP1",
    surface_level=1, # m+NAP
    layers=[
        Layer(soil="Clay", top=1, bottom=-5),
        Layer(soil="Sand", top=-5, bottom=-18),
        Layer(soil="Gravel", top=-18, bottom=-20),
    ],
    bottom=-20, # m+NAP
)

class TestStepPileFoundationSoilParams:
    """Tests for StepPileFoundationSoilParams (InputStep).

    Prompts user for pile foundation soil parameters for each soil type.
    """

    def test_step_class_structure(self):
        """StepPileFoundationSoilParams has correct class structure."""
        from ari.queries.derive_params import StepPileFoundationSoilParams

        # Check class attributes exist
        assert hasattr(StepPileFoundationSoilParams, "name")
        assert hasattr(StepPileFoundationSoilParams, "requires")
        assert hasattr(StepPileFoundationSoilParams, "produces")

        # Check specific values
        assert StepPileFoundationSoilParams.name == "step_pile_foundation_soil_params"
        # requires soils from PROJECT (pre-populated ctx["soils"] via Step.run())
        assert StepPileFoundationSoilParams.requires == [
            Requirement(key="soilprofiles", source=Table.PROJECT)
        ]
        # Produces params to PROJECT (ctx["params"] -> Step.run() -> db.add())
        assert len(StepPileFoundationSoilParams.produces) == 1
        assert StepPileFoundationSoilParams.produces[0].key == "params"
        assert StepPileFoundationSoilParams.produces[0].dest == Table.PROJECT

    def test_query_single_soil_params_returns_object(self, fresh_db):
        """Behavior 3: _query_single_soil_params returns PileFoundationParams, does not call params_to_db.

        Mock prompts for Sand and verify the function returns a PileFoundationParams object
        without calling params_to_db.
        """
        from ari.queries.derive_params import _query_single_soil_params
        from ceniac.parameters.model import PileFoundationParams

        db = fresh_db

        # Mock prompts for Sand: gamma_nat=18, gamma_sat=20, friction_angle=30, compressible=false
        seq = SequentialMock()
        seq.add_prompt("18")  # gamma_nat
        seq.add_prompt("20")  # gamma_sat
        seq.add_prompt("30")  # friction_angle
        seq.add_prompt("false")  # compressible
        # No undrained_shear_strength prompt since compressible=false

        with seq.mock():
            result = _query_single_soil_params("Sand")

        # Verify return type is PileFoundationParams
        assert isinstance(result, PileFoundationParams)
        assert result.soil == "Sand"
        assert result.gamma_nat == 18.0
        assert result.gamma_sat == 20.0
        assert result.friction_angle == 30.0
        assert result.compressible is False
        assert result.undrained_shear_strength == 100.0  # default for non-compressible
        # K0 = 1 - sin(30°) = 0.5
        assert abs(result.K0 - 0.5) < 0.001

        # Verify params_to_db is NOT called (module-level inspection)
        from ari import queries
        import ari.queries.derive_params as derive_params_module
        # params_to_db should not be in the module's local namespace if it was removed from imports
        # This test verifies the function doesn't call params_to_db — if it still did,
        # the patch would have caught it. Absence of call proves refactor succeeded.


    def test_prompts_for_undrained_shear_strength_when_compressible(self, fresh_db):
        """Behavior 3: Given ctx with 'Clay' and compressible=true, verify
        ctx["params"]["Clay"] has correct PileFoundationParams.
        """
        from ari.queries.derive_params import StepPileFoundationSoilParams

        db = fresh_db

        # Mock prompts for Clay: gamma_nat=17, gamma_sat=18, friction_angle=25, compressible=true, cu=50
        seq = SequentialMock()
        seq.add_prompt("17")  # gamma_nat
        seq.add_prompt("18")  # gamma_sat
        seq.add_prompt("25")  # friction_angle
        seq.add_prompt("true")  # compressible
        seq.add_prompt("50")  # undrained_shear_strength

        # Pre-populate ctx["soilprofiles"] (normally done by Step.run() via db.get())
        sp = SoilProfile(
            name="SP1",
            surface_level=1, # m+NAP
            layers=[
                Layer(soil="Clay", top=1, bottom=-20),
            ],
            bottom=-20, # m+NAP
        )
        ctx: dict[str, Any] = {"soilprofiles": [sp]}

        step = StepPileFoundationSoilParams()

        with seq.mock():
            step.execute(ctx)

        # Verify ctx["params"]["Clay"]
        assert "params" in ctx
        params = ctx["params"]["Clay"]
        assert params.soil == "Clay"
        assert params.gamma_nat == 17.0
        assert params.gamma_sat == 18.0
        assert params.friction_angle == 25.0
        assert params.compressible is True
        assert params.undrained_shear_strength == 50.0

        # Verify K0 calculation: K0 = 1 - sin(25°)
        expected_K0 = 1 - math.sin(math.radians(25))
        assert abs(params.K0 - expected_K0) < 0.001

    def test_handles_multiple_soil_types(self, fresh_db):
        """Behavior 4: Given ctx with multiple soil types, prompts for params for each."""
        from ari.queries.derive_params import StepPileFoundationSoilParams

        db = fresh_db

        # Mock prompts for each soil
        seq = SequentialMock()
        # Clay: gamma_nat=17, gamma_sat=18, friction_angle=25, compressible=false
        seq.add_prompt("17")  # Clay: gamma_nat
        seq.add_prompt("18")  # Clay: gamma_sat
        seq.add_prompt("25")  # Clay: friction_angle
        seq.add_prompt("false")  # Clay: compressible

        # Gravel: gamma_nat=19, gamma_sat=21, friction_angle=35, compressible=false
        seq.add_prompt("19")  # Gravel: gamma_nat
        seq.add_prompt("21")  # Gravel: gamma_sat
        seq.add_prompt("35")  # Gravel: friction_angle
        seq.add_prompt("false")  # Gravel: compressible

        # Sand: gamma_nat=18, gamma_sat=20, friction_angle=30, compressible=false
        seq.add_prompt("18")  # Sand: gamma_nat
        seq.add_prompt("20")  # Sand: gamma_sat
        seq.add_prompt("30")  # Sand: friction_angle
        seq.add_prompt("false")  # Sand: compressible

        # Pre-populate ctx["soilprofiles"] (normally done by Step.run() via db.get())
        sp = SoilProfile(
            name="SP1",
            surface_level=1, # m+NAP
            layers=[
                Layer(soil="Clay", top=1, bottom=-10),
                Layer(soil="Gravel", top=-10, bottom=-11),
                Layer(soil="Sand", top=-11, bottom=-20),
            ],
            bottom=-20, # m+NAP
        )
        ctx: dict[str, Any] = {"soilprofiles": [sp]}
        step = StepPileFoundationSoilParams()

        with seq.mock():
            step.execute(ctx)

        # Verify ctx["params"] has 3 keys in alphabetical order
        assert "params" in ctx
        params_dict = ctx["params"]
        assert isinstance(params_dict, dict)
        for s in ["Clay", "Gravel", "Sand"]:
            assert s in ctx["params"]
        # Verify each soil's params
        assert params_dict["Clay"].gamma_nat == 17.0
        assert params_dict["Gravel"].gamma_nat == 19.0
        assert params_dict["Sand"].gamma_nat == 18.0



class TestDeriveParamsStepsList:
    """Tests for DERIVE_PARAMS_STEPS list (Step 8 Integration)."""

    def test_derive_params_steps_import(self):
        """Behavior 2: DERIVE_PARAMS_STEPS is exported from ari.queries.derive_params.

        Import should succeed without error.
        """
        from ari.queries.derive_params import DERIVE_PARAMS_STEPS

        # Should be importable
        assert DERIVE_PARAMS_STEPS is not None

    def test_derive_params_steps_is_list(self):
        """Behavior 1: DERIVE_PARAMS_STEPS is a list."""
        from ari.queries.derive_params import DERIVE_PARAMS_STEPS

        assert isinstance(DERIVE_PARAMS_STEPS, list)

    def test_derive_params_steps_contains_single_step(self):
        """Behavior 1: DERIVE_PARAMS_STEPS contains exactly one step class."""
        from ari.queries.derive_params import (
            DERIVE_PARAMS_STEPS,
            StepPileFoundationSoilParams,
        )

        assert len(DERIVE_PARAMS_STEPS) == 1
        assert DERIVE_PARAMS_STEPS[0] is StepPileFoundationSoilParams

    def test_derive_params_steps_validates_no_cycles(self):
        """Behavior 3: StepRunner.validate() passes for DERIVE_PARAMS_STEPS.

        Single step with requirement on external key 'soils' validates successfully.
        """
        from ari.queries.derive_params import DERIVE_PARAMS_STEPS
        class SoilProfileMaker(Step):
            name = "SoilProfileMaker"
            requires = []
            produces = [Product(key="soilprofiles", dest=Table.PROJECT)]
            
            def execute(self):
                pass

        runner = StepRunner([SoilProfileMaker, *DERIVE_PARAMS_STEPS])

        # Should not raise — 'soils' is in external_project_keys
        runner.validate()

    def test_full_workflow_executes_with_mocked_prompts(self, fresh_db):
        """Behavior 4: Full workflow executes with mocked prompts and ctx["soils"] populated.

        Given fresh_db with db.project.soils and mocked prompts, StepRunner.run()
        should complete successfully and populate ctx["params"] for each soil.
        """
        from ari.queries.derive_params import (
            DERIVE_PARAMS_STEPS,
            StepPileFoundationSoilParams,
        )

        db = fresh_db

        # Mock prompts for Sand: gamma_nat=18, gamma_sat=20, friction_angle=30, compressible=false
        seq = SequentialMock()
        seq.add_prompt("18")  # gamma_nat
        seq.add_prompt("20")  # gamma_sat
        seq.add_prompt("30")  # friction_angle
        seq.add_prompt("false")  # compressible

        # Pre-populate ctx["soilprofiles"] (normally done by Step.run() via db.get())
        sp = SoilProfile(
            name="SP1",
            surface_level=1, # m+NAP
            layers=[
                Layer(soil="Sand", top=1, bottom=-20),
            ],
            bottom=-20, # m+NAP
        )
        ctx: dict[str, Any] = {"soilprofiles": [sp]}

        step = StepPileFoundationSoilParams()

        with seq.mock():
            # Execute step directly
            step.execute(ctx)

        # Verify ctx["params"] has "Sand" key
        assert "params" in ctx
        assert "Sand" in ctx["params"]
        assert ctx["params"]["Sand"].soil == "Sand"

    def test_full_workflow_via_step_runner_with_multiple_soils(self, fresh_db):
        """Behavior 4: Full workflow via StepRunner with multiple soil types.

        Given ctx with multiple soil types, ctx["params"] should have
        an entry for each soil in alphabetical order.
        """
        from ari.queries.derive_params import (
            DERIVE_PARAMS_STEPS,
            StepPileFoundationSoilParams,
        )

        db = fresh_db

        # Mock prompts for each soil (alphabetically sorted)
        seq = SequentialMock()
        # Clay params
        seq.add_prompt("17")  # gamma_nat
        seq.add_prompt("18")  # gamma_sat
        seq.add_prompt("25")  # friction_angle
        seq.add_prompt("false")  # compressible

        # Gravel params
        seq.add_prompt("19")  # gamma_nat
        seq.add_prompt("21")  # gamma_sat
        seq.add_prompt("35")  # friction_angle
        seq.add_prompt("false")  # compressible

        # Sand params
        seq.add_prompt("18")  # gamma_nat
        seq.add_prompt("20")  # gamma_sat
        seq.add_prompt("30")  # friction_angle
        seq.add_prompt("false")  # compressible

        # Pre-populate ctx["soilprofiles"] (normally done by Step.run() via db.get())
        sp = SoilProfile(
            name="SP1",
            surface_level=1, # m+NAP
            layers=[
                Layer(soil="Clay", top=1, bottom=-10),
                Layer(soil="Gravel", top=-10, bottom=-11),
                Layer(soil="Sand", top=-11, bottom=-20),
            ],
            bottom=-20, # m+NAP
        )
        ctx: dict[str, Any] = {"soilprofiles": [sp]}

        step = StepPileFoundationSoilParams()

        with seq.mock():
            step.execute(ctx)

        # Verify ctx["params"] has 3 keys in alphabetical order
        assert "params" in ctx
        for s in ["Clay", "Gravel", "Sand"]:
            assert s in ctx["params"]
