"""Cosine similarity search over document chunk embeddings."""

from __future__ import annotations

import numpy as np

from ari.input.pdf import Chunk


def cosine_search(
    query_emb: np.ndarray,
    chunk_embs: list[np.ndarray],
    chunks: list[Chunk],
    k: int,
) -> list[tuple[float, Chunk]]:
    """Ranks document chunks by cosine similarity to a query and returns top-k matches.

    Args:
        query_emb: Pre-normalized query embedding vector (from embed_query).
        chunk_embs: List of pre-normalized chunk embedding vectors (from embed_chunks).
        chunks: List of Chunk objects corresponding to chunk_embs.
        k: Number of top results to return. If k <= 0, returns empty list.

    Returns:
        List of (score, Chunk) tuples sorted by score in descending order.
        Score is the raw dot product (cosine similarity) ranging from -1.0 to 1.0.
        Returns empty list when:
            - k <= 0
            - chunk_embs is empty
            - chunks is empty
            - chunk_embs and chunks have different lengths

    Note:
        Embeddings are assumed to be pre-normalized (unit length). For such vectors,
        the dot product equals the cosine similarity.
    """
    # Return empty for invalid k
    if k <= 0:
        return []

    # Return empty for mismatched or empty inputs
    if not chunk_embs or not chunks:
        return []

    # Ensure chunk_embs and chunks are in sync
    if len(chunk_embs) != len(chunks):
        return []

    # Compute dot products (cosine similarity for normalized vectors)
    scores_with_chunks: list[tuple[float, Chunk]] = []
    for emb, chunk in zip(chunk_embs, chunks):
        score = float(np.dot(query_emb, emb))
        scores_with_chunks.append((score, chunk))

    # Sort by score descending
    scores_with_chunks.sort(key=lambda x: x[0], reverse=True)

    # Return top-k
    return scores_with_chunks[:k]