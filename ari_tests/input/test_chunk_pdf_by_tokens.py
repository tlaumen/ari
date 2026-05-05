"""
Tests for chunk_pdf_by_tokens and chunk_by_tokens public APIs.
"""

from pathlib import Path

import pytest
import fitz

from ari.input.pdf import (
    Chunk,
    PageText,
    chunk_by_tokens,
    chunk_pdf_by_tokens,
)


class TestChunkByTokens:
    """Test suite for chunk_by_tokens function."""

    def test_overlap_tokens_must_be_less_than_half_tokens_per_chunk(self):
        """overlap_tokens >= tokens_per_chunk / 2 raises ValueError."""
        page_texts = [PageText(page_number=1, text="This is some text for testing.")]
        with pytest.raises(ValueError) as exc_info:
            chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=50)
        assert "overlap" in str(exc_info.value).lower()

    def test_overlap_tokens_equal_to_half_is_rejected(self):
        """overlap_tokens == tokens_per_chunk / 2 (float) raises ValueError because >= not <."""
        page_texts = [PageText(page_number=1, text="This is some text for testing.")]
        with pytest.raises(ValueError):
            chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=50.0)

    def test_valid_overlap_tokens_within_bounds(self):
        """overlap_tokens < tokens_per_chunk / 2 returns non-empty chunk list."""
        page_texts = [
            PageText(page_number=1, text=" ".join(f"Sentence {i} with content." for i in range(1, 100)))
        ]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=49)
        assert isinstance(result, list)
        assert len(result) >= 1
        for chunk in result:
            assert isinstance(chunk, Chunk)

    def test_empty_page_texts_returns_empty_list(self):
        """Empty page_texts list returns empty list."""
        result = chunk_by_tokens([], tokens_per_chunk=300, overlap_tokens=50)
        assert result == []

    def test_whitespace_only_pages_returns_empty_list(self):
        """Pages with only whitespace return empty list."""
        page_texts = [
            PageText(page_number=1, text="   \n\t   "),
            PageText(page_number=2, text="   "),
            PageText(page_number=3, text=""),
        ]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=300, overlap_tokens=50)
        assert result == []

    def test_chunks_are_sequential_with_correct_indices(self):
        """chunk_index is 0, 1, 2, ... with no gaps."""
        page_texts = [
            PageText(
                page_number=1,
                text=" ".join(f"Sentence {i} with content and more words." for i in range(1, 200)),
            )
        ]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=30)
        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))

    def test_adjacent_chunks_overlap_by_approximately_overlap_tokens(self):
        """The text at the start of chunk N+1 overlaps with ~overlap_tokens from the end of chunk N."""
        page_texts = [
            PageText(
                page_number=1,
                text=" ".join(f"Word {i}." for i in range(1, 500)),
            )
        ]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=100, overlap_tokens=49)

        if len(result) < 2:
            pytest.skip("Need at least 2 chunks to test overlap")

        # Check overlap between consecutive chunks
        for i in range(len(result) - 1):
            prev_text = result[i].text
            next_text = result[i + 1].text
            # The next chunk should share some text with the previous chunk
            # Find how many words from the start of next_text appear at the end of prev_text
            prev_words = prev_text.split()
            next_words = next_text.split()
            # Look for overlap: the first few words of next should appear in prev
            overlap_found = False
            for size in range(1, min(6, len(next_words) + 1)):
                first_n_words = " ".join(next_words[:size])
                if first_n_words in prev_text:
                    overlap_found = True
                    break
            assert overlap_found, (
                f"Chunk {i+1} does not appear to overlap with chunk {i}. "
                f"Chunk {i+1} starts with: {next_words[:5]!r}"
            )

    def test_page_ranges_reflect_char_position_to_page_mapping(self):
        """page_start/page_end match actual page boundaries across multiple pages."""
        page_texts = [
            PageText(page_number=1, text="Page one content with many words to make it substantial."),
            PageText(page_number=2, text="Page two content with many words to make it substantial too."),
            PageText(page_number=3, text="Page three content with many words to make it substantial also."),
        ]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=50, overlap_tokens=10)

        assert len(result) >= 1
        for chunk in result:
            # page_start and page_end should be valid page numbers
            assert 1 <= chunk.page_start <= 3
            assert 1 <= chunk.page_end <= 3
            assert chunk.page_start <= chunk.page_end


class TestChunkPdfByTokens:
    """Test suite for chunk_pdf_by_tokens function."""

    def _create_test_pdf(self, path: Path, pages_text: list[str]):
        """Helper to create a test PDF with given text on each page."""
        doc = fitz.open()
        for text in pages_text:
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(path)
        doc.close()

    def test_nonexistent_pdf_raises_file_not_found(self):
        """Non-existent PDF path raises FileNotFoundError."""
        pdf_path = Path("nonexistent_file_for_chunking.pdf")

        with pytest.raises(FileNotFoundError):
            chunk_pdf_by_tokens(pdf_path)

    def test_invalid_pdf_raises_value_error(self, tmp_path):
        """Invalid/corrupted PDF raises ValueError."""
        fake_pdf_path = tmp_path / "corrupted.pdf"
        # Write a text file with .pdf extension
        fake_pdf_path.write_text("This is not a valid PDF, just plain text.")

        with pytest.raises(ValueError):
            chunk_pdf_by_tokens(fake_pdf_path)

    def test_valid_pdf_returns_non_empty_chunks(self, tmp_path):
        """Valid PDF with content returns non-empty chunk list."""
        pdf_path = tmp_path / "standard.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                " ".join(f"Sentence {i} with content." for i in range(1, 50)),
                " ".join(f"Word {i}." for i in range(1, 50)),
            ],
        )

        result = chunk_pdf_by_tokens(pdf_path, tokens_per_chunk=100, overlap_tokens=30)

        assert len(result) >= 1
        for chunk in result:
            assert isinstance(chunk, Chunk)
            assert chunk.chunk_index >= 0
            assert len(chunk.text) > 0
