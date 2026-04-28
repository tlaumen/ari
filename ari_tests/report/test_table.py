import pytest

from ari.report.table import Table


def test_table_instantiation():
    t = Table(
        data={
            "column1": ["1", "2", "3", "4"],
            "column2": ["a", "b", "c", "d"],
        },
        caption="test table",
        number=1,
    )
    assert isinstance(t, Table)


def test_table_no_string_validation_error():
    # Header is not string
    with pytest.raises(ValueError):
        t = Table(
            data={
                1: ["1", "2", "3", "4"],  # pyright: ignore
                "column2": ["a", "b", "c", "d"],
            },
            caption="test table",
            number=1,
        )

    # Datapoint is not string
    with pytest.raises(ValueError):
        t = Table(
            data={
                "column1": [1, "2", "3", "4"],  # pyright: ignore
                "column2": ["a", "b", "c", "d"],
            },
            caption="test table",
            number=1,
        )


def test_table_data_different_lengths_validation_error():
    with pytest.raises(ValueError):
        t = Table(
            data={
                "column1": ["1", "2", "3"],
                "column2": ["a", "b", "c", "d"],
            },
            caption="test table",
            number=1,
        )


def test_to_latex():
    from pylatex import Document

    geometry_options = {"margin": "2.54cm", "includeheadfoot": True}
    doc = Document(page_numbers=True, geometry_options=geometry_options)

    t = Table(
        data={
            "column1": ["1", "2", "3", "4"],
            "column2": ["a", "b", "c", "d"],
        },
        caption="test table",
        number=1,
    )
    t.to_latex(doc)

    doc.generate_pdf("test_table", clean_tex=False)


def test_transpose_data():
    t = Table(
        data={
            "column1": ["1", "2", "3", "4"],
            "column2": ["a", "b", "c", "d"],
        },
        caption="test table",
        number=1,
    )
    assert t._transpose_data() == [["1", "a"], ["2", "b"], ["3", "c"], ["4", "d"]]
