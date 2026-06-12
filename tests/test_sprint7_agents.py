"""
Sprint 7 tests: researcher → writer multi-agent pipeline.

All tests mock the Anthropic SDK — no API key or network required.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.agents.researcher import ResearcherAgent, ResearchSynthesis
from packages.shared.agents.writer import SUPPORTED_AUDIENCES, WriterAgent
from packages.shared.schemas.director_os import (
    EvidenceItem,
    GroundedItem,
    WeeklyUpdateResponse,
)
from packages.shared.schemas.orchestrator import AgentCall, OrchestratorRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    source: str = "notes.md",
    line_number: int = 1,
    excerpt: str = "shipped v2",
) -> EvidenceItem:
    return EvidenceItem(source=source, line_number=line_number, title="Note", excerpt=excerpt)


def _make_usage(cache_read: int = 0, cache_creation: int = 0) -> MagicMock:
    u = MagicMock()
    u.input_tokens = 100
    u.output_tokens = 50
    u.cache_read_input_tokens = cache_read
    u.cache_creation_input_tokens = cache_creation
    return u


def _tool_response(payload: dict) -> MagicMock:
    block = SimpleNamespace(type="tool_use", input=payload)
    resp = MagicMock()
    resp.content = [block]
    resp.usage = _make_usage()
    return resp


def _text_response(text: str) -> MagicMock:
    block = SimpleNamespace(type="text", text=text)
    resp = MagicMock()
    resp.content = [block]
    resp.usage = _make_usage(cache_read=100)
    return resp


# ---------------------------------------------------------------------------
# ResearcherAgent
# ---------------------------------------------------------------------------


def test_researcher_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ResearcherAgent()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        agent.synthesize(focus=None, evidence=[_make_evidence()])


def test_researcher_returns_synthesis_and_agent_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    payload = {
        "narrative": "Team shipped the v2 API ahead of schedule.",
        "key_findings": ["v2 API shipped", "Auth latency reduced by 40%"],
        "risk_signals": ["Terraform upgrade still blocked"],
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _tool_response(payload)

    with patch("anthropic.Anthropic", return_value=mock_client):
        agent = ResearcherAgent()
        synthesis, call = agent.synthesize(focus="sprint review", evidence=[_make_evidence()])

    assert isinstance(synthesis, ResearchSynthesis)
    assert "v2 API" in synthesis.narrative
    assert len(synthesis.key_findings) == 2
    assert len(synthesis.risk_signals) == 1

    assert isinstance(call, AgentCall)
    assert call.agent == "researcher"
    assert call.input_tokens == 100
    assert call.output_tokens == 50


def test_researcher_handles_missing_risk_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    payload = {
        "narrative": "Clean week.",
        "key_findings": ["all tasks done"],
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _tool_response(payload)

    with patch("anthropic.Anthropic", return_value=mock_client):
        synthesis, _ = ResearcherAgent().synthesize(focus=None, evidence=[_make_evidence()])

    assert synthesis.risk_signals == []


def test_researcher_raises_when_no_tool_use_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    resp = MagicMock()
    resp.content = [SimpleNamespace(type="text", text="oops")]
    resp.usage = _make_usage()

    mock_client = MagicMock()
    mock_client.messages.create.return_value = resp

    with patch("anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(ValueError, match="tool_use block"):
            ResearcherAgent().synthesize(focus=None, evidence=[_make_evidence()])


# ---------------------------------------------------------------------------
# WriterAgent
# ---------------------------------------------------------------------------


def test_writer_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    synthesis = ResearchSynthesis(
        narrative="Team shipped v2.", key_findings=["v2 shipped"], risk_signals=[]
    )
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        WriterAgent().format(synthesis=synthesis, target_audience="linkedin_post")


def test_writer_raises_on_unsupported_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    synthesis = ResearchSynthesis(
        narrative="Team shipped v2.", key_findings=["v2 shipped"], risk_signals=[]
    )
    with pytest.raises(ValueError, match="Unsupported target_audience"):
        WriterAgent().format(synthesis=synthesis, target_audience="smoke_signal")


@pytest.mark.parametrize("audience", sorted(SUPPORTED_AUDIENCES))
def test_writer_returns_content_and_agent_call_for_all_audiences(
    audience: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _text_response(
        f"Formatted for {audience}: shipped v2."
    )

    synthesis = ResearchSynthesis(
        narrative="Team shipped v2.",
        key_findings=["v2 shipped", "latency improved"],
        risk_signals=["infra upgrade pending"],
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        content, call = WriterAgent().format(synthesis=synthesis, target_audience=audience)

    assert isinstance(content, str)
    assert len(content) > 0

    assert isinstance(call, AgentCall)
    assert call.agent == "writer"
    assert call.cache_read_input_tokens == 100


# ---------------------------------------------------------------------------
# Chief of staff wires researcher → writer when target_audience is set
# ---------------------------------------------------------------------------


def _fake_result() -> WeeklyUpdateResponse:
    return WeeklyUpdateResponse(
        summary="Good week.",
        wins=[GroundedItem(text="shipped v2", source="notes.md", line_number=1)],
        risks=[],
        next_steps=[],
        evidence=[_make_evidence("notes.md", 1, "shipped v2")],
    )


def test_orchestrator_populates_formatted_content_and_agent_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When target_audience is set, formatted_content and agent_calls must be populated."""
    from packages.shared.orchestration import chief_of_staff as csm

    fake_synthesis = ResearchSynthesis(
        narrative="Researcher narrative.",
        key_findings=["finding 1"],
        risk_signals=[],
    )

    monkeypatch.setattr(csm, "build_weekly_update", lambda _req: _fake_result())
    monkeypatch.setattr(
        "packages.shared.agents.researcher.ResearcherAgent.synthesize",
        lambda self, focus, evidence: (
            fake_synthesis,
            AgentCall(agent="researcher", model="test", input_tokens=10, output_tokens=5),
        ),
    )
    monkeypatch.setattr(
        "packages.shared.agents.writer.WriterAgent.format",
        lambda self, synthesis, target_audience: (
            "LinkedIn post content here.",
            AgentCall(agent="writer", model="test", input_tokens=20, output_tokens=30),
        ),
    )

    resp = csm.route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
            target_audience="linkedin_post",
        )
    )

    assert resp.formatted_content == "LinkedIn post content here."
    assert len(resp.trace.agent_calls) == 2
    assert resp.trace.agent_calls[0].agent == "researcher"
    assert resp.trace.agent_calls[1].agent == "writer"


def test_orchestrator_formatted_content_is_none_without_target_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.shared.orchestration import chief_of_staff as csm

    monkeypatch.setattr(csm, "build_weekly_update", lambda _req: _fake_result())

    resp = csm.route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
        )
    )

    assert resp.formatted_content is None
    assert resp.trace.agent_calls == []
