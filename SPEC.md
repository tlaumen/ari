# SPEC.md — Document Extraction Pipeline: BAML Rerank

## ROADMAP

### 1. BAML Types and Function (`baml_src/rerank_input_reports.baml`)
```baml
class Candidate {
    chunk_id: int
    text: string
    similarity_score: float
}

class RerankedMatch {
    answer: string
    source_chunk_index: int
    relevance_score: float
    reasoning: string
}

function RerankCandidates(query: string, candidates: Candidate[]) -> RerankedMatch[]
```
- Uses `client Claude4_5Haiku`
- Returns exactly 3 results ordered by descending relevance

### 2. Python Wrapper (`ari/embeddings/rerank.py`)
```python
def candidates_from_cosine_results(results: list[tuple[float, Chunk]]) -> list[Candidate]
    """Convert cosine search results to BAML Candidate format."""

def rerank_candidates(query: str, candidates: list[Candidate], top_k: int = 3) -> list[RerankedMatch]
    """Call BAML RerankCandidates and return raw RerankedMatch list."""

def rerank_results(results: list[tuple[float, Chunk]], query: str, top_k: int = 3) -> list[SearchResult]
    """Combine cosine results with BAML rerank, return SearchResult list."""
```

### 3. SearchResult Dataclass (`ari/embeddings/rerank.py`)
```python
@dataclass
class SearchResult:
    chunk: Chunk
    answer: str
    relevance_score: float
    reasoning: str
```

**Decisions (Step 2):**
- Used list comprehension in `candidates_from_cosine_results` — straightforward iteration, order preserved naturally by Python's left-to-right evaluation.
- Built a dict for O(1) chunk lookup in `rerank_results` — `chunk_by_index: dict[int, Chunk]` trades small memory overhead for clean, constant-time lookup when mapping reranked matches back to Chunks.
- `top_k` parameter accepted but unused in `rerank_candidates` — BAML's generated client always returns exactly 3; the parameter is present for API symmetry with `search_and_rerank` in Step 3.
- `TYPE_CHECKING` guard for Chunk import — avoids circular import since `rerank.py` may be imported before `Chunk` class is fully initialized.
- `types.Candidate` and `types.RerankedMatch` come from `baml_client` — the module is coupled to BAML's generated type definitions, which is unavoidable and intentional.

**Step 2:** `candidates_from_cosine_results`, `rerank_candidates`, `rerank_results` — Converts cosine search results to BAML format, calls the reranker, and maps results back to enriched SearchResult objects.

**Decisions (Step 3):**
- `or` condition in empty guard — Spec says "chunks is empty or initial_k ≤ 0"; implementation uses `or` to cover both cases in one guard. This conflates two conceptually separate failure modes into one return path.
- Ordering delegated to BAML — S-4 says results are "ordered by BAML relevance score descending." The implementation does not re-sort in Python; it returns `rerank_results` directly, trusting BAML's ordering.
- `final_k` passed but not independently verified — The parameter flows through to `rerank_results`'s `top_k`, but no unit test exercises a non-default value. The integration test uses `final_k=3` (default), so the path is exercised but not varied.
- `ValueError` propagation implicit — S-5 is satisfied by Python's natural propagation of the exception from `rerank_results`; no explicit `try/except` or `raise` in the function.

**Step 3:** `search_and_rerank` — Combines cosine similarity search with BAML semantic reranking; returns enriched `SearchResult` objects ordered by BAML relevance score descending.

### 4. Public API (`ari/embeddings/search.py`)
```python
def search_and_rerank(
    query: str,
    chunks: list[Chunk],
    initial_k: int = 12,
    final_k: int = 3,
) -> list[SearchResult]
    """Full pipeline: search + BAML rerank, returns top 3 SearchResult."""
```

### 5. Integration Tests (`tests/embeddings/test_rerank.py`)
```python
def test_rerank_returns_top_3_results()
def test_rerank_preserves_chunk_indices()
def test_rerank_with_empty_candidates()
def test_search_and_rerank_combined()
```

---

## CURRENT STEP

**Step 4: Integration Test — `search_and_rerank` against real PDF**

**File:** `ari_tests/embeddings/test_search_and_rerank_integration.py`

**Purpose:** End-to-end validation that `search_and_rerank` finds pile load values ("152 kN", "79 kN") when searching "paalbelasting" in the real 37-page Dutch engineering PDF.

### Behavior:

- Load the real PDF from `ari_tests/data/test_pdf_pile_load.pdf`
- Chunk with `chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=30)`
- Call `search_and_rerank("paalbelasting", chunks, initial_k=12, final_k=3)`
- Assert at least one result contains "152 kN" or "79 kN" in `answer` attribute (BAML-extracted answer, not just `chunk.text`)

### Tests:


- [Test: `search_and_rerank` finds pile load values in top results for "paalbelasting" query]

### Integration:

- Imports `search_and_rerank` from `ari.embeddings.search`
- Imports `extract_text_from_pdf`, `chunk_by_tokens` from `ari.input.pdf`
- Uses test PDF at `ari_tests/data/test_pdf_pile_load.pdf`


### Done when:

- `ari_tests/embeddings/test_search_and_rerank_integration.py` created and passes
- `uv run pytest ari_tests/embeddings/test_search_and_rerank_integration.py` is green

---

## COMPLETED STEPS

**Step 1:** `RerankCandidates` — BAML function that semantically reranks candidate chunks and returns top 3 matches with reasoning.


**Step 2:** `candidates_from_cosine_results`, `rerank_candidates`, `rerank_results` — Converts cosine search results to BAML format, calls the reranker, and maps results back to enriched SearchResult objects.

**Step 3:** `search_and_rerank` — Combines cosine similarity search with BAML semantic reranking; returns enriched `SearchResult` objects ordered by BAML relevance score descending.
