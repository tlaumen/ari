enum Berekening {
    PAALFUNDERING
    STABILITEIT
    ZETTINGEN
    DAMWAND
}

class VerzoekVerduidelijking {
  intentie "Geef meer informatie" @description("Je verzoek is onduidelijk, je moet duidelijker formuleren welke berekening gemaakt moet worden")
  verzoek_tot_verduidelijking string
}


function ChooseWorkflow(input: string) -> Berekening | VerzoekVerduidelijking {
  client Claude4_5Haiku
  prompt #"
    {{ _.role("system") }} 
    Bent een geotechnisch ingenieur en moet classificeren welke berekening er gemaakt moet worden.
    Classificeer alleen welk type berekening uitgevoerd moet worden.
    Je mag geen acties uitvoeren omtrent te berekening.
    Als het verzoek onduidelijk is, vraag dan ENKEL verduidelijking welk type berekening er uitgevoerd moet worden.
    Je mag niet doorvragen over de details van de berekening.


    {{ ctx.output_format }}

    {{ _.role("user") }} 

    {{ input }}
  "#
}

test TestChooseWorkflowPile{
    functions [ChooseWorkflow]
    args {
        input "Ik wil graag een heipaal uitrekenen bij cpt001"
    }
    @@assert({{ this == "PAALFUNDERING" }})
}
test TestChooseWorkflowPile2{
    functions [ChooseWorkflow]
    args {
        input "Ik wil graag de draagkracht uitrekenen bij cpt001"
    }
    @@assert({{this == "PAALFUNDERING"}})
}
test TestChooseWorkflowZetting{
    functions [ChooseWorkflow]
    args {
        input "Reken de zettingen uit bij cpt001"
    }
    @@assert({{ this == "ZETTINGEN" }})
}
test TestChooseWorkflowZetting2{
    functions [ChooseWorkflow]
    args {
        input "Wat is de zakking ter plaatse van km 23.5?"
    }
    @@assert({{ this.intentie == "Geef meer informatie" }})
}
test TestChooseWorkflowStabiliteit{
    functions [ChooseWorkflow]
    args {
        input "Reken de stbi uit bij de Dorpstraat in Krimpen aan de IJssel"
    }
    @@assert({{ this.intentie == "Geef meer informatie" }})
}
test TestChooseWorkflowStabiliteit2{
    functions [ChooseWorkflow]
    args {
        input "Hoe stabiel is de Lekdijk?"
    }
    @@assert({{ this.intentie == "Geef meer informatie" }})
}