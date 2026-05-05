"""
Tests for chunk_pdf_by_paragraphs public API.
"""

from pathlib import Path

import pytest
import fitz

from ari.input.pdf import (
    Chunk,
    chunk_pdf_by_paragraphs,
)


class TestChunkPdfByParagraphs:
    """Test suite for chunk_pdf_by_paragraphs function."""

    def test_valid_pdf_with_section_markers_returns_aligned_chunks(self, tmp_path):
        """Valid PDF with SECTION markers returns chunks aligned to those markers."""
        pdf_path = tmp_path / "structured.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                "1. Introduction\nThis is the introduction text.",
                "2. Methods\nThis is the methods section.",
            ],
        )

        result = chunk_pdf_by_paragraphs(pdf_path)

        # Should have 3 chunks: before first marker (empty), between markers, after last marker
        assert len(result) == 3
        # Chunk indices should be sequential
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1
        assert result[2].chunk_index == 2
        # First chunk is before first marker (empty since marker at position 0)
        assert result[0].text == ""
        # Second chunk should contain the intro body text
        assert "introduction text" in result[1].text.lower()
        # Last chunk should contain the methods body text
        assert "methods section" in result[2].text.lower()

    def test_valid_pdf_with_no_markers_returns_single_chunk(self, tmp_path):
        """Valid PDF with no markers returns single chunk with all text."""
        pdf_path = tmp_path / "plain.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                "This is plain text without any section markers.",
                "More plain text on the second page.",
            ],
        )

        result = chunk_pdf_by_paragraphs(pdf_path)

        assert len(result) == 1
        assert result[0].chunk_index == 0
        assert "plain text" in result[0].text.lower()
        assert result[0].page_start == 1
        assert result[0].page_end == 2

    def test_valid_pdf_with_only_whitespace_pages_returns_empty_list(self, tmp_path):
        """Valid PDF with only whitespace pages returns empty list."""
        pdf_path = tmp_path / "blank.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                "   \n\t   ",
                "   ",
                "",
            ],
        )

        result = chunk_pdf_by_paragraphs(pdf_path)

        assert result == []

    def test_nonexistent_path_raises_file_not_found_error(self):
        """Non-existent PDF path raises FileNotFoundError."""
        pdf_path = Path("nonexistent_file.pdf")

        with pytest.raises(FileNotFoundError):
            chunk_pdf_by_paragraphs(pdf_path)

    def test_invalid_corrupted_pdf_raises_value_error(self, tmp_path):
        """Invalid/corrupted PDF raises ValueError."""
        fake_pdf_path = tmp_path / "corrupted.pdf"
        # Write a text file with .pdf extension
        fake_pdf_path.write_text("This is not a valid PDF, just plain text.")

        with pytest.raises(ValueError) as exc_info:
            chunk_pdf_by_paragraphs(fake_pdf_path)

        assert "invalid pdf" in str(exc_info.value).lower()

    def _create_test_pdf(self, path: Path, pages_text: list[str]):
        """Helper to create a test PDF with given text on each page."""
        doc = fitz.open()
        for text in pages_text:
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(path)
        doc.close()
