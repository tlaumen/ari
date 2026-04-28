"""Tests for Step 9: Table enum and generic Database.has/get/add methods."""

import pytest
from ari.db.database import Database, ProjectTable, CalcTable, Table


# === Table enum tests ===


def test_table_enum_has_project_and_calc_members():
    """Table.PROJECT and Table.CALC exist and are distinct."""
    assert hasattr(Table, "PROJECT")
    assert hasattr(Table, "CALC")
    assert Table.PROJECT is not Table.CALC
    # Verify they are the only members
    assert len(Table) == 2


def test_table_enum_members_are_enum_instances():
    """Table.PROJECT and Table.CALC are valid Table enum instances."""
    assert isinstance(Table.PROJECT, Table)
    assert isinstance(Table.CALC, Table)
