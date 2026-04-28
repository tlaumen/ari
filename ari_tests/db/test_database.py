"""Tests for Step 1: ProjectTable with cpts dict + db.add() routing."""

import pickle
from pathlib import Path

import pytest

from ari.db.database import Database, CalcTableEntry, ProjectTable, Table
from ari.db import db as db_module
from ari.db.db import db as app_db
from ari_tests.test_utils import cpt, sp


def test_soil_profile_add_stores_based_on(fresh_db):
    """db.add(Table.PROJECT, 'soilprofiles', sp) stores based_on from sp.based_on field."""
    db_module.db.add(Table.PROJECT, "cpts", cpt)
    sp.based_on = cpt.id_
    db_module.db.add(Table.PROJECT, "soilprofiles", sp)

    # based_on is the canonical tracker (not profilemap after Step 17)
    assert sp in app_db.project.soilprofiles
    assert app_db.project.soilprofiles[0].based_on == cpt.id_


def test_add_cpt_stores_cpt_correctly(fresh_db):
    """db.add(Table.PROJECT, 'cpts', cpt) stores cpt with id_ as key."""
    assert len(app_db.project.cpts) == 0

    db_module.db.add(Table.PROJECT, "cpts", cpt)

    assert cpt in app_db.project.cpts
    assert app_db.project.cpts[0] is cpt


def test_database_dump_roundtrip_empty(tmp_path):
    """dump() then load() restores all sub-tables as empty dicts."""
    from ceniac.soil_investigation.cpt import Cpt

    db = Database(path=tmp_path)
    db.dump()

    # Verify pickle file was written
    dump_file = tmp_path / ".ceniac" / "db.pkl"
    assert dump_file.exists()

    # Load into fresh db instance
    fresh_db = Database(path=tmp_path)
    fresh_db.load(dump_file)

    assert fresh_db.project.cpts == []
    assert fresh_db.project.soilprofiles == []
    assert fresh_db.project.params == []
    assert fresh_db.project.colors == []
    assert fresh_db.calc.sessions == {}
    assert fresh_db.calc._current_session_id is None


def test_database_dump_roundtrip_with_data(tmp_path):
    """dump() preserves CPT data; load() restores it correctly."""
    db = Database(path=tmp_path)
    db.project.cpts.append(cpt)
    db.dump()

    # Load into fresh db instance
    fresh_db = Database(path=tmp_path)
    fresh_db.load(tmp_path / ".ceniac" / "db.pkl")

    # pickle creates new object instances on deserialization, so check id_ field
    restored = fresh_db.project.cpts[0]
    assert restored.id_ == cpt.id_


def test_database_dump_roundtrip_with_sessions(tmp_path):
    """dump() preserves calc sessions and data; load() restores them correctly."""
    from baml_client.types import Berekening

    db = Database(path=tmp_path)
    session_id = db.calc.create_session(Berekening.PAALFUNDERING)
    db.calc.set_calc("test_key", "test_value")
    db.dump()

    # Load into fresh db instance
    fresh_db = Database(path=tmp_path)
    fresh_db.load(tmp_path / ".ceniac" / "db.pkl")

    # Session restored
    assert session_id in fresh_db.calc.sessions
    session = fresh_db.calc.sessions[session_id]
    assert isinstance(session, CalcTableEntry)
    assert session.type == Berekening.PAALFUNDERING
    assert "test_key" in session.data
    assert session.data["test_key"] == "test_value"

    # _current_session_id restored
    assert fresh_db.calc._current_session_id == session_id
