"""Workflow fixtures for testing pile calculation workflows.

This module provides layered fixtures that build on `fresh_db` to provide
progressively more populated database state for workflow testing.

Fixture chain:
    fresh_db -> workflow_db -> workflow_db_with_session -> paalfundering_full_db
"""

from pathlib import Path

import pytest

# Import fresh_db from sibling directory to ensure fixture chain works
from ari_tests.db.conftest import fresh_db  # noqa: F401

from ari.db.db import (
    initialize_db,
    color_to_db,
    create_new_calculation_table,
    write_calc_data,
    db,
)
from ari.db.database import Table
from ari.workflows.calculate.pile import (
    PILE_TYPE_KEY,
    PILE_DIMENSIONS_KEY,
    PILE_LOCATION_KEY,
    PILE_TIP_LEVEL_KEY,
    WORK_ORDER_KEY,
    PHREATIC_LEVEL_KEY,
    STRUCTURE_RIGIDITY_KEY,
    FUTURE_GROUND_LEVEL_KEY,
    SLS_LOAD_KEY,
    ULS_LOAD_KEY,
    SKIN_FRICTION_RANGES_KEY,
    SOIL_INVESTIGATION_TOPVIEW_IMAGE,
    PileType,
)
from ceniac.parameters.model import PileFoundationParams, Color
from ceniac.calculate.pile import SkinFrictionRanges
from geolib.models.dfoundations.profiles import TimeOrderType
from baml_client.types import Berekening

from ari_tests.test_utils import DB_DUMP_FOLDER, cpt, sp


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workflow_db(fresh_db) -> "Database":
    """Yields Database object with CPT, soil profile, params, and colors populated.

    This fixture builds on `fresh_db` and adds:
    - CPT table populated with `cpt` from test_utils
    - soilprofiles table populated with `sp` from test_utils (with based_on set)
    - params table with klei, veen, and zand PileFoundationParams
    - colors table with corresponding colors

    Note: profilemap was removed in Step 18. CPT-to-profile provenance is now
    tracked via the SoilProfile.based_on field.

    Yields:
        Database: The database singleton with populated data

    Teardown:
        Uses fresh_db's teardown (clears tables, removes .ceniac folder)
    """
    # Add CPT
    db.add(Table.PROJECT, "cpts", cpt)

    # Add soil profile
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)

    # Add soil parameters for klei, veen, zand (matching sp fixture)
    klei = PileFoundationParams(
        soil="klei",
        K0=0.5,
        gamma_nat=15,
        gamma_sat=15,
        compressible=True,
        friction_angle=25,
        undrained_shear_strength=20,
    )
    veen = PileFoundationParams(
        soil="veen",
        K0=0.6,
        gamma_nat=11,
        gamma_sat=11,
        compressible=True,
        friction_angle=23,
        undrained_shear_strength=15,
    )
    zand = PileFoundationParams(
        soil="zand",
        K0=0.4,
        gamma_nat=18,
        gamma_sat=18,
        compressible=False,
        friction_angle=35,
        undrained_shear_strength=200,
    )
    db.add(Table.PROJECT, "params", klei)
    db.add(Table.PROJECT, "params", veen)
    db.add(Table.PROJECT, "params", zand)

    # Add soil colors
    db.add(Table.PROJECT, "colors", Color(soil="klei", color="#00614d"))
    db.add(Table.PROJECT, "colors", Color(soil="veen", color="#8B4513"))
    db.add(Table.PROJECT, "colors", Color(soil="zand", color="#ffdb58"))

    yield db


@pytest.fixture
def workflow_db_with_session(workflow_db) -> "Database":
    """Yields Database object with calculation session created.

    This fixture builds on `workflow_db` and adds:
    - A calculation session with type Berekening.PAALFUNDERING

    The session is ready for `write_calc_data` calls.

    Yields:
        Database: The database singleton with active session

    Teardown:
        Uses workflow_db's teardown (via fresh_db's teardown)
    """
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)

    yield db


@pytest.fixture
def paalfundering_full_db(workflow_db_with_session) -> "Database":
    """Yields Database object with all paalfundering calc inputs populated.

    This fixture builds on `workflow_db_with_session` and adds:
    - Pile type: PileType.SCHROEFPAAL
    - Dimensions: 650
    - Location: (100000.0, 450000.0)
    - SLS load: 500.0
    - ULS load: 700.0
    - Pile tip level: -15.0
    - Work order: TimeOrderType.CPT_EXCAVATION_INSTALL
    - Phreatic level: -1.0
    - Structure rigidity: True
    - Future ground level: 0.0
    - SkinFrictionRanges: {}
    - Topview image: None

    Yields:
        Database: The database singleton with all calc data populated

    Teardown:
        Uses workflow_db_with_session's teardown (via fresh_db's teardown)
    """
    # Pile type
    write_calc_data(key=PILE_TYPE_KEY, data=PileType.SCHROEFPAAL)

    # Dimensions
    write_calc_data(key=PILE_DIMENSIONS_KEY, data=650)

    # Location
    write_calc_data(key=PILE_LOCATION_KEY, data=(100000.0, 450000.0))

    # SLS and ULS loads
    write_calc_data(key=SLS_LOAD_KEY, data=500.0)
    write_calc_data(key=ULS_LOAD_KEY, data=700.0)

    # Pile tip level
    write_calc_data(key=PILE_TIP_LEVEL_KEY, data=-15.0)

    # Work order
    write_calc_data(key=WORK_ORDER_KEY, data=TimeOrderType.CPT_EXCAVATION_INSTALL)

    # Phreatic level
    write_calc_data(key=PHREATIC_LEVEL_KEY, data=-1.0)

    # Structure rigidity
    write_calc_data(key=STRUCTURE_RIGIDITY_KEY, data=True)

    # Future ground level
    write_calc_data(key=FUTURE_GROUND_LEVEL_KEY, data=0.0)

    # Skin friction ranges (empty)
    write_calc_data(key=SKIN_FRICTION_RANGES_KEY, data={})

    # Topview image (None)
    write_calc_data(key=SOIL_INVESTIGATION_TOPVIEW_IMAGE, data=None)

    yield db


@pytest.fixture
def session_db(fresh_db) -> "Database":
    """Yields Database object with calculation session created.

    This fixture builds on `fresh_db` and adds:
    - A calculation session with type Berekening.PAALFUNDERING

    Unlike `workflow_db_with_session`, this fixture does NOT pre-populate
    CPT, soil profile, or params data. Use this for E2E tests that need
    to go through the full workflow including soil interpretation.

    Yields:
        Database: The database singleton with active session

    Teardown:
        Uses fresh_db's teardown (clears tables, removes .ceniac folder)
    """
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)

    yield db


@pytest.fixture
def db_path() -> Path:
    """Returns the path to the .ceniac folder for the test database.

    This is useful for tests that need to verify folder existence/removal
    during teardown.
    """
    return DB_DUMP_FOLDER / ".ceniac"
