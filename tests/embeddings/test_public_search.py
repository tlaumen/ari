"""Tests for search_chunks() public API."""

import pytest

from ari.embeddings.search import search_chunks
from ari.input.pdf import Chunk


@pytest.fixture(scope="module")
def _real_chunks():
    """Real Chunk objects for integration testing."""
    return [
        Chunk(text="What is diabetes?", page_start=1, page_end=1, chunk_index=0),
        Chunk(text="Diabetes is a chronic condition affecting blood sugar levels.", page_start=2, page_end=2, chunk_index=1),
        Chunk(text="Treatment includes medication and lifestyle changes.", page_start=3, page_end=3, chunk_index=2),
    ]


class TestSearchChunksBasic:
    """Basic search_chunks functionality."""

    def test_returns_list_of_tuples_sorted_descending(self, _real_chunks):
        """search_chunks returns results sorted by cosine similarity descending."""
        results = search_chunks("what is diabetes", _real_chunks, k=2)

        assert isinstance(results, list)
        assert len(results) == 2
        # Verify structure
        for score, chunk in results:
            assert isinstance(score, float)
            assert isinstance(chunk, Chunk)
        # Verify descending order
        scores = [score for score, _ in results]
        assert scores == sorted(scores, reverse=True)

    def test_returns_top_k_results(self, _real_chunks):
        """Test that k parameter controls number of returned results."""
        results = search_chunks("diabetes treatment", _real_chunks, k=1)

        assert len(results) == 1
        score, chunk = results[0]
        assert isinstance(score, float)
        assert isinstance(chunk, Chunk)

    def test_scores_in_valid_range(self, _real_chunks):
        """Scores should be floats in the range [-1.0, 1.0]."""
        results = search_chunks("what is diabetes", _real_chunks, k=3)

        for score, _ in results:
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0, f"Score {score} outside valid range [-1.0, 1.0]"


class TestSearchChunksEmptyInputs:
    """Tests for empty/invalid input handling."""

    def test_empty_chunks_returns_empty(self):
        """When chunks is empty, returns empty list regardless of k."""
        results = search_chunks("what is diabetes", [], k=5)
        assert results == []

    def test_k_zero_returns_empty(self):
        """When k <= 0, returns empty list."""
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = search_chunks("test query", [chunk], k=0)
        assert results == []

    def test_k_negative_returns_empty(self):
        """When k < 0, returns empty list."""
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = search_chunks("test query", [chunk], k=-3)
        assert results == []


class TestSearchChunksReturnType:
    """Tests for return type and structure."""

    def test_returns_list_of_score_chunk_tuples(self):
        """Results should be a list of (score, Chunk) tuples."""
        chunk = Chunk(text="Diabetes affects blood sugar regulation.", page_start=1, page_end=1, chunk_index=0)
        results = search_chunks("diabetes", [chunk], k=1)

        assert isinstance(results, list)
        assert len(results) == 1
        score, returned_chunk = results[0]
        assert isinstance(score, float)
        assert isinstance(returned_chunk, Chunk)

    def test_chunk_objects_preserved(self):
        """The original Chunk objects should be returned in results."""
        chunk1 = Chunk(text="First chunk about diabetes", page_start=1, page_end=1, chunk_index=0)
        chunk2 = Chunk(text="Second chunk about treatment", page_start=2, page_end=2, chunk_index=1)
        chunks = [chunk1, chunk2]

        results = search_chunks("diabetes treatment", chunks, k=2)

        returned_chunks = [c for _, c in results]
        assert chunk1 in returned_chunks
        assert chunk2 in returned_chunks
