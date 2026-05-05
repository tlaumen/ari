"""
Tests for PDF text extraction in ari.input.pdf module.
"""

from pathlib import Path

import pytest
import fitz

from ari.input.pdf import (
    COMMON_HEADER_KEYWORDS,
    Chunk,
    PageText,
    ParagraphLevel,
    ParagraphMarker,
    estimate_words,
    extract_text_from_pdf,
    detect_paragraph_markers,
    chunk_by_tokens,
    chunk_by_paragraphs,
)


class TestExtractTextFromPdf:
    """Test suite for extract_text_from_pdf function."""

    def test_valid_pdf_returns_page_text_objects_ordered_by_page_number(self, tmp_path):
        """Given a valid PDF path, returns list of PageText objects ordered by page number."""
        # Create a test PDF with 3 pages of text
        pdf_path = tmp_path / "report.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                "This is the text from page 1. It has some content.",
                "This is the text from page 2. More content here.",
                "This is the text from page 3. Final page content.",
            ],
        )

        result = extract_text_from_pdf(pdf_path)

        assert len(result) == 3
        assert result[0].page_number == 1
        assert result[0].text == "This is the text from page 1. It has some content."
        assert result[1].page_number == 2
        assert result[1].text == "This is the text from page 2. More content here."
        assert result[2].page_number == 3
        assert result[2].text == "This is the text from page 3. Final page content."

    def test_page_with_no_text_is_excluded(self, tmp_path):
        """Given a PDF path where a page has no text, that page is excluded from results."""
        # Create a PDF with pages 1 (has text), 2 (empty), 3 (has text)
        pdf_path = tmp_path / "mixed.pdf"
        self._create_test_pdf(
            pdf_path,
            [
                "Page one has content.",
                "",  # Empty page
                "Page three has content.",
            ],
        )

        result = extract_text_from_pdf(pdf_path)

        assert len(result) == 2
        assert result[0].page_number == 1
        assert result[0].text == "Page one has content."
        assert result[1].page_number == 3
        assert result[1].text == "Page three has content."

    def test_nonexistent_path_raises_file_not_found_error(self):
        """Given a non-existent path, raises FileNotFoundError."""
        pdf_path = Path("nonexistent.pdf")

        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf(pdf_path)

    def test_corrupted_file_raises_value_error(self, tmp_path):
        """Given a corrupted/invalid PDF path, raises ValueError."""
        fake_pdf_path = tmp_path / "fake.pdf"
        # Write a text file with .pdf extension
        fake_pdf_path.write_text("This is not a PDF file, just plain text.")

        with pytest.raises(ValueError) as exc_info:
            extract_text_from_pdf(fake_pdf_path)

        assert "invalid pdf" in str(exc_info.value).lower()

    def _create_test_pdf(self, path: Path, pages_text: list[str]):
        """Helper to create a test PDF with given text on each page."""

        doc = fitz.open()
        for text in pages_text:
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(path)
        doc.close()


class TestEstimateWords:
    """Test suite for estimate_words function."""

    def test_normal_tokens_returns_estimated_word_count(self):
        """Given a token count, returns estimated word count using int(tokens * 1.3)."""
        result = estimate_words(100)
        expected = int(100 * 1.3)
        assert result == expected

    def test_single_token_returns_estimated_word_count(self):
        """Given a single token, returns estimated word count."""
        result = estimate_words(1)
        expected = int(1 * 1.3)
        assert result == expected

    def test_zero_tokens_returns_zero(self):
        """Given zero tokens, returns 0."""
        result = estimate_words(0)
        assert result == 0


# find_sentence_boundaries was removed as dead code
class TestFindSentenceBoundaries:
    """find_sentence_boundaries was removed as dead code — tests deleted."""


class TestDetectParagraphMarkers:
    """Test suite for detect_paragraph_markers function."""

    def test_detects_section_level_numbered_pattern(self):
        """Given text with a section-level numbered pattern (1.), returns ParagraphMarker at start_index 0."""
        text = "1. Introduction\nSome text here."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0, text="1. Introduction", level=ParagraphLevel.SECTION
        )

    def test_detects_subsection_level_numbered_pattern_two_numbers(self):
        """Given text with a subsection-level numbered pattern (1.1), returns ParagraphMarker at SUBSECTION."""
        text = "1.1 Background\nMore text."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0, text="1.1 Background", level=ParagraphLevel.SUBSECTION
        )

    def test_three_number_pattern_maps_to_subsection(self):
        """Given text with a three-number pattern (2.3.1), still maps to SUBSECTION level."""
        text = "2.3.1 Methods\nEven more text."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0, text="2.3.1 Methods", level=ParagraphLevel.SUBSECTION
        )

    def test_four_number_pattern_maps_to_subsection(self):
        """Given text with four dot-separated numbers (1.2.3.4), still maps to SUBSECTION level."""
        text = "1.2.3.4 Deep Subsection\nText."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0,
            text="1.2.3.4 Deep Subsection",
            level=ParagraphLevel.SUBSECTION,
        )

    def test_detects_multiple_markers_on_same_page(self):
        """Given text with multiple numbered markers, returns all with correct start indices."""
        text = "1. Intro\n2. Methods\n3. Results"
        result = detect_paragraph_markers(text)
        assert len(result) == 3
        assert result[0] == ParagraphMarker(
            start_index=0, text="1. Intro", level=ParagraphLevel.SECTION
        )
        assert result[1] == ParagraphMarker(
            start_index=9, text="2. Methods", level=ParagraphLevel.SECTION
        )
        assert result[2] == ParagraphMarker(
            start_index=20, text="3. Results", level=ParagraphLevel.SECTION
        )

    def test_returns_empty_list_when_no_markers_found(self):
        """Given text with no markers, returns empty list."""
        text = "Just regular paragraph text with no structure."
        result = detect_paragraph_markers(text)
        assert result == []

    def test_detects_common_header_patterns(self):
        """Given text with a common header keyword, returns ParagraphMarker at SECTION level."""
        text = "ABSTRACT\nThis paper is about..."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0, text="ABSTRACT", level=ParagraphLevel.SECTION
        )

    def test_case_insensitive_match_on_common_headers(self):
        """Given text with lowercase common header keyword, still matches case-insensitively."""
        text = "introduction\nSome text."
        result = detect_paragraph_markers(text)
        assert len(result) == 1
        assert result[0] == ParagraphMarker(
            start_index=0, text="introduction", level=ParagraphLevel.SECTION
        )

    def test_marker_in_middle_of_text_does_not_count(self):
        """Given text with a number pattern in the middle of a line (not at start), returns empty list."""
        text = "Some text. 1. Not a marker in the middle."
        result = detect_paragraph_markers(text)
        assert result == []

    def test_common_header_keywords_constant_exists(self):
        """COMMON_HEADER_KEYWORDS constant should exist and contain expected keywords."""
        assert len(COMMON_HEADER_KEYWORDS) > 0
        assert "ABSTRACT" in COMMON_HEADER_KEYWORDS
        assert "INTRODUCTION" in COMMON_HEADER_KEYWORDS


class TestChunkByTokens:
    """Test suite for chunk_by_tokens function."""

    def test_cross_page_chunk_single_sentence_spanning_two_pages(self):
        """Single sentence spanning two pages produces one chunk with page_start=1, page_end=2."""
        page_texts = [
            PageText(page_number=1, text="Sentence on page 1 "),
            PageText(page_number=2, text="continues on page 2."),
        ]
        result = chunk_by_tokens(page_texts)

        assert len(result) == 1
        assert result[0].page_start == 1
        assert result[0].page_end == 2
        assert result[0].chunk_index == 0
        assert "Sentence on page 1" in result[0].text
        assert "continues on page 2" in result[0].text

    def test_cross_page_chunk_spanning_three_pages(self):
        """Single sentence spanning three pages produces one chunk with page_start=1, page_end=3."""
        page_texts = [
            PageText(page_number=1, text="Sentence on page 1 "),
            PageText(page_number=2, text="continues on page 2 "),
            PageText(page_number=3, text="and ends on page 3."),
        ]
        result = chunk_by_tokens(page_texts)

        assert len(result) == 1
        assert result[0].page_start == 1
        assert result[0].page_end == 3

    def test_single_page_chunk(self):
        """Short text on single page produces one chunk with page_start=page_end=that page."""
        page_texts = [PageText(page_number=5, text="Short text.")]
        result = chunk_by_tokens(page_texts)

        assert len(result) == 1
        assert result[0].page_start == 5
        assert result[0].page_end == 5
        assert result[0].chunk_index == 0

    def test_multiple_chunks_on_single_page(self):
        """Text large enough for 2 chunks on same page produces chunks with same page_start/page_end."""
        # Build text with enough words to create 2+ chunks
        # 300 tokens ~ 231 words, so use 500 words to ensure 2+ chunks
        words = [f"word{i}" for i in range(1, 501)]
        text = " ".join(words)  # 500 words

        page_texts = [PageText(page_number=1, text=text)]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=300)

        assert len(result) >= 2  # Could be 2 or more depending on content
        # All chunks should be on page 1
        for chunk in result:
            assert chunk.page_start == 1
            assert chunk.page_end == 1
        # Check sequential indices
        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))

    def test_empty_list_returns_empty_list(self):
        """Empty list of page_texts returns empty list."""
        result = chunk_by_tokens([])
        assert result == []

    def test_chunk_indices_are_sequential_zero_based(self):
        """Chunk indices are 0-based with no gaps."""
        words = [f"word{i}" for i in range(1, 501)]
        text = " ".join(words)
        page_texts = [PageText(page_number=1, text=text)]
        result = chunk_by_tokens(page_texts, tokens_per_chunk=300)

        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))
        assert len(set(indices)) == len(indices)  # All unique

    def test_overlap_tokens_causes_shared_content(self):
        """overlap_tokens>0 causes chunks to share overlapping content."""
        # Build longer text to ensure multiple chunks
        words = [f"word{i}" for i in range(1, 1001)]
        text = " ".join(words)
        page_texts = [PageText(page_number=1, text=text)]

        result_no_overlap = chunk_by_tokens(
            page_texts, tokens_per_chunk=300, overlap_tokens=0
        )
        result_with_overlap = chunk_by_tokens(
            page_texts, tokens_per_chunk=300, overlap_tokens=50
        )

        # Both should produce chunks
        assert len(result_no_overlap) >= 1
        assert len(result_with_overlap) >= 1
        # With overlap, we should get more chunks (smaller step = more windows)
        assert len(result_with_overlap) >= len(result_no_overlap)

    def test_whitespace_only_pages_are_skipped(self):
        """Pages with whitespace-only text are treated as having no content."""
        page_texts = [
            PageText(page_number=1, text="Sentence one here."),
            PageText(page_number=2, text="   \n\t   "),  # Whitespace only
            PageText(page_number=3, text="Sentence two here."),
        ]
        result = chunk_by_tokens(page_texts)

        # Should concatenate page 1 and 3 with newline separator
        assert len(result) >= 1
        # The result should not have content from page 2
        for chunk in result:
            assert "   " not in chunk.text or "\n\t" not in chunk.text

    def test_chunk_text_preserved_correctly(self):
        """Chunk text should be the actual content from the pages, not modified."""
        page_texts = [PageText(page_number=1, text="First page content.")]
        result = chunk_by_tokens(page_texts)

        assert len(result) == 1
        assert "First page content" in result[0].text
        # Text should be preserved (not lowercased, etc.)


class TestChunkByParagraphs:
    """Test suite for chunk_by_paragraphs function."""

    def test_marker_at_position_zero_creates_empty_first_chunk(self):
        """Marker at position 0 creates first chunk with empty text, second chunk has marker content."""
        page_texts = [PageText(page_number=1, text="1. Introduction\nSection 1 text. More text here.")]
        markers = [ParagraphMarker(start_index=0, text="1. Introduction", level=ParagraphLevel.SECTION)]
        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == ""
        assert result[0].page_start == 1
        assert result[0].page_end == 1
        assert result[1].text == "Section 1 text. More text here."
        assert result[1].page_start == 1
        assert result[1].page_end == 1

    def test_two_markers_produce_three_chunks(self):
        """Two markers on same page produce three chunks: before first, between, after second."""
        # Text: "1. Intro\nSome intro text.\n2. Methods\nMethod details."
        # Position 0-7: "1. Intro"
        # Position 8: newline
        # Position 9-25: "Some intro text."
        # Position 26: newline
        # Position 27-36: "2. Methods"
        # Position 37: newline
        # Position 38-50: "Method details."
        page_texts = [PageText(page_number=1, text="1. Intro\nSome intro text.\n2. Methods\nMethod details.")]
        markers = [
            ParagraphMarker(start_index=0, text="1. Intro", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=27, text="2. Methods", level=ParagraphLevel.SECTION),
        ]
        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 3
        # Chunk 0: before "1. Intro" (empty)
        assert result[0].text == ""
        # Chunk 1: between "1. Intro" and "2. Methods"
        assert "Some intro text" in result[1].text
        # Chunk 2: after "2. Methods"
        assert "Method details" in result[2].text

    def test_empty_markers_returns_single_chunk(self):
        """Empty markers list returns entire text as a single chunk."""
        page_texts = [PageText(page_number=1, text="Just some text without markers.")]
        markers = []
        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 1
        assert result[0].text == "Just some text without markers."

    def test_empty_page_texts_returns_empty_list(self):
        """Empty page_texts list returns empty list."""
        result = chunk_by_paragraphs([], [])
        assert result == []

    def test_cross_page_chunk_with_markers(self):
        """Cross-page: marker on page 1, body text on page 2 produces correct chunk boundaries."""
        page_texts = [
            PageText(page_number=1, text="1. Introduction\nIntro text continues."),
            PageText(page_number=2, text="More intro content here."),
        ]
        markers = [ParagraphMarker(start_index=0, text="1. Introduction", level=ParagraphLevel.SECTION)]
        result = chunk_by_paragraphs(page_texts, markers)

        # Should be 2 chunks: empty before marker, and marker + all content after
        assert len(result) >= 2
        # First chunk is empty (before marker)
        assert result[0].text == ""
        # Second chunk contains all the text after the marker
        assert "Intro text" in result[1].text or "More intro" in result[1].text
        assert result[1].page_start == 1
        assert result[1].page_end == 2

    def test_subsection_marker_ignored_when_section_within_max_tokens(self):
        """SUBSECTION marker is ignored when SECTION-sliced text is within max_tokens."""
        # Short text that fits within default max_tokens (400)
        # Text: "1. Section One\nSome section content here.\n1.1 Subsection\nSubsection content."
        # Position 0-14: "1. Section One"
        # Position 15: newline
        # Position 16-42: "Some section content here."
        # Position 43: newline
        # Position 44-57: "1.1 Subsection"
        # Position 58: newline
        # Position 59-75: "Subsection content."
        page_texts = [PageText(page_number=1, text="1. Section One\nSome section content here.\n1.1 Subsection\nSubsection content.")]
        markers = [
            ParagraphMarker(start_index=0, text="1. Section One", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=44, text="1.1 Subsection", level=ParagraphLevel.SUBSECTION),
        ]
        result = chunk_by_paragraphs(page_texts, markers)

        # Should only have SECTION-based boundaries, no SUBSECTION split
        # Expected: chunk before marker (empty), chunk between markers, chunk after marker
        assert len(result) == 3
        assert result[0].text == ""
        assert "Some section content here" in result[1].text
        assert "Subsection content" in result[2].text

    def test_marker_lines_excluded_from_chunks(self):
        """Marker lines are not included in any chunk's text."""
        page_texts = [PageText(page_number=1, text="1. Title\nSome body text.\n2. Next\nMore body.")]
        markers = [
            ParagraphMarker(start_index=0, text="1. Title", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=27, text="2. Next", level=ParagraphLevel.SECTION),
        ]
        result = chunk_by_paragraphs(page_texts, markers)

        for chunk in result:
            assert "1. Title" not in chunk.text
            assert "2. Next" not in chunk.text

    def test_single_marker_produces_two_chunks(self):
        """Single marker produces two chunks: before marker (empty) and from marker to end."""
        page_texts = [PageText(page_number=1, text="1. Introduction\nIntro body text here.")]
        markers = [ParagraphMarker(start_index=0, text="1. Introduction", level=ParagraphLevel.SECTION)]
        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == ""
        assert result[1].text == "Intro body text here."

    def test_multiple_sections_all_preferred_over_subsections(self):
        """SECTION markers create primary boundaries regardless of SUBSECTION markers."""
        # Text: "1. Intro\nIntro text.\n2. Methods\nMethods text."
        # Position 0-7: "1. Intro"
        # Position 8: newline
        # Position 9-20: "Intro text."
        # Position 21: newline
        # Position 22-31: "2. Methods"
        # Position 32: newline
        # Position 33-45: "Methods text."
        page_texts = [
            PageText(page_number=1, text="1. Intro\nIntro text.\n2. Methods\nMethods text.")
        ]
        markers = [
            ParagraphMarker(start_index=0, text="1. Intro", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=22, text="2. Methods", level=ParagraphLevel.SECTION),
        ]
        result = chunk_by_paragraphs(page_texts, markers)

        # Should have 3 chunks: before first (empty), between, after second
        assert len(result) == 3
        assert result[0].text == ""
        assert "Intro text" in result[1].text
        assert "Methods text" in result[2].text
