"""Tests for ProjectTable.add method."""

import pytest
import numpy as np

from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import Layer, SoilProfile
from ceniac.parameters.model import PileFoundationParams
from ari.db.database import ProjectTable


class TestAddSingleCpt:
    """Test adding a single CPT object."""

    def test_add_single_cpt(self):
        """Given a Cpt object, project.add("B-01", cpt) stores it so project.cpts["B-01"] is cpt."""
        project = ProjectTable()
        cpt = Cpt(
            id_="B-01",
            x=100.0,
            y=200.0,
            surface_level=2.0,
            predrill_depth=0.5,
            a_cone=0.8,
            depths=np.array([0.0, 1.0, 2.0]),
            qc=np.array([1.0, 2.0, 3.0]),
            fs=np.array([10.0, 20.0, 30.0]),
        )
        project.add(cpt)
        assert cpt == project.cpts[0]
        assert project.cpts[0] is cpt


class TestAddSingleSoilProfile:
    """Test adding a single SoilProfile object."""

    def test_add_single_soilprofile(self):
        """Given a SoilProfile object, project.add("SP-01", sp) stores it so project.soilprofiles["SP-01"] is sp."""
        project = ProjectTable()
        layer = Layer(soil="sand", top=2.0, bottom=-3.0)
        sp = SoilProfile(
            name="SP-01",
            surface_level=2.0,
            layers=[layer],
            bottom=-3.0,
        )
        project.add(sp)
        assert sp == project.soilprofiles[0]
        assert project.soilprofiles[0] is sp


class TestAddSingleParams:
    """Test adding a single PileFoundationParams object."""

    def test_add_single_params(self):
        """Given PileFoundationParams object, project.add("klei", params) stores it so project.params["klei"] is params."""
        project = ProjectTable()
        params = PileFoundationParams(
            soil="klei",
            K0=0.5,
            gamma_nat=16.0,
            gamma_sat=18.0,
            friction_angle=25.0,
            compressible=True,
            undrained_shear_strength=30.0,
        )
        project.add(params)
        assert params == project.params[0]
        assert project.params[0] is params

# TODO: fix colors stuff
class TestAddSingleColor:
    """Test adding a single color string."""

#    def test_add_single_color(self):
#        """Given a hex color string, project.add("klei", "#FF0000") stores it so project.colors["klei"] == "#FF0000"."""
#        project = ProjectTable()
#        project.add("#FF0000")
#        assert "klei" in project.colors
#        assert project.colors["klei"] == "#FF0000"



class TestAddUnknownTypeRaisesTypeError:
    """Test that adding an unknown type raises TypeError."""

    def test_add_unknown_type_raises_typeerror(self):
        """Calling project.add("key", some_unknown_object) raises TypeError with the type name in the message."""
        project = ProjectTable()

        class UnknownObject:
            pass

        unknown_obj = UnknownObject()
        with pytest.raises(TypeError, match="Unsupported type"):
            project.add(unknown_obj)
