"""
Tests for the One-on-One OS meeting brief graph.

All tests use the checked-in sample data under data/local_only/one_on_one/
and do not require an API key or Ollama.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from one_on_one_os.workflows.meeting_brief import build_meeting_brief
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse

DATA_PATH = "data/local_only/one_on_one"


def test_one_on_one_brief_returns_response() -> None:
    request = OneOnOneRequest(data_path=DATA_PATH, max_documents=5)
    response = build_meeting_brief(request)
    assert isinstance(response, OneOnOneResponse)
    assert response.meeting_summary
    assert len(response.evidence) > 0


def test_one_on_one_brief_surfaces_action_items() -> None:
    request = OneOnOneRequest(data_path=DATA_PATH, focus="action items", max_documents=5)
    response = build_meeting_brief(request)
    assert len(response.action_items) > 0
    for item in response.action_items:
        assert item.text
        assert item.source
        assert item.line_number > 0


def test_one_on_one_brief_surfaces_blockers() -> None:
    request = OneOnOneRequest(data_path=DATA_PATH, focus="blockers blocked", max_documents=5)
    response = build_meeting_brief(request)
    assert len(response.blockers) > 0


def test_one_on_one_brief_surfaces_kudos() -> None:
    request = OneOnOneRequest(data_path=DATA_PATH, focus="kudos recognition", max_documents=5)
    response = build_meeting_brief(request)
    assert len(response.kudos) > 0


def test_one_on_one_brief_multifile_retrieval() -> None:
    request = OneOnOneRequest(
        data_path=DATA_PATH, focus="team action items", max_documents=10
    )
    response = build_meeting_brief(request)
    sources = {item.source for item in response.evidence}
    assert len(sources) >= 2, f"Expected multiple source files, got: {sources}"


def test_one_on_one_brief_direct_report_in_summary() -> None:
    request = OneOnOneRequest(
        data_path=DATA_PATH, direct_report="Sarah Chen", max_documents=5
    )
    response = build_meeting_brief(request)
    assert "Sarah Chen" in response.meeting_summary


def test_one_on_one_brief_all_items_grounded() -> None:
    request = OneOnOneRequest(data_path=DATA_PATH, max_documents=10)
    response = build_meeting_brief(request)
    for section in (response.action_items, response.talking_points,
                    response.blockers, response.kudos):
        for item in section:
            assert item.source, f"Item missing source: {item.text}"
            assert item.line_number > 0, f"Item missing line_number: {item.text}"


def test_one_on_one_brief_raises_on_empty_data_path(tmp_path) -> None:
    request = OneOnOneRequest(data_path=str(tmp_path), max_documents=5)
    with pytest.raises(ValueError):
        build_meeting_brief(request)


def test_one_on_one_brief_use_model_calls_provider() -> None:
    from packages.shared.schemas.director_os import EvidenceItem, GroundedItem

    mock_response = OneOnOneResponse(
        meeting_summary="Claude-synthesized 1:1 brief.",
        action_items=[
            GroundedItem(text="Action: follow up", source="1on1_sarah_sre_lead.md", line_number=10)
        ],
        talking_points=[],
        blockers=[],
        kudos=[],
        evidence=[
            EvidenceItem(
                source="1on1_sarah_sre_lead.md",
                title="1:1 Notes — Sarah Chen",
                excerpt="Action: follow up",
                line_number=10,
            )
        ],
    )
    mock_provider = MagicMock()
    mock_provider.generate_one_on_one_brief.return_value = mock_response
    mock_provider.get_last_usage.return_value = {}

    with patch(
        "packages.shared.graphs.one_on_one_os._build_provider",
        return_value=mock_provider,
    ):
        request = OneOnOneRequest(
            data_path=DATA_PATH, focus="Sarah", use_model=True, max_documents=5
        )
        response = build_meeting_brief(request)

    mock_provider.generate_one_on_one_brief.assert_called_once()
    assert response.meeting_summary == "Claude-synthesized 1:1 brief."


def test_one_on_one_brief_falls_back_on_provider_error() -> None:
    mock_provider = MagicMock()
    mock_provider.generate_one_on_one_brief.side_effect = ValueError("API error")

    with patch(
        "packages.shared.graphs.one_on_one_os._build_provider",
        return_value=mock_provider,
    ):
        request = OneOnOneRequest(
            data_path=DATA_PATH,
            focus="Sarah",
            use_model=True,
            fallback_to_deterministic=True,
            max_documents=5,
        )
        response = build_meeting_brief(request)

    assert isinstance(response, OneOnOneResponse)
    assert response.meeting_summary


def test_one_on_one_os_route_in_orchestrator() -> None:
    from packages.shared.orchestration.chief_of_staff import route_request
    from packages.shared.schemas.orchestrator import OrchestratorRequest

    response = route_request(
        OrchestratorRequest(
            workflow="one_on_one_os.brief",
            data_path=DATA_PATH,
            focus="team blockers",
            max_documents=5,
        )
    )
    assert response.selected_workflow == "one_on_one_os.brief"
    assert response.result is not None
    assert response.trace.section_counts.get("action_items") is not None


def test_one_on_one_os_keyword_routing() -> None:
    from packages.shared.orchestration.chief_of_staff import route_request
    from packages.shared.schemas.orchestrator import OrchestratorRequest

    response = route_request(
        OrchestratorRequest(
            prompt="Prepare my 1:1 meeting brief for direct report check-in",
            data_path=DATA_PATH,
            max_documents=5,
        )
    )
    assert response.selected_workflow == "one_on_one_os.brief"
