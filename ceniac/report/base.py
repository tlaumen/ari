from dataclasses import dataclass
from dataclasses import field

from ..calculate.base import Calculation


@dataclass
class Chapter:
    """Class representing smaller parts of a report"""

    name: str
    template: list[str]

    def fill(self) -> str:
        chapter = f"## {self.name}\n"
        for t in self.template:
            chapter += t + "\n"
        return chapter


@dataclass
class ReportTemplateBase:
    """This is the generic implementation of a report template"""

    name: str
    chapters: list[Chapter]

    def _fill_chapters(self):
        """Abstract representation of the method to fill the chapter templates"""
        raise NotImplementedError(
            "_fill_chapters method is not a concrete implementation"
        )

    def report(self, calculation: Calculation) -> str:
        """Abstract representation of the method to report the results"""
        raise NotImplementedError("report method is not a concrete implementation")


def create_pile_foundation_report() -> list[Chapter]:
    """Creates a pile foundation report"""
    return [
        Chapter(name="Introductie", template=["Dit is de introductie"]),
        Chapter(
            name="Grondonderzoek", template=["Dit is het hoofdstuk over grondonderzoek"]
        ),
        Chapter(
            name="Uitgangspunten",
            template=["Dit is het hoofdstuk over de gemaakte aannames"],
        ),
        Chapter(
            name="Berekening", template=["Dit is het hoofdstuk over de berekening"]
        ),
        Chapter(name="Conclusie", template=["Dit is de conclusie"]),
    ]


class PileFoundationReport(ReportTemplateBase):
    """The concrete implementation of a report for a pile foundation design"""

    chapters: list[Chapter] = field(default_factory=create_pile_foundation_report)

    def _fill_chapters(self):
        """Fill all chapters based on the performed calculation. This private method is used to call the report method"""
        pass

    def report(self, calculation: Calculation) -> str:
        """Based on all chapters and there respective data, the report is created by writing all chapter"""
        s = ""
        for c in self.chapters:
            s += c.fill()
        return s
