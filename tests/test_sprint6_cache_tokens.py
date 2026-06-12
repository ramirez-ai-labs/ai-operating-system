"""
Sprint 6 tests: prompt caching and WorkflowTrace cache token fields.

All tests mock the Anthropic SDK — no API key or network required.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.providers.claude import ClaudeWeeklyUpdateProvider
from packages.shared.schemas.director_os import (
    EvidenceItem,
    GroundedItem,
    WeeklyUpdateResponse,
)
from packages.shared.schemas.orchestrator import OrchestratorRequest, WorkflowTrace

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    source: str = "notes.md",
    line_number: int = 1,
    excerpt: str = "shipped v2",
) -> EvidenceItem:
    return EvidenceItem(source=source, line_number=line_number, title="Note", excerpt=excerpt)


def _make_usage(
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = cache_read
    usage.cache_creation_input_tokens = cache_creation
    return usage


def _make_api_response(payload: dict, cache_read: int = 0, cache_creation: int = 0) -> MagicMock:
    block = SimpleNamespace(type="tool_use", input=payload)
    resp = MagicMock()
    resp.content = [block]
    resp.usage = _make_usage(cache_read=cache_read, cache_creation=cache_creation)
    return resp


# ---------------------------------------------------------------------------
# Base provider default
# ---------------------------------------------------------------------------


def test_base_provider_get_last_usage_returns_empty_dict() -> None:
    """Default implementation must return {} so callers can always call get_last_usage()."""

    class _Concrete(WeeklyUpdateProvider):
        def generate_weekly_update(self, focus, evidence):  # type: ignore[override]
            return MagicMock()

    assert _Concrete().get_last_usage() == {}


# ---------------------------------------------------------------------------
# Claude provider records usage after a call
# ---------------------------------------------------------------------------


def test_claude_provider_records_cache_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    payload = {
        "summary": "Good week.",
        "wins": [{"text": "shipped v2", "source": "notes.md", "line_number": 1}],
        "risks": [],
        "next_steps": [],
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response(
        payload, cache_read=800, cache_creation=0
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        provider.generate_weekly_update(focus=None, evidence=[_make_evidence()])

    usage = provider.get_last_usage()
    assert usage["cache_read_input_tokens"] == 800
    assert usage["cache_creation_input_tokens"] == 0
    assert "input_tokens" in usage
    assert "output_tokens" in usage


def test_claude_provider_records_cache_creation_on_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    payload = {
        "summary": "First run.",
        "wins": [{"text": "shipped v2", "source": "notes.md", "line_number": 1}],
        "risks": [],
        "next_steps": [],
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response(
        payload, cache_read=0, cache_creation=1200
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        provider.generate_weekly_update(focus=None, evidence=[_make_evidence()])

    usage = provider.get_last_usage()
    assert usage["cache_read_input_tokens"] == 0
    assert usage["cache_creation_input_tokens"] == 1200


def test_claude_provider_usage_empty_before_first_call() -> None:
    provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
    assert provider.get_last_usage() == {}


# ---------------------------------------------------------------------------
# WorkflowTrace schema fields
# ---------------------------------------------------------------------------


def test_workflow_trace_has_cache_fields_defaulting_to_zero() -> None:
    trace = WorkflowTrace(
        data_path="data/local_only/projects",
        focus_used=None,
        evidence_count=3,
        evidence_sources=["notes.md"],
        model_requested=False,
        model_supported=True,
        model_used=False,
        provider_used=None,
        model_id_used=None,
        fallback_used=False,
        section_counts={"wins": 1, "risks": 0, "next_steps": 0},
        validation_summary="ok",
    )
    assert trace.cache_read_input_tokens == 0
    assert trace.cache_creation_input_tokens == 0


# ---------------------------------------------------------------------------
# Cache tokens surface in WorkflowTrace via chief_of_staff
# ---------------------------------------------------------------------------


def test_cache_tokens_surface_in_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cache tokens stored in WeeklyUpdateResponse.provider_usage must reach the trace."""
    from packages.shared.orchestration import chief_of_staff as csm

    def fake_weekly_update(_req):
        return WeeklyUpdateResponse(
            summary="Good week.",
            wins=[GroundedItem(text="shipped v2", source="notes.md", line_number=1)],
            risks=[],
            next_steps=[],
            evidence=[_make_evidence("notes.md", 1, "shipped v2")],
            provider_usage={
                "input_tokens": 300,
                "output_tokens": 80,
                "cache_read_input_tokens": 250,
                "cache_creation_input_tokens": 0,
            },
        )

    monkeypatch.setattr(csm, "build_weekly_update", fake_weekly_update)

    resp = csm.route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
            use_model=True,
        )
    )

    assert resp.trace.cache_read_input_tokens == 250
    assert resp.trace.cache_creation_input_tokens == 0


def test_cache_tokens_zero_when_provider_usage_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic path (no model call) should leave cache token fields at zero."""
    from packages.shared.orchestration import chief_of_staff as csm

    def fake_weekly_update(_req):
        return WeeklyUpdateResponse(
            summary="Deterministic summary.",
            wins=[GroundedItem(text="shipped v2", source="notes.md", line_number=1)],
            risks=[],
            next_steps=[],
            evidence=[_make_evidence("notes.md", 1, "shipped v2")],
        )

    monkeypatch.setattr(csm, "build_weekly_update", fake_weekly_update)

    resp = csm.route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
        )
    )

    assert resp.trace.cache_read_input_tokens == 0
    assert resp.trace.cache_creation_input_tokens == 0
