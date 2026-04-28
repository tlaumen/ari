"""DB fixtures for testing."""

from shutil import rmtree
from pathlib import Path

import pytest

from ari.db.db import initialize_db, db  # noqa: F401
from ari.db.database import Table
from ari_tests.test_utils import DB_DUMP_FOLDER


@pytest.fixture
def fresh_db(request: pytest.FixtureRequest) -> "Database":
    """Clean, initialized database for a single test.

    Setup:
        - Remove existing .ceniac folder if present
        - Clear module-level fixture singletons (sp, cpt) that may carry state
        - Initialize fresh DB with empty tables

    Teardown:
        - Clear all db.project.* tables
        - Reset module-level fixture singletons
        - Reset calc sessions
        - Remove .ceniac folder

    Usage:
        def test_add_cpt(fresh_db):
            db.add(Table.PROJECT, "cpts", my_cpt)
            assert my_cpt.id_ in fresh_db.project.cpts
    """
    db_path = DB_DUMP_FOLDER / ".ceniac"

    # Setup: Remove stale artifacts
    if db_path.exists():
        rmtree(db_path)

    # Setup: Reset module-level fixture singletons that may carry state
    # from previous tests (in particular the `based_on` field which is
    # mutated in-place during the soil_profile_to_db pattern)
    from ari_tests.test_utils import sp

    sp.based_on = None

    # Setup: Initialize fresh DB
    initialize_db(DB_DUMP_FOLDER)

    yield db

    # Teardown: Reset db.project (db.project is the authoritative store)
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.project.params.clear()
    db.project.colors.clear()
    # Note: profilemap was removed in Step 18

    # Teardown: Reset calc table
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Teardown: Remove artifacts
    if db_path.exists():
        rmtree(db_path)
