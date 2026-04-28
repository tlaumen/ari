class ModellingPointers {
    soil_profiles string[] // containing information about the intepretation of cpt -> soil profile + bottom of negative skin friction and top of positive skin
    pile string[] // all pile information should be entered here
    variability_information string[] // used cpts used per foundation, if rigid construction and the resulting ksi values
    environmental_factors string[] // when is the cpt executed relative to pile installation, what is future ground level, what are phreatic water levels
}

class ReportBaseLineModelling {
  pointers ModellingPointers @alias("Pointers on what should be included in the text")
  elements ReportElement[]
}

function FoundationDesignModellingReporter(
    input: ReportBaseLineModelling
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

        You should only write chapter 4, on how the foundation calculation is modelled.
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

// TODO: add relavent Figures/Tables


test TestFoundationModellingChapter {
  functions [FoundationDesignModellingReporter]
  args {
    input {
      pointers {
        soil_profiles [
          "The soil profiles are interpreted based on simple qc and rf rules",
          "The positive and negative skin friction is based on the compressibility of the material and validated by the geotechnical engineer",
        ],
        pile [
          "The pile used is a Fundex pile, tip diameter: 450, shaft diameter: 400, assumption shaft diameter is half of both.", 
        ],
        variability_information [
          "The cpts used per pile are provided in table XXX. In accordance with the Eurocode, every pile should be covered from all winddirections. This is also shown in the accompanying table",
          "The construction is rigid, resulting into the ksi values in accordance with NEN9997-1 table XXXX. Provided the number of cpts used per pile, covering the foundation, the ksi values are also presented in the accompanying table"
        ],
        environmental_factors [
          "The cpts were performed before excavation and installation of the piles",
          "The future ground level will be xxx, which means a decrease of the cone resistance due to the reduction of effective stresses"
          "Phreatic water levels: 0.1, 0.3, 1.2, -0.3, 0.5, based on piezometer XXXXX",
        ]
      } 
      elements [
        {
          element "Table 4"
          description "Every soil profile, the corresponding cpt and the bottom of the negative skin friction and top of positive skin friction"
        }
        {
          element "Table 5"
          description "Pile dimensions and model factors, in accordance with NEN9997-1"
        }
        {
          element "Table 6"
          description "Cpts used per pile and resulting ksi values"
        } 
      ]
    }
  }
}
