"""Tests for ProjectTable.add() polymorphic method."""

import numpy as np
import pytest

from ari.db.database import ProjectTable
from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import SoilProfile, Layer
from ceniac.parameters.model import PileFoundationParams


class TestProjectTableAdd:
    """Test ProjectTable.add() method."""

    @pytest.fixture
    def project(self) -> ProjectTable:
        """Fresh ProjectTable for each test."""
        return ProjectTable()

    @pytest.fixture
    def sample_cpt(self) -> Cpt:
        """A minimal CPT for testing."""
        return Cpt(
            id_="cpt-1",
            x=100.0,
            y=200.0,
            surface_level=0.0,
            predrill_depth=0.0,
            a_cone=0.8,
            depths=np.array([0.0, 1.0, 2.0]),
            qc=np.array([0.5, 1.0, 1.5]),
            fs=np.array([5.0, 10.0, 15.0]),
        )

    @pytest.fixture
    def sample_soil_profile(self) -> SoilProfile:
        """A minimal SoilProfile for testing."""
        return SoilProfile(
            name="clay layer",
            surface_level=0.0,
            layers=[Layer(soil="klei", top=0.0, bottom=-3.0)],
            bottom=-3.0,
        )

    @pytest.fixture
    def sample_params(self) -> PileFoundationParams:
        """Minimal PileFoundationParams for testing."""
        return PileFoundationParams(
            soil="clay",
            K0=0.5,
            gamma_nat=16.0,
            gamma_sat=18.0,
            friction_angle=30.0,
            compressible=False,
            undrained_shear_strength=0.0,
        )

    # CPT tests

    def test_add_cpt_stores_under_id(
        self, project: ProjectTable, sample_cpt: Cpt
    ) -> None:
        """A CPT is stored in cpts keyed by its id_."""
        project.add(sample_cpt)
        assert project.cpts[0] == sample_cpt

    # SoilProfile tests

    def test_add_soil_profile_stores_under_name(
        self, project: ProjectTable, sample_soil_profile: SoilProfile
    ) -> None:
        """A SoilProfile is stored in soilprofiles keyed by its name."""
        project.add(sample_soil_profile)
        assert project.soilprofiles[0] == sample_soil_profile

    # PileFoundationParams tests

    def test_add_params_stores_under_soil(
        self, project: ProjectTable, sample_params: PileFoundationParams
    ) -> None:
        """PileFoundationParams are stored in params keyed by soil."""
        project.add(sample_params)
        assert project.params[0] == sample_params

    # Type error tests

    def test_add_raises_type_error_on_unknown_type(self, project: ProjectTable) -> None:
        """Passing an unsupported type raises TypeError with the type name."""
        with pytest.raises(TypeError) as exc_info:
            project.add("not a supported object")
        assert "str" in str(exc_info.value)
