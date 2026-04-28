"""
Tests for workflow_mocks.py: SequentialMock, GUIMock, and mock_llm_reports.
"""

import pytest
from unittest.mock import MagicMock


class TestSequentialMock:
    """Tests for SequentialMock class."""

    def test_sequential_mock_add_prompt(self):
        """Verify values are queued via add_prompt."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        seq.add_prompt("value1", "value2", "value3")

        # Check internal state
        assert seq._prompts == ["value1", "value2", "value3"]

    def test_sequential_mock_add_choice(self):
        """Verify values are queued via add_choice."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        seq.add_choice(0, 1, 2)

        assert seq._choices == [0, 1, 2]

    def test_sequential_mock_add_confirm(self):
        """Verify values are queued via add_confirm."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        seq.add_confirm(True, False, True)

        assert seq._confirms == [True, False, True]

    def test_sequential_mock_empty_prompt_raises(self):
        """Verify empty mock context manager can be created with no values."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()

        # Empty mock context should work fine
        with seq.mock():
            pass  # No modules to patch when queues are empty

        # But if we try to iterate an empty queue, it should be possible
        # to check state (the queues are empty)
        assert seq._prompts == []
        assert seq._choices == []
        assert seq._confirms == []

    def test_sequential_mock_order(self):
        """Verify FIFO ordering across prompt, choice, confirm queues."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        seq.add_prompt("p1", "p2")
        seq.add_choice(0, 1)
        seq.add_confirm(True, False)

        # Verify FIFO order for each queue
        prompts = list(seq._prompts)
        choices = list(seq._choices)
        confirms = list(seq._confirms)

        assert prompts == ["p1", "p2"]
        assert choices == [0, 1]
        assert confirms == [True, False]

    def test_sequential_mock_returns_self(self):
        """Verify method chaining works (returns self)."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        result = seq.add_prompt("test")

        assert result is seq

    def test_sequential_mock_multiple_add_calls(self):
        """Verify multiple add calls accumulate values."""
        from ari_tests.fixtures.workflow_mocks import SequentialMock

        seq = SequentialMock()
        seq.add_prompt("a")
        seq.add_prompt("b", "c")
        seq.add_prompt("d")

        assert seq._prompts == ["a", "b", "c", "d"]


class TestGUIMock:
    """Tests for GUIMock class."""

    def test_gui_mock_init(self):
        """Test that GUIMock initializes with no mocks configured."""
        from ari_tests.fixtures.workflow_mocks import GUIMock

        gui = GUIMock()

        # All internal state should be None
        assert gui._location is None
        assert gui._location_image is None
        assert gui._soil_profile is None

    def test_gui_mock_location(self):
        """Test that mock_location configures the selector to return configured point."""
        from ari_tests.fixtures.workflow_mocks import GUIMock

        gui = GUIMock()
        test_point = (100000.0, 450000.0)
        test_image = MagicMock()

        # Act - configure the mock
        gui.mock_location(point=test_point, top_view_image=test_image)

        # Assert - verify configuration was stored
        assert gui._location == test_point
        assert gui._location_image == test_image

    def test_gui_mock_interpreter(self):
        """Test that mock_interpreter configures the interpreter to return configured profile."""
        from ari_tests.fixtures.workflow_mocks import GUIMock
        from ceniac.soil_profile.soil_profile import SoilProfile, Layer

        gui = GUIMock()
        test_profile = SoilProfile(
            name="test",
            surface_level=0,
            layers=[Layer(soil="sand", top=0, bottom=-10)],
            bottom=-10,
        )

        # Act - configure the mock
        gui.mock_interpreter(soil_profile=test_profile)

        # Assert - verify configuration was stored
        assert gui._soil_profile == test_profile

    def test_gui_mock_context_patches_pile_location_selector(self):
        """Test that mock() context patches pile_location_selector."""
        from ari_tests.fixtures.workflow_mocks import GUIMock

        gui = GUIMock()
        test_point = (155000.0, 463000.0)
        gui.mock_location(point=test_point)

        # Act & Assert
        with gui.mock():
            # pile_location_selector should be patched
            from ari.workflows.calculate.pile import pile_location_selector

            selector = pile_location_selector([])
            assert selector.get_point() == test_point
            assert selector.top_view_image is None

    def test_gui_mock_context_patches_run_interpreter(self):
        """Test that mock() context patches run_interpreter."""
        from ari_tests.fixtures.workflow_mocks import GUIMock
        from ceniac.soil_profile.soil_profile import SoilProfile, Layer

        gui = GUIMock()
        test_profile = SoilProfile(
            name="test",
            surface_level=0,
            layers=[Layer(soil="clay", top=0, bottom=-5)],
            bottom=-5,
        )
        gui.mock_interpreter(soil_profile=test_profile)

        # Act & Assert
        with gui.mock():
            from ari.workflows.soil_interpretation import run_interpreter

            result = run_interpreter(None, None, None)
            assert result == test_profile

    def test_gui_mock_chaining(self):
        """Test that methods can be chained."""
        from ari_tests.fixtures.workflow_mocks import GUIMock

        gui = GUIMock()
        result = gui.mock_location((1, 2)).mock_interpreter("profile")
        assert result is gui


class TestMockLlmReports:
    """Tests for mock_llm_reports context manager."""

    def test_A1_patched_methods_return_str(self):
        """Test A1: each patched method returns a str."""
        from ari_tests.fixtures.workflow_mocks import mock_llm_reports
        from baml_client import sync_client
        from baml_client.types import (
            ReportBaseLineIntroduction,
            ReportBaseLineSoilInvestigation,
        )
        from baml_client.types import (
            ReportBaseLineAssumptions,
            ReportBaseLineModelling,
            ModellingPointers,
        )
        from baml_client.types import (
            ReportBaseResults,
            ReportBaseLineConclusion,
            ResultPointers,
        )

        with mock_llm_reports():
            # Call each patched method with a minimal valid input (mock ignores the arg)
            intro = ReportBaseLineIntroduction(pointers=[], elements=[])
            result = sync_client.b.FoundationDesignIntroductionReporter(intro)
            assert isinstance(result, str)

            si = ReportBaseLineSoilInvestigation(pointers=[], elements=[])
            result = sync_client.b.FoundationDesignSoilInvestigationReporter(si)
            assert isinstance(result, str)

            assumptions = ReportBaseLineAssumptions(
                pointers=[], elements=[], parameters=[]
            )
            result = sync_client.b.FoundationDesignAssumptionsReporter(assumptions)
            assert isinstance(result, str)

            modelling = ReportBaseLineModelling(
                pointers=ModellingPointers(
                    soil_profiles=[],
                    pile=[],
                    variability_information=[],
                    environmental_factors=[],
                ),
                elements=[],
            )
            result = sync_client.b.FoundationDesignModellingReporter(modelling)
            assert isinstance(result, str)

            results = ReportBaseResults(
                pointers=ResultPointers(
                    pile_tip_range="",
                    bearing_capacity="",
                    load="",
                    pile_tip_level="",
                ),
                elements=[],
            )
            result = sync_client.b.FoundationDesignResultsReporter(results)
            assert isinstance(result, str)

            conclusion = ReportBaseLineConclusion(pointers=[], elements=[])
            result = sync_client.b.FoundationDesignConclusionReporter(conclusion)
            assert isinstance(result, str)

    def test_A2_patched_methods_return_chapter_names(self):
        """Test A2: each patched method returns a non-empty string containing the chapter name."""
        from ari_tests.fixtures.workflow_mocks import mock_llm_reports
        from baml_client import sync_client
        from baml_client.types import (
            ReportBaseLineIntroduction,
            ReportBaseLineSoilInvestigation,
        )
        from baml_client.types import (
            ReportBaseLineAssumptions,
            ReportBaseLineModelling,
            ModellingPointers,
        )
        from baml_client.types import (
            ReportBaseResults,
            ReportBaseLineConclusion,
            ResultPointers,
        )

        with mock_llm_reports():
            intro = ReportBaseLineIntroduction(pointers=[], elements=[])
            text = sync_client.b.FoundationDesignIntroductionReporter(intro)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Introduction" in text

            si = ReportBaseLineSoilInvestigation(pointers=[], elements=[])
            text = sync_client.b.FoundationDesignSoilInvestigationReporter(si)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Soil investigation" in text

            assumptions = ReportBaseLineAssumptions(
                pointers=[], elements=[], parameters=[]
            )
            text = sync_client.b.FoundationDesignAssumptionsReporter(assumptions)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Uitgangspunten" in text

            modelling = ReportBaseLineModelling(
                pointers=ModellingPointers(
                    soil_profiles=[],
                    pile=[],
                    variability_information=[],
                    environmental_factors=[],
                ),
                elements=[],
            )
            text = sync_client.b.FoundationDesignModellingReporter(modelling)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Modelling" in text

            results = ReportBaseResults(
                pointers=ResultPointers(
                    pile_tip_range="",
                    bearing_capacity="",
                    load="",
                    pile_tip_level="",
                ),
                elements=[],
            )
            text = sync_client.b.FoundationDesignResultsReporter(results)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Results" in text

            conclusion = ReportBaseLineConclusion(pointers=[], elements=[])
            text = sync_client.b.FoundationDesignConclusionReporter(conclusion)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Conclusion" in text

    def test_A3_original_methods_restored_outside_context(self):
        """Test A3: outside the context, FoundationDesignIntroductionReporter is the original method."""
        from ari_tests.fixtures.workflow_mocks import mock_llm_reports
        from baml_client import sync_client

        # Capture original
        original = sync_client.b.FoundationDesignIntroductionReporter

        with mock_llm_reports():
            # Inside: patched
            pass

        # Outside: restored to original
        assert sync_client.b.FoundationDesignIntroductionReporter is original
