"""Tests for combine_soil_profiles_cpts using based_on field."""

import pytest
import numpy as np

from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import SoilProfile, Layer
from ari.workflows.calculate.pile import combine_soil_profiles_cpts


def make_cpt(id_: str) -> Cpt:
    """Create a minimal CPT for testing (only id_ matters for this function)."""
    return Cpt(
        id_=id_,
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


class TestCombineSoilProfilesCpts:
    """Test combine_soil_profiles_cpts function."""

    def test_basic_matching(self):
        """Test basic matching: cpts=[cpt with id_='CPT001'], soil_profiles=[sp with based_on='CPT001'] → returns [(cpt, sp)]."""
        # Create a CPT with id_
        cpt = make_cpt("CPT001")

        # Create a SoilProfile with based_on matching the CPT id_
        soil_profile = SoilProfile(
            name="test_profile",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT001",
        )

        # Call the function
        result = combine_soil_profiles_cpts(
            cpts=[cpt],
            soil_profiles=[soil_profile],
            sp_cpt_mapping={'test_profile': "CPT001"},
        )

        # Verify the result
        assert len(result) == 1
        assert result[0] == (cpt, soil_profile)

    def test_missing_cpt_raises_valueerror(self):
        """Test missing CPT: cpts=[], soil_profiles=[sp with based_on='CPT001'] → raises ValueError."""
        # Create a SoilProfile with based_on referencing a CPT that doesn't exist
        soil_profile = SoilProfile(
            name="test_profile",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT001",
        )

        # Call with empty CPT list
        with pytest.raises(ValueError, match="CPT001"):
            combine_soil_profiles_cpts(
                cpts=[],
                soil_profiles=[soil_profile],
                sp_cpt_mapping={'test_profile': "CPT001"},
            )

    def test_skip_none_based_on(self):
        """Test skip None: cpts=[cpt], soil_profiles=[sp with based_on=None] → returns []."""
        # Create a CPT with id_
        cpt = make_cpt("CPT001")

        # Create a SoilProfile with based_on=None (manually created)
        soil_profile = SoilProfile(
            name="test_profile",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-10)],
            bottom=-10,
            based_on=None,
        )

        # Call with profiles mapped to None
        with pytest.raises(ValueError, match="None"):
            result = combine_soil_profiles_cpts(
                cpts=[cpt],
                soil_profiles=[soil_profile],
                sp_cpt_mapping={'test_profile': None},
            )

    def test_multiple_profiles_match_same_cpt(self):
        """Test multiple soil profiles based on the same CPT."""
        cpt = make_cpt("CPT001")

        soil_profile_1 = SoilProfile(
            name="profile_1",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-5)],
            bottom=-5,
            based_on="CPT001",
        )

        soil_profile_2 = SoilProfile(
            name="profile_2",
            surface_level=0,
            layers=[Layer(soil="klei", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT001",
        )

        result = combine_soil_profiles_cpts(
            cpts=[cpt],
            soil_profiles=[soil_profile_1, soil_profile_2],
            sp_cpt_mapping={'profile_1': "CPT001", 'profile_2': "CPT001"},
        )

        assert len(result) == 2
        assert (cpt, soil_profile_1) in result
        assert (cpt, soil_profile_2) in result


    def test_multiple_cpts_with_matching_profiles(self):
        """Test multiple CPTs each with their own derived profiles."""
        cpt1 = make_cpt("CPT001")
        cpt2 = make_cpt("CPT002")

        profile1 = SoilProfile(
            name="profile_1",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT001",
        )

        profile2 = SoilProfile(
            name="profile_2",
            surface_level=0,
            layers=[Layer(soil="klei", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT002",
        )

        result = combine_soil_profiles_cpts(
            cpts=[cpt1, cpt2],
            soil_profiles=[profile1, profile2],
            sp_cpt_mapping={'profile_1': "CPT001", 'profile_2': "CPT002"},
        )

        assert len(result) == 2
        assert (cpt1, profile1) in result
        assert (cpt2, profile2) in result

    def test_missing_based_on_cpt_raises_valueerror(self):
        """Test that a ValueError is raised when based_on references a non-existent CPT."""
        cpt = make_cpt("CPT001")

        # Profile references a CPT that doesn't exist in the list
        profile = SoilProfile(
            name="profile",
            surface_level=0,
            layers=[Layer(soil="zand", top=0, bottom=-10)],
            bottom=-10,
            based_on="CPT999",
        )

        with pytest.raises(ValueError, match="CPT999"):
            combine_soil_profiles_cpts(
                cpts=[cpt],
                soil_profiles=[profile],
                sp_cpt_mapping={'profile': "CPT999"},

            )
