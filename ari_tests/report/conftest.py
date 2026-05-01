"""Pytest configuration for report tests.

This module provides fixtures for testing the report generation functionality.
It sets up a test database with all required data for the query_foundation_report
and create_report functions.
"""

from shutil import rmtree
from typing import Any

import pytest
from geolib.models.dfoundations.profiles import TimeOrderType
from geolib.models.dfoundations import piles

from ceniac.calculate.pile import PileResult, PileResults, SkinFrictionRanges
from ceniac.parameters.model import PileFoundationParams, Color

from baml_client.types import Berekening

from ari.db.database import Database
from ari.db.database import Table
from ari_tests.test_utils import DB_DUMP_FOLDER, cpt, sp
from ari.queries.soil_interpretation import CPT_NAME_KEY
from ari.queries.pile_calc import (
    PILE_TYPE_KEY,
    PILE_TIP_LEVEL_KEY,
    WORK_ORDER_KEY,
    PHREATIC_LEVEL_KEY,
    STRUCTURE_RIGIDITY_KEY,
    FUTURE_GROUND_LEVEL_KEY,
    CALCULATION_RESULTS_KEY,
    SLS_LOAD_KEY,
    ULS_LOAD_KEY,
    SKIN_FRICTION_RANGES_KEY,
    PileType,
)


@pytest.fixture(scope="function")
def setup_report_test_db(fresh_db: Database):
    """Set up a test database with all data required for report generation tests.

    This fixture:
    1. Initializes the database
    2. Adds CPT data (from test_utils.py)
    3. Adds soil profile linked to the CPT
    4. Adds soil parameters for sand and clay
    5. Adds soil colors
    6. Creates a calculation session with all required keys
    7. Adds mock calculation results

    Yields:
        None: The database is set up and torn down automatically
    """
    # Reset global table/figure counters so each test starts at Tabel 1, Figuur 1
    from ari.report import pile as pile_module
    
    pile_module.table_number = 1
    pile_module.figure_number = 1
    
    db = fresh_db

    # 1. Add CPT to database
    db.add(Table.PROJECT, "cpts", cpt)

    # 2. Add soil profile linked to the CPT
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)

    # 3. Add soil parameters
    sand_params = PileFoundationParams(
        soil="sand",
        K0=0.3,
        gamma_nat=18,
        gamma_sat=20,
        friction_angle=34,
        compressible=False,
        undrained_shear_strength=0,  # Not relevant for sand
    )
    clay_params = PileFoundationParams(
        soil="clay",
        K0=0.6,
        gamma_nat=15,
        gamma_sat=15,
        friction_angle=25,
        compressible=True,
        undrained_shear_strength=30,
    )
    db.add(Table.PROJECT, "params", sand_params)
    db.add(Table.PROJECT, "params", clay_params)

    # 4. Add soil colors
    db.add(Table.PROJECT, "colors", Color(soil="sand", color="#F4D03F"))
    db.add(Table.PROJECT, "colors", Color(soil="clay", color="#808B96"))

    # 5. Create calculation session

    db.create_new_calculation(Berekening.PAALFUNDERING)

    # 6. Write all required calculation data
    # CPT name
    db.add(Table.CALC, CPT_NAME_KEY, cpt.id_)

    # Pile type
    db.add(Table.CALC, PILE_TYPE_KEY, PileType.BUISSCHROEFPAAL) 

    # Pile tip level
    db.add(Table.CALC, key=PILE_TIP_LEVEL_KEY, value=-10.5)

    # Work order (CPT execution order)
    db.add(Table.CALC,  key=WORK_ORDER_KEY, value=TimeOrderType.CPT_EXCAVATION_INSTALL)

    # Phreatic level
    db.add(Table.CALC, key=PHREATIC_LEVEL_KEY, value=-1.0)

    # Structure rigidity
    db.add(Table.CALC, key=STRUCTURE_RIGIDITY_KEY, value=True)

    # Future ground level
    db.add(Table.CALC, key=FUTURE_GROUND_LEVEL_KEY, value=0.0)

    # SLS and ULS loads
    db.add(Table.CALC, key=SLS_LOAD_KEY, value=500.0)
    db.add(Table.CALC, key=ULS_LOAD_KEY, value=750.0)

    # Skin friction ranges
    skin_friction_ranges = {
        cpt.id_: SkinFrictionRanges(
            top_positive_skin_friction=-3.0,  # Top of positive skin friction (bottom of clay layer)
            bottom_negative_skin_friction=-3.0,  # Bottom of negative skin friction (same as top of positive)
        )
    }
    db.add(Table.CALC, key=SKIN_FRICTION_RANGES_KEY, value=skin_friction_ranges)

    # 7. Add mock calculation results

    pile = piles.BearingRoundPile(
        diameter=0.3,
        pile_name="pile1",
        pile_type=piles.PileType.USER_DEFINED_LOW_VIBRATING,  # TODO: check if correct! only USER DEFINED allowed for this pile
        pile_class_factor_tip=0.3,  # alpha_p -> TODO: check if correct
        pile_class_factor_shaft_sand_gravel=0.01,  # alpha_s -> TODO: check if correct
        pile_class_factor_shaft_clay_silt_peat=0.03,  # alpha_s -> TODO: check if correct
        preset_pile_class_factor_shaft_clay_silt_peat=piles.BasePileTypeForClaySiltPeat.STANDARD,  # TODO: check what it is and if correct!
        overrule_pile_tip_shape_factor=False,
        characteristic_adhesion=10,  # TODO: check what does and if correct!
        load_settlement_curve=piles.LoadSettlementCurve.THREE,
        elasticity_modulus=20e3,  # MPA? TODO: check if correct order of magnitude in terms of units
        use_manual_reduction_for_qc=False,  # TODO: assess if correct, for auger piles, qc3 -> 2 MPa
        user_defined_pile_type_as_prefab=False,
        overrule_pile_tip_cross_section_factors=False,
    )
    calculation_results = PileResults(
        pile=pile,
        results=[
            PileResult(
                cpt=cpt,
                tip_level=-10.5,
                bc_shaft_rep=500.0,
                bc_tip_rep=800.0,
                nsf_rep=100.0,
                design_bearing_capacity=864.7,
            ),
            PileResult(
                cpt=cpt,
                tip_level=-12.0,
                bc_shaft_rep=600.0,
                bc_tip_rep=900.0,
                nsf_rep=120.0,
                design_bearing_capacity=994.2,
            ),
        ],
    )
    db.add(Table.CALC, key=CALCULATION_RESULTS_KEY, value=calculation_results)

    # Yield control to the test
    yield

    # Teardown: clean up the database
    _cleanup_report_test_db(db)


def get_report_test_data() -> dict[str, Any]:
    """Helper function to get all test data used in the report fixture.

    Returns:
        Dictionary containing all test data for report generation
    """
    return {
        "cpt": cpt,
        "soil_profile": sp,
        "pile_type": PileType.BUISSCHROEFPAAL,
        "pile_tip_level": -10.5,
        "work_order": TimeOrderType.CPT_EXCAVATION_INSTALL,
        "phreatic_level": -1.0,
        "structure_rigidity": True,
        "future_ground_level": 0.0,
        "sls_load": 500.0,
        "uls_load": 750.0,
        "skin_friction_ranges": {
            cpt.id_: SkinFrictionRanges(
                top_positive_skin_friction=-3.0,
                bottom_negative_skin_friction=-3.0,
            )
        },
        "calculation_results": [
            PileResult(
                cpt=cpt,
                tip_level=-10.5,
                bc_shaft_rep=500.0,
                bc_tip_rep=800.0,
                nsf_rep=100.0,
                design_bearing_capacity=864.7,
            ),
            PileResult(
                cpt=cpt,
                tip_level=-12.0,
                bc_shaft_rep=600.0,
                bc_tip_rep=900.0,
                nsf_rep=120.0,
                design_bearing_capacity=994.2,
            ),
        ],
    }


def _cleanup_report_test_db(db: Database):
    """Clean up the test database after each test.

    This function:
    1. Clears db.project sub-tables
    2. Clears calc table
    3. Removes the database folder if it exists
    """
    # Clear db.project sub-tables
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.project.params.clear()
    db.project.colors.clear()

    # Clear calc table
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Remove the database folder
    db_folder = DB_DUMP_FOLDER / ".ceniac"
    if db_folder.exists():
        rmtree(db_folder)
