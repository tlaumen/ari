"""End-to-end integration tests for search_chunks() against a real PDF."""

from pathlib import Path

import pytest

from ari.embeddings.search import search_chunks
from ari.input.pdf import chunk_by_tokens, extract_text_from_pdf

_TEST_PDF = Path(__file__).parent.parent / "data" / "test_pdf_pile_load.pdf"


class TestSearchChunksIntegration:
    """End-to-end integration tests using the real 37-page Dutch engineering PDF."""

    def test_search_chunks_finds_pile_loads_from_pdf(self):
        """search_chunks finds pile load values ("152 kN", "79 kN") in top-k results when searching "paalbelasting"."""
        # Extract text from the real PDF
        page_texts = extract_text_from_pdf(_TEST_PDF)

        # Chunk using smaller token sizes so "paalbelasting" likely appears in its own chunk
        chunks = chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=30)

        # Search for "paalbelasting"
        results = search_chunks("paalbelasting", chunks, k=5)

        # Verify we got results
        assert len(results) > 0, f"Expected at least 1 result, got {len(results)}"

        # At least one of the top-5 results should contain a load value
        load_values = ["152 kN", "79 kN"]
        found = any(
            any(val in chunk.text for val in load_values) for _, chunk in results
        )
        assert found, (
            f"'paalbelasting' search did not return any chunk with load values {load_values}. "
            f"Top results: {[c.text[:100] for _, c in results]}"
        )
