"""
Logic to handle input data from pdf's is gathered in this python file
"""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional

import fitz


# Module-level constant for extendable header detection
COMMON_HEADER_KEYWORDS: list[str] = [
    "ABSTRACT",
    "INTRODUCTION",
    "CONCLUSION",
    "REFERENCES",
    "METHODS",
    "RESULTS",
    "DISCUSSION",
    "BACKGROUND",
    "BACKGROUND AND AIMS",
    "BACKGROUND:",
    "BACKGROUND –",
]


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    chunk_index: int


@dataclass
class PageText:
    page_number: int
    text: str


class ParagraphLevel(IntEnum):
    SECTION = 1
    SUBSECTION = 2
    SUBSUBSECTION = 3


@dataclass
class ParagraphMarker:
    start_index: int
    text: str
    level: ParagraphLevel


def extract_text_from_pdf(pdf_path: Path) -> list[PageText]:
    """
    Opens a PDF file with pymupdf and extracts raw text from each page,
    returning a list of PageText objects ordered by page number.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of PageText objects with page_number (1-indexed) and text

    Raises:
        FileNotFoundError: If the PDF does not exist
        ValueError: If the file is not a valid PDF
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except fitz.FileDataError as e:
        raise ValueError(f"Invalid PDF file: {pdf_path}") from e

    try:
        page_texts = []
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            text = page.get_text("text").strip()
            if text:
                page_texts.append(PageText(page_number=page_num, text=text))
        return page_texts
    finally:
        doc.close()


def estimate_words(tokens: int) -> int:
    """Returns estimated word count: int(tokens * 1.3) for token-to-word conversion."""
    return int(tokens * 1.3)


# ---------------------------------------------------------------------------
# Helper functions for chunk_by_tokens
# ---------------------------------------------------------------------------


def _concatenate_page_texts(
    page_texts: list[PageText],
) -> tuple[str, list[tuple[int, int, int]]]:
    """Concatenate page texts with newline separators.

    Args:
        page_texts: List of PageText objects

    Returns:
        Tuple of (full_text, page_ranges) where page_ranges is
        [(start_char, end_char_exclusive, page_number), ...]
    """
    if not page_texts:
        return "", []

    concatenated_parts: list[str] = []
    page_ranges: list[tuple[int, int, int]] = []
    current_pos = 0

    for i, page in enumerate(page_texts):
        if page.text.strip():  # Skip whitespace-only pages
            concatenated_parts.append(page.text)
            page_ranges.append(
                (current_pos, current_pos + len(page.text), page.page_number)
            )
            current_pos += len(page.text)
            # Add newline separator between pages (but not after last page)
            if i < len(page_texts) - 1:
                # Check if next page has content
                if i + 1 < len(page_texts) and page_texts[i + 1].text.strip():
                    concatenated_parts.append("\n")
                    current_pos += 1

    full_text = "".join(concatenated_parts)
    return full_text, page_ranges


def _get_page_for_position(
    char_pos: int,
    page_ranges: list[tuple[int, int, int]],
) -> int:
    """Find which page a character position belongs to.

    Args:
        char_pos: Character position in concatenated text
        page_ranges: List of (start, end, page_number) tuples

    Returns:
        Page number containing this position
    """
    for start, end, page_num in page_ranges:
        if start <= char_pos < end:
            return page_num

    # If past all ranges, return the last page
    if page_ranges:
        return page_ranges[-1][2]

    return 1  # Default fallback


def _build_chunk(
    text: str,
    start_pos: int,
    end_pos: int,
    page_ranges: list[tuple[int, int, int]],
    chunk_index: int,
) -> Chunk:
    """Create a Chunk object from text and positions.

    Args:
        text: Full concatenated text
        start_pos: Start character position (inclusive)
        end_pos: End character position (exclusive)
        page_ranges: List of (start, end, page_number) tuples
        chunk_index: Index for this chunk

    Returns:
        Chunk object with text, page_start, page_end, and chunk_index
    """
    chunk_text = text[start_pos:end_pos]

    # Handle empty text edge case
    if not chunk_text:
        if page_ranges:
            return Chunk(
                text="",
                page_start=page_ranges[0][2],
                page_end=page_ranges[0][2],
                chunk_index=chunk_index,
            )
        return Chunk(text="", page_start=1, page_end=1, chunk_index=chunk_index)

    page_start = _get_page_for_position(start_pos, page_ranges)
    page_end = _get_page_for_position(end_pos - 1, page_ranges)

    return Chunk(
        text=chunk_text,
        page_start=page_start,
        page_end=page_end,
        chunk_index=chunk_index,
    )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def chunk_by_tokens(
    page_texts: list[PageText],
    tokens_per_chunk: int = 300,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Splits a list of pages' text into chunks using a sliding window by word count.

    The window advances by (tokens_per_chunk - overlap_tokens) estimated tokens,
    producing chunks that overlap by approximately overlap_tokens tokens.

    Args:
        page_texts: List of PageText objects (all pages of a PDF, or any contiguous sequence)
        tokens_per_chunk: Target estimated tokens per chunk (default 300)
        overlap_tokens: Number of estimated tokens to overlap between chunks (default 50)

    Returns:
        List of Chunk objects with text, page_start, page_end, and chunk_index

    Raises:
        ValueError: If overlap_tokens >= tokens_per_chunk / 2
    """
    # Validate overlap
    if overlap_tokens >= tokens_per_chunk / 2:
        raise ValueError(
            f"overlap_tokens ({overlap_tokens}) must be less than "
            f"tokens_per_chunk / 2 ({tokens_per_chunk / 2})"
        )

    # Concatenate pages and track ranges
    full_text, page_ranges = _concatenate_page_texts(page_texts)

    if not full_text:
        return []

    # Split into words for precise counting
    words = full_text.split()
    if not words:
        return []

    # Convert token counts to word counts
    words_per_chunk = estimate_words(tokens_per_chunk)
    words_overlap = estimate_words(overlap_tokens)
    step_words = words_per_chunk - words_overlap

    # Build chunks by stepping through word indices
    chunks: list[Chunk] = []
    chunk_index = 0
    word_pos = 0

    while word_pos < len(words):
        # Find end position for this chunk (exclusive word index)
        end_word = word_pos + words_per_chunk

        # Clamp to end of text
        if end_word > len(words):
            end_word = len(words)

        # Extract text for this chunk
        chunk_words = words[word_pos:end_word]
        chunk_text = " ".join(chunk_words)

        # Skip empty chunks
        if chunk_text:
            # Convert word positions to character positions
            # Find start char: sum of lengths of all words before word_pos, plus spaces
            start_char = sum(len(words[i]) for i in range(word_pos)) + word_pos
            end_char = sum(len(words[i]) for i in range(end_word)) + end_word

            chunk = _build_chunk(
                full_text, start_char, end_char, page_ranges, chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1

        # Advance by step_words (not words_per_chunk) to create overlap
        word_pos += step_words

    return chunks


def detect_paragraph_markers(text: str) -> list[ParagraphMarker]:
    """Scans text line by line for paragraph/section markers.

    Detects:
    - Numbered patterns at line start:
        - 1 number (e.g. "1.", "1 ") → SECTION
        - 2+ dot-separated numbers (e.g. "1.1", "2.3.1") → SUBSECTION
    - Common header patterns via COMMON_HEADER_KEYWORDS (case-insensitive) → SECTION

    Returns empty list if no markers found.
    """
    import re

    markers = []
    lines = text.split("\n")
    pos = 0

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            pos += len(line) + 1  # +1 for the newline
            continue

        leading_ws = len(line) - len(stripped)
        if leading_ws != 0:
            # Not at start of line
            pos += len(line) + 1
            continue

        # Check numbered pattern at start of line
        num_match = re.match(r"^(\d+)(\.)\s*(\S.*)?$", stripped)
        if num_match:
            # Count dot-separated numbers
            num_str = num_match.group(1)
            level = ParagraphLevel.SECTION
            # Check if there are more dot-separated numbers after the first
            remainder = num_match.group(3) or ""
            full_text = stripped
            # Re-check for multi-level numbering like 1.1 or 2.3.1
            multi_match = re.match(r"^(\d+(?:\.\d+)+)(?:\s+(.*))?$", stripped)
            if multi_match:
                dot_parts = multi_match.group(1).split(".")
                if len(dot_parts) >= 2:
                    level = ParagraphLevel.SUBSECTION
                full_text = multi_match.group(0)
                start_index = pos
                markers.append(
                    ParagraphMarker(
                        start_index=start_index, text=full_text, level=level
                    )
                )
                pos += len(line) + 1
                continue
            else:
                start_index = pos
                markers.append(
                    ParagraphMarker(
                        start_index=start_index, text=full_text, level=level
                    )
                )
                pos += len(line) + 1
                continue

        # Check common header keywords (case-insensitive)
        upper_stripped = stripped.upper()
        for kw in COMMON_HEADER_KEYWORDS:
            if upper_stripped.startswith(kw):
                start_index = pos
                markers.append(
                    ParagraphMarker(
                        start_index=start_index,
                        text=stripped,
                        level=ParagraphLevel.SECTION,
                    )
                )
                break

        pos += len(line) + 1

    return markers


def chunk_by_paragraphs(
    page_texts: list[PageText], markers: list[ParagraphMarker]
) -> list[Chunk]:
    """Splits a list of pages' text into chunks aligned to paragraph/section marker boundaries.

    Args:
        page_texts: List of PageText objects (all pages of a PDF, or any contiguous sequence)
        markers: Pre-detected list of ParagraphMarker sorted by start_index ascending

    Returns:
        List of Chunk objects with text, page_start, page_end, and chunk_index
    """
    if not page_texts:
        return []

    # Concatenate pages using the same helper as chunk_by_tokens
    full_text, page_ranges = _concatenate_page_texts(page_texts)

    if not full_text:
        return []

    # Empty markers: return entire text as a single chunk
    if not markers:
        return [_build_chunk(full_text, 0, len(full_text), page_ranges, 0)]

    def _find_line_end(text: str, start_pos: int) -> int:
        """Find position after the newline that ends the line starting at start_pos."""
        i = start_pos
        while i < len(text):
            if text[i] == "\n":
                return i + 1
            i += 1
        return len(text)

    # Build chunks using marker positions as boundaries
    # The marker line itself is NOT included in any chunk's text
    # Chunk boundaries fall at marker positions (start_index values)
    chunks: list[Chunk] = []
    chunk_index = 0

    # Chunk 0: from start of text (0) to markers[0].start_index (before marker line)
    chunk = _build_chunk(full_text, 0, markers[0].start_index, page_ranges, chunk_index)
    chunks.append(chunk)
    chunk_index += 1

    # Intermediate chunks: from end of marker N-1 line to start of marker N
    for i in range(1, len(markers)):
        prev_end = _find_line_end(full_text, markers[i - 1].start_index)
        curr_start = markers[i].start_index
        chunk = _build_chunk(full_text, prev_end, curr_start, page_ranges, chunk_index)
        chunks.append(chunk)
        chunk_index += 1

    # Final chunk: from end of last marker line to end of text
    last_end = _find_line_end(full_text, markers[-1].start_index)
    chunk = _build_chunk(full_text, last_end, len(full_text), page_ranges, chunk_index)
    chunks.append(chunk)

    return chunks


def chunk_pdf_by_tokens(
    pdf_path: Path,
    tokens_per_chunk: int = 300,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Public API that extracts text from a PDF and applies token-based sliding-window chunking with optional overlap.

    Args:
        pdf_path: Path to the PDF file
        tokens_per_chunk: Target estimated tokens per chunk (default 300)
        overlap_tokens: Number of estimated tokens to overlap between chunks (default 50)

    Returns:
        List of Chunk objects from token-based chunking

    Raises:
        FileNotFoundError: If the PDF does not exist
        ValueError: If the file is not a valid PDF
    """
    page_texts = extract_text_from_pdf(pdf_path)
    full_text, _ = _concatenate_page_texts(page_texts)
    if not full_text:
        return []
    return chunk_by_tokens(page_texts, tokens_per_chunk, overlap_tokens)


def chunk_pdf_by_paragraphs(pdf_path: Path) -> list[Chunk]:
    """Public API: extracts text from PDF, applies paragraph-based chunking, returns flat list of Chunks.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of Chunk objects from paragraph-based chunking

    Raises:
        FileNotFoundError: If the PDF does not exist
        ValueError: If the file is not a valid PDF
    """
    page_texts = extract_text_from_pdf(pdf_path)
    full_text, _ = _concatenate_page_texts(page_texts)
    if not full_text:
        return []
    markers = detect_paragraph_markers(full_text)
    chunks = chunk_by_paragraphs(page_texts, markers)
    return chunks
