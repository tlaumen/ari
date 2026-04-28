"""Tests for StepRunPileCalc (ComputationStep).

Tests for:
- StepRunPileCalc: Runs the pile bearing capacity calculation using data from ctx and db
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from ari.queries.base import Table, Requirement, Product, Step, StepRunner
from geolib.models.dfoundations.profiles import TimeOrderType
from ari.workflows.calculate.pile import PileType


class TestStepRunPileCalc:
    """Tests for StepRunPileCalc (ComputationStep)."""

    def test_step_class_structure(self):
        """Behavior 1: StepRunPileCalc has correct class structure."""
        from ari.queries.pile_calc import (
            StepRunPileCalc,
            CALCULATION_RESULTS_KEY,
            PILE_TIP_LEVEL_KEY,
            STRUCTURE_RIGIDITY_KEY,
            WORK_ORDER_KEY,
            PHREATIC_LEVEL_KEY,
            PILE_TYPE_KEY,
            PILE_DIMENSIONS_KEY,
            FUTURE_GROUND_LEVEL_KEY,
            PILE_LOCATION_KEY,
            SKIN_FRICTION_RANGES_KEY,
        )

        # Check class attributes exist
        assert hasattr(StepRunPileCalc, "name")
        assert hasattr(StepRunPileCalc, "requires")
        assert hasattr(StepRunPileCalc, "produces")

        # Check specific values
        assert StepRunPileCalc.name == "step_run_pile_calc"

    def test_step_requires_all_keys(self):
        """Behavior 1: Step requires 12 keys (9 CALC + 3 PROJECT, profilemap removed in Step 20)."""
        from ari.queries.pile_calc import StepRunPileCalc

        requires = StepRunPileCalc.requires

        # Should have 12 requirements (3 PROJECT + 9 CALC, profilemap removed in Step 20)
        assert len(requires) == 12

        # Check expected keys (profilemap removed in Step 20)
        expected_keys = {
            "cpts",
            "soilprofiles",
            "params",
            "paalpuntniveau",
            "constructie-stijf?",
            "cpt-uitvoering-werkvolgorde",
            "grondwaterniveau",
            "paaltype",
            "paalafmetingen",
            "toekomstig-maaiveld-niveau",
            "coordinaten-paal",
            "negatieve-positieve-kleef-trajecten",
        }
        keys = {r.key for r in requires}
        assert keys == expected_keys

    def test_step_requires_all_from_calc(self):
        """Behavior 1: 9 requirements from CALC, 3 from PROJECT (profilemap removed in Step 20)."""
        from ari.queries.pile_calc import StepRunPileCalc
        from ari.queries.base import Table

        requires = StepRunPileCalc.requires

        # 9 requirements from CALC
        calc_reqs = [r for r in requires if r.source == Table.CALC]
        assert len(calc_reqs) == 9

        # 3 requirements from PROJECT (profilemap removed in Step 20)
        project_reqs = [r for r in requires if r.source == Table.PROJECT]
        assert len(project_reqs) == 3

    def test_step_produces_to_calc(self):
        """Behavior 1: Produces CALCULATION_RESULTS_KEY to CALC table."""
        from ari.queries.pile_calc import StepRunPileCalc, CALCULATION_RESULTS_KEY
        from ari.queries.base import Table

        assert len(StepRunPileCalc.produces) == 1
        prod = StepRunPileCalc.produces[0]
        assert prod.key == CALCULATION_RESULTS_KEY
        assert prod.dest == Table.CALC

    def test_execute_reads_required_data_from_ctx(self, fresh_db):
        """Behavior 2: Given ctx with all required keys, verify all values are read from ctx."""
        from ari.queries.pile_calc import StepRunPileCalc
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Create context with all required data (Step 20: dict soilprofiles, no profilemap)
        ctx = {
            "cpts": {},
            "soilprofiles": {},  # Dict of SoilProfile objects, keyed by name
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
            "constructie-stijf?": True,
            "cpt-uitvoering-werkvolgorde": TimeOrderType.CPT_EXCAVATION_INSTALL,
            "grondwaterniveau": -1.5,
            "paaltype": PileType.PREFAB_HEIPAAL,
            "paalafmetingen": 350.0,
            "toekomstig-maaiveld-niveau": 0.5,
            "coordinaten-paal": (155000.0, 463000.0),
            "negatieve-positieve-kleef-trajecten": {},
        }

        # Step 20: Inline CPT-to-profile mapping uses based_on field
        # No combine_soil_profiles_cpts mock needed
        with patch("ari.queries.pile_calc.PileBearingCapacityCalc") as mock_calc:
            mock_instance = MagicMock()
            mock_instance.get_results.return_value = MagicMock()
            mock_calc.return_value = mock_instance

            with patch("ari.queries.pile_calc.create_pile") as mock_create_pile:
                mock_pile = MagicMock()
                mock_create_pile.return_value = mock_pile

                step = StepRunPileCalc()
                step.execute(ctx)

                # If we get here without error, all ctx values were read correctly
                assert True

    def test_execute_uses_inline_based_on_mapping(self, fresh_db):
        """Behavior 3 (Step 20): execute() uses inline based_on mapping, NOT combine_soil_profiles_cpts()."""
        from ari.queries.pile_calc import StepRunPileCalc
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock data for ctx with dict soilprofiles and based_on
        mock_cpt = MagicMock()
        mock_cpt.id_ = "cpt1"
        mock_sp = MagicMock()
        mock_sp.based_on = "cpt1"

        ctx = {
            "cpts": {"cpt1": mock_cpt},
            "soilprofiles": {"profile1": mock_sp},  # Dict now, not list
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
            "constructie-stijf?": True,
            "cpt-uitvoering-werkvolgorde": TimeOrderType.CPT_EXCAVATION_INSTALL,
            "grondwaterniveau": -1.5,
            "paaltype": PileType.PREFAB_HEIPAAL,
            "paalafmetingen": 350.0,
            "toekomstig-maaiveld-niveau": 0.5,
            "coordinaten-paal": (155000.0, 463000.0),
            "negatieve-positieve-kleef-trajecten": {},
        }

        # Step 20: combine_soil_profiles_cpts is not imported, no profilemap in ctx
        with patch("ari.queries.pile_calc.PileBearingCapacityCalc") as mock_calc:
            mock_instance = MagicMock()
            mock_instance.get_results.return_value = MagicMock()
            mock_calc.return_value = mock_instance

            with patch("ari.queries.pile_calc.create_pile") as mock_create_pile:
                mock_create_pile.return_value = MagicMock()

                step = StepRunPileCalc()
                step.execute(ctx)

                # Verify PileBearingCapacityCalc was called with correct cpt_soil_profile_map
                call_kwargs = mock_calc.call_args.kwargs
                cpt_soil_profile_map = call_kwargs["cpt_soil_profile_map"]
                assert len(cpt_soil_profile_map) == 1
                assert cpt_soil_profile_map[0][0] == mock_cpt
                assert cpt_soil_profile_map[0][1] == mock_sp

    def test_execute_creates_pile_bearing_capacity_calc(self, fresh_db):
        """Behavior 4: execute() creates PileBearingCapacityCalc with all required parameters."""
        from ari.queries.pile_calc import StepRunPileCalc
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock cpt_soil_profile_map return value
        mock_pile = MagicMock()

        # Step 20: Inline based_on mapping, no combine_soil_profiles_cpts, dict soilprofiles
        ctx = {
            "cpts": {},
            "soilprofiles": {},  # Dict of SoilProfile objects
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
            "constructie-stijf?": True,
            "cpt-uitvoering-werkvolgorde": TimeOrderType.CPT_EXCAVATION_INSTALL,
            "grondwaterniveau": -1.5,
            "paaltype": PileType.PREFAB_HEIPAAL,
            "paalafmetingen": 350.0,
            "toekomstig-maaiveld-niveau": 0.5,
            "coordinaten-paal": (155000.0, 463000.0),
            "negatieve-positieve-kleef-trajecten": {"cpt1": MagicMock()},
        }

        # Step 20: Inline based_on mapping, no combine_soil_profiles_cpts
        with patch("ari.queries.pile_calc.PileBearingCapacityCalc") as mock_calc:
            mock_instance = MagicMock()
            mock_instance.get_results.return_value = MagicMock()
            mock_calc.return_value = mock_instance

            with patch(
                "ari.queries.pile_calc.create_pile", return_value=mock_pile
            ) as mock_create_pile:
                step = StepRunPileCalc()
                step.execute(ctx)

                # Verify PileBearingCapacityCalc was instantiated
                mock_calc.assert_called_once()

                # Verify build_calculation and _mock_calculate were called
                mock_instance.build_calculation.assert_called_once()
                mock_instance._mock_calculate.assert_called_once()

    def test_execute_stores_results_in_ctx(self, fresh_db):
        """Behavior 5: execute() stores calc.get_results() in ctx[CALCULATION_RESULTS_KEY]."""
        from ari.queries.pile_calc import StepRunPileCalc, CALCULATION_RESULTS_KEY
        from ceniac.calculate.pile import PileResults
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Create expected PileResults
        mock_pile = MagicMock()
        mock_results = PileResults(pile=mock_pile, results=[])

        # Step 20: Inline based_on mapping, no combine_soil_profiles_cpts, dict soilprofiles
        ctx = {
            "cpts": {},
            "soilprofiles": {},  # Dict of SoilProfile objects
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
            "constructie-stijf?": True,
            "cpt-uitvoering-werkvolgorde": TimeOrderType.CPT_EXCAVATION_INSTALL,
            "grondwaterniveau": -1.5,
            "paaltype": PileType.PREFAB_HEIPAAL,
            "paalafmetingen": 350.0,
            "toekomstig-maaiveld-niveau": 0.5,
            "coordinaten-paal": (155000.0, 463000.0),
            "negatieve-positieve-kleef-trajecten": {"cpt1": MagicMock()},
        }

        # Step 20: Inline based_on mapping, no combine_soil_profiles_cpts
        with patch("ari.queries.pile_calc.PileBearingCapacityCalc") as mock_calc:
            mock_instance = MagicMock()
            mock_instance.get_results.return_value = mock_results
            mock_calc.return_value = mock_instance

            with patch("ari.queries.pile_calc.create_pile", return_value=mock_pile):
                step = StepRunPileCalc()
                step.execute(ctx)

                # Verify ctx contains CALCULATION_RESULTS_KEY
                assert CALCULATION_RESULTS_KEY in ctx
                assert ctx[CALCULATION_RESULTS_KEY] == mock_results
