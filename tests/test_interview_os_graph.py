"""
Tests for the Interview OS brief graph.

All tests use the checked-in sample data under data/local_only/interviews/
and do not require an API key or Ollama.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from interview_os.workflows.interview_brief import build_interview_brief
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse

DATA_PATH = "data/local_only/interviews"


def test_interview_brief_returns_response() -> None:
    """The workflow should return a valid InterviewBriefResponse from local data."""
    request = InterviewBriefRequest(
        data_path=DATA_PATH, focus="interview questions", max_documents=5
    )
    response = build_interview_brief(request)
    assert isinstance(response, InterviewBriefResponse)
    assert response.candidate_summary
    assert isinstance(response.evidence, list)
    assert len(response.evidence) > 0


def test_interview_brief_surfaces_questions() -> None:
    """A candidate-focused query should surface key questions from the notes."""
    request = InterviewBriefRequest(
        data_path=DATA_PATH,
        focus="interview questions",
        max_documents=5,
    )
    response = build_interview_brief(request)
    assert len(response.key_questions) > 0
    for item in response.key_questions:
        assert item.text
        assert item.source
        assert item.line_number > 0


def test_interview_brief_surfaces_red_flags() -> None:
    """A red-flag focused query should populate the red_flags section."""
    request = InterviewBriefRequest(
        data_path=DATA_PATH,
        focus="red flags concerns",
        max_documents=5,
    )
    response = build_interview_brief(request)
    assert len(response.red_flags) > 0


def test_interview_brief_multifile_retrieval() -> None:
    """A broad query should retrieve evidence from more than one source file."""
    request = InterviewBriefRequest(
        data_path=DATA_PATH,
        focus="senior AI engineer interview",
        max_documents=10,
    )
    response = build_interview_brief(request)
    sources = {item.source for item in response.evidence}
    assert len(sources) >= 2, f"Expected multiple source files, got: {sources}"


def test_interview_brief_candidate_name_in_summary() -> None:
    """When candidate_name is provided it should appear in the summary."""
    request = InterviewBriefRequest(
        data_path=DATA_PATH,
        candidate_name="Alex Chen",
        role="Senior AI Engineer",
        max_documents=5,
    )
    response = build_interview_brief(request)
    assert "Alex Chen" in response.candidate_summary
    assert "Senior AI Engineer" in response.candidate_summary


def test_interview_brief_all_items_grounded() -> None:
    """Every item in every section must cite a source file and line number."""
    request = InterviewBriefRequest(data_path=DATA_PATH, max_documents=10)
    response = build_interview_brief(request)
    for section in (response.key_questions, response.talking_points, response.red_flags):
        for item in section:
            assert item.source, f"Item missing source: {item.text}"
            assert item.line_number > 0, f"Item missing line_number: {item.text}"


def test_interview_brief_raises_on_empty_data_path(tmp_path) -> None:
    """An empty data directory should raise ValueError, not return an empty response."""
    request = InterviewBriefRequest(data_path=str(tmp_path), max_documents=5)
    with pytest.raises(ValueError):
        build_interview_brief(request)


def test_interview_os_route_in_orchestrator() -> None:
    """interview_os.brief should be a valid explicit workflow in the orchestrator."""
    from packages.shared.orchestration.chief_of_staff import route_request
    from packages.shared.schemas.orchestrator import OrchestratorRequest

    response = route_request(
        OrchestratorRequest(
            workflow="interview_os.brief",
            data_path=DATA_PATH,
            focus="candidate brief",
            max_documents=5,
        )
    )
    assert response.selected_workflow == "interview_os.brief"
    assert response.result is not None
    assert response.trace.section_counts.get("key_questions") is not None


def test_interview_brief_use_model_calls_provider() -> None:
    """When use_model=True the graph must call the Claude provider, not the deterministic path."""
    from packages.shared.schemas.director_os import EvidenceItem, GroundedItem

    mock_response = InterviewBriefResponse(
        candidate_summary="Claude-synthesized brief for the candidate.",
        key_questions=[
            GroundedItem(
                text="Question: describe your experience with distributed systems",
                source="role_brief_senior_ai_engineer.md",
                line_number=5,
            )
        ],
        talking_points=[],
        red_flags=[],
        evidence=[
            EvidenceItem(
                source="role_brief_senior_ai_engineer.md",
                title="Role Brief",
                excerpt="Question: describe your experience with distributed systems",
                line_number=5,
            )
        ],
    )
    mock_provider = MagicMock()
    mock_provider.generate_interview_brief.return_value = mock_response
    mock_provider.get_last_usage.return_value = {}

    with patch(
        "packages.shared.graphs.interview_os._build_provider",
        return_value=mock_provider,
    ):
        request = InterviewBriefRequest(
            data_path=DATA_PATH,
            focus="candidate brief",
            use_model=True,
            max_documents=5,
        )
        response = build_interview_brief(request)

    mock_provider.generate_interview_brief.assert_called_once()
    assert response.candidate_summary == "Claude-synthesized brief for the candidate."


def test_interview_brief_use_model_falls_back_on_error() -> None:
    """When the provider raises and fallback_to_deterministic=True, the deterministic path runs."""
    mock_provider = MagicMock()
    mock_provider.generate_interview_brief.side_effect = ValueError("API error")

    with patch(
        "packages.shared.graphs.interview_os._build_provider",
        return_value=mock_provider,
    ):
        request = InterviewBriefRequest(
            data_path=DATA_PATH,
            focus="candidate brief",
            use_model=True,
            fallback_to_deterministic=True,
            max_documents=5,
        )
        response = build_interview_brief(request)

    assert isinstance(response, InterviewBriefResponse)
    assert response.candidate_summary  # deterministic path produced a summary


def test_interview_brief_validate_response_triggers_fallback_on_empty_sections(
    monkeypatch,
) -> None:
    """validate_response must fall back to deterministic when model returns empty sections."""
    from packages.shared.schemas.director_os import EvidenceItem

    def fake_retrieve(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="role_brief.md",
                line_number=1,
                title="Role Brief",
                excerpt="Question: describe your approach to system design",
            )
        ]

    class EmptySectionsProvider:
        def generate_interview_brief(self, focus, evidence):
            return InterviewBriefResponse(
                candidate_summary="ok",
                key_questions=[],
                talking_points=[],
                red_flags=[],
                evidence=evidence,
            )

        def get_last_usage(self):
            return {"input_tokens": 10, "output_tokens": 5}

    with patch("packages.shared.graphs.interview_os._build_provider",
               return_value=EmptySectionsProvider()):
        with patch("packages.shared.graphs.interview_os.retrieve_relevant_documents",
                   side_effect=fake_retrieve):
            result = build_interview_brief(
                InterviewBriefRequest(
                    data_path=DATA_PATH,
                    focus="interview questions",
                    use_model=True,
                    fallback_to_deterministic=True,
                    max_documents=5,
                )
            )
    # Deterministic fallback should populate at least key_questions from the data.
    assert any((result.key_questions, result.talking_points, result.red_flags)), (
        "Expected deterministic fallback to populate at least one section"
    )


def test_interview_os_keyword_routing() -> None:
    """Prompts mentioning 'interview' or 'candidate' should route to interview_os.brief."""
    from packages.shared.orchestration.chief_of_staff import route_request
    from packages.shared.schemas.orchestrator import OrchestratorRequest

    response = route_request(
        OrchestratorRequest(
            prompt="Prepare an interview brief for the candidate",
            data_path=DATA_PATH,
            max_documents=5,
        )
    )
    assert response.selected_workflow == "interview_os.brief"
