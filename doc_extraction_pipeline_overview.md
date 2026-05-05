# PDF Semantic Extraction Pipeline
### Architecture & Design Overview — BAML · sentence-transformers · uv

---

## 1. Goal

Given a **fixed query value** and a PDF document that changes over time, extract the **top 3 best-matching chunks** from the document.

> **Key insight:** because the query never changes, its embedding vector is computed once and treated as a constant. Every pipeline run only needs to embed the new document.

---

## 2. High-Level Architecture

```
PDF → Extract text → Chunk → Embed chunks → Cosine similarity → Top-K → BAML rerank → Top 3
                                                ↑
                                       query vector (constant)
```

| Stage | What happens | Cost |
|---|---|---|
| PDF Extraction | Raw text pulled from the PDF per page/section | Free — no AI |
| Chunking | Text split into logical pieces with metadata (page, id) | Free — no AI |
| Embed chunks | Each chunk converted to a vector; query vector is a constant | Cheap — small model |
| Cosine similarity | In-memory dot-product scoring against the query vector | Free — pure math |
| BAML rerank | Top-K candidates reasoned over; returns Top 3 with scores | Token cost — small input |

---

## 3. Component Detail

### 3.1 PDF Extraction
Use `pdfplumber` or `pymupdf` to extract raw text. No AI involved. Output is a list of text strings, one per page or section.

### 3.2 Chunking
Choose based on document structure:
- **Page-based** — one chunk per page. Simple, works well for dense documents.
- **Section-based** — split on headers. Better for structured/report-style documents.
- **Sliding window** — overlapping fixed-size chunks. Good for continuous prose.

Each chunk carries metadata: `{ id, page_number, text }`.

### 3.3 Embedding Layer
Convert each chunk and the query into a vector using a local embedding model. Since the query is fixed, **its vector is computed once and stored as a constant** in the codebase.

No vector database needed — all embeddings live in a plain Python list in memory and are discarded after the process exits.

### 3.4 Cosine Similarity
Score every chunk against the query vector using cosine similarity. This is a single `numpy` operation — no LLM, millisecond speed. Sort by score and take the Top-K indices.

**Recommended K: 10–15.**
- Too small (K < 5): risk of missing a relevant chunk that BAML cannot recover.
- Too large (K > 25): defeats the purpose and inflates BAML token usage.

### 3.5 BAML Reranking
Feed only the Top-K candidates into a BAML function. BAML handles deep semantic reasoning — context, nuance, partial matches — and returns exactly 3 results as structured output.

Suggested BAML types:
```
class Candidate {
  chunk_id:         string
  text:             string
  page_number:      int
  similarity_score: float   // soft hint from embedding stage
}

class MatchResult {
  chunk_id:         string
  relevance_score:  float   // 0.0 – 1.0
  reasoning:        string  // why it matched
  excerpt:          string  // relevant portion
}

function RerankCandidates(query: string, candidates: Candidate[]) -> MatchResult[]
```

Passing the pre-computed similarity score as a soft hint to BAML typically improves final ranking quality.

---

## 4. Division of Labour: Embeddings vs. BAML

| | Embedding similarity | BAML / LLM |
|---|---|---|
| **Speed** | Milliseconds | Seconds |
| **Cost** | Near-zero | Token-based |
| **Strength** | Broad relevance — high recall | Deep reasoning — high precision |
| **Weakness** | Misses nuance and context | Expensive at scale |
| **Role** | Narrow the candidate pool | Pick the truly best matches |

---

## 5. Local Embedding Setup with uv

### 5.1 The CUDA Problem
`sentence-transformers` depends on PyTorch, which on Linux pulls in a large set of NVIDIA CUDA packages by default (`nvidia_cublas_cu12`, `nvidia_cudnn_cu12`, etc.). This adds gigabytes of unwanted drivers for a CPU-only workflow.

### 5.2 Solution: CPU-only PyTorch via pyproject.toml
uv has first-class support for routing PyTorch to its CPU-only index:

```toml
[project]
dependencies = ["torch", "sentence-transformers"]

[[tool.uv.index]]
name = "pytorch-cpu"
url  = "https://download.pytorch.org/whl/cpu"
explicit = true   # only used for packages explicitly routed here

[tool.uv.sources]
torch = [{ index = "pytorch-cpu" }]
```

Then install with `uv sync`. All other dependencies still resolve from PyPI normally.

### 5.3 Quick One-liner Alternative
For a script without a `pyproject.toml`:
```bash
uv pip install torch sentence-transformers --torch-backend cpu
```
> ⚠️ `--torch-backend` only works with `uv pip`. It does not work with `uv lock`, `uv sync`, or `uv run`.

### 5.4 Explicit CPU Device in Code
Always specify the device explicitly when loading the model:
```python
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
```

---

## 6. Full Component Summary

| Component | Tool / Approach | Notes |
|---|---|---|
| PDF Extraction | `pdfplumber` or `pymupdf` | Runs every time; document changes |
| Chunking | Page-based or section-based | Runs every time |
| Query Embedding | `sentence-transformers` (CPU) | Computed once; stored as a constant |
| Chunk Embedding | `sentence-transformers` (CPU) | Re-computed each run, in-memory |
| Similarity Scoring | `numpy` cosine similarity | No database; in-memory only |
| Candidate Selection | argsort + slice Top-K (10–15) | Pure math; no AI cost |
| Reranking | BAML function | Sees only Top-K candidates |
| Output | `MatchResult[]` | Top 3 with scores + reasoning |
| Package management | uv with `pytorch-cpu` index | No CUDA packages installed |
