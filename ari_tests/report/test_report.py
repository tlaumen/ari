import pytest
from pylatex import Command, NoEscape, Document

from ari.report.report import Section, find_element_line, markdown_to_section
from ari.report.plot import Plot
from ari.report.table import Table


@pytest.mark.auto
def test_markdown_to_section_multi_subsection():
    llm_output = "# 4. Modelling\n\n## 4.1 Soil Profiles\n\nThe soil profiles are interpreted based on simple qc and rf rules. The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer. Each soil profile is linked to its corresponding CPT location. The depth at which negative skin friction transitions to positive skin friction is presented in Tabel 4.\n\n[Tabel 4]\n\n## 4.2 Pile Characteristics\n\nThe pile used is a Fundex pile with a tip diameter of 450 mm and a shaft diameter of 400 mm. For the calculation model, the shaft diameter is assumed to be half of both the tip and shaft diameter.\n\nThe pile dimensions and corresponding model factors in accordance with NEN9997-1 are presented in Tabel 5.\n\n[Tabel 5]\n\n## 4.3 Variability and Spatial Coverage\n\nThe CPTs used per pile are provided in Tabel 6. In accordance with the Eurocode, every pile should be covered from all wind directions. This spatial coverage is verified and presented in the accompanying table.\n\nThe construction is rigid, resulting in ksi values in accordance with NEN9997-1 table XXXX. Provided the number of CPTs used per pile covering the foundation, the ksi values are presented in Tabel 6.\n\n[Tabel 6]\n\n## 4.4 Environmental Factors\n\nThe CPTs were performed before excavation and installation of the piles. The future ground level will be at xxx, which means a decrease of the cone resistance due to the reduction of effective stresses.\n\nPhreatic water levels of 0.1 m, 0.3 m, 1.2 m, -0.3 m, and 0.5 m were recorded based on piezometer XXXXX. These water levels are incorporated in the calculation model."
    elements: list[Plot | Table] = [
        Table(data={"test": ["1"]}, caption="", number=4),
        Table(data={"test": ["1"]}, caption="", number=5),
        Table(data={"test": ["1"]}, caption="", number=6),
    ]
    section = markdown_to_section(llm_output, elements)
    assert isinstance(section, Section)

    # Check error is raised when not validated!
    elements.append(
        Table(data={"test": ["1"]}, caption="", number=7),
    )
    with pytest.raises(ValueError):
        _ = markdown_to_section(llm_output, elements)


@pytest.mark.auto
def test_markdown_to_section_single_subsection():
    llm_output = "# 4. Modelling\n\n## 4.1 Soil Profiles\n\nThe soil profiles are interpreted based on simple qc and rf rules. The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer. Each soil profile is linked to its corresponding CPT location. The depth at which negative skin friction transitions to positive skin friction is presented in Tabel 4.\n\n[Tabel 4]"
    elements: list[Plot | Table] = [
        Table(data={"test": ["1"]}, caption="", number=4),
    ]
    section = markdown_to_section(llm_output, elements)
    assert isinstance(section, Section)

    # Check error is raised when not validated!
    elements.append(
        Table(data={"test": ["1"]}, caption="", number=7),
    )
    with pytest.raises(ValueError):
        _ = markdown_to_section(llm_output, elements)


@pytest.mark.auto
def test_markdown_to_section_no_subsection():
    llm_output = "# 4. Modelling\n\nThe soil profiles are interpreted based on simple qc and rf rules. The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer. Each soil profile is linked to its corresponding CPT location. The depth at which negative skin friction transitions to positive skin friction is presented in Tabel 4.\n\n[Tabel 4]"
    elements: list[Plot | Table] = [
        Table(data={"test": ["1"]}, caption="", number=4),
    ]
    section = markdown_to_section(llm_output, elements)
    assert isinstance(section, Section)

    # Check error is raised when not validated!
    elements.append(
        Table(data={"test": ["1"]}, caption="", number=7),
    )
    with pytest.raises(ValueError):
        _ = markdown_to_section(llm_output, elements)


@pytest.mark.auto
def test_section_to_latex():
    # Document with `\maketitle` command activated
    doc = Document()

    doc.preamble.append(Command("title", "Awesome Title"))
    doc.preamble.append(Command("author", "Anonymous author"))
    doc.preamble.append(Command("date", NoEscape(r"\today")))

    llm_output = "# 4. Modelling\n\n## 4.1 Soil Profiles\n\nThe soil profiles are interpreted based on simple qc and rf rules. The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer. Each soil profile is linked to its corresponding CPT location. The depth at which negative skin friction transitions to positive skin friction is presented in Tabel 4.\n\n[Tabel 4]\n\n## 4.2 Pile Characteristics\n\nThe pile used is a Fundex pile with a tip diameter of 450 mm and a shaft diameter of 400 mm. For the calculation model, the shaft diameter is assumed to be half of both the tip and shaft diameter.\n\nThe pile dimensions and corresponding model factors in accordance with NEN9997-1 are presented in Tabel 5.\n\n[Tabel 5]\n\n## 4.3 Variability and Spatial Coverage\n\nThe CPTs used per pile are provided in Tabel 6. In accordance with the Eurocode, every pile should be covered from all wind directions. This spatial coverage is verified and presented in the accompanying table.\n\nThe construction is rigid, resulting in ksi values in accordance with NEN9997-1 table XXXX. Provided the number of CPTs used per pile covering the foundation, the ksi values are presented in Tabel 6.\n\n[Tabel 6]\n\n## 4.4 Environmental Factors\n\nThe CPTs were performed before excavation and installation of the piles. The future ground level will be at xxx, which means a decrease of the cone resistance due to the reduction of effective stresses.\n\nPhreatic water levels of 0.1 m, 0.3 m, 1.2 m, -0.3 m, and 0.5 m were recorded based on piezometer XXXXX. These water levels are incorporated in the calculation model."
    elements: list[Plot | Table] = [
        Table(data={"test": ["1"]}, caption="", number=4),
        Table(data={"test": ["1"]}, caption="", number=5),
        Table(data={"test": ["1"]}, caption="", number=6),
    ]
    section = markdown_to_section(llm_output, elements)
    section.to_doc(doc)
    doc.generate_pdf("test_report")


@pytest.mark.auto
def test_find_element_line():
    llm_output = "# 4. Modelling\n\n## 4.1 Soil Profiles\n\nThe soil profiles are interpreted based on simple qc and rf rules. The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer. Each soil profile is linked to its corresponding CPT location. The depth at which negative skin friction transitions to positive skin friction is presented in Tabel 4.\n\n[Tabel 4]\n\n## 4.2 Pile Characteristics\n\nThe pile used is a Fundex pile with a tip diameter of 450 mm and a shaft diameter of 400 mm. For the calculation model, the shaft diameter is assumed to be half of both the tip and shaft diameter.\n\nThe pile dimensions and corresponding model factors in accordance with NEN9997-1 are presented in Tabel 5.\n\n[Tabel 5]\n\n## 4.3 Variability and Spatial Coverage\n\nThe CPTs used per pile are provided in Tabel 6. In accordance with the Eurocode, every pile should be covered from all wind directions. This spatial coverage is verified and presented in the accompanying table.\n\nThe construction is rigid, resulting in ksi values in accordance with NEN9997-1 table XXXX. Provided the number of CPTs used per pile covering the foundation, the ksi values are presented in Tabel 6.\n\n[Tabel 6]\n\n## 4.4 Environmental Factors\n\nThe CPTs were performed before excavation and installation of the piles. The future ground level will be at xxx, which means a decrease of the cone resistance due to the reduction of effective stresses.\n\nPhreatic water levels of 0.1 m, 0.3 m, 1.2 m, -0.3 m, and 0.5 m were recorded based on piezometer XXXXX. These water levels are incorporated in the calculation model."
    text: list[str] = list(llm_output.split("\n"))
    assert find_element_line(text=text, element_name="Tabel 4") == 6
    assert find_element_line(text=text, element_name="Tabel 5") == 14
    assert find_element_line(text=text, element_name="Tabel 6") == 22
