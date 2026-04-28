"""Tests for ProjectTable CPT access via db.get(Table.PROJECT, "cpts")."""

import pytest
import numpy as np

from ari.db.database import Table, ProjectTable
from ari.db import db as db_module
from ari.db.db import db as app_db
from ari_tests.test_utils import cpt
from ceniac.soil_investigation.cpt import Cpt


@pytest.fixture
def sample_cpt():
    """Create a sample CPT for testing."""
    return Cpt(
        id_="test-cpt-001",
        x=100.0,
        y=200.0,
        surface_level=0.0,
        predrill_depth=0.0,
        a_cone=0.001,
        depths=np.array([0.5, 1.5, 2.5]),
        qc=np.array([1.0, 2.0, 3.0]),
        fs=np.array([0.1, 0.2, 0.3]),
        u2=None,
    )


class TestCptsViaNewAPI:
    """Tests for CPT access via db.get(Table.PROJECT, "cpts")."""

    def test_get_cpts_returns_dict(self, sample_cpt, fresh_db):
        """db.get(Table.PROJECT, 'cpts') returns a dict."""
        db_module.db.add(Table.PROJECT, "cpts", sample_cpt)
        result = app_db.get(Table.PROJECT, "cpts")
        assert isinstance(result, list)

    def test_get_cpts_returns_copy(self, sample_cpt, fresh_db):
        """db.get(Table.PROJECT, 'cpts') returns a deep copy."""
        db_module.db.add(Table.PROJECT, "cpts", sample_cpt)
        result = app_db.get(Table.PROJECT, "cpts")
        # Mutate the copy
        result[0].x = 9999.9
        # Original should be unchanged
        assert app_db.project.cpts[0].x == 100.0

    def test_get_cpts_contains_cpt_after_add(self, sample_cpt, fresh_db):
        """'cpt-id in db.get(Table.PROJECT, "cpts")' is True after adding."""
        db_module.db.add(Table.PROJECT, "cpts", sample_cpt)
        cpts = app_db.get(Table.PROJECT, "cpts")
        assert sample_cpt.id_ == cpts[0].id_

    def test_get_cpts_missing_returns_empty(self, fresh_db):
        """db.get(Table.PROJECT, 'cpts') returns empty dict when no CPTs."""
        result = app_db.get(Table.PROJECT, "cpts")
        assert isinstance(result, list)
        assert len(result) == 0


class TestCptsViaDirectDict:
    """Tests for CPT access via direct dict attribute access on project.cpts."""

    def test_project_cpts_has_key(self, sample_cpt, fresh_db):
        """'cpt-id in app_db.project.cpts' is True after adding."""
        db_module.db.add(Table.PROJECT, "cpts", sample_cpt)
        assert sample_cpt.id_ == app_db.project.cpts[0].id_

