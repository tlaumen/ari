// human tools are async requests to a human
type HumanTools = ClarificationRequest | DoneForNow

class ClarificationRequest {
  intent "request_more_information" @description("you can request more information from me")
  message string
}

class DoneForNow {
  intent "done_for_now"

  message string @description(#"
    message to send to the user about the work that was done. 
  "#)
}

function DetermineNextStep(
    thread: string 
) -> CalculatorTools | HumanTools {
    client Claude4_5Haiku

    prompt #"
        {{ _.role("system") }}

        You are a helpful assistant that can help with tasks.

        {{ _.role("user") }}
        
        You are working on the following thread:

        {{ thread }}

        What should the next step be?

        {{ ctx.output_format }}
    "#
}


test MathOperation {
  functions [DetermineNextStep]
  args {
    thread "can you multiply 3 and 4, then multiply the result with 2?"
  }
}
