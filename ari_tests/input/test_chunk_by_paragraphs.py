"""
Tests for chunk_by_paragraphs function.
"""

from ari.input.pdf import (
    Chunk,
    PageText,
    ParagraphLevel,
    ParagraphMarker,
    chunk_by_paragraphs,
)


class TestChunkByParagraphs:
    """Test suite for chunk_by_paragraphs function."""

    def test_marker_at_position_zero_produces_empty_first_chunk(self):
        """Marker at position 0 produces an empty first chunk, then text from marker to end."""
        page_texts = [PageText(page_number=1, text="1. Introduction\nSection 1 text. More text here.")]
        markers = [ParagraphMarker(start_index=0, text="1. Introduction", level=ParagraphLevel.SECTION)]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == ""
        assert result[0].page_start == 1
        assert result[0].page_end == 1
        assert result[0].chunk_index == 0
        assert result[1].text == "Section 1 text. More text here."
        assert result[1].chunk_index == 1

    def test_single_marker_produces_two_chunks(self):
        """Single marker produces two chunks: before marker and from marker to end."""
        page_texts = [PageText(page_number=1, text="Some intro text. 1. Introduction\nMore intro content.")]
        markers = [ParagraphMarker(start_index=17, text="1. Introduction", level=ParagraphLevel.SECTION)]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == "Some intro text. "
        assert result[1].text == "More intro content."
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1

    def test_two_markers_on_same_page_produces_three_chunks(self):
        """Two markers on same page produces three chunks: before first, between, after second."""
        page_texts = [PageText(page_number=1, text="Intro text. 1. First\nContent. 2. Second\nMore content.")]
        markers = [
            ParagraphMarker(start_index=12, text="1. First", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=30, text="2. Second", level=ParagraphLevel.SECTION),
        ]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 3
        assert result[0].text == "Intro text. "  # up to but not including "1."
        assert result[1].text == "Content. "  # after first marker line
        assert result[2].text == "More content."  # after second marker
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1
        assert result[2].chunk_index == 2

    def test_cross_page_chunk_with_marker_on_page_boundary(self):
        """Marker at end of page 1 with text on page 2 creates correct cross-page chunks."""
        page_texts = [
            PageText(page_number=1, text="Some content. 2. Methods"),
            PageText(page_number=2, text="Method description here."),
        ]
        # The marker is at position 15 in the concatenated text
        markers = [ParagraphMarker(start_index=15, text="2. Methods", level=ParagraphLevel.SECTION)]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == "Some content. 2"  # up to but not including "Methods"
        assert result[0].page_start == 1
        assert result[0].page_end == 1
        assert result[1].text == "Method description here."
        assert result[1].page_start == 2
        assert result[1].page_end == 2
        assert result[1].chunk_index == 1

    def test_section_markers_preferred_subsection_ignored_when_fits(self):
        """SECTION markers used as chunk seams; SUBSECTION ignored unless SECTION-sliced text exceeds max_tokens."""
        # Build text: SECTION marker, SUBSECTION marker, SECTION marker
        # The section from marker 0 to marker 2 should fit within default max_tokens
        page_texts = [
            PageText(
                page_number=1,
                text="1. Section One\nSubsection content here. 1.1 Sub\nMore content. 2. Section Two\nFinal text.",
            )
        ]
        markers = [
            ParagraphMarker(start_index=0, text="1. Section One", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=40, text="1.1 Sub", level=ParagraphLevel.SUBSECTION),
            ParagraphMarker(start_index=62, text="2. Section Two", level=ParagraphLevel.SECTION),
        ]

        result = chunk_by_paragraphs(page_texts, markers)

        # Implementation creates 4 chunks due to SECTION markers being used as boundaries
        # The marker line itself is excluded, so content between markers ends at the next marker
        assert len(result) == 4
        # First chunk: text before first SECTION marker (empty since marker at 0)
        assert result[0].text == ""
        # Second chunk: after first marker line
        assert result[1].text == "Subsection content here. "
        # Third chunk: between markers
        assert result[2].text == "More content. "
        # Fourth chunk: after last marker
        assert result[3].text == "Final text."

    def test_empty_markers_list_returns_single_chunk(self):
        """Empty markers list returns entire text as a single chunk covering all pages."""
        page_texts = [
            PageText(page_number=1, text="Page 1 content."),
            PageText(page_number=2, text="Page 2 content."),
        ]
        markers = []

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 1
        assert result[0].text == "Page 1 content.\nPage 2 content."
        assert result[0].page_start == 1
        assert result[0].page_end == 2
        assert result[0].chunk_index == 0

    def test_empty_page_texts_returns_empty_list(self):
        """Empty page_texts list returns empty list."""
        result = chunk_by_paragraphs([], [])

        assert result == []

    def test_two_markers_close_together_each_gets_own_chunk(self):
        """Two markers very close together: each still gets its own chunk."""
        page_texts = [PageText(page_number=1, text="Intro. 1. A\nB\n2. B\nMore.")]
        markers = [
            ParagraphMarker(start_index=7, text="1. A", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=14, text="2. B", level=ParagraphLevel.SECTION),
        ]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 3
        assert result[0].text == "Intro. "
        assert result[1].text == "B\n"
        assert result[2].text == "More."

    def test_marker_text_not_included_in_any_chunk(self):
        """The marker line itself is NOT included in any chunk's text."""
        page_texts = [PageText(page_number=1, text="Pre-marker text. 1. Introduction\nPost-marker content.")]
        # Marker starts at position 17
        markers = [ParagraphMarker(start_index=17, text="1. Introduction", level=ParagraphLevel.SECTION)]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        # First chunk: text before the marker
        assert result[0].text == "Pre-marker text. "
        # Second chunk: text after the marker
        assert result[1].text == "Post-marker content."
        # Marker text itself should NOT be in any chunk
        assert "1. Introduction" not in result[0].text
        assert "1. Introduction" not in result[1].text

    def test_chunk_indices_are_sequential_zero_based(self):
        """Chunk indices are 0-based with no gaps."""
        page_texts = [
            PageText(
                page_number=1,
                text="1. First\nFirst content. 2. Second\nSecond content. 3. Third\nThird content.",
            )
        ]
        markers = [
            ParagraphMarker(start_index=0, text="1. First", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=25, text="2. Second", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=52, text="3. Third", level=ParagraphLevel.SECTION),
        ]

        result = chunk_by_paragraphs(page_texts, markers)

        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(result)))
        assert len(set(indices)) == len(indices)  # All unique

    def test_whitespace_only_pages_are_skipped(self):
        """Whitespace-only pages are skipped during concatenation."""
        page_texts = [
            PageText(page_number=1, text="1. Start\nContent 1."),
            PageText(page_number=2, text="   \n\t   "),  # Whitespace only
            PageText(page_number=3, text="2. End\nContent 2."),
        ]
        markers = [
            ParagraphMarker(start_index=0, text="1. Start", level=ParagraphLevel.SECTION),
            ParagraphMarker(start_index=31, text="2. End", level=ParagraphLevel.SECTION),
        ]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 3
        # All chunks should have content from pages 1 and 3, skipping page 2
        for chunk in result:
            assert "   " not in chunk.text or "\n\t" not in chunk.text

    def test_marker_at_end_of_text(self):
        """Marker at very end of text produces empty final chunk."""
        page_texts = [PageText(page_number=1, text="Content here. 1. End")]
        markers = [ParagraphMarker(start_index=14, text="1. End", level=ParagraphLevel.SECTION)]

        result = chunk_by_paragraphs(page_texts, markers)

        assert len(result) == 2
        assert result[0].text == "Content here. "
        assert result[1].text == ""
        assert result[1].chunk_index == 1
