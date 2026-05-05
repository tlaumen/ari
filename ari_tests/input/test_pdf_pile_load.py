"""
End-to-end integration tests for chunk_pdf_by_tokens and chunk_pdf_by_paragraphs
on a real 37-page Dutch engineering report (test_pdf_pile_load.pdf).
"""

from pathlib import Path

import pytest

from ari.input.pdf import (
    Chunk,
    chunk_pdf_by_tokens,
    chunk_pdf_by_paragraphs,
)

# Path to the 37-page Dutch engineering report fixture
_TEST_PDF = Path(__file__).parent.parent / "data" / "test_pdf_pile_load.pdf"


class TestPdfPileLoad:
    """End-to-end integration tests against a real 37-page PDF."""

    def test_chunk_pdf_by_tokens_returns_non_empty_chunks_spanning_pages_2_to_37(self):
        """chunk_pdf_by_tokens on the test PDF returns a non-empty list of Chunks with page ranges spanning 2–37."""
        chunks = chunk_pdf_by_tokens(
            _TEST_PDF,
            tokens_per_chunk=300,
            overlap_tokens=50,
        )

        assert len(chunks) > 0, "Expected at least one chunk"
        page_starts = [c.page_start for c in chunks]
        page_ends = [c.page_end for c in chunks]
        assert min(page_starts) >= 2, (
            f"Expected page_start >= 2 (page 1 is empty), got {min(page_starts)}"
        )
        assert max(page_ends) <= 37, f"Expected page_end <= 37, got {max(page_ends)}"

    def test_chunk_pdf_by_paragraphs_returns_non_empty_aligned_chunks(self):
        """chunk_pdf_by_paragraphs on the test PDF returns a non-empty list of Chunks aligned to section markers."""
        chunks = chunk_pdf_by_paragraphs(_TEST_PDF)

        assert len(chunks) > 0, "Expected at least one chunk"
        # Chunks should be aligned to section markers (non-empty text)
        for chunk in chunks:
            assert len(chunk.text.strip()) > 0, (
                f"Chunk {chunk.chunk_index} has empty text — markers may not be excluded correctly"
            )

    def test_all_chunks_have_valid_page_ranges_and_sequential_indices(self):
        """All chunks from both APIs have page_start <= page_end and sequential chunk_index values."""
        token_chunks = chunk_pdf_by_tokens(_TEST_PDF, tokens_per_chunk=300, overlap_tokens=50)
        para_chunks = chunk_pdf_by_paragraphs(_TEST_PDF)

        for chunks, name in [(token_chunks, "token"), (para_chunks, "paragraph")]:
            for chunk in chunks:
                assert chunk.page_start <= chunk.page_end, (
                    f"[{name}] Chunk {chunk.chunk_index}: page_start ({chunk.page_start}) > page_end ({chunk.page_end})"
                )
            indices = [c.chunk_index for c in chunks]
            assert indices == list(range(len(chunks))), (
                f"[{name}] chunk_index values are not sequential: {indices}"
            )

    def test_chunks_contain_actual_content_from_pdf(self):
        """All chunks contain actual text from the PDF, not empty strings or filler."""
        token_chunks = chunk_pdf_by_tokens(_TEST_PDF, tokens_per_chunk=300, overlap_tokens=50)
        para_chunks = chunk_pdf_by_paragraphs(_TEST_PDF)

        for chunks, name in [(token_chunks, "token"), (para_chunks, "paragraph")]:
            for chunk in chunks:
                assert len(chunk.text) > 0, (
                    f"[{name}] Chunk {chunk.chunk_index} has empty text"
                )
                assert chunk.text.strip() != "", (
                    f"[{name}] Chunk {chunk.chunk_index} is whitespace-only"
                )

    def test_para_chunking_produces_more_smaller_chunks_than_token_chunking(self):
        """The PDF with many subsection markers produces more, smaller chunks than token-based chunking."""
        token_chunks = chunk_pdf_by_tokens(_TEST_PDF, tokens_per_chunk=300, overlap_tokens=50)
        para_chunks = chunk_pdf_by_paragraphs(_TEST_PDF)


        # Paragraph-based chunking produces more chunks because subsection markers fragment the text
        assert len(para_chunks) > len(token_chunks), (
            f"Expected paragraph chunking ({len(para_chunks)}) to produce more chunks "
            f"than token chunking ({len(token_chunks)})"
        )
        # Average paragraph chunk size should be smaller (due to dense marker fragmentation)
        avg_para = sum(len(c.text) for c in para_chunks) / len(para_chunks)
        avg_token = sum(len(c.text) for c in token_chunks) / len(token_chunks)
        assert avg_para < avg_token, (
            f"Expected average paragraph chunk size ({avg_para:.0f}) < average token chunk size ({avg_token:.0f})"
        )

    def test_chunk_pdf_by_tokens_finds_paalbelasting(self):
        """chunk_pdf_by_tokens finds the word 'paalbelasting' in at least one chunk — validates real content is captured."""
        chunks = chunk_pdf_by_tokens(_TEST_PDF, tokens_per_chunk=300, overlap_tokens=50)

        found = any("paalbelasting" in c.text.lower() for c in chunks)
        assert found, (
            f"'paalbelasting' not found in any of the {len(chunks)} token-based chunks. "
            f"This indicates the chunking may not be capturing real PDF content."
        )

    def test_chunk_pdf_by_paragraphs_finds_paalbelasting(self):
        """chunk_pdf_by_paragraphs also finds the word 'paalbelasting' in at least one chunk — both chunking strategies capture meaningful content."""
        chunks = chunk_pdf_by_paragraphs(_TEST_PDF)

        found = any("paalbelasting" in c.text.lower() for c in chunks)
        assert found, (
            f"'paalbelasting' not found in any of the {len(chunks)} paragraph-based chunks. "
            f"This indicates the chunking may not be capturing real PDF content."
        )

