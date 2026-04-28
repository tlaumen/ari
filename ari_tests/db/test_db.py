from pathlib import Path

from geolib.models.dseries_parser import is_structure_collection
from shapely.geometry.base import dump_coords
import pytest

from baml_client.types import Berekening
from ceniac.soil_investigation.cpt import load_cpt
from ceniac.soil_profile.soil_profile import Layer
from ceniac.soil_profile.soil_profile import SoilProfile

from ari.db.db import (
    create_new_calculation_table,
    dump_db,
    get_calc_data,
    load_db,
    write_calc_data,
)
from ari.db.db import initialize_db
from ari.db.db import db
from ari.db.database import Table

from ari_tests.test_utils import DB_DUMP_FOLDER, DB_PATH
from ari_tests.test_utils import cpt, sp



@pytest.mark.auto
def test_initial_db(fresh_db):
    """After initialize_db, db.project has all expected sub-tables (empty)."""
    assert "cpts" in db.project.__dict__
    assert "soilprofiles" in db.project.__dict__
    assert "params" in db.project.__dict__
    assert len(db.project.cpts) == 0
    assert len(db.project.soilprofiles) == 0
    assert len(db.project.params) == 0


@pytest.mark.auto
def test_add_cpt_via_db_add(fresh_db):
    """db.add(Table.PROJECT, 'cpts', cpt) stores CPT in db.project.cpts."""
    db.add(Table.PROJECT, "cpts", cpt)
    assert cpt.id_ == db.project.cpts[0].id_


@pytest.mark.auto
def test_dump_db(fresh_db):
    """dump_db() saves db state to disk without errors."""
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    dump_db()


@pytest.mark.auto
def test_load_db(fresh_db):
    from ari.db.db import db

    # Populate DB with test data
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    # Dump to file so load_db() has something to read
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file
    load_db(DB_PATH)

    # Verify data survived round-trip
    assert cpt.id_ == db.project.cpts[0].id_
    assert sp.name == db.project.soilprofiles[0].name
    assert db.project.soilprofiles[0].based_on == cpt.id_


@pytest.mark.auto
def test_create_new_calculation_table(fresh_db):
    """create_new_calculation_table creates a session in db.calc and a session folder."""
    from ari.db.db import db, create_new_calculation_table

    # Populate DB and dump to file so load_db() has data to read
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file
    load_db(DB_PATH)
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)

    # Verify session created in db.calc.sessions
    assert len(db.calc.sessions) == 1
    session_id = list(db.calc.sessions.keys())[0]
    session = db.calc.sessions[session_id]
    assert session.type == Berekening.PAALFUNDERING

    # Verify session folder was created
    session_folder = db._dump_path / str(session_id)
    assert session_folder.exists()

    dump_db()  # dump db so subsequent tests can use it


@pytest.mark.auto
def test_write_calc_data(fresh_db):
    # Populate DB and create session (required for write_calc_data)
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file and write calc data
    load_db(DB_PATH)
    write_calc_data(key="sum", data=4)


@pytest.mark.auto
def test_write_calc_data_cpt(fresh_db):
    # Populate DB and dump to file so load_db() has data to read
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file and test ValueError on invalid data type
    load_db(DB_PATH)
    with pytest.raises(ValueError):
        _ = write_calc_data(key="cpt", data=cpt)


@pytest.mark.auto
def test_write_calc_data_soil_profile(fresh_db):
    # Populate DB and dump to file so load_db() has data to read
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file and test ValueError on invalid data type
    load_db(DB_PATH)
    with pytest.raises(ValueError):
        _ = write_calc_data(key="soil-profile", data=sp)


@pytest.mark.auto
def test_get_calc_data(fresh_db):
    # Populate DB and create session (required for write_calc_data)
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file and test calc data round-trip
    load_db(DB_PATH)
    S = 4
    write_calc_data(key="sum", data=S)
    s = get_calc_data("sum")
    assert s == S


@pytest.mark.auto
def test_get_calc_data_wrong_key(fresh_db):
    # Populate DB and dump to file so load_db() has data to read
    db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db.add(Table.PROJECT, "soilprofiles", sp)
    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)
    dump_db()

    # Clear in-memory DB to simulate fresh start
    db.project.cpts.clear()
    db.project.soilprofiles.clear()
    db.calc.sessions.clear()
    db.calc._current_session_id = None

    # Load from file and test KeyError on non-existent key
    load_db(DB_PATH)
    with pytest.raises(KeyError):
        _ = get_calc_data("non-existant key")
