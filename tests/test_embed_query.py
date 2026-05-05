"""Tests for embed_query function."""

import numpy as np
import pytest

from ari.embeddings._embed import embed_query
from ari.embeddings._model import _load_e5_model_cached


@pytest.fixture(scope="session")
def _real_model():
    """Load the E5 model once per test session."""
    return _load_e5_model_cached()


def test_embed_query_returns_numpy_array(_real_model) -> None:
    """Test that embed_query returns a numpy array with float32 dtype."""
    text = "What is machine learning?"
    result = embed_query(text, _real_model)

    assert isinstance(result, np.ndarray), "Result should be a numpy array"
    assert result.dtype == np.float32, f"Expected float32, got {result.dtype}"


def test_embed_query_returns_correct_shape(_real_model) -> None:
    """Test that embed_query returns a 1D vector."""
    text = "What is machine learning?"
    result = embed_query(text, _real_model)

    assert result.ndim == 1, f"Expected 1D array, got {result.ndim}D"
    assert result.shape[0] == 384, f"Expected 384-dim embedding, got {result.shape}"


def test_embed_query_deterministic(_real_model) -> None:
    """Test that embed_query produces consistent results for the same input."""
    text = "What is machine learning?"
    result1 = embed_query(text, _real_model)
    result2 = embed_query(text, _real_model)

    np.testing.assert_array_equal(result1, result2)


def test_embed_query_normalized(_real_model) -> None:
    """Test that embed_query returns a unit-normalized vector."""
    text = "What is machine learning?"
    result = embed_query(text, _real_model)

    norm = np.linalg.norm(result)
    np.testing.assert_almost_equal(
        norm,
        1.0,
        decimal=2,
        err_msg=f"Embedding should be unit-normalized, got norm={norm}",
    )


def test_embed_query_different_texts(_real_model) -> None:
    """Test that different texts produce different embeddings."""
    text1 = "What is machine learning?"
    text2 = "What is cooking?"

    result1 = embed_query(text1, _real_model)
    result2 = embed_query(text2, _real_model)

    # Results should differ for different texts
    assert not np.array_equal(result1, result2), (
        "Different texts should produce different embeddings"
    )


def test_embed_query_preserves_values(_real_model) -> None:
    """Test that embed_query preserves the embedding values."""
    text = "test input"
    result = embed_query(text, _real_model)

    # Re-encode to get expected values
    expected = _real_model.encode_query(text).astype(np.float32)

    np.testing.assert_array_almost_equal(
        result, expected, err_msg="Embedding values should be preserved"
    )
