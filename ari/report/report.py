from dataclasses import dataclass
from itertools import pairwise
import re

from pylatex import Command, Document, Table
from pylatex import Section as PyLatexSection
from pylatex import Subsection as PyLatexSubsection

from baml_client.types import (
    ReportBaseLineAssumptions,
    ReportBaseLineConclusion,
    ReportBaseLineIntroduction,
    ReportBaseLineSoilInvestigation,
    ReportBaseLineModelling,
    ReportBaseResults,
)
from baml_client.types import ReportElement
from ari.report.table import Table
from ari.report.plot import Plot

_PILE_MODEL_CHAPTER_INPUT = (
    ReportBaseLineIntroduction
    | ReportBaseLineSoilInvestigation
    | ReportBaseLineAssumptions
    | ReportBaseLineModelling
    | ReportBaseResults
    | ReportBaseLineConclusion
)

@dataclass
class CaptionNumbers:
    table: int | None  = None
    figure: int | None = None

    def new_table(self):
        if self.table is None:
            self.table = 1
        else:
            self.table += 1

    def new_figure(self):
        if self.figure is None:
            self.figure = 1
        else:
            self.figure += 1


@dataclass
class _SectionInput:
    model_input: _PILE_MODEL_CHAPTER_INPUT  # input for the BAML function
    elements: list[Table | Plot]  # all non-text elements in the report

    def to_llm_input(self) -> _PILE_MODEL_CHAPTER_INPUT:
        if len(self.model_input.elements) != 0:
            raise ValueError(
                f"Something has gone wrong. The elements on the llm input should ONLY be filled in automtically. This should be empty currently. However, it contains: {self.model_input.elements}"
            )
        _elements: list[ReportElement] = []
        for element in self.elements:
            if isinstance(element, Table):
                name = f"Tabel {element.number}"
            elif isinstance(element, Plot):
                name = f"Figuur {element.number}"
            else:
                raise ValueError(
                    f"An element in the _SectionInput is not of type Table or Plot but of type: {type(element)}. This is not implemented."
                )
            _elements.append(ReportElement(element=name, description=element.caption))
        self.model_input.elements = _elements
        return self.model_input


@dataclass
class SubSection:
    title: str
    text: list[str]
    line_element_map: dict[int, Plot | Table]

    def to_doc(self, doc: Document):
        sanitized_text: list[str] = [sanitize_for_latex(line) for line in self.text]
        # find_element_line()
        with doc.create(PyLatexSubsection(self.title)):
            for line in sanitized_text:
                doc.append(line)


@dataclass
class Section:
    title: str
    sub_sections: list[SubSection]  # if present
    text: list[
        str
    ]  # (introductory) text, in case of SubSections before the SubSections start
    line_element_map: dict[int, Table | Plot]  # only in self.text

    def to_doc(self, doc: Document):
        sanitized_text: list[str] = [sanitize_for_latex(line) for line in self.text]
        # find_element_line()
        with doc.create(PyLatexSection(self.title)):
            for line in sanitized_text:
                doc.append(line)
            for subsection in self.sub_sections:
                subsection.to_doc(doc)

    def get_all_elements(self) -> list[Plot | Table]:
        elements: list[Plot | Table] = list(self.line_element_map.values())
        for subsection in self.sub_sections:
            elements.extend(list(subsection.line_element_map.values()))
        return elements


def markdown_to_section(chapter: str, elements: list[Plot | Table]) -> Section:
    """
    Chapter is the text written by the language model, elements is a mapping of the name of an element and the ReportElement itself
    """
    _chapter: str = chapter.strip()
    lines = _chapter.split("\n")
    section_starts: list[int] = []
    sub_section_starts: list[int] = []
    for i, line in enumerate(lines):
        if line.startswith("# "):
            section_starts.append(i)
        elif line.startswith("## "):
            sub_section_starts.append(i)

    # Validation
    if len(section_starts) != 1:
        raise ValueError(
            f"Something strange happened! The section starts found are in lines: {section_starts}. The current implementation of the logic only permits 1."
        )
    if section_starts[0] != 0:
        raise ValueError(
            "The markdown_to_section function assumes the input string starts at a 'new' section"
        )

    # Extract sub sections
    START_TITLE_SECTION = (
        5  # from the 5th character, before it is '# 1. ' with 1 arbitrarily chosen
    )
    START_TITLE_SUBSECTION = (
        7  # from the 7th character, before it is '## 1.1 ' with 1.1 arbitrarily chosen
    )

    def extract_subsection(line_start: int, line_end: int | None = None) -> SubSection:
        """Get subsection from text. When line_end is None, take text to end of lines"""
        # Get text
        text: list[str] = (
            lines[line_start + 1 : line_end]
            if line_end is not None
            else lines[line_start + 1 :]
        )
        line_element_map = extract_line_element_map_from_text(
            text=text, elements=elements
        )
        return SubSection(
            title=lines[line_start][START_TITLE_SUBSECTION:],
            text=text,
            line_element_map=line_element_map,
        )

    # Flat chapter with only Section and text, no subsections
    if len(sub_section_starts) == 0:
        text: list[str] = lines[1:]
        line_element_map = extract_line_element_map_from_text(
            text=text, elements=elements
        )
        section = Section(
            title=lines[0][START_TITLE_SECTION:],
            text=text,
            sub_sections=[],
            line_element_map=line_element_map,
        )
        if not _validate_all_elements_found(
            required_elements=elements, found_elements=section.get_all_elements()
        ):
            raise ValueError(
                f"Not all elements required were found in the created text. Required elements: {[e.name for e in elements]}, found elements: {section.get_all_elements()}"
            )
        return section
    # Only 1 sub section in the chapter
    if len(sub_section_starts) == 1:
        line_start_subsection: int = sub_section_starts[0]
        text_section: list[str] = lines[1:line_start_subsection]
        line_element_map = extract_line_element_map_from_text(
            text=text_section, elements=elements
        )  # only for the Section, not the SubSection
        section = Section(
            title=lines[0][START_TITLE_SECTION:],
            text=text_section,
            sub_sections=[extract_subsection(line_start=line_start_subsection)],
            line_element_map=line_element_map,
        )
        if not _validate_all_elements_found(
            required_elements=elements, found_elements=section.get_all_elements()
        ):
            raise ValueError(
                f"Not all elements required were found in the created text. Required elements: {[e.name for e in elements]}, found elements: {section.get_all_elements()}"
            )
        return section

    # Get sub sections from text -> multiple subsections
    sub_sections: list[SubSection] = []
    for start, end in pairwise(sub_section_starts):
        sub_sections.append(extract_subsection(line_start=start, line_end=end))
    sub_sections.append(extract_subsection(line_start=sub_section_starts[-1]))

    # Extract elements
    text: list[str] = lines[1 : sub_section_starts[0]]
    line_element_map = extract_line_element_map_from_text(
        text=text, elements=elements
    )  # only for the Section, not the SubSection
    section = Section(
        title=lines[0][START_TITLE_SECTION:],
        text=text,
        sub_sections=sub_sections,
        line_element_map=line_element_map,
    )
    if not _validate_all_elements_found(
        required_elements=elements, found_elements=section.get_all_elements()
    ):
        raise ValueError(
            f"Not all elements required were found in the created text. Required elements: {[e.name for e in elements]}, found elements: {section.get_all_elements()}"
        )
    return section


def find_element_line(text: list[str], element_name: str) -> int:
    """Finds element (Figuur or Tabel) in text and returns its line number"""
    for idx, line in enumerate(text):
        if line.strip() == f"[{element_name}]":
            return idx
    raise ValueError(f"Could not find: {element_name}")


def extract_line_element_map_from_text(
    text: list[str], elements: list[Plot | Table]
) -> dict[int, Plot | Table]:
    """"""
    # Get report elements
    line_element_map: dict[int, Plot | Table] = {}
    for element in elements:
        try:
            line_number = find_element_line(text=text, element_name=element.name)
            line_element_map[line_number] = element
        except ValueError:
            pass  # TODO: assess how to handle this callflow in a better way
    return line_element_map


def _validate_all_elements_found(
    required_elements: list[Plot | Table], found_elements: list[Plot | Table]
) -> bool:
    for element in required_elements:
        if element not in found_elements:
            return False
    return True


def sanitize_for_latex(text: str) -> str:
    """Convert Unicode subscripts/superscripts to LaTeX commands"""

    # Subscript mapping
    subscripts = {
        "₀": r"$_0$",
        "₁": r"$_1$",
        "₂": r"$_2$",
        "₃": r"$_3$",
        "₄": r"$_4$",
        "₅": r"$_5$",
        "₆": r"$_6$",
        "₇": r"$_7$",
        "₈": r"$_8$",
        "₉": r"$_9$",
        "₊": r"$_+$",
        "₋": r"$_-$",
        "₌": r"$_=$",
        "₍": r"$_($",
        "₎": r"$_)$",
    }

    # Superscript mapping
    superscripts = {
        "⁰": r"$^0$",
        "¹": r"$^1$",
        "²": r"$^2$",
        "³": r"$^3$",
        "⁴": r"$^4$",
        "⁵": r"$^5$",
        "⁶": r"$^6$",
        "⁷": r"$^7$",
        "⁸": r"$^8$",
        "⁹": r"$^9$",
        "⁺": r"$^+$",
        "⁻": r"$^-$",
        "⁼": r"$^=$",
        "⁽": r"$^($",
        "⁾": r"$^)$",
    }

    # Replace subscripts
    for unicode_char, latex_cmd in subscripts.items():
        text = text.replace(unicode_char, latex_cmd)

    # Replace superscripts
    for unicode_char, latex_cmd in superscripts.items():
        text = text.replace(unicode_char, latex_cmd)

    # Escape other LaTeX special characters
    special_chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    # Note: Only escape these if they're not already part of LaTeX commands
    # You may need more sophisticated logic here

    return text
