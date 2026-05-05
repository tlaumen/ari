"""E5 embedding encoding functions for queries and documents."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from ari.input.pdf import Chunk


def embed_query(text: str, model: SentenceTransformer) -> np.ndarray:
    """Encodes a query string into a normalized embedding vector using the E5 model.

    Args:
        text: The query string to encode.
        model: A loaded SentenceTransformer instance.

    Returns:
        A normalized float32 numpy array representing the query embedding.
        The embedding is normalized to unit length (norm ~= 1.0).

    Note:
        E5 models normalize outputs by default, so the returned vector is unit-normalized.
    """
    embedding = model.encode_query(text)
    return embedding.astype(np.float32)


def embed_chunks(chunks: list[Chunk], model: SentenceTransformer) -> list[np.ndarray]:
    """Encodes a list of document chunks into a list of normalized embedding vectors.

    Args:
        chunks: List of Chunk objects to encode.
        model: A loaded SentenceTransformer instance.

    Returns:
        A list of normalized float32 numpy arrays, one per input chunk, in the same order.
        Returns an empty list if input chunks is empty.

    Note:
        E5 models normalize outputs by default, so each returned vector is unit-normalized
        (norm ~= 1.0).
    """
    if not chunks:
        return []

    embeddings: list[np.ndarray] = []

    for i, chunk in enumerate(chunks):
        print(f"embedding chunk: {i} of {len(chunks)}")
        embedding = model.encode_document(chunk.text)
        embeddings.append(embedding.astype(np.float32))

    return embeddings
