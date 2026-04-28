import tempfile

from pylatex import Document
from pylatex import Figure as LatexFigure
from pylatex import NoEscape
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes


class Plot:
    """Plot object to add a plot with caption to the report"""

    def __init__(self, fig: Figure, ax: Axes, caption: str, number: int):
        self.number = number
        self.fig = fig
        self.ax = ax
        self.caption = caption

    @property
    def name(self) -> str:
        return f"Figuur {self.number}"

    def to_latex(self, doc: Document):
        # Create temporary file for plot to add to Latex
        # N.B.: it seems this file needs to exists until the .pdf is created thus it cannot be deleted
        #       deleting will happen automatically at the end of runtime
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", mode="wb", delete=False
        ) as temp_file:
            self.fig.savefig(temp_file)
            temp_path = temp_file.name

        # Add to Figure environment
        # TODO: improve formatting plot (as side alligned?)
        with doc.create(LatexFigure(position="h!")) as plot:
            plot.add_image(temp_path)
            plot.add_caption(self.caption)

        plt.close(self.fig)
