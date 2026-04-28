class ResultPointers {
  pile_tip_range string
  bearing_capacity string
  load string // ULS load
  pile_tip_level string
}


class ReportBaseResults {
  pointers ResultPointers @alias("Pointers on what should be included in the text")
  elements ReportElement[]
}

function FoundationDesignResultsReporter(
    input: ReportBaseResults
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

        You should only write chapter 5, on the results of the calculation.
        Be very factual, only report what is provided as input.
        Do not explain geotechnical terminology.
        Explicitly link the ULS load to the design capacity and denote it is sufficient if so.
        Do not create markdown tables, they are created separately.
        Add a marker: `[Figuur X]` or `[Tabel X]` for every Figure and Table , with accompanying whitespace.
        LAST, YOU NEED TO WRITE THE REPORT IN DUTCH.

        {{ _.role("user") }}  

        Please write the chapter that should include the following pointers:

        {{ input.pointers }}

        The graphs and tables are already created and should be included are:

        {{ input.elements }}
    "#
}

test TestFoundationResultsChapter {
  functions [FoundationDesignResultsReporter]
  args {
    input {
      pointers {
        pile_tip_range "Between NAP-16 m and NAP-20 m"
        bearing_capacity "The bearing capacities vary significantly due to varying top of sand, once in Pleistocene -> sufficient bearing capacity. Bearing capacities can be found in Table xxx"
        load "ULS load of 1000 kN"
        pile_tip_level " Chosen pile tip level: NAP-18 m, varying top of Pleistocene sand -> robust choice"
      }
      elements [
        {
          element "Table 7"
          description "Bearing capacities over depth per cpt, with resulting variance and design value of bearing capacity"
        }
      ]
    }
  }
}
