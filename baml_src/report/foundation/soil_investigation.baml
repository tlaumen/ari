
class ReportElement {
  element string @alias("name and number of the graph or table")
  description string
}

class ReportBaseLineSoilInvestigation {
  pointers string[] @alias("Pointers on what should be included in the text")
  elements ReportElement[]
}

function FoundationDesignSoilInvestigationReporter(
    input: ReportBaseLineSoilInvestigation
) -> string {
    client Claude4_5Haiku

    prompt #"
        {{ _.role("system") }}

        You are a geotechical engineer writing a report on a foundation calculation.
        The report has the following structure:
          1.  Introduction
          2.  Soil investigation
          3.  Parameters
          4.  Modelling
          5.  Results
          6.  Conclusion
          7.  Recommendations

        You should only write chapter 2, on soil investigation.
        Be very factual, only report what is provided as input.
        Do not add sub paragraphs.
        Do not explain geotechnical terminology.
        Add a marker: `[Figuur X]` or `[Tabel X]` for every Figure and Table , with accompanying whitespace.
        {# Leave whitespace after a Figure or Table is discussed. Only add the Table or Figure and its number, not the caption. #}
        LAST, YOU NEED TO WRITE THE REPORT IN DUTCH.

        {{ _.role("user") }}
        
        Please write the chapter that should include the following pointers:

        {{ input}}

        The graphs and tables are already created and should be included are:

    "#
}


test TestFoundationSoilInvestigationChapter {
  functions [FoundationDesignSoilInvestigationReporter]
  args {
    input {
      pointers [
        "It is a foundation design near Rotterdam Central station."
      ]
      elements [
        {
          element "Figure 1"
          description "Toplevel overview of the cpts and boreholes"
        }
        {
          element "Table 1"
          description "All cpts present in the viscinity of the foundation"
        }
      ]
    }
  }
}
