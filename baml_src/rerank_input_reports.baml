class Candidate {
    chunk_id int
    text string
    similarity_score float
}

class RerankedMatch {
    answer string
    source_chunk_index int
    relevance_score float
    reasoning string
}

function RerankCandidates(query: string, candidates: Candidate[]) -> RerankedMatch[] {
    client Claude4_5Haiku
    prompt #"
        {{ _.role("system") }}
        
        You are a semantic search reranking assistant. You will receive a query and a list of candidate chunks with their IDs, text, and cosine similarity scores.
        
        Your task is to:
        1. Analyze each candidate's semantic relevance to the query
        2. Consider both the semantic meaning AND the provided similarity_score as a soft hint
        3. Select the TOP 3 most relevant candidates
        4. For each selected candidate, provide:
           - answer: A brief answer or relevant snippet extracted from the chunk
           - source_chunk_index: The original chunk_id from the candidate
           - relevance_score: A score from 0-1 where 1 is most relevant
           - reasoning: Brief explanation of why this chunk is relevant to the query

        Always return exactly 3 results, even if fewer candidates are provided. If not enough candidates exist, fill remaining slots with lower relevance scores.

        {{ ctx.output_format }}

        {{ _.role("user") }}
        
        Query: {{ query }}
        
        Candidates: {{ candidates }}
    "#
}

// BAML-T1: Given a query and candidates with varying relevance, returns exactly 3 results ordered by descending relevance_score
test TestRerankReturnsTop3OrderedByRelevance {
    functions [RerankCandidates]
    args {
        query "What is the bearing capacity of piles?"
        candidates [
            { chunk_id 0, text "Weather today is sunny.", similarity_score 0.95 }
            { chunk_id 1, text "Pile bearing capacity calculation method.", similarity_score 0.70 }
            { chunk_id 2, text "Pile load test results show capacity of 1500kN.", similarity_score 0.85 }
            { chunk_id 3, text "The foundation design follows Eurocode 7.", similarity_score 0.60 }
        ]
    }
}

// BAML-T2: Given candidates with chunk_ids 0, 5, 10, returns those same chunk_ids in source_chunk_index
test TestRerankPreservesChunkIndices {
    functions [RerankCandidates]
    args {
        query "Foundation settlement analysis"
        candidates [
            { chunk_id 0, text "Settlement analysis method.", similarity_score 0.8 }
            { chunk_id 5, text "Terzaghi's consolidation theory.", similarity_score 0.75 }
            { chunk_id 10, text "Time-settlement curves.", similarity_score 0.85 }
        ]
    }
}

// BAML-T3: The LLM may override cosine ordering based on semantic reasoning
test TestRerankMayOverrideCosineOrdering {
    functions [RerankCandidates]
    args {
        query "How to calculate pile length?"
        candidates [
            { chunk_id 0, text "Coffee break schedule.", similarity_score 0.95 }
            { chunk_id 1, text "Pile length determination based on bearing capacity.", similarity_score 0.50 }
            { chunk_id 2, text "Meeting room availability.", similarity_score 0.90 }
            { chunk_id 3, text "Formula for required pile length: L = Q/(Ab*c).", similarity_score 0.65 }
        ]
    }
}
