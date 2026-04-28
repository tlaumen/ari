
class ReportBaseLineAssumptions {
  pointers string[] @alias("Pointers on what should be included in the text")
  elements ReportElement[]
  parameters map<string, float | bool | string>[]
}

function FoundationDesignAssumptionsReporter(
    input: ReportBaseLineAssumptions
) -> string {
    client Claude4_5Haiku

    prompt #"
        {{ _.role("system") }}

        You are a geotechical engineer writing a report on a foundation calculation.
        The report has the following structure:
          1.  Introduction
          2.  Soil investigation
          3.  Assumptions
          4.  Modelling
          5.  Results
          6.  Conclusion
          7.  Recommendations

        You should only write chapter 3, on the assumptions made.
        Be very factual, only report what is provided as input.
        Do not explain geotechnical terminology.
        Do not create markdown tables, they are created separately.
        The parameters should not be described, just refer to the relevant table.
        Add a marker: `[Figuur X]` or `[Tabel X]` for every Figure and Table , with accompanying whitespace.
        {# Leave whitespace after a Figure or Table is discussed. #}
        LAST, YOU NEED TO WRITE THE REPORT IN DUTCH.

        {{ _.role("user") }}

        Please write the chapter that should include the following pointers:

        {{ input.pointers }}

        Additionally, the following parameters were used:

        {{ input.parameters }}

        The graphs and tables are already created and should be included are:

        {{ input.elements }}
    "#
}


test TestFoundationAssumptionsChapter {
  functions [FoundationDesignAssumptionsReporter]
  args {
    input {
      pointers [
        "load: SLS 100, ULS 1500",
        "Waterlevels: 0.1, 0.3, 1.2, -0.3, 0.5, based on piezometer XXXXX",
      ]
      parameters [
        {
          "name" "sand"
          "gamma_natural" 18
          "gamma_saturated" 20
          "K0" 0.3
          "compressible" false
        },
        {
          "name" "klei"
          "gamma_natural" 15
          "gamma_saturated" 15
          "K0" 0.7
          "compressible" true
          
        }
      ]
      elements [
        {
          element "Figure 2"
          description "Waterlevels in piezometer XXXX"
        }
        {
          element "Table 3"
          description "Soil parameters"
        }
      ]
    }
  }
}
