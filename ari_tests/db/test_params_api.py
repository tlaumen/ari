"""Tests for params access via db.get(Table.PROJECT, "params")."""

import pytest
from dataclasses import dataclass

from ari.db.database import Table, ProjectTable
from ari_tests.test_utils import cpt
from ceniac.parameters.model import PileFoundationParams
from ari.db.database import Database

class SampleParams(PileFoundationParams):
    """Concrete params fixture for testing."""

    def __init__(self, soil: str):
        super().__init__(
            soil=soil,
            K0=1.0,
            gamma_nat=16.0,
            gamma_sat=18.0,
            friction_angle=30.0,
            compressible=False,
            undrained_shear_strength=0.0,
        )


def _add_params(db: Database, params: PileFoundationParams) -> None:
    """ "Helper to add params using db.add() instead of removed params_to_db()."""
    db.add(Table.PROJECT, "params", params)


class TestParamsViaNewAPI:
    """Tests for params access via db.get(Table.PROJECT, "params")."""

    def test_get_params_returns_list(self, fresh_db):
        """db.get(Table.PROJECT, 'params') returns a list."""
        db = Database()
        params = SampleParams(soil="klei")
        _add_params(db,params)
        result = db.get(Table.PROJECT, "params")
        assert isinstance(result, list)

    def test_get_params_returns_copy(self, fresh_db):
        """db.get(Table.PROJECT, 'params') returns a deep copy."""
        db = Database()
        params = SampleParams(soil="klei")
        _add_params(db, params)
        result = db.get(Table.PROJECT, "params")
        # Mutate the copy
        result[0].gamma_nat = 9999.9
        # Original should be unchanged
        assert db.project.params[0].gamma_nat == 16.0

    def test_get_params_contains_params_after_add(self, fresh_db):
        """'soil-name in db.get(Table.PROJECT, "params")' is True after adding."""
        db = Database()
        params = SampleParams(soil="klei")
        _add_params(db, params)
        result = db.get(Table.PROJECT, "params")
        assert params in result

    def test_get_params_missing_returns_empty(self, fresh_db):
        """db.get(Table.PROJECT, 'params') returns empty dict when no params."""
        db = Database()
        result = db.get(Table.PROJECT, "params")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_params_missing_params_not_in_result(self, fresh_db):
        """'nonexistent' in db.get(Table.PROJECT, "params") is False."""
        db = Database()
        result = db.get(Table.PROJECT, "params")
        assert "nonexistent" not in result


class TestParamsViaDirectDict:
    """Tests for params access via direct dict attribute on project.params."""

    def test_project_params_getitem(self, fresh_db):
        """app_db.project.params['soil-name'] returns the params."""
        db = Database()
        params = SampleParams(soil="klei")
        _add_params(db, params)
        assert db.project.params[0].soil == "klei"

