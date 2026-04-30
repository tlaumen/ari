from typing import Any


from geolib.models.dfoundations.profiles import TimeOrderType
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.shortcuts import confirm
from pylatex import Command, NoEscape, Document, section


from ceniac.parameters.model import PileFoundationParams
from ceniac.calculate.pile import (
    PileResults,
    SkinFrictionRanges,
    calc_ksi3,
    calc_ksi4,
    plot_bearing_capacity,
)
from ceniac.soil_investigation.cpt import Cpt
from ari.report.report import markdown_to_section, CaptionNumbers
from ari.queries.base import Requirement, Product

from baml_client.types import (
    ReportBaseLineConclusion,
    ReportBaseLineIntroduction,
    ReportBaseLineSoilInvestigation,
)
from baml_client.types import ReportBaseLineAssumptions
from baml_client.types import ReportBaseLineModelling
from baml_client.types import ModellingPointers
from baml_client.types import ReportBaseResults
from baml_client.types import ResultPointers
from baml_client.sync_client import b

from ari.queries.base import Step, Table
from ari.report.table import Table as ReportTable
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
)
from ari.queries.pile_calc import PILE_TYPE_KEY
from ari.report.report import _SectionInput
from ari.report.plot import Plot
from ari.report.report import Section

REPORT_SI_KEY = "input-grondonderzoek-rapport"
REPORT_ASSUMPTIONS_KEY = "input-aannames-rapport"
REPORT_MODELLING_KEY = "input-modellering-rapport"
REPORT_RESULTS_KEY = "input-resultaten-rapport"
REPORT_INTRODUCTION_KEY = "input-introduction-rapport"
REPORT_CONCLUSION_KEY = "input-conclusie-rapport"
REPORT_KEY = "rapport"

CAPTION_NUMBERS_KEY = "nummer-figuren-tabellen"
TABLE_NUMBER = "TABLE-NUMMER"
FIGURE_NUMBER = "FIGURE_NUMBER"

class StepSoilInvestigationChapter(Step):
    name = "Soil investigation chapter of pile report"
    requires: list[Requirement] = [Requirement(key=CPT_NAME_KEY, source=Table.CALC)]
    produces: list[Product] = [
        Product(key=REPORT_SI_KEY, dest=Table.CALC),
        Product(key=CAPTION_NUMBERS_KEY, dest=Table.CALC),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:

        # 0. Create soil investigation chapter
        #   - show soil investigation present (top view)
        #   - show geological situation(?)
        #   - show important cpts if required
        # TODO: add default pointers for every report(if required)
        # TODO: show user default pointers (so no duplicates are provided)
        # Get cpt name
        used_cpt_id = ctx[CPT_NAME_KEY]
        
        caption_numbers = CaptionNumbers()
        si_pointers = _get_pointers(chapter="Soil investigation")

        # create table
        caption_numbers.new_table()
        cpts_table = ReportTable(
            data={"sonderingen": [used_cpt_id]},
            caption="Alle cpts uitgevoerd rond de fundering",
            number=caption_numbers.table,
        )

        # TODO: add top view image of all soil investigation
        si_base_line = ReportBaseLineSoilInvestigation(pointers=si_pointers, elements=[])
        ctx[REPORT_SI_KEY] = _SectionInput(model_input=si_base_line, elements=[cpts_table])
        ctx[CAPTION_NUMBERS_KEY] = caption_numbers

class StepAssumptionsChapter(Step):
    name = "Assumptions chapter of pile report"
    requires: list[Requirement] = [Requirement(key="params", source=Table.PROJECT), Requirement(key=CAPTION_NUMBERS_KEY, source=Table.CALC)]
    produces: list[Product] = [Product(key=REPORT_ASSUMPTIONS_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        
        # 1. Create 'uitgangspunten' chapter
        #   - report assumptions and parameters
        #   - soil parameters
        #   - ground water table
        #   - loads
        #   - ...

        # TODO: add default pointers
        # TODO: show default pointers to user (to avoid duplicates)
        
        # TODO: create piezometer time series plot & assess if present?! (assess later if to implement)
        params: list[PileFoundationParams] = ctx["params"]
        caption_numbers: CaptionNumbers = ctx[CAPTION_NUMBERS_KEY]
        assumptions_pointers = _get_pointers(chapter="Uitgangspunten")
 
        # Create parameters table
        caption_numbers.new_table()
        parameter_table: ReportTable = _create_params_table(params, caption_numbers.table)

        # TODO: assess how to track references used for 'uitgangspunten' --> add to new 'references' chapter
        assumptions_base_line = ReportBaseLineAssumptions(
            pointers=assumptions_pointers,
            elements=[],
            parameters=[
                p.__dict__ for p in params
            ],  # TODO: assess if correct datastructure!
        )
        ctx[REPORT_ASSUMPTIONS_KEY] = _SectionInput(
            model_input=assumptions_base_line, elements=[parameter_table]
        )


class StepModellingChapter(Step):
    name = "Modelling chapter of pile report"
    requires: list[Requirement] = [
        Requirement(key=CAPTION_NUMBERS_KEY, source=Table.CALC),
        Requirement(key=CPT_NAME_KEY, source=Table.CALC),
        Requirement(key=PILE_TYPE_KEY, source=Table.CALC),
        Requirement(key=SKIN_FRICTION_RANGES_KEY, source=Table.CALC),
        Requirement(key=STRUCTURE_RIGIDITY_KEY, source=Table.CALC),
        Requirement(key=WORK_ORDER_KEY, source=Table.CALC),
        Requirement(key=FUTURE_GROUND_LEVEL_KEY, source=Table.CALC),
        Requirement(key=PHREATIC_LEVEL_KEY, source=Table.CALC),
        Requirement("cpts", source=Table.PROJECT),
    ]
    produces: list[Product] = [Product(key=REPORT_MODELLING_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        # 2. Create modelling/calculation chapter
        #   - report software used
        #   - cpts used per pile
        #   - report assumptions with regards to:
        #       - negative skin friction
        #       - influence execution:
        #           - cpt workflow relative to pile installation
        #           - new groundlevel
        #           - installation method of pile (vibrations)
        #       - ...

        # TODO: add pointer references (also see previous chapter)
        # TODO: create table with: cpt, soil profile and skin friction ranges
        # TODO: create table with: pile dimensions and pile factors
        # TODO: add cpts and ksi value pointer and/or table

        # Get the initial table number
        caption_numbers = ctx[CAPTION_NUMBERS_KEY]

        # Add modelling pointers
        modelling_pile_pointers = [""]

        pile_type: PileType = ctx[PILE_TYPE_KEY]
        modelling_pile_pointers.append(
            f"Voor het funderingsontwerp een paal van het paaltype: {pile_type} gebruikt. De aangenomen paalklasse factoren zijn weergegeven in Tabel XXX."
        )

        # Create pile factors table
        caption_numbers.new_table()
        pile_factors_table: ReportTable = _create_pile_factors_table(pile_type=pile_type, table_number=caption_numbers.table)
        
        # Create pointers modelling/calculation pointers
        modelling_soil_profile_pointers: list[str] = []

        # Create cpts and negative skin friction table
        skin_friction_ranges: dict[str, SkinFrictionRanges] = ctx[SKIN_FRICTION_RANGES_KEY]
        
        cpt_ids: list[str] = []
        bottom_nsf: list[str] = []
        top_psf: list[str] = []
        for cpt_id, sfr in skin_friction_ranges.items():
            cpt_ids.append(str(cpt_id))
            bottom_nsf.append(str(sfr.bottom_negative_skin_friction))
            top_psf.append(str(sfr.top_positive_skin_friction))

        # Create table for skin friction ranges
        caption_numbers.new_table()
        skin_friction_table = ReportTable(
            data={
                "sonderingen": cpt_ids,
                "onderkant negatieve kleef [m+NAP]": bottom_nsf,
                "bovenkant schachtwrijving [m+NAP]": top_psf,
            },
            caption="CPT met onderkant van negatieve kleef en positieve ",
            number=caption_numbers.table,
        )
        # Add relevant pointer for cpts and skin friction zones
        modelling_soil_profile_pointers.append(
            "Om de berekening te kunnen maken, zijn de sondering in Tabel XXX gebruikt.Deze sonderingen zijn vertaald naar een stuk paal waar negatieve kleef optreedt en schachtwrijvingsgebied. Deze zijn ook weergegeven in Tabel XXX."
        )

        # Show existing variability pointers set and ask if more should be provided
        modelling_variability_pointers = [""]
        rigid_structure: bool = ctx[STRUCTURE_RIGIDITY_KEY]
        ksi3 = calc_ksi3(
            rigid_construction=rigid_structure, n_cpts=1
        )  # TODO: n_cpts needs to be changed for multiple cpts
        ksi4 = calc_ksi4(
            rigid_construction=rigid_structure, n_cpts=1
        )  # TODO: idem previous line n_cpts

        # Add pointers on what cpts were used
        _used_cpts: str = ""
        used_cpt_id = ctx[CPT_NAME_KEY]
        for cpt_name in [used_cpt_id]:  # TODO: change to list of used cpts in future
            _used_cpts += f"\n\t- {cpt_name}"
        modelling_variability_pointers.append(
            f"For the calculations, the following cpts were used: {_used_cpts} "
        )
        modelling_variability_pointers.append(
            f"The ksi values used are: ksi3 = {ksi3}, ksi4= {ksi4} "
        )

        var_info: str = ""
        for p in modelling_variability_pointers:
            var_info += f"\n\t- {p}"
        print_formatted_text(
            f"Voor het uitvoeren van de funderingsberekening zijn de volgende uitgangspunten gebruikt:{var_info}"
        )

        modelling_variability_pointers.extend(
            _get_pointers(chapter="Modelling - cpts used")
        )

        # Add pointers on environmental factors
        modelling_environmental_factors_pointers = [""]
        cpt_execution_order: TimeOrderType = ctx[WORK_ORDER_KEY]
        modelling_environmental_factors_pointers.append(
            f"De uitvoeringsvolgorde is als volgt: {cpt_execution_order}"
        )

        # Shift in groundlevel --> assumptions reduced cone resistance (if required)
        future_ground_level: float = ctx[FUTURE_GROUND_LEVEL_KEY]
        cpts: list[Cpt] = ctx["cpts"]
        current_ground_levels: list[float] = []
        for cpt in cpts:
            if (
                cpt.id_ == used_cpt_id
            ):  # TODO: in future with multiple cpts -> == becomes 'in'
                current_ground_levels.append(cpt.surface_level)

        STRESS_REDUCTION_WORK_ORDERS = [
            TimeOrderType.CPT_EXCAVATION_INSTALL,
            TimeOrderType.INSTALL_CPT_EXCAVATION,
            TimeOrderType.CPT_INSTALL_EXCAVATION,
        ]
        if cpt_execution_order in STRESS_REDUCTION_WORK_ORDERS:
            if all(cgl <= future_ground_level for cgl in current_ground_levels):
                modelling_environmental_factors_pointers.append(
                    f"Het toekomstige grondniveau is overal hoger dan de huidige situatie. De korrelspanningen worden niet beinvloed."
                )
            elif all(cgl >= future_ground_level for cgl in current_ground_levels):
                modelling_environmental_factors_pointers.append(
                    f"Het toekomstige grondniveau is overal lager dan de huidige situatie. De draagkracht wordt gereduceerd conform het paaltype."
                )
            else:  # some current ground levels are lower, others are higher
                modelling_environmental_factors_pointers.append(
                    f"Het toekomstige grondniveau is voor sommige cpts lager en voor anderen hoger. De draagkracht wordt gereduceerd conform het paaltype waar er ontgraven wordt."
                )
        else:
            modelling_environmental_factors_pointers.append(
                "De cpt is uitgevoerd na ontgraving. De conusweerstanden hoeven dus niet gereduceerd te worden."
            )

        # Add phreatic surface assumption
        groundwater_level = ctx[PHREATIC_LEVEL_KEY]
        modelling_environmental_factors_pointers.append(
            f"De aangehouden grondwaterstand is {groundwater_level} m+NAP"
        )

        # Create LLM prompt input
        modelling_base_line = ReportBaseLineModelling(
            pointers=ModellingPointers(
                soil_profiles=modelling_soil_profile_pointers,
                pile=modelling_pile_pointers,
                variability_information=modelling_variability_pointers,
                environmental_factors=modelling_environmental_factors_pointers,
            ),
            elements=[],
        )
        ctx[REPORT_MODELLING_KEY] = _SectionInput(
            model_input=modelling_base_line,
            elements=[skin_friction_table, pile_factors_table],
        )

class StepResultsChapter(Step):
    name = "Result chapter of pile report"
    requires: list[Requirement] = [
        Requirement(key=PILE_TIP_LEVEL_KEY, source=Table.CALC),
        Requirement(key=CALCULATION_RESULTS_KEY, source=Table.CALC),
        Requirement(key=SLS_LOAD_KEY, source=Table.CALC),
        Requirement(key=ULS_LOAD_KEY, source=Table.CALC),
        Requirement(key=CAPTION_NUMBERS_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [
        Product(key=REPORT_RESULTS_KEY, dest=Table.CALC),
    ]

    def execute(self, ctx: dict[str, Any]) -> None:
        
        # 3. Create results chapter
        #   - Show results of calculations
        #       - bearing capacity
        #       - pile stiffness if required
        #   - Report the results -> bearing capacity vs load -> pile tip level
        #   - ...

        # TODO: create table with design value of bearing capacity: nsf, shaft, tip and total on a given level
        caption_numbers: CaptionNumbers = ctx[CAPTION_NUMBERS_KEY]   

        pile_tip_levels: list[float] = [ctx[PILE_TIP_LEVEL_KEY]]  # TODO: will become multiple levels
        pile_tip_range_pointer = f"Paalpuntniveau's overwogen: {pile_tip_levels} m+NAP"
        bearing_capacity_pointer = "De draagkracht is weergegeven in Tabel XXX"

        # Get results from calculation and make table + plot
        results = ctx[CALCULATION_RESULTS_KEY]
        caption_numbers.new_table() 
        bearing_capacity_table: ReportTable = _create_bearing_capacity_table(results, caption_numbers.table)
        
        # Create figure
        caption_numbers.new_figure()
        fig, ax = plot_bearing_capacity(
            results=results, calculation_name="Draagkracht over diepte"
        )
        bearing_capacity_plot = Plot(
            fig=fig,
            ax=ax,
            caption="Draagkracht (rep.) over de diepte",
            number=caption_numbers.figure,
        )
        
        sls_load: float = ctx[SLS_LOAD_KEY]
        uls_load: float = ctx[ULS_LOAD_KEY]
        pile_tip_level_final: float = ctx[PILE_TIP_LEVEL_KEY]  # m +NAP
        load_pointer = f"De verticale belasting op de paal is {sls_load} kN en {uls_load} kN, respectievelijk de representatieve en ontwerp belasting."  # TODO: get ULS load from database
        pile_tip_level_pointer = f"Gekozen paalpuntniveau voor voldoende draagkracht: {pile_tip_level_final} m+NAP"  # TODO: get from database
        result_pointers = ResultPointers(
            pile_tip_range=pile_tip_range_pointer,
            bearing_capacity=bearing_capacity_pointer,
            load=load_pointer,
            pile_tip_level=pile_tip_level_pointer,
        )
        result_base_line = ReportBaseResults(
            pointers=result_pointers,
            elements=[],
        )
        ctx[REPORT_RESULTS_KEY] = _SectionInput(
            model_input=result_base_line,
            elements=[bearing_capacity_table, bearing_capacity_plot],
        )

class StepIntroductionChapter(Step):
    name = "introduction of pile report"
    requires: list[Requirement] = []
    produces: list[Product] = [Product(key=REPORT_INTRODUCTION_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        # 4. Create introduction chapter
        # TODO: assess if providing all information and let Claude write the introduction is better in future
        introduction_chapter_pointers = _get_pointers("Introductie")
        introduction_base_line = ReportBaseLineIntroduction(
            pointers=introduction_chapter_pointers,
            elements=[],
        )
        ctx[REPORT_INTRODUCTION_KEY] = _SectionInput(model_input=introduction_base_line, elements=[])

class StepConclusionChapter(Step):
    name = "conclusion of pile report"
    requires: list[Requirement] = [Requirement(key=PILE_TYPE_KEY, source=Table.CALC), Requirement(key=PILE_TIP_LEVEL_KEY, source=Table.CALC)]
    produces: list[Product] = [Product(key=REPORT_CONCLUSION_KEY, dest=Table.CALC)]
    
    def execute(self, ctx: dict[str, Any]) -> None:
        
        # 5. Create conclusion chapter
        # TODO: in future, considerations regarding:
        #   - add short summary on geology
        #   - add rationale why foundation is chosen
        #   - add extrapolation on settlements
        #   - excecution aspects
        #   - possible liability shortcomings should be noted here!

        # N.B.: probably best to ask these before starting the calculation to guide the user!
        conclusion_chapter_pointers = _get_pointers("Conclusie")
        conclusion_chapter_pointers.append(f"Paalsysteem gekozen: {ctx[PILE_TYPE_KEY]}")
        conclusion_chapter_pointers.append(
            f"Paalpuntniveau gekozen: {ctx[PILE_TIP_LEVEL_KEY]}"
        )
        conclusion_base_line = ReportBaseLineConclusion(
            pointers=conclusion_chapter_pointers,
            elements=[],
        )
        ctx[REPORT_CONCLUSION_KEY] = _SectionInput(model_input=conclusion_base_line, elements=[])

class StepCreateReport(Step):
    name = "Build pile foundation report"
    requires: list[Requirement] = [
        Requirement(key=REPORT_SI_KEY, source=Table.CALC),
        Requirement(key=REPORT_ASSUMPTIONS_KEY, source=Table.CALC),
        Requirement(key=REPORT_MODELLING_KEY, source=Table.CALC),
        Requirement(key=REPORT_RESULTS_KEY, source=Table.CALC),
        Requirement(key=REPORT_INTRODUCTION_KEY, source=Table.CALC),
        Requirement(key=REPORT_CONCLUSION_KEY, source=Table.CALC),
    ]
    produces: list[Product] = [Product(key=REPORT_KEY, dest=Table.CALC)]

    def execute(self, ctx: dict[str, Any]) -> None:
        section_inputs: list[_SectionInput] = list(ctx.values()) # all values in the ctx are section input

        # TODO: assess if in future, there should be while loops over every chapter + user can add pointers based on output of model
        # 1. Create all text using LLM calls and user defined input
        # 2. Parse Section objects from the llm generated text (string)
        texts: list[str] = []
        sections: list[Section] = []
        for section_input in section_inputs:
            text = _llm_text_generation_router(section_input)
            texts.append(text)
            sections.append(
                markdown_to_section(chapter=text, elements=section_input.elements)
            )

        # Create the Latex document
        # Instantiate Latex document
        doc = Document()

        # TODO: add metadata input query
        doc.preamble.append(Command("title", "Awesome Title"))
        doc.preamble.append(Command("author", "Anonymous author"))
        doc.preamble.append(Command("date", NoEscape(r"\today")))

        # Add all sections to Latex document
        for section in sections:
            section.to_doc(doc)

        # Dump document
        doc.generate_pdf("report", clean_tex=False)  # TODO: add report to DB(?)
        ctx[REPORT_KEY] = doc

def _llm_text_generation_router(section_input: _SectionInput) -> str:
    if isinstance(section_input.model_input, ReportBaseLineIntroduction):
        return b.FoundationDesignIntroductionReporter(section_input.to_llm_input())
    elif isinstance(section_input.model_input, ReportBaseLineSoilInvestigation):
        return b.FoundationDesignSoilInvestigationReporter(section_input.to_llm_input())
    elif isinstance(section_input.model_input, ReportBaseLineAssumptions):
        return b.FoundationDesignAssumptionsReporter(section_input.to_llm_input())
    elif isinstance(section_input.model_input, ReportBaseLineModelling):
        return b.FoundationDesignModellingReporter(section_input.to_llm_input())
    elif isinstance(section_input.model_input, ReportBaseResults):
        return b.FoundationDesignResultsReporter(section_input.to_llm_input())
    elif isinstance(section_input.model_input, ReportBaseLineConclusion):
        return b.FoundationDesignConclusionReporter(section_input.to_llm_input())
    else:
        raise ValueError(
            f"The section_input argument is not of the object type that can be handled, but: {type(section_input)}"
        )


PILE_REPORTING_STEPS = [
    StepSoilInvestigationChapter,
    StepAssumptionsChapter,
    StepModellingChapter,
    StepResultsChapter,
    StepIntroductionChapter,
    StepConclusionChapter,
    StepCreateReport,
]

# ====================================================================================

def _create_pile_factors_table(pile_type: PileType, table_number: int) -> ReportTable:

    # TODO: validate the pile class factors with NEN9997-1
    if pile_type == PileType.BUISSCHROEFPAAL:
        alpha_p = 0.63
        alpha_s = 0.006
        a = 1
        b = 1
    elif pile_type == PileType.BUISSCHROEFPAAL_VERLOREN_CASING:
        alpha_p = 0.63
        alpha_s = 0.006
        a = 1
        b = 1
    elif pile_type == PileType.PREFAB_HEIPAAL:
        alpha_p = 0.7
        alpha_s = 0.01
        a = 1
        b = 1
    elif pile_type == PileType.SCHROEFPAAL:
        alpha_p = 0.3
        alpha_s = 0.006
        a = 1
        b = 1
    elif pile_type == PileType.VIBROPAAL:
        alpha_p = 0.6
        alpha_s = 0.012
        a = 0.9
        b = 1
    else:
        raise NotImplementedError(f"The piletype: {pile_type} is not implemented!")
    table = ReportTable(
        data={
            "alpha_p": [str(alpha_p)],
            "alpha_s": [str(alpha_s)],
            "a": [str(a)],
            "b": [str(b)],
        },
        caption="Paalafmetingen en model factoren volgens NEN9997-1",
        number=table_number,
    )
    table_number += 1
    return table


def _get_pointers(chapter: str) -> list[str]:
    pointers: list[str] = []
    more_pointers = True
    print_formatted_text(f"Geef alle uitgangspunten voor de `{chapter}` paragraaf")
    while more_pointers:
        pointer = prompt(f"{chapter} uitgangspunt: ")
        pointers.append(pointer)
        more_pointers = confirm("Wil je nog een uitgangspunt toevoegen?")
    return pointers


def _create_params_table(params: list[PileFoundationParams], table_number: int) -> ReportTable:

    """From list of params from the DB, makes a Table object"""
    _attribute_name_map: list[tuple[str, str]] = [
        ("soil", "Grondsoort"),
        ("gamma_nat", "Natuurlijk vol. gewicht [kN/m3]"),
        ("gamma_sat", "Verzadigd vol. gewicht [kN/m3]"),
        ("friction_angle", "Wrijvingshoek [graden]"),
    ]
    data: dict[str, list[str]] = {}
    for attribute_name, table_name in _attribute_name_map:
        d: list[str] = []
        for soil in params:
            attr = getattr(soil, attribute_name)
            if isinstance(attr, float):
                attr = round(attr, 1)
            d.append(str(attr))
        data[table_name] = d
    table = ReportTable(data=data, caption="Grondparameters", number=table_number)
    return table


def _create_bearing_capacity_table(results: PileResults, table_number: int) -> ReportTable:
    ptl_col: str = "PPN [m+NAP]"
    shaft_col: str = "Schachtwrijving (rep) [kN]"
    tip_col: str = "Draagkracht punt (rep) [kN]"
    nsf_col: str = "Negatieve kleef (rep) [kN]"
    rep_bc_col: str = "Totale draagkracht (rep) [kN]"
    design_bc_col: str = "Totale draagkracht (ontwerp) [kN]"

    data: dict[str, list[str]] = {
        ptl_col: [],
        shaft_col: [],
        tip_col: [],
        nsf_col: [],
        rep_bc_col: [],
        design_bc_col: [],
    }

    for result in results.results:
        data[ptl_col].append(str(round(result.tip_level, 2)))
        data[shaft_col].append(str(round(result.bc_shaft_rep, 1)))
        data[tip_col].append(str(round(result.bc_tip_rep, 1)))
        data[nsf_col].append(str(round(result.nsf_rep, 1)))
        data[rep_bc_col].append(str(round(result.rep_bearing_capacity, 1)))
        data[design_bc_col].append(str(round(result.design_bearing_capacity, 1)))

    table = ReportTable(data=data, caption="Draagkracht per PPN", number=table_number)
    table_number += 1
    return table



