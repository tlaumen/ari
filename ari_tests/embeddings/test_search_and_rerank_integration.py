"""End-to-end integration tests for search_and_rerank() against a real PDF."""

from pathlib import Path

import pytest

from ari.embeddings.search import search_and_rerank
from ari.input.pdf import chunk_by_tokens, extract_text_from_pdf

_TEST_PDF = Path(__file__).parent.parent / "data" / "test_pdf_pile_load.pdf"


class TestSearchAndRerankIntegration:
    """End-to-end integration tests using the real 37-page Dutch engineering PDF."""

    def test_search_and_rerank_finds_pile_load_values(self):
        """search_and_rerank finds pile load values ("152 kN", "79 kN") in top results when searching "paalbelasting"."""
        # Extract text from the real PDF
        page_texts = extract_text_from_pdf(_TEST_PDF)

        # Chunk with smaller token sizes so "paalbelasting" likely appears in its own chunk
        chunks = chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=30)

        # Search and rerank for "paalbelasting"
        results = search_and_rerank("paalbelasting", chunks, initial_k=12, final_k=3)

        for result in results:
            print("\n" + "-" * 50 + "\n")
            print(result)
            print("\n" + "-" * 50 + "\n")

        # Verify we got results
        assert len(results) > 0, f"Expected at least 1 result, got {len(results)}"

        # At least one result's answer should contain a pile load value
        # Note: The answer attribute is the BAML-extracted answer, not the raw chunk text
        load_values = ["152 kN", "79 kN"]
        found = any(
            any(val in result.answer for val in load_values) for result in results
        )
        assert found, (
            f"'paalbelasting' search_and_rerank did not return any result with answer "
            f"containing load values {load_values}. Results: "
            f"[(answer='{r.answer[:100]}...', score={r.relevance_score:.3f}) for r in results]"
        )
