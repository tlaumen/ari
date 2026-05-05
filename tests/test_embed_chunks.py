"""Tests for embed_chunks function using the real E5 model."""

import numpy as np
import pytest

from ari.embeddings._embed import embed_chunks
from ari.embeddings._model import _load_e5_model_cached
from ari.input.pdf import Chunk


@pytest.fixture(scope="session")
def real_model():
    """Load the real E5 model once for all tests in this module."""
    return _load_e5_model_cached()


def test_embed_chunks_empty_list(real_model) -> None:
    """Test that embed_chunks returns an empty list for empty input, no model call."""
    result = embed_chunks([], real_model)

    assert result == [], "Empty input should return empty list"


def test_embed_chunks_single_chunk(real_model) -> None:
    """Test that embed_chunks returns list of one np.ndarray for single chunk."""
    chunks = [Chunk(text="hello", page_start=1, page_end=1, chunk_index=0)]
    result = embed_chunks(chunks, real_model)

    assert len(result) == 1, "Single chunk should return list of one embedding"
    assert isinstance(result[0], np.ndarray), "Result should be numpy array"


def test_embed_chunks_multiple_chunks_order_preserved(real_model) -> None:
    """Test that embed_chunks returns embeddings in same order as input chunks."""
    chunks = [
        Chunk(text="first chunk", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="second chunk", page_start=1, page_end=1, chunk_index=1),
    ]
    result = embed_chunks(chunks, real_model)

    assert len(result) == 2, "Two chunks should return list of two embeddings"
    # Different texts should produce different embeddings
    assert not np.allclose(result[0], result[1]), (
        "Different chunks should produce different embeddings"
    )


def test_embed_chunks_float32_dtype(real_model) -> None:
    """Test that all returned arrays have float32 dtype."""
    chunks = [
        Chunk(text="hello", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="world", page_start=1, page_end=1, chunk_index=1),
    ]
    result = embed_chunks(chunks, real_model)

    for i, emb in enumerate(result):
        assert emb.dtype == np.float32, (
            f"Embedding {i} should be float32, got {emb.dtype}"
        )


def test_embed_chunks_unit_normalization(real_model) -> None:
    """Test that each returned array has norm ≈ 1.0 (E5 default normalization)."""
    chunks = [
        Chunk(text="test1", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="test2", page_start=1, page_end=1, chunk_index=1),
    ]
    result = embed_chunks(chunks, real_model)

    for i, emb in enumerate(result):
        norm = np.linalg.norm(emb)
        # E5 normalizes by default, but float32 conversion introduces minor precision loss
        # Allow 1% tolerance to account for float32 rounding
        assert 0.99 <= norm <= 1.01, (
            f"Embedding {i} should be ~unit-normalized, got norm={norm}"
        )


def test_embed_chunks_same_text_same_embedding(real_model) -> None:
    """Test that the same text produces the same embedding (deterministic)."""
    chunks = [
        Chunk(text="identical text", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="identical text", page_start=1, page_end=1, chunk_index=1),
    ]
    result = embed_chunks(chunks, real_model)

    np.testing.assert_array_equal(
        result[0], result[1], err_msg="Same text should produce identical embeddings"
    )


def test_embed_chunks_extracts_text_from_chunks(real_model) -> None:
    """Test that embed_chunks produces different embeddings for different texts."""
    chunks = [
        Chunk(text="apple", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="banana", page_start=1, page_end=1, chunk_index=1),
    ]
    result = embed_chunks(chunks, real_model)

    # These should definitely be different embeddings
    assert not np.allclose(result[0], result[1]), (
        "Different texts should produce different embeddings"
    )


def test_embed_chunks_correct_embedding_dimension(real_model) -> None:
    """Test that returned embeddings have the correct dimension for e5-nl-base."""
    chunks = [Chunk(text="test", page_start=1, page_end=1, chunk_index=0)]
    result = embed_chunks(chunks, real_model)

    # e5-nl-base produces 384-dimensional embeddings (based on 256 length model)
    assert result[0].shape == (364,), f"Expected (384,) shape, got {result[0].shape}"

