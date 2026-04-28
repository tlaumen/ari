"""Tests for the fresh_db fixture."""


def test_fresh_db_provides_project_and_calc(fresh_db):
    """Test fresh_db provides a Database with project and calc sub-tables."""
    assert hasattr(fresh_db, "project")
    assert hasattr(fresh_db, "calc")


def test_fresh_db_tables_are_empty(fresh_db):
    """Test that project sub-tables are empty upon fixture initialization."""
    assert len(fresh_db.project.cpts) == 0
    assert len(fresh_db.project.soilprofiles) == 0
    assert len(fresh_db.project.params) == 0
    assert len(fresh_db.project.colors) == 0
    assert len(fresh_db.calc.sessions) == 0
