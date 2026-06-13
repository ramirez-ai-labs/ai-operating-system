"""
Tests for the Interview OS brief graph.

All tests use the checked-in sample data under data/local_only/interviews/
and do not require an API key or Ollama.
"""

from __future__ import annotations

import pytest

from interview_os.workflows.interview_brief import build_interview_brief
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse

DATA_PATH = "data/local_only/interviews"


def test_interview_brief_returns_response() -> None:
    """The workflow should return a valid InterviewBriefResponse from local data."""
    request = InterviewBriefRequest(data_path=DATA_PATH, max_documents=5)
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
