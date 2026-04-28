"""Tests for Step 7: CalcTable and Database classes."""

import pytest
from pathlib import Path

from baml_client.types import Berekening

from ari.db.database import CalcTableEntry, CalcTable, Database, ProjectTable
from ari.db import db as db_module


# =============================================================================
# CalcTableEntry
# =============================================================================


def test_calc_table_entry_dataclass():
    """CalcTableEntry stores type, created string, and data dict."""
    entry = CalcTableEntry(
        type=Berekening.PAALFUNDERING,
        created="2026-01-01 10:00:00",
        data={"key": "value"},
    )
    assert entry.type == Berekening.PAALFUNDERING
    assert entry.created == "2026-01-01 10:00:00"
    assert entry.data == {"key": "value"}


# =============================================================================
# CalcTable
# =============================================================================


def test_calc_table_init_empty():
    """CalcTable.__init__ creates empty sessions dict and null current session."""
    ct = CalcTable()
    assert isinstance(ct.sessions, dict)
    assert len(ct.sessions) == 0
    assert ct._current_session_id is None


def test_calc_table_create_session():
    """CalcTable.create_session adds a session and sets it as current."""
    ct = CalcTable()
    id_ = ct.create_session(Berekening.PAALFUNDERING)

    assert id_ == 0
    assert id_ in ct.sessions
    assert ct.sessions[id_].type == Berekening.PAALFUNDERING
    assert ct._current_session_id == id_
    assert ct.current_session is ct.sessions[id_]


def test_calc_table_create_multiple_sessions():
    """CalcTable.create_session increments session IDs correctly."""
    ct = CalcTable()
    id0 = ct.create_session(Berekening.PAALFUNDERING)
    id1 = ct.create_session(Berekening.STABILITEIT)
    id2 = ct.create_session(Berekening.PAALFUNDERING)

    assert id0 == 0
    assert id1 == 1
    assert id2 == 2
    assert len(ct.sessions) == 3
    # Last created session is current
    assert ct._current_session_id == id2


def test_calc_table_has_true_when_key_present():
    """CalcTable.has returns True when key exists in current session data."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)
    ct.set_calc("key1", "value1")

    assert ct.has("key1") is True


def test_calc_table_has_false_when_no_session():
    """CalcTable.has returns False when no active session."""
    ct = CalcTable()
    assert ct.has("key1") is False


def test_calc_table_has_false_when_key_missing():
    """CalcTable.has returns False when session exists but key does not."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)

    assert ct.has("nonexistent") is False


def test_calc_table_set_and_get_calc():
    """CalcTable.set_calc and get_calc store and retrieve values."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)
    ct.set_calc("sum", 42)

    assert ct.get_calc("sum") == 42


def test_calc_table_get_calc_raises_on_no_session():
    """CalcTable.get_calc raises RuntimeError when no active session."""
    ct = CalcTable()
    with pytest.raises(RuntimeError) as exc_info:
        ct.get_calc("key")

    assert "session" in str(exc_info.value).lower()


def test_calc_table_get_calc_raises_on_missing_key():
    """CalcTable.get_calc raises KeyError when key not in session data."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)

    with pytest.raises(KeyError) as exc_info:
        ct.get_calc("nonexistent")

    assert "nonexistent" in str(exc_info.value)


def test_calc_table_remove_calc():
    """CalcTable.remove_calc deletes a key from current session data."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)
    ct.set_calc("temp", "data")

    assert ct.has("temp") is True
    ct.remove_calc("temp")
    assert ct.has("temp") is False


def test_calc_table_remove_calc_raises_on_no_session():
    """CalcTable.remove_calc raises RuntimeError when no active session."""
    ct = CalcTable()
    with pytest.raises(RuntimeError) as exc_info:
        ct.remove_calc("key")

    assert "session" in str(exc_info.value).lower()


def test_calc_table_remove_calc_raises_on_missing_key():
    """CalcTable.remove_calc raises KeyError when key not in session data."""
    ct = CalcTable()
    ct.create_session(Berekening.PAALFUNDERING)

    with pytest.raises(KeyError):
        ct.remove_calc("nonexistent")


# =============================================================================
# Database
# =============================================================================


def test_database_init_defaults():
    """Database() creates empty project and calc, default dump path."""
    db = Database()

    assert isinstance(db.project, ProjectTable)
    assert isinstance(db.calc, CalcTable)
    assert db.calc._current_session_id is None


def test_database_init_with_path():
    """Database(path) sets _dump_path to path / '.ceniac'."""
    db = Database(path=Path("/tmp/myproject"))

    assert db._dump_path == Path("/tmp/myproject/.ceniac")


def test_database_init_with_calc_type():
    """Database(calc_type) creates a session immediately."""
    db = Database(calc_type=Berekening.PAALFUNDERING)

    assert db.calc._current_session_id == 0
    assert db.calc.sessions[0].type == Berekening.PAALFUNDERING


def test_database_calc_folder_with_no_session():
    """Database.calc_folder raises when no session exists."""
    db = Database()
    with pytest.raises(ValueError):
        _ = db.calc_folder


def test_database_calc_folder_returns_session_path():
    """Database.calc_folder returns _dump_path / session_id when session exists."""
    db = Database(path=Path("/tmp/test"), calc_type=Berekening.PAALFUNDERING)

    assert db.calc_folder == Path("/tmp/test/.ceniac/0")


# =============================================================================
# Wrapper: create_new_calculation_table delegates to db.calc
# =============================================================================


def test_create_new_calculation_table_creates_session_on_db(fresh_db):
    """create_new_calculation_table delegates to db.calc.create_session."""
    from ari.db.db import create_new_calculation_table, db

    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)

    assert db.calc._current_session_id == 0
    assert db.calc.sessions[0].type == Berekening.PAALFUNDERING


# =============================================================================
# Wrapper: write_calc_data delegates to db.calc
# =============================================================================


def test_write_calc_data_uses_db_singleton(fresh_db):
    """write_calc_data writes to db.calc instead of legacy DB."""
    from ari.db.db import write_calc_data, create_new_calculation_table, db

    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)
    write_calc_data(key="answer", data=42)

    # Verify data is stored in db.calc
    assert db.calc.has("answer") is True
    assert db.calc.get_calc("answer") == 42


# =============================================================================
# Wrapper: get_calc_data delegates to db.calc
# =============================================================================


def test_get_calc_data_uses_db_singleton(fresh_db):
    """get_calc_data reads from db.calc instead of legacy DB."""
    from ari.db.db import (
        get_calc_data,
        write_calc_data,
        create_new_calculation_table,
        db,
    )

    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)
    write_calc_data(key="x", data=99)

    assert get_calc_data("x") == 99


# =============================================================================
# Wrapper: get_calc_folder delegates to db.calc_folder
# =============================================================================


def test_get_calc_folder_uses_db_calc_folder(fresh_db):
    """get_calc_folder returns db.calc_folder."""
    from ari.db.db import get_calc_folder, create_new_calculation_table, db

    create_new_calculation_table(calc_type=Berekening.PAALFUNDERING)

    result = get_calc_folder()

    assert result == db.calc_folder


# =============================================================================
# Wrapper: initialize_db updates db._dump_path
# =============================================================================


def test_initialize_db_sets_db_dump_path(fresh_db):
    """initialize_db sets db._dump_path to path / '.ceniac'."""
    from ari.db.db import initialize_db, db
    from ari_tests.test_utils import DB_DUMP_FOLDER

    initialize_db(DB_DUMP_FOLDER)

    assert db._dump_path == DB_DUMP_FOLDER / ".ceniac"
