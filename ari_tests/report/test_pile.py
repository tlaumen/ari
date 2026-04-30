import pytest
from unittest.mock import MagicMock

from ceniac.calculate.pile import PileResult, PileResults
from ceniac.parameters.model import PileFoundationParams
from ari.queries.pile_report import (
    _create_pile_factors_table,
)
from ari.queries.pile_report import _create_params_table, _create_bearing_capacity_table

from baml_client.types import (
    ReportBaseLineModelling,
    ReportBaseLineSoilInvestigation,
    ReportBaseResults,
    ReportBaseLineIntroduction,
    ReportBaseLineConclusion,
)
from baml_client.types import ReportBaseLineAssumptions

from ari.report.report import _SectionInput
from ari.report.table import Table
from ari.queries.pile_calc import PileType
from ari.queries.pile_report import _llm_text_generation_router
from ari_tests.fixtures.workflow_mocks import SequentialMock, mock_llm_reports



@pytest.mark.auto
def test_create_params_table():
    params = [
        PileFoundationParams(
            soil="zand",
            K0=0.3,
            gamma_nat=18,
            gamma_sat=20,
            friction_angle=34,
            compressible=False,
            undrained_shear_strength=200,
        ),
        PileFoundationParams(
            soil="klei",
            K0=0.6,
            gamma_nat=15,
            gamma_sat=15,
            friction_angle=25,
            compressible=True,
            undrained_shear_strength=30,
        ),
    ]
    table = _create_params_table(params, 1)
    assert table.data == {
        "Grondsoort": ["zand", "klei"],
        "Natuurlijk vol. gewicht [kN/m3]": ["18", "15"],
        "Verzadigd vol. gewicht [kN/m3]": ["20", "15"],
        "Wrijvingshoek [graden]": ["34", "25"],
    }


@pytest.mark.auto
def test_create_pile_factors_table():
    t = _create_pile_factors_table(pile_type=PileType.BUISSCHROEFPAAL, table_number=1)
    assert isinstance(t, Table)

    t = _create_pile_factors_table(pile_type=PileType.VIBROPAAL, table_number=1)
    assert isinstance(t, Table)

    with pytest.raises(NotImplementedError):
        _ = _create_pile_factors_table(pile_type=3, table_number=1)  # pyright: ignore


@pytest.mark.auto
def test_create_bearing_capacity_table():
    # Create mock CPT object
    mock_cpt = MagicMock()
    mock_cpt.id_ = "CPT001"

    # Create sample PileResult objects
    _results = [
        PileResult(
            cpt=mock_cpt,
            tip_level=-10.5,
            bc_shaft_rep=500.0,
            bc_tip_rep=800.0,
            nsf_rep=100.0,
            design_bearing_capacity=864.7,
        ),
        PileResult(
            cpt=mock_cpt,
            tip_level=-12.0,
            bc_shaft_rep=600.0,
            bc_tip_rep=900.0,
            nsf_rep=120.0,
            design_bearing_capacity=994.2,
        ),
    ]
    results = PileResults(pile="1", results=_results)  # pyright: ignore
    # Call the function
    table = _create_bearing_capacity_table(results, 1)

    # Assert the result is a Table
    assert isinstance(table, Table)

    # Assert all expected columns are present
    expected_columns = [
        "PPN [m+NAP]",
        "Schachtwrijving (rep) [kN]",
        "Draagkracht punt (rep) [kN]",
        "Negatieve kleef (rep) [kN]",
        "Totale draagkracht (rep) [kN]",
        "Totale draagkracht (ontwerp) [kN]",
    ]
    for col in expected_columns:
        assert col in table.data

    # Assert data is correctly populated
    assert table.data["PPN [m+NAP]"] == ["-10.5", "-12.0"]
    assert table.data["Schachtwrijving (rep) [kN]"] == ["500.0", "600.0"]
    assert table.data["Draagkracht punt (rep) [kN]"] == ["800.0", "900.0"]
    assert table.data["Negatieve kleef (rep) [kN]"] == ["100.0", "120.0"]
    assert table.data["Totale draagkracht (rep) [kN]"] == ["1200.0", "1380.0"]
    assert table.data["Totale draagkracht (ontwerp) [kN]"] == ["864.7", "994.2"]

    # Assert all columns have the same length
    n_rows = len(table.data["PPN [m+NAP]"])
    for col_data in table.data.values():
        assert len(col_data) == n_rows


@pytest.mark.ai
def test_llm_text_generation_router():
    pointers = ReportBaseLineIntroduction(
        pointers=["Paalberekening in Rotterdam"], elements=[]
    )

    text = _llm_text_generation_router(
        section_input=_SectionInput(model_input=pointers, elements=[])
    )
    assert isinstance(text, str)
