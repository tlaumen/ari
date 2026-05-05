"""Tests for search_and_rerank function."""

import pytest

from ari.embeddings.search import search_and_rerank
from ari.embeddings.rerank import SearchResult
from ari.input.pdf import Chunk


class TestSearchAndRerankEmptyInputs:
    """Tests for S-1: Empty/invalid input handling."""

    def test_empty_chunks_list_returns_empty(self):
        """S-1: Query with empty chunks list → returns empty SearchResult list."""
        results = search_and_rerank("what is diabetes", [], initial_k=12, final_k=3)
        assert results == []

    def test_initial_k_zero_returns_empty(self):
        """S-1: initial_k <= 0 → returns empty SearchResult list."""
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = search_and_rerank("test query", [chunk], initial_k=0, final_k=3)
        assert results == []

    def test_initial_k_negative_returns_empty(self):
        """S-1: initial_k < 0 → returns empty SearchResult list."""
        chunk = Chunk(text="test", page_start=1, page_end=1, chunk_index=0)
        results = search_and_rerank("test query", [chunk], initial_k=-5, final_k=3)
        assert results == []


class TestSearchAndRerankBehavior:
    """Tests for S-2 through S-5: Function behavior.

    These tests call the real BAML API with sufficient test data so that
    BAML's response (always 3 results) has valid source_chunk_index values.
    """

    def test_expected_output(self):
        """S-3: Normal query with matching chunks → returns up to 3 SearchResult objects."""
        chunks = [
            Chunk(
                text="Foundation design principles for buildings and structures...",
                page_start=1,
                page_end=1,
                chunk_index=0,
            ),
            Chunk(
                text="Pile capacity calculation methods and bearing resistance...",
                page_start=2,
                page_end=2,
                chunk_index=1,
            ),
            Chunk(
                text="Concrete specifications for foundation construction...",
                page_start=3,
                page_end=3,
                chunk_index=2,
            ),
        ]

        # BAML returns exactly 3 results, so we need at least 3 chunks
        results = search_and_rerank(
            "foundation design", chunks, initial_k=12, final_k=3
        )
        assert len(results) == 3

        # Verify descending order
        assert results[0].relevance_score >= results[1].relevance_score
        assert results[1].relevance_score >= results[2].relevance_score

        # Each result's chunk should be one of our input chunks
        input_chunks = {c.chunk_index: c for c in chunks}
        for result in results:
            assert result.chunk.chunk_index in input_chunks
            assert result.chunk is input_chunks[result.chunk.chunk_index]

        # Relevance scores should be between 0 and 1.0
        for result in results:
            assert 0.0 <= result.relevance_score <= 1.0

