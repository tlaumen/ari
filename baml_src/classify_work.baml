enum TypeOfWork {
    INTERPRET_SOIL_INVESTIGATION
    DERIVE_SOIL_PARAMETERS
    CALCULATE
    REPORT
}

function ClassifyWork(input: string) -> TypeOfWork | ClarificationRequest {
  client Claude4_5Haiku
  prompt #"
    You only need to classify what work the user wants to perform. 
    If the user comes with an action, providing the category of work he wants to perform is sufficient.
    If unsure, ask for clarification.

    {{ ctx.output_format }}

    {{ _.role("user") }} 

    {{ input }}
  "#
}

test InitialTest{
    functions [ClassifyWork]
    args {
        input "Make a pile foundation calculation with cpt001"
    }
}