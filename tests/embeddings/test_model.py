"""Tests for ari.embeddings._model._load_e5_model_cached()"""

import pytest
from sentence_transformers import SentenceTransformer

from ari.embeddings._model import _load_e5_model_cached


@pytest.fixture(scope="session")
def _real_model():
    """Load the E5 model once per test session."""
    return _load_e5_model_cached()


class TestLoadE5ModelCached:
    """Tests for the simple model loader."""

    def test_returns_sentence_transformer_instance(self, _real_model) -> None:
        """Verify _load_e5_model_cached returns a SentenceTransformer instance."""
        assert isinstance(_real_model, SentenceTransformer), (
            "Result should be a SentenceTransformer instance"
        )
        assert _real_model.transformers_model.name_or_path == "clips/e5-small-trm-nl", (
            f"Expected model name 'clips/e5-small-trm-nl', got {_real_model.transformers_model.name_or_path}"
        )
