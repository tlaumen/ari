"""
Shared fixtures and configuration for tests.

This module provides pytest fixtures for creating test data and mock objects
used across the test suite, including MapPointSelector and scenario runner tests.
"""

import pytest
from pathlib import Path


# =============================================================================
# Scenario Runner Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def tests_dir(project_root):
    """Return the tests directory."""
    return project_root / "tests"


@pytest.fixture(scope="session")
def scenario_dir(tests_dir):
    """Return the scenarios directory."""
    return tests_dir / "scenarios"


@pytest.fixture(scope="session")
def e2e_workflows_dir(tests_dir):
    """Return the end-to-end workflows directory."""
    return tests_dir / "end-to-end-workflows"


@pytest.fixture(scope="function")
def clean_scenario_context():
    """
    Ensure ScenarioContext is reset before and after each test.

    This prevents state leakage between tests.
    """
    try:
        from ari_tests.end_to_end_workflows.scenario_runner import ScenarioContext

        ScenarioContext.reset()
        yield
        ScenarioContext.reset()
    except ImportError:
        # Module not yet fully implemented, skip fixture
        yield


@pytest.fixture(scope="session")
def cpt_file_path(tests_dir):
    """Return the path to the CPT002.xml test file."""
    return tests_dir / "soil_investigation" / "CPT002.xml"


# =============================================================================
# MapPointSelector Fixtures (existing)
# =============================================================================


@pytest.fixture
def mock_cpt():
    """
    Create a mock CPT object for testing.

    Returns an object with x, y (RD coordinates) and id_ attributes.
    Uses Amsterdam Dam Square coordinates by default.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture mock_cpt not implemented")


@pytest.fixture
def mock_cpt_list():
    """
    Create a list of mock CPT objects for testing.

    Returns a list of 3 CPT objects with varied coordinates suitable
    for testing bounds calculation and multi-marker display.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture mock_cpt_list not implemented")


@pytest.fixture
def mock_tk_root():
    """
    Create a mock tkinter.Tk root window for testing.

    Returns a mock object that simulates tk.Tk behavior without
    creating an actual GUI window.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture mock_tk_root not implemented")


@pytest.fixture
def sample_html_content():
    """
    Provide sample HTML content for webview testing.

    Returns a minimal valid HTML string that can be loaded into
    the webview wrapper for testing purposes.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture sample_html_content not implemented")


@pytest.fixture
def reference_rd_coordinates():
    """
    Provide reference RD coordinates for testing conversions.

    Returns a tuple (x, y) of known RD coordinates (Amsterdam Dam Square)
    for verifying coordinate conversion accuracy.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture reference_rd_coordinates not implemented")


@pytest.fixture
def reference_wgs84_coordinates():
    """
    Provide reference WGS84 coordinates for testing conversions.

    Returns a tuple (lat, lon) of known WGS84 coordinates (Amsterdam Dam Square)
    for verifying coordinate conversion accuracy.

    Raises:
        NotImplementedError: Fixture not yet implemented.
    """
    raise NotImplementedError("Fixture reference_wgs84_coordinates not implemented")


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Add custom markers for scenario runner tests."""
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end test that may require human interaction (MapPointSelector)",
    )
    config.addinivalue_line(
        "markers",
        "manual: test step that requires manual (human) intervention",
    )
