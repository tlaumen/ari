"""Tests for cosine_search function."""

import numpy as np
import pytest

from ari.embeddings._search import cosine_search
from ari.input.pdf import Chunk


class TestCosineSearchBasic:
    """Basic cosine search functionality."""

    def test_returns_top_result_with_cosine_similarity(self):
        """Test that cosine_search returns results with correct similarity scores."""
        # Query [1, 0] dot product with chunk [0.5, 0.5] (normalized)
        # cos(45°) = 0.7071
        query_emb = np.array([1.0, 0.0])
        chunk_emb = np.array([0.7071, 0.7071])
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)

        results = cosine_search(query_emb, [chunk_emb], [chunk], k=1)

        assert len(results) == 1
        score, returned_chunk = results[0]
        assert returned_chunk == chunk
        assert abs(score - 0.7071) < 0.001

    def test_returns_result_with_perfect_match(self):
        """Test that a query matching a chunk perfectly returns score of 1.0."""
        query_emb = np.array([1.0, 0.0])
        chunk_emb = np.array([1.0, 0.0])
        chunk = Chunk(text="exact match", page_start=1, page_end=1, chunk_index=0)

        results = cosine_search(query_emb, [chunk_emb], [chunk], k=1)

        assert len(results) == 1
        score, _ = results[0]
        assert abs(score - 1.0) < 0.001

    def test_returns_top_k_results(self):
        """Test that top-k results are returned sorted descending."""
        query_emb = np.array([1.0, 0.0])
        chunk1 = Chunk(text="c1", page_start=1, page_end=1, chunk_index=0)
        chunk2 = Chunk(text="c2", page_start=1, page_end=1, chunk_index=1)
        chunks = [chunk1, chunk2]
        # chunk1 is perfect match (score 1.0), chunk2 is orthogonal (score 0.0)
        chunk_embs = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]

        results = cosine_search(query_emb, chunk_embs, chunks, k=1)

        assert len(results) == 1
        score, top_chunk = results[0]
        assert top_chunk == chunk1
        assert abs(score - 1.0) < 0.001


class TestCosineSearchEmptyInputs:
    """Tests for empty/invalid input handling."""

    def test_empty_chunk_embs_and_chunks(self):
        """Returns empty list when both chunk_embs and chunks are empty."""
        query_emb = np.array([1.0, 0.0])
        results = cosine_search(query_emb, [], [], k=5)
        assert results == []

    def test_empty_chunks_mismatch(self):
        """Returns empty list when chunk_embs has items but chunks is empty."""
        query_emb = np.array([1.0, 0.0])
        chunk_emb = np.array([1.0, 0.0])
        results = cosine_search(query_emb, [chunk_emb], [], k=1)
        assert results == []

    def test_empty_chunk_embs_with_chunks(self):
        """Returns empty list when chunk_embs is empty but chunks has items."""
        query_emb = np.array([1.0, 0.0])
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = cosine_search(query_emb, [], [chunk], k=1)
        assert results == []


class TestCosineSearchKBehavior:
    """Tests for k parameter behavior."""

    def test_k_zero_returns_empty(self):
        """When k <= 0, returns empty list."""
        query_emb = np.array([1.0, 0.0])
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = cosine_search(query_emb, [np.array([1.0, 0.0])], [chunk], k=0)
        assert results == []

    def test_k_negative_returns_empty(self):
        """When k < 0, returns empty list."""
        query_emb = np.array([1.0, 0.0])
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = cosine_search(
            query_emb, [np.array([1.0, 0.0])], [chunk], k=-3
        )
        assert results == []

    def test_k_greater_than_chunks_returns_all(self):
        """When k is greater than number of chunks, returns all chunks."""
        query_emb = np.array([1.0, 0.0])
        chunk1 = Chunk(text="c1", page_start=1, page_end=1, chunk_index=0)
        chunk2 = Chunk(text="c2", page_start=1, page_end=1, chunk_index=1)
        results = cosine_search(
            query_emb,
            [np.array([1.0, 0.0]), np.array([0.0, 1.0])],
            [chunk1, chunk2],
            k=10,  # More than available chunks
        )
        assert len(results) == 2

    def test_results_sorted_descending(self):
        """Results should be sorted by score in descending order."""
        query_emb = np.array([1.0, 0.0])
        chunk1 = Chunk(text="c1", page_start=1, page_end=1, chunk_index=0)
        chunk2 = Chunk(text="c2", page_start=1, page_end=1, chunk_index=1)
        chunk3 = Chunk(text="c3", page_start=1, page_end=1, chunk_index=2)

        results = cosine_search(
            query_emb,
            [
                np.array([0.5, 0.5]),  # score ~0.5
                np.array([1.0, 0.0]),  # score 1.0
                np.array([0.0, 1.0]),  # score 0.0
            ],
            [chunk1, chunk2, chunk3],
            k=3,
        )

        assert len(results) == 3
        scores = [score for score, _ in results]
        assert scores == sorted(scores, reverse=True)
        # Verify highest is chunk2 (score 1.0)
        assert results[0][1] == chunk2


class TestCosineSearchReturnType:
    """Tests for return type and structure."""

    def test_returns_list_of_tuples(self):
        """Results should be a list of (score, Chunk) tuples."""
        query_emb = np.array([1.0, 0.0])
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = cosine_search(query_emb, [np.array([1.0, 0.0])], [chunk], k=1)

        assert isinstance(results, list)
        assert len(results) == 1
        score, returned_chunk = results[0]
        assert isinstance(score, float)
        assert isinstance(returned_chunk, Chunk)

    def test_score_range_normalized_vectors(self):
        """For normalized unit vectors, dot product ranges from -1 to 1."""
        query_emb = np.array([1.0, 0.0])
        # Perfect opposite (would only happen with non-normalized data)
        # For normalized vectors, the minimum dot product is -1
        opposite_chunk = Chunk(text="opposite", page_start=1, page_end=1, chunk_index=0)

        results = cosine_search(
            query_emb, [np.array([-1.0, 0.0])], [opposite_chunk], k=1
        )

        assert len(results) == 1
        score, _ = results[0]
        assert score == -1.0