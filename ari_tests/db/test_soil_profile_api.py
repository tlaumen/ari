"""Tests for soil profile access via db.get(Table.PROJECT, "soilprofiles").

Note: After Step 17, soil_profile_to_db() was removed. The canonical provenance
tracker is now the `based_on` field on SoilProfile objects, NOT profilemap.
Profilemap is only maintained for legacy pickle file compatibility.
"""

import pytest

from ari.db.database import Table, ProjectTable
from ari_tests.test_utils import cpt, sp
from ceniac.soil_profile.soil_profile import SoilProfile
from ari.db.database import Database

def _add_cpt(db: Database, cpt_obj) -> None:
    """Helper to add CPT using db.add() instead of removed cpt_to_db()."""
    db.add(Table.PROJECT, "cpts", cpt_obj)


def _add_soil_profile(db: Database, soil_profile: SoilProfile, based_on_cpt: str) -> None:
    """Helper to add soil profile with based_on using db.add().

    Sets based_on in-place before adding (mirrors the old soil_profile_to_db pattern).
    Note: profilemap is NOT written — based_on field is the canonical tracker.
    """
    soil_profile.based_on = based_on_cpt
    db.add(Table.PROJECT, "soilprofiles", soil_profile)


class TestSoilProfilesViaNewAPI:
    """Tests for soil profile access via db.get(Table.PROJECT, "soilprofiles")."""

    def test_get_soilprofiles_returns_dict(self, fresh_db):
        """db.get(Table.PROJECT, 'soilprofiles') returns a dict."""
        db = Database()
        _add_cpt(db, cpt)
        _add_soil_profile(db, sp, cpt.id_)
        result = db.get(Table.PROJECT, "soilprofiles")
        assert isinstance(result, list)

    def test_get_soilprofiles_returns_copy(self, fresh_db):
        """db.get(Table.PROJECT, 'soilprofiles') returns a deep copy."""
        db = Database()
        _add_cpt(db, cpt)
        _add_soil_profile(db, sp, cpt.id_)
        result = db.get(Table.PROJECT, "soilprofiles")
        # Mutate the copy
        result[0].surface_level = 9999.9
        # Original should be unchanged
        assert db.project.soilprofiles[0].surface_level == sp.surface_level

    def test_get_soilprofiles_contains_profile_after_add(self, fresh_db):
        """'profile-name in db.get(Table.PROJECT, "soilprofiles")' is True after adding."""
        db = Database()
        _add_cpt(db, cpt)
        _add_soil_profile(db, sp, cpt.id_)
        result = db.get(Table.PROJECT, "soilprofiles")
        assert sp.name == result[0].name

    def test_get_soilprofiles_missing_returns_empty(self, fresh_db):
        """db.get(Table.PROJECT, 'soilprofiles') returns empty dict when no profiles."""
        db = Database()
        result = db.get(Table.PROJECT, "soilprofiles")
        assert isinstance(result, list)
        assert len(result) == 0

