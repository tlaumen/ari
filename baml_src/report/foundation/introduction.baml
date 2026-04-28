class ReportBaseLineIntroduction {
  pointers string[] @alias("Pointers on what should be included in the text")
  elements ReportElement[]
}

function FoundationDesignIntroductionReporter(
    input: ReportBaseLineIntroduction
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

        You should only write chapter 1, the introduction of the report.
        Be very factual, only report what is provided as input.
        Do not explain geotechnical terminology.
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

test TestFoundationIntroductionChapter {
  functions [FoundationDesignIntroductionReporter]
  args {
    input {
      pointers [
        "Fundering nieuw viaduct A20",
        "Kleine afstand bestaande bebouwing dus gekozen voortrillingsvrij paalsysteem"
      ]
      elements []
    }
  }
}
