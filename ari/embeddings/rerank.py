"""Reranking module for semantic search results using BAML."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from baml_client import b, types

if TYPE_CHECKING:
    from ari.input.pdf import Chunk


@dataclass
class SearchResult:
    """Enriched search result with semantic reranking.

    Attributes:
        chunk: The original Chunk object from the document.
        answer: A brief answer or relevant snippet extracted from the chunk.
        relevance_score: A score from 0-1 where 1 is most relevant.
        reasoning: Brief explanation of why this chunk is relevant to the query.
    """

    chunk: Chunk
    answer: str
    relevance_score: float
    reasoning: str


def candidates_from_cosine_results(
    results: list[tuple[float, Chunk]],
) -> list[types.Candidate]:
    """Convert cosine search results to BAML Candidate format.

    Args:
        results: List of (score, Chunk) tuples from cosine_search, ordered
            by descending cosine similarity.

    Returns:
        List of Candidate objects with chunk_id from Chunk.chunk_index,
        the chunk text, and the cosine similarity score.
        Returns empty list when input results is empty.

    Example:
        >>> from ari.input.pdf import Chunk
        >>> chunks = [Chunk("Foundation design...", page_start=1, page_end=1, chunk_index=0)]
        >>> results = [(0.95, chunks[0])]
        >>> candidates = candidates_from_cosine_results(results)
        >>> candidates[0].chunk_id
        0
    """
    return [
        types.Candidate(
            chunk_id=chunk.chunk_index,
            text=chunk.text,
            similarity_score=score,
        )
        for score, chunk in results
    ]


def rerank_candidates(
    query: str,
    candidates: list[types.Candidate],
    top_k: int = 3,
) -> list[types.RerankedMatch]:
    """Call BAML RerankCandidates and return raw RerankedMatch list.

    Args:
        query: The search query string.
        candidates: List of Candidate objects from candidates_from_cosine_results.
        top_k: Number of top results to return (for API consistency; BAML
            always returns 3 results).

    Returns:
        List of RerankedMatch objects from BAML, ordered by descending
        relevance_score.

    Raises:
        RuntimeError: If the BAML call fails, with the original exception
            as the cause.

    Example:
        >>> candidates = [
        ...     types.Candidate(chunk_id=0, text="Pile capacity: 1500kN", similarity_score=0.85)
        ... ]
        >>> matches = rerank_candidates("pile bearing capacity", candidates)
        >>> len(matches)
        3
    """
    try:
        return b.RerankCandidates(query=query, candidates=candidates)
    except Exception as e:
        raise RuntimeError(f"BAML reranking failed: {e}") from e


def rerank_results(
    results: list[tuple[float, Chunk]],
    query: str,
    top_k: int = 3,
) -> list[SearchResult]:
    """Combine cosine results with BAML rerank, return SearchResult list.

    This function performs the full reranking pipeline:
    1. Converts cosine search results to BAML Candidate format
    2. Calls BAML RerankCandidates to get semantic reranking
    3. Maps the reranked matches back to SearchResult objects

    Args:
        results: List of (score, Chunk) tuples from cosine_search.
        query: The search query string.
        top_k: Number of top results to return (for API consistency).

    Returns:
        List of SearchResult objects in the same order as reranked
        matches from BAML, with chunk references to the original Chunks.

    Raises:
        ValueError: If source_chunk_index from BAML doesn't match any
            Chunk's chunk_index in results.

    Example:
        >>> from ari.input.pdf import Chunk
        >>> chunks = [Chunk("Foundation design...", page_start=1, page_end=1, chunk_index=0)]
        >>> cosine_results = [(0.95, chunks[0])]
        >>> search_results = rerank_results(cosine_results, "foundation design")
        >>> search_results[0].chunk.text
        'Foundation design...'
    """
    # Convert cosine results to BAML candidates
    candidates = candidates_from_cosine_results(results)

    # Call BAML reranker
    reranked_matches = rerank_candidates(query, candidates, top_k)

    # Build a lookup from chunk_index to Chunk
    chunk_by_index: dict[int, Chunk] = {chunk.chunk_index: chunk for _, chunk in results}

    # Map reranked matches back to SearchResult objects
    search_results: list[SearchResult] = []
    for match in reranked_matches:
        chunk = chunk_by_index.get(match.source_chunk_index)
        if chunk is None:
            raise ValueError(
                f"source_chunk_index {match.source_chunk_index} not found in cosine results"
            )
        search_results.append(
            SearchResult(
                chunk=chunk,
                answer=match.answer,
                relevance_score=match.relevance_score,
                reasoning=match.reasoning,
            )
        )

    return search_results
