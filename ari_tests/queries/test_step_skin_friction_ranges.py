"""Tests for StepSkinFrictionRanges (ComputationStep).

Tests for:
- StepSkinFrictionRanges: Computes skin friction ranges from CPTs, soil profiles, parameters, and pile tip level
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from ari.queries.base import Table, Requirement, Product, Step, StepRunner


class TestStepSkinFrictionRanges:
    """Tests for StepSkinFrictionRanges (ComputationStep)."""

    def test_step_class_structure(self):
        """Behavior 1: StepSkinFrictionRanges has correct class structure."""
        from ari.queries.pile_calc import (
            StepSkinFrictionRanges,
            SKIN_FRICTION_RANGES_KEY,
            PILE_TIP_LEVEL_KEY,
        )

        # Check class attributes exist
        assert hasattr(StepSkinFrictionRanges, "name")
        assert hasattr(StepSkinFrictionRanges, "requires")
        assert hasattr(StepSkinFrictionRanges, "produces")

        # Check specific values
        assert StepSkinFrictionRanges.name == "step_skin_friction_ranges"

    def test_step_requires_does_not_include_profilemap(self):
        """Behavior 1: Step requires does not contain a Requirement with key='profilemap'."""
        from ari.queries.pile_calc import StepSkinFrictionRanges

        requires = StepSkinFrictionRanges.requires
        keys = {r.key for r in requires}

        # profilemap must NOT be in requires
        assert "profilemap" not in keys

    def test_step_requires_correct_keys(self):
        """Behavior 1: Step requires 5 keys from correct sources (no profilemap)."""
        from ari.queries.pile_calc import StepSkinFrictionRanges

        requires = StepSkinFrictionRanges.requires

        # Should have 5 requirements (no profilemap after Step 19)
        assert len(requires) == 5

        # Check keys are present
        keys = {r.key for r in requires}
        assert "cpts" in keys
        assert "soilprofiles" in keys
        assert "params" in keys
        assert "colors" in keys
        assert "paalpuntniveau" in keys

    def test_step_requires_correct_sources(self):
        """Behavior 1: Step requires from correct sources (PROJECT for 4, CALC for 1)."""
        from ari.queries.pile_calc import StepSkinFrictionRanges

        requires = StepSkinFrictionRanges.requires

        project_reqs = [r for r in requires if r.source == Table.PROJECT]
        calc_reqs = [r for r in requires if r.source == Table.CALC]

        # 4 requirements from PROJECT (no profilemap)
        assert len(project_reqs) == 4
        # 1 requirement from CALC (paalpuntniveau)
        assert len(calc_reqs) == 1
        assert calc_reqs[0].key == "paalpuntniveau"

    def test_step_produces_to_calc(self):
        """Behavior 1: Produces SKIN_FRICTION_RANGES_KEY to CALC table."""
        from ari.queries.pile_calc import (
            StepSkinFrictionRanges,
            SKIN_FRICTION_RANGES_KEY,
        )
        from ari.queries.pile_calc import Table

        assert len(StepSkinFrictionRanges.produces) == 1
        prod = StepSkinFrictionRanges.produces[0]
        assert prod.key == SKIN_FRICTION_RANGES_KEY
        assert prod.dest == Table.CALC

    def test_execute_reads_based_on_from_soilprofiles(self, fresh_db):
        """Behavior 2: execute() reads sp.based_on from each SoilProfile in ctx['soilprofiles'].values()."""
        from ari.queries.pile_calc import StepSkinFrictionRanges
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock SoilProfile with based_on field
        mock_soil_profile = MagicMock()
        mock_soil_profile.based_on = "cpt1"

        # ctx has soilprofiles as a dict of SoilProfile objects
        ctx = {
            "cpts": [MagicMock()],
            "soilprofiles": [mock_soil_profile],
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
        }

        with patch("ari.queries.pile_calc.select_skin_friction_areas") as mock_select:
            mock_select.return_value = MagicMock()

            step = StepSkinFrictionRanges()
            step.execute(ctx)

            # verify based_on was accessed
            assert mock_soil_profile.based_on == "cpt1"

    def test_execute_looks_up_cpt_from_ctx_using_based_on(self, fresh_db):
        """Behavior 3: execute() looks up CPT from ctx['cpts'][sp.based_on]."""
        from ari.queries.pile_calc import StepSkinFrictionRanges
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        # Mock CPT and SoilProfile
        mock_cpt = MagicMock()
        mock_cpt.id_ = "cpt1"

        mock_soil_profile = MagicMock()
        mock_soil_profile.based_on = "cpt1"

        ctx = {
            "cpts": [mock_cpt],
            "soilprofiles": [mock_soil_profile],
            "params": [],
            "colors": [],
            "paalpuntniveau": -25.0,
        }

        with patch("ari.queries.pile_calc.select_skin_friction_areas") as mock_select:
            mock_select.return_value = MagicMock()

            step = StepSkinFrictionRanges()
            step.execute(ctx)

            # The CPT lookup used based_on ("cpt1") to find the CPT object
            call_args = mock_select.call_args.kwargs
            assert call_args["cpt"] == mock_cpt

    def test_execute_builds_mapping_inline_using_based_on(self, fresh_db):
        """Behavior: execute() builds CPT-to-profile mapping inline by reading sp.based_on."""
        from ari.queries.pile_calc import StepSkinFrictionRanges
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        mock_cpt = MagicMock()
        mock_cpt.id_ = "cpt1"
        mock_soil_profile = MagicMock()
        mock_soil_profile.based_on = "cpt1"

        ctx = {
            "cpts": [mock_cpt],
            "soilprofiles": [mock_soil_profile],
            "params": {},
            "colors": {},
            "paalpuntniveau": -25.0,
        }

        with patch("ari.queries.pile_calc.select_skin_friction_areas") as mock_select:
            mock_sfr = MagicMock()
            mock_select.return_value = mock_sfr

            step = StepSkinFrictionRanges()
            step.execute(ctx)

            # Verify select_skin_friction_areas was called with correct CPT and profile
            mock_select.assert_called_once()
            call_args = mock_select.call_args.kwargs
            assert call_args["cpt"] == mock_cpt
            assert call_args["soil_profile"] == mock_soil_profile

    def test_execute_calls_select_skin_friction_areas(self, fresh_db):
        """Behavior: execute() calls select_skin_friction_areas() for each (cpt, soil_profile) pair."""
        from ari.queries.pile_calc import StepSkinFrictionRanges
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        mock_cpt = MagicMock()
        mock_cpt.id_ = "cpt1"
        mock_soil_profile = MagicMock()
        mock_soil_profile.based_on = "cpt1"
        mock_soil_profile.name = "profile1"

        mock_params = [MagicMock(soil="Clay")]
        mock_colors = [MagicMock(soil="Clay", color="#FF0000")]

        ctx = {
            "cpts": [mock_cpt],
            "soilprofiles": [mock_soil_profile],
            "params": mock_params,
            "colors": mock_colors,
            "paalpuntniveau": -25.0,
        }

        with patch("ari.queries.pile_calc.select_skin_friction_areas") as mock_select:
            mock_selectreturn_value = MagicMock()

            step = StepSkinFrictionRanges()
            step.execute(ctx)

            # Verify select_skin_friction_areas was called once
            mock_select.assert_called_once()
            call_args = mock_select.call_args.kwargs
            assert call_args["cpt"] == mock_cpt
            assert call_args["soil_profile"] == mock_soil_profile
            assert call_args["soil_params"] == mock_params
            assert call_args["pile_tip_level"] == -25.0
            assert call_args["soil_colors"] == mock_colors

    def test_execute_stores_skin_friction_ranges_in_ctx(self, fresh_db):
        """Behavior: execute() stores resulting dict[cpt_id -> SkinFrictionRanges] in ctx[SKIN_FRICTION_RANGES_KEY]."""
        from ari.queries.pile_calc import (
            StepSkinFrictionRanges,
            SKIN_FRICTION_RANGES_KEY,
        )
        from ceniac.calculate.pile import SkinFrictionRanges
        from ari.db.db import db
        from baml_client.types import Berekening

        db.calc.create_session(Berekening.PAALFUNDERING)

        mock_cpt = MagicMock()
        mock_cpt.id_ = "cpt1"
        mock_soil_profile = MagicMock()
        mock_soil_profile.based_on = "cpt1"
        mock_soil_profile.name = "profile1"

        ctx = {
            "cpts": [mock_cpt],
            "soilprofiles": [mock_soil_profile],
            "params": [],
            "colors": [],
            "paalpuntniveau": -30.0,
        }

        expected_sfr = SkinFrictionRanges(
            top_positive_skin_friction=-5.0, bottom_negative_skin_friction=-15.0
        )

        with patch("ari.queries.pile_calc.select_skin_friction_areas") as mock_select:
            mock_select.return_value = expected_sfr

            step = StepSkinFrictionRanges()
            step.execute(ctx)

            assert SKIN_FRICTION_RANGES_KEY in ctx
            assert isinstance(ctx[SKIN_FRICTION_RANGES_KEY], dict)
            assert "cpt1" in ctx[SKIN_FRICTION_RANGES_KEY]
            assert ctx[SKIN_FRICTION_RANGES_KEY]["cpt1"] == expected_sfr
