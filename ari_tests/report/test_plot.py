from pylatex import Document, Package
import matplotlib.pyplot as plt
import matplotlib

from ari.report.plot import Plot


def test_plot():
    doc = Document()
    doc.packages.append(Package("tikz"))  # Changed from 'pgf' to 'tikz'
    doc.packages.append(Package("xcolor"))
    doc.packages.append(Package("caption"))

    fig, ax = plt.subplots()
    ax.plot(range(1, 10), range(2, 20, 2), color="m")
    ax.grid()
    # fig.tight_layout()
    fig2, ax2 = plt.subplots()
    ax2.plot(range(1, 10), range(2, 20, 2), color="g")
    ax2.grid()

    plot = Plot(fig=fig, ax=ax, caption="very beautiful test plot", number=1)
    plot.to_latex(doc=doc)
    plot = Plot(fig=fig2, ax=ax2, caption="very beautiful test plot 2", number=2)
    plot.to_latex(doc=doc)
    doc.generate_pdf("test_plot", clean_tex=False)
