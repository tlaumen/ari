"""Tests for the reranking module."""

import pytest
from unittest.mock import patch, MagicMock

from ari.embeddings.rerank import (
    candidates_from_cosine_results,
    rerank_candidates,
    rerank_results,
    SearchResult,
)
from ari.input.pdf import Chunk
from baml_client import types, b


class TestCandidatesFromCosineResults:
    """Tests for candidates_from_cosine_results function."""

    def test_maps_tuples_to_candidates_with_correct_fields(self):
        """Test C-1: Maps each (score, Chunk) tuple to a Candidate with chunk_id from Chunk.chunk_index, the chunk text, and the cosine similarity score."""
        chunks = [
            Chunk(text="First chunk text", page_start=1, page_end=1, chunk_index=0),
            Chunk(text="Second chunk text", page_start=2, page_end=2, chunk_index=5),
        ]
        results = [(0.9, chunks[0]), (0.8, chunks[1])]

        candidates = candidates_from_cosine_results(results)

        assert len(candidates) == 2
        # Check first candidate
        assert candidates[0].chunk_id == 0
        assert candidates[0].text == "First chunk text"
        assert candidates[0].similarity_score == 0.9
        # Check second candidate
        assert candidates[1].chunk_id == 5
        assert candidates[1].text == "Second chunk text"
        assert candidates[1].similarity_score == 0.8

    def test_preserves_order_from_input(self):
        """Test C-2: Preserves ordering — candidates list maintains the same order as input results (descending by cosine score from cosine_search)."""
        chunks = [
            Chunk(text="Score 0.95", page_start=1, page_end=1, chunk_index=3),
            Chunk(text="Score 0.85", page_start=1, page_end=1, chunk_index=7),
            Chunk(text="Score 0.75", page_start=1, page_end=1, chunk_index=12),
        ]
        results = [
            (0.95, chunks[0]),
            (0.85, chunks[1]),
            (0.75, chunks[2]),
        ]

        candidates = candidates_from_cosine_results(results)

        # Verify order is preserved
        assert [c.chunk_id for c in candidates] == [3, 7, 12]
        assert [c.similarity_score for c in candidates] == [0.95, 0.85, 0.75]

    def test_returns_empty_list_for_empty_input(self):
        """Test C-3: Returns empty list when input results is empty."""
        candidates = candidates_from_cosine_results([])
        assert candidates == []


class TestRerankCandidates:
    """Tests for rerank_candidates function."""

    def test_calls_baml_with_correct_arguments(self):
        """Test R-1: Calls b.RerankCandidates(query=query, candidates=candidates) using the generated BAML client."""
        query = "What is pile bearing capacity?"
        candidates = [
            types.Candidate(chunk_id=0, text="Pile capacity is 1500kN.", similarity_score=0.85),
            types.Candidate(chunk_id=1, text="Foundation design follows Eurocode.", similarity_score=0.70),
        ]
        mock_reranked = [
            types.RerankedMatch(
                answer="Pile capacity: 1500kN",
                source_chunk_index=0,
                relevance_score=0.95,
                reasoning="Directly answers the query.",
            ),
            types.RerankedMatch(
                answer="Follows Eurocode 7",
                source_chunk_index=1,
                relevance_score=0.75,
                reasoning="Relevant design standard.",
            ),
            types.RerankedMatch(
                answer="Additional info",
                source_chunk_index=2,
                relevance_score=0.60,
                reasoning="Somewhat related.",
            ),
        ]

        with patch.object(b, "RerankCandidates", return_value=mock_reranked) as mock_call:
            result = rerank_candidates(query, candidates)

            mock_call.assert_called_once_with(query=query, candidates=candidates)
            assert result == mock_reranked
            assert len(result) == 3

    def test_returns_reranked_match_list(self):
        """Test R-2: Returns the list of RerankedMatch objects from BAML (exactly 3 by BAML design, or fewer if BAML returns fewer)."""
        query = "Test query"
        candidates = [
            types.Candidate(chunk_id=0, text="Text 1", similarity_score=0.9),
        ]
        mock_reranked = [
            types.RerankedMatch(
                answer="Answer 1",
                source_chunk_index=0,
                relevance_score=0.9,
                reasoning="Good match.",
            ),
            types.RerankedMatch(
                answer="Answer 2",
                source_chunk_index=1,
                relevance_score=0.7,
                reasoning="Moderate match.",
            ),
            types.RerankedMatch(
                answer="Answer 3",
                source_chunk_index=2,
                relevance_score=0.5,
                reasoning="Partial match.",
            ),
        ]

        with patch.object(b, "RerankCandidates", return_value=mock_reranked):
            result = rerank_candidates(query, candidates)

        assert all(isinstance(r, types.RerankedMatch) for r in result)
        assert all(hasattr(r, attr) for r in result for attr in ["answer", "source_chunk_index", "relevance_score", "reasoning"])

    def test_raises_runtime_error_on_baml_failure(self):
        """Test R-3: Raises RuntimeError with the original exception as the cause on BAML failure."""
        query = "Test query"
        candidates = [
            types.Candidate(chunk_id=0, text="Text", similarity_score=0.9),
        ]

        with patch.object(b, "RerankCandidates", side_effect=Exception("BAML API error")):
            with pytest.raises(RuntimeError) as exc_info:
                rerank_candidates(query, candidates)

            assert "BAML" in str(exc_info.value) or "reranking" in str(exc_info.value).lower()
            assert exc_info.value.__cause__ is not None
            assert "BAML API error" in str(exc_info.value.__cause__)


class TestRerankResults:
    """Tests for rerank_results function."""

    def test_full_pipeline_returns_search_results(self):
        """Test RR-1: Calls candidates_from_cosine_results to convert cosine results to Candidate format, then calls rerank_candidates, and maps results back to SearchResult objects."""
        chunks = [
            Chunk(text="Pile bearing capacity is 1500kN.", page_start=1, page_end=1, chunk_index=0),
            Chunk(text="Foundation design per Eurocode 7.", page_start=2, page_end=2, chunk_index=5),
            Chunk(text="Settlement analysis method.", page_start=3, page_end=3, chunk_index=10),
            Chunk(text="Pile load test results.", page_start=4, page_end=4, chunk_index=15),
            Chunk(text="Soil investigation report.", page_start=5, page_end=5, chunk_index=20),
        ]
        cosine_results = [
            (0.95, chunks[0]),
            (0.85, chunks[1]),
            (0.75, chunks[2]),
            (0.65, chunks[3]),
            (0.55, chunks[4]),
        ]

        mock_reranked = [
            types.RerankedMatch(
                answer="1500kN bearing capacity",
                source_chunk_index=0,
                relevance_score=0.95,
                reasoning="Direct answer to query.",
            ),
            types.RerankedMatch(
                answer="Eurocode 7 foundation design",
                source_chunk_index=5,
                relevance_score=0.85,
                reasoning="Relevant design standard.",
            ),
            types.RerankedMatch(
                answer="Settlement analysis method",
                source_chunk_index=10,
                relevance_score=0.80,
                reasoning="Related technical content.",
            ),
        ]

        with patch("ari.embeddings.rerank.candidates_from_cosine_results") as mock_convert:
            with patch("ari.embeddings.rerank.rerank_candidates", return_value=mock_reranked) as mock_rerank:
                mock_convert.return_value = [
                    types.Candidate(chunk_id=0, text=chunks[0].text, similarity_score=0.95),
                    types.Candidate(chunk_id=5, text=chunks[1].text, similarity_score=0.85),
                    types.Candidate(chunk_id=10, text=chunks[2].text, similarity_score=0.75),
                    types.Candidate(chunk_id=15, text=chunks[3].text, similarity_score=0.65),
                    types.Candidate(chunk_id=20, text=chunks[4].text, similarity_score=0.55),
                ]

                result = rerank_results(cosine_results, "What is pile bearing capacity?")

        # Verify candidates_from_cosine_results was called
        mock_convert.assert_called_once_with(cosine_results)

        # Verify rerank_candidates was called
        mock_rerank.assert_called_once()

        # Verify SearchResult list in same order as reranked matches
        assert len(result) == 3
        assert isinstance(result[0], SearchResult)
        assert result[0].chunk == chunks[0]
        assert result[0].answer == "1500kN bearing capacity"
        assert result[0].relevance_score == 0.95
        assert result[0].reasoning == "Direct answer to query."

        assert result[1].chunk == chunks[1]
        assert result[1].answer == "Eurocode 7 foundation design"

        assert result[2].chunk == chunks[2]
        assert result[2].answer == "Settlement analysis method"

    def test_returns_up_to_3_search_results(self):
        """Test RR-1 variant: With 5 cosine results, returns up to 3 SearchResult objects (BAML always returns 3)."""
        chunks = [
            Chunk(text=f"Chunk {i}", page_start=1, page_end=1, chunk_index=i * 5)
            for i in range(5)
        ]
        cosine_results = [(0.9 - i * 0.1, chunks[i]) for i in range(5)]

        mock_reranked = [
            types.RerankedMatch(
                answer=f"Answer {i}",
                source_chunk_index=i * 5,
                relevance_score=0.9 - i * 0.1,
                reasoning=f"Reason {i}.",
            )
            for i in range(3)
        ]

        with patch("ari.embeddings.rerank.candidates_from_cosine_results") as mock_convert:
            with patch("ari.embeddings.rerank.rerank_candidates", return_value=mock_reranked):
                mock_convert.return_value = [
                    types.Candidate(chunk_id=c.chunk_index, text=c.text, similarity_score=s)
                    for s, c in cosine_results
                ]

                result = rerank_results(cosine_results, "test query")

        assert len(result) == 3

    def test_raises_value_error_for_missing_chunk_index(self):
        """Test RR-5: Raises ValueError if source_chunk_index does not match any Chunk in results."""
        chunks = [
            Chunk(text="Chunk 0", page_start=1, page_end=1, chunk_index=0),
            Chunk(text="Chunk 100", page_start=2, page_end=2, chunk_index=100),
        ]
        cosine_results = [(0.9, chunks[0]), (0.8, chunks[1])]

        # RerankedMatch references chunk_index=999 which doesn't exist
        mock_reranked = [
            types.RerankedMatch(
                answer="Answer",
                source_chunk_index=999,  # Doesn't exist in chunks
                relevance_score=0.9,
                reasoning="Invalid chunk.",
            ),
            types.RerankedMatch(
                answer="Another",
                source_chunk_index=0,
                relevance_score=0.8,
                reasoning="Valid.",
            ),
            types.RerankedMatch(
                answer="Third",
                source_chunk_index=100,
                relevance_score=0.7,
                reasoning="Also valid.",
            ),
        ]

        with patch("ari.embeddings.rerank.candidates_from_cosine_results") as mock_convert:
            with patch("ari.embeddings.rerank.rerank_candidates", return_value=mock_reranked):
                mock_convert.return_value = [
                    types.Candidate(chunk_id=c.chunk_index, text=c.text, similarity_score=s)
                    for s, c in cosine_results
                ]

                with pytest.raises(ValueError) as exc_info:
                    rerank_results(cosine_results, "test query")

                assert "999" in str(exc_info.value) or "source_chunk_index" in str(exc_info.value)


class TestSearchResultDataclass:
    """Tests for the SearchResult dataclass."""

    def test_search_result_has_required_fields(self):
        """Verify SearchResult has chunk, answer, relevance_score, and reasoning fields."""
        chunk = Chunk(text="Test chunk", page_start=1, page_end=1, chunk_index=0)
        result = SearchResult(
            chunk=chunk,
            answer="Test answer",
            relevance_score=0.95,
            reasoning="Test reasoning",
        )

        assert result.chunk == chunk
        assert result.answer == "Test answer"
        assert result.relevance_score == 0.95
        assert result.reasoning == "Test reasoning"
