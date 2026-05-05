"""Public semantic search API for document chunks."""

from __future__ import annotations

from ari.embeddings._embed import embed_chunks, embed_query
from ari.embeddings._model import _load_e5_model_cached
from ari.embeddings._search import cosine_search
from ari.embeddings.rerank import SearchResult, rerank_results
from ari.input.pdf import Chunk


def search_chunks(
    query: str,
    chunks: list[Chunk],
    k: int,
) -> list[tuple[float, Chunk]]:
    """Searches document chunks by semantic similarity to a query.

    This is the public entry point for semantic chunk search. It:
    1. Loads the E5 embedding model
    2. Encodes the query string
    3. Encodes all document chunks
    4. Computes cosine similarity between query and chunks
    5. Returns top-k results sorted by relevance

    Args:
        query: The search query string.
        chunks: List of Chunk objects to search through.
        k: Number of top results to return. If k <= 0, returns empty list.

    Returns:
        List of (score, Chunk) tuples sorted by cosine similarity in descending order.
        Score is a float in the range [-1.0, 1.0] representing the raw dot product
        between normalized embedding vectors.
        Returns empty list when:
            - k <= 0
            - chunks is empty

    Example:
        >>> from ari.input.pdf import Chunk
        >>> chunks = [Chunk("Diabetes is a chronic condition...", page_start=1, page_end=1, chunk_index=0)]
        >>> results = search_chunks("what is diabetes", chunks, k=1)
        >>> if results:
        ...     score, chunk = results[0]
        ...     print(f"Best match (score={score:.3f}): {chunk.text[:50]}...")
    """
    # Return empty for invalid k or empty chunks
    if k <= 0 or not chunks:
        return []

    # Load the E5 model
    model = _load_e5_model_cached()

    # Encode the query
    query_emb = embed_query(query, model)

    # Encode the chunks
    chunk_embs = embed_chunks(chunks, model)

    # Run cosine search
    results = cosine_search(query_emb, chunk_embs, chunks, k)

    return results


def search_and_rerank(
    query: str,
    chunks: list[Chunk],
    initial_k: int = 12,
    final_k: int = 3,
) -> list[SearchResult]:
    """Full pipeline: search + BAML rerank, returns top 3 SearchResult.

    This function combines cosine similarity search with BAML semantic reranking:
    1. Performs cosine similarity search using E5 embeddings
    2. Sends top candidates to BAML for semantic reranking
    3. Returns enriched results with answer, relevance score, and reasoning

    Args:
        query: The search query string.
        chunks: List of Chunk objects to search through.
        initial_k: Number of top cosine results to send for reranking (default 12).
        final_k: Maximum number of results to return after reranking (default 3).

    Returns:
        List of SearchResult objects ordered by BAML relevance score descending.
        Each SearchResult contains the original chunk, an extracted answer,
        relevance score (0-1), and reasoning.
        Returns empty list when:
            - chunks is empty
            - initial_k <= 0

    Raises:
        ValueError: If source_chunk_index from BAML doesn't match any
            Chunk's chunk_index in the cosine results.

    Example:
        >>> from ari.input.pdf import Chunk
        >>> chunks = [Chunk("Foundation design principles...", page_start=1, page_end=1, chunk_index=0)]
        >>> results = search_and_rerank("foundation design", chunks)
        >>> if results:
        ...     top = results[0]
        ...     print(f"Best match: {top.answer} (score={top.relevance_score:.2f})")
    """
    # S-1: Return empty for invalid initial_k or empty chunks
    if initial_k <= 0 or not chunks:
        return []

    # S-2: Get initial cosine candidates
    cosine_results = search_chunks(query, chunks, initial_k)

    # S-3 & S-4: Rerank and return SearchResult list
    # S-5: Propagates ValueError from rerank_results if mismatch occurs
    return rerank_results(cosine_results, query, final_k)
