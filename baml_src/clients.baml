// Learn more about clients at https://docs.boundaryml.com/docs/snippets/clients/overview

// Not performing good as a simple calculator agent
client<llm> Qwen3_06b {
  provider openai-generic
  options {
    base_url "http://localhost:11434/v1"
    model "qwen3:0.6b"
    default_role "user" // Most local models prefer the user role
    temperature 0.1
  }
}

// Performing good as a simple calculator agent
client<llm> Qwen3_4b {
  provider openai-generic
  options {
    base_url "http://localhost:11434/v1"
    model "qwen3:4b"
    default_role "user" // Most local models prefer the user role
    temperature 0.1
  }
}


// Not performing good as a simple calculator agent
client<llm> Gemma3_1b {
  provider openai-generic
  options {
    base_url "http://localhost:11434/v1"
    model "gemma3:1b"
    default_role "user" // Most local models prefer the user role
    temperature 0.1
  }
}

// Not performing good as a simple calculator agent
client<llm> Smollm2 {
  provider openai-generic
  options {
    base_url "http://localhost:11434/v1"
    model "smollm:360m"
    temperature 0.1
  }
}

// To get the Anthropic model names, run the following commands:
//  1. source .env --> loads the environment variables
//  2. get the model names with the following command:
//    curl https://api.anthropic.com/v1/models --header "x-api-key: $ANTHROPIC_API_KEY" --header "anthropic-version: 2023-06-01"

client<llm> Claude4_5Haiku {
  provider anthropic
  options {
    model "claude-haiku-4-5-20251001"
    temperature 0
  }
}
