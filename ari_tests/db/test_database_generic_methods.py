"""Tests for Step 9: Table enum and generic Database.has/get/add methods."""

import pytest
from ari.db.database import Database, ProjectTable, CalcTable, Table
from ari_tests.test_utils import cpt, sp


# === Database.has tests ===


def test_database_has_project_returns_true_for_valid_subtable():
    """db.has(Table.PROJECT, key) returns True for valid sub-table names."""
    db = Database()
    for key in ("cpts", "soilprofiles", "params", "colors"):
        assert db.has(Table.PROJECT, key) is True, f"Expected True for '{key}'"


def test_database_has_project_returns_false_for_unknown_key():
    """db.has(Table.PROJECT, key) returns False for unknown keys."""
    db = Database()
    assert db.has(Table.PROJECT, "nonexistent") is False
    assert db.has(Table.PROJECT, "unknown") is False
    assert db.has(Table.PROJECT, "") is False


def test_database_has_project_does_not_check_if_subtable_is_non_empty():
    """db.has(Table.PROJECT, key) returns True even for empty sub-tables."""
    db = Database()
    # All sub-tables start empty, but should still return True
    assert db.has(Table.PROJECT, "cpts") is True
    assert db.has(Table.PROJECT, "soilprofiles") is True


def test_database_has_calc_delegates_to_calc_has():
    """db.has(Table.CALC, key) delegates to self.calc.has(key)."""
    db = Database()
    # No session yet - should return False
    assert db.has(Table.CALC, "anything") is False

    # Create a session
    from baml_client.types import Berekening

    db.calc.create_session(Berekening.PAALFUNDERING)

    # Without key in session data - should return False
    assert db.has(Table.CALC, "mykey") is False

    # Add data to session
    db.calc.set_calc("mykey", 42)

    # With key in session data - should return True
    assert db.has(Table.CALC, "mykey") is True


# === Database.get tests ===


def test_database_get_project_returns_deepcopy():
    """db.get(Table.PROJECT, key) returns a deep copy of the sub-table.

    The returned object is a fully independent copy — callers can mutate
    it freely without affecting the database's internal state.
    """
    db = Database()
    for key in ("cpts", "soilprofiles", "params", "colors"):
        copy_ = db.get(Table.PROJECT, key)
        assert isinstance(copy_, list), (
            f"Expected dict for '{key}', got {type(copy_).__name__}"
        )
        assert copy_ is not getattr(db.project, key), (
            f"Return for '{key}' must be a copy, not the raw dict"
        )


def test_database_get_project_raises_on_unknown_key():
    """db.get(Table.PROJECT, key) raises KeyError for unknown keys."""
    db = Database()
    with pytest.raises(KeyError):
        db.get(Table.PROJECT, "nonexistent")
    with pytest.raises(KeyError):
        db.get(Table.PROJECT, "unknown")


def test_database_get_calc_delegates_to_calc_get_calc():
    """db.get(Table.CALC, key) delegates to self.calc.get_calc(key)."""
    db = Database()
    from baml_client.types import Berekening

    db.calc.create_session(Berekening.PAALFUNDERING)

    # Set a value
    db.calc.set_calc("answer", 42)

    # Get it back
    assert db.get(Table.CALC, "answer") == 42


def test_database_get_calc_raises_on_missing_key():
    """db.get(Table.CALC, key) raises KeyError when key is not in session."""
    db = Database()
    from baml_client.types import Berekening

    db.calc.create_session(Berekening.PAALFUNDERING)

    with pytest.raises(KeyError):
        db.get(Table.CALC, "missing")



# === Database.add tests ===


def test_database_add_project_routes_cpt_to_cpts(fresh_db):
    """db.add(Table.PROJECT, key, cpt) stores CPT in db.project.cpts."""
    db = fresh_db
    db.add(Table.PROJECT, "cpts", cpt)

    assert cpt in db.project.cpts
    assert db.project.cpts[0].id_ == cpt.id_


def test_database_add_project_routes_multiple_cpts_to_cpts(fresh_db):
    """db.add(Table.PROJECT, key, cpt) stores CPT in db.project.cpts."""
    db = fresh_db
    # First add the CPT it's based on
    db.add(Table.PROJECT, "cpts", [cpt, cpt, cpt])
    assert len(db.project.cpts) == 3
    assert db.project.cpts[0].id_ == cpt.id_

def test_database_add_project_routes_params_to_params(fresh_db):
    """db.add(Table.PROJECT, key, params) stores in db.project.params."""
    from ceniac.parameters.model import PileFoundationParams

    db = fresh_db
    params = PileFoundationParams(
        soil="klei",
        K0=0.5,
        gamma_nat=18.0,
        gamma_sat=20.0,
        friction_angle=30.0,
        compressible=False,
        undrained_shear_strength=50.0,
    )

    db.add(Table.PROJECT, "params", params)

    assert params in db.project.params
    assert db.project.params[0] is params

def test_database_add_project_raises_on_unsupported_type(fresh_db):
    """db.add(Table.PROJECT, key, value) raises ValueError for unsupported types."""
    db = fresh_db

    with pytest.raises(ValueError) as exc_info:
        db.add(Table.PROJECT, "cpts", "not a supported type")

    assert "key of the db operation is" in str(exc_info.value)

def test_database_add_project_raises_on_unsupported_key(fresh_db):
    """db.add(Table.PROJECT, key, value) raises ValueError for unsupported types."""
    db = fresh_db

    with pytest.raises(KeyError) as exc_info:
        db.add(Table.PROJECT, "unsupported", "not a supported type")

    assert "Unknown sub-table" in str(exc_info.value)


def test_database_add_calc_stores_in_session():
    """db.add(Table.CALC, key, value) stores value under key in current session."""
    from baml_client.types import Berekening

    db = Database()
    db.calc.create_session(Berekening.PAALFUNDERING)

    db.add(Table.CALC, "mykey", 42)

    assert db.calc.has("mykey") is True
    assert db.calc.get_calc("mykey") == 42


def test_database_add_calc_raises_when_no_session():
    """db.add(Table.CALC, key, value) raises when no session is active."""
    db = Database()

    with pytest.raises(RuntimeError) as exc_info:
        db.add(Table.CALC, "mykey", 42)

    assert "No active session" in str(exc_info.value)
