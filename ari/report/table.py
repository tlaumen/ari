from pylatex import Document, FlushLeft, NoEscape
from pylatex import Table as LaTexTable
from pylatex import Tabu
from pylatex.utils import bold
from pylatex import FlushLeft


class Table:
    """Generic table object to translate data to a table in a report/figure"""

    def __init__(self, data: dict[str, list[str]], caption: str, number: int):
        """
        Instantiates table object with data. Data is a dictionary of from {<column header>: [<data>, ...]}.
        All columns should be of equal length and all data should be of type str.
        """
        # Validate input
        if not all(isinstance(h, str) for h in data):
            raise ValueError(
                "All headers (keys) in the Table object should be of type string"
            )
        for header, col in data.items():
            if not all(isinstance(d, str) for d in col):
                raise ValueError(
                    f"Not all data in header: {header} is a string. This should be the case!"
                )

        # Check all columns have the same length
        length_first_column = len(list(data.values())[0])
        if not all(length_first_column == len(d) for d in data.values()):
            raise ValueError("Not all columns of the table have the same length!")

        self.data = data
        self.caption = caption
        self._n_rows = length_first_column
        self.number = number

    @property
    def name(self) -> str:
        return f"Tabel {self.number}"

    @property
    def headers(self) -> list[str]:
        return list(self.data.keys())

    def _transpose_data(self) -> list[list[str]]:
        rows: list[list[str]] = []
        headers: tuple[str, ...] = tuple(self.data.keys())
        for i in range(self._n_rows):
            row: list[str] = []
            for header in headers:
                row.append(self.data[header][i])
            rows.append(row)
        return rows

    def to_latex(self, doc: Document):
        rows: list[list[str]] = self._transpose_data()
        with doc.create(LaTexTable(position="htbp")) as table:
            table.add_caption(self.caption)  # Caption centered on page
            with doc.create(Tabu("|c|c|")) as tabu:  # Table centered to left
                tabu.add_hline()
                tabu.add_row([bold(header) for header in self.data.keys()])
                tabu.add_hline()
                for row in rows:
                    tabu.add_row(row)
                    tabu.add_hline()
