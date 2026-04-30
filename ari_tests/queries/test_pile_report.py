from unittest.mock import Mock 

from pylatex import Document

from ceniac.parameters.model import PileFoundationParams
from ceniac.calculate.pile import PileResults, PileResult

from baml_client.types import (
    ReportBaseLineAssumptions,
    ReportBaseLineConclusion,
    ReportBaseLineIntroduction,
    ReportBaseLineSoilInvestigation,
    ReportBaseLineModelling,
    ReportBaseResults,
)

from ari.queries.pile_report import StepSoilInvestigationChapter, REPORT_SI_KEY, REPORT_ASSUMPTIONS_KEY, FIGURE_NUMBER, TABLE_NUMBER
from ari.queries.pile_report import StepResultsChapter, StepAssumptionsChapter, StepModellingChapter, REPORT_MODELLING_KEY, REPORT_RESULTS_KEY, REPORT_INTRODUCTION_KEY
from ari.queries.pile_report import StepIntroductionChapter, REPORT_CONCLUSION_KEY, StepConclusionChapter, StepCreateReport, REPORT_KEY, CAPTION_NUMBERS_KEY
from ari.report.report import _SectionInput, CaptionNumbers
from ari.queries.soil_interpretation import CPT_NAME_KEY
from ari.queries.pile_calc import (
    CALCULATION_RESULTS_KEY,
    FUTURE_GROUND_LEVEL_KEY,
    PHREATIC_LEVEL_KEY,
    PILE_TIP_LEVEL_KEY,
    SKIN_FRICTION_RANGES_KEY,
    SLS_LOAD_KEY,
    STRUCTURE_RIGIDITY_KEY,
    ULS_LOAD_KEY,
    WORK_ORDER_KEY,
    PileType,
    PILE_TYPE_KEY
)

from ari_tests.fixtures.workflow_mocks import SequentialMock

def test_step_soil_investigation_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Soil investigation pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepSoilInvestigationChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CPT_NAME_KEY: "CPT002"
    }
        
    with seq.mock():
        step.execute(ctx)
    
    assert REPORT_SI_KEY in ctx
    assert CAPTION_NUMBERS_KEY in ctx

def test_step_soil_investigation_chapter_correct():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Soil investigation pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepSoilInvestigationChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CPT_NAME_KEY: "CPT002"
    }
        
    with seq.mock():
        step.execute(ctx)
    
    assert isinstance(ctx[REPORT_SI_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_SI_KEY].model_input, ReportBaseLineSoilInvestigation)
    assert ctx[CAPTION_NUMBERS_KEY].table == 1

def test_step_assumptions_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Assumptions pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepAssumptionsChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CAPTION_NUMBERS_KEY: CaptionNumbers(),
        "params": [
            PileFoundationParams(soil="sand", K0=0.3, gamma_nat=18, gamma_sat=20, friction_angle=35, compressible=False, undrained_shear_strength=100),
        ],
    }

    with seq.mock():
        step.execute(ctx)

    assert REPORT_ASSUMPTIONS_KEY in ctx


def test_step_assumptions_chapter_correct():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Assumptions pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepAssumptionsChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CAPTION_NUMBERS_KEY: CaptionNumbers(table=1),
        "params": [
            PileFoundationParams(soil="sand", K0=0.3, gamma_nat=18, gamma_sat=20, friction_angle=35, compressible=False, undrained_shear_strength=100),
        ],
    }

    with seq.mock():
        step.execute(ctx)

    assert isinstance(ctx[REPORT_ASSUMPTIONS_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_ASSUMPTIONS_KEY].model_input, ReportBaseLineAssumptions)
    assert ctx[CAPTION_NUMBERS_KEY].table == 2

def test_step_modelling_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Modelling pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepModellingChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CPT_NAME_KEY: "CPT002",
        CAPTION_NUMBERS_KEY: CaptionNumbers(table=2, figure=1),
        PILE_TYPE_KEY: PileType.PREFAB_HEIPAAL,
        SKIN_FRICTION_RANGES_KEY: {"CPT002": Mock(bottom_negative_skin_friction=-2, top_positive_skin_friction=-2)},
        STRUCTURE_RIGIDITY_KEY: True,
        WORK_ORDER_KEY: "some workorder mock",
        FUTURE_GROUND_LEVEL_KEY: 1.5, #m+NAP
        PHREATIC_LEVEL_KEY: 1.0, #m +NAP
        "cpts": [Mock(id_="CPT002", surface_level=2)],
    }

    with seq.mock():
        step.execute(ctx)

    assert REPORT_MODELLING_KEY in ctx


def test_step_modelling_chapter_correct():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("Modelling pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepModellingChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CPT_NAME_KEY: "CPT002",
        CAPTION_NUMBERS_KEY: CaptionNumbers(table=2, figure=None),
        PILE_TYPE_KEY: PileType.PREFAB_HEIPAAL,
        SKIN_FRICTION_RANGES_KEY: {"CPT002": Mock(bottom_negative_skin_friction=-2, top_positive_skin_friction=-2)},
        STRUCTURE_RIGIDITY_KEY: True,
        WORK_ORDER_KEY: "some workorder mock",
        FUTURE_GROUND_LEVEL_KEY: 1.5, #m+NAP
        PHREATIC_LEVEL_KEY: 1.0, #m +NAP
        "cpts": [Mock(id_="CPT002", surface_level=2)],
    }

    with seq.mock():
        step.execute(ctx)

    assert isinstance(ctx[REPORT_MODELLING_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_MODELLING_KEY].model_input, ReportBaseLineModelling)
    assert ctx[CAPTION_NUMBERS_KEY].table == 4


def test_step_results_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("results pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepResultsChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CAPTION_NUMBERS_KEY: CaptionNumbers(table=4, figure=None),
        PILE_TIP_LEVEL_KEY: -20,
        CALCULATION_RESULTS_KEY: PileResults(
            pile=Mock(),
            results=[
                PileResult(cpt=Mock(), tip_level=-20, bc_shaft_rep=1000, bc_tip_rep=1000, nsf_rep=200, design_bearing_capacity=1500)
            ]
        ),
        SLS_LOAD_KEY: 1000,
        ULS_LOAD_KEY: 1500,
    }
    with seq.mock():
        step.execute(ctx)

    assert REPORT_RESULTS_KEY in ctx

def test_step_results_chapter_correct():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("results pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepResultsChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        CAPTION_NUMBERS_KEY: CaptionNumbers(table=4, figure=None),
        PILE_TIP_LEVEL_KEY: -20,
        CALCULATION_RESULTS_KEY: PileResults(
            pile=Mock(),
            results=[
                PileResult(cpt=Mock(), tip_level=-20, bc_shaft_rep=1000, bc_tip_rep=1000, nsf_rep=200, design_bearing_capacity=1500)
            ]
        ),
        SLS_LOAD_KEY: 1000,
        ULS_LOAD_KEY: 1500,
    }
    with seq.mock():
        step.execute(ctx)

    assert isinstance(ctx[REPORT_RESULTS_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_RESULTS_KEY].model_input, ReportBaseResults)
    assert ctx[CAPTION_NUMBERS_KEY].table == 5
    assert ctx[CAPTION_NUMBERS_KEY].figure == 1


def test_step_introduction_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("introduction pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepIntroductionChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {}
    with seq.mock():
        step.execute(ctx)

    assert REPORT_INTRODUCTION_KEY in ctx
    assert isinstance(ctx[REPORT_INTRODUCTION_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_INTRODUCTION_KEY].model_input, ReportBaseLineIntroduction)

def test_step_conclusion_chapter_executes():
    # Mocking input
    seq = SequentialMock()
    # 1 prompt + 1 confirm (all False to exit loop)
    seq.add_prompt("introduction pointer")
    seq.add_confirm(False)

    # Instatiate step
    step = StepConclusionChapter()
    
    # Mock relevant context
    ctx: dict[str, Any] = {
        PILE_TYPE_KEY: Mock(),
        PILE_TIP_LEVEL_KEY: Mock(),
    }
    with seq.mock():
        step.execute(ctx)

    assert REPORT_CONCLUSION_KEY in ctx
    assert isinstance(ctx[REPORT_CONCLUSION_KEY], _SectionInput)
    assert isinstance(ctx[REPORT_CONCLUSION_KEY].model_input, ReportBaseLineConclusion)
 
def test_step_create_report_executes():
    # Instatiate step
    step = StepCreateReport()

    # Mock relevant context
    ctx: dict[str, Any] = {
        REPORT_SI_KEY: _SectionInput(model_input=ReportBaseLineSoilInvestigation(pointers=[], elements=[]), elements=[]),
        REPORT_ASSUMPTIONS_KEY: _SectionInput(model_input=ReportBaseLineAssumptions(pointers=[], parameters=[], elements=[]), elements=[]),
        REPORT_MODELLING_KEY: _SectionInput(model_input=ReportBaseLineModelling(pointers={"soil_profiles": [], "pile": [], "variability_information": [], "environmental_factors": []}, elements=[]), elements=[]),
        REPORT_RESULTS_KEY: _SectionInput(model_input=ReportBaseResults(pointers={"pile_tip_range": "", "bearing_capacity": "", "load": "1000", "pile_tip_level": ""}, elements=[]), elements=[]),
        REPORT_INTRODUCTION_KEY: _SectionInput(model_input=ReportBaseLineIntroduction(pointers=[], elements=[]), elements=[]),
        REPORT_CONCLUSION_KEY: _SectionInput(model_input=ReportBaseLineConclusion(pointers=[], elements=[]), elements=[]),
    }
    step.execute(ctx)

    assert REPORT_KEY in ctx
    assert isinstance(ctx[REPORT_KEY], Document)

