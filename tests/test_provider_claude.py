"""
Unit tests for ClaudeWeeklyUpdateProvider (packages/shared/providers/claude.py).

All tests mock the Anthropic SDK — no API key or network required.
Live integration tests are in test_director_os_evaluations.py and skip
automatically when ANTHROPIC_API_KEY is absent.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.providers.claude import (
    ClaudeWeeklyUpdateProvider,
    _build_prompt,
    _parse_grounded_items,
)
from packages.shared.schemas.director_os import EvidenceItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(
    source: str = "notes.md",
    line_number: int = 1,
    excerpt: str = "shipped v2",
) -> EvidenceItem:
    return EvidenceItem(source=source, line_number=line_number, title="Note", excerpt=excerpt)


def _make_tool_use_block(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", input=payload)


def _make_text_block(text: str = "hello") -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _make_api_response(content: list) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    return resp


# ---------------------------------------------------------------------------
# Missing API key
# ---------------------------------------------------------------------------

def test_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        provider.generate_weekly_update(focus=None, evidence=[_make_evidence()])


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_returns_draft_from_valid_tool_use_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    payload = {
        "summary": "Team shipped v2 on time.",
        "wins": [{"text": "shipped v2", "source": "notes.md", "line_number": 1}],
        "risks": [],
        "next_steps": [],
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response(
        [_make_tool_use_block(payload)]
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        draft = provider.generate_weekly_update(
            focus="sprint review", evidence=[_make_evidence()]
        )

    assert draft.summary == "Team shipped v2 on time."
    assert len(draft.wins) == 1
    assert draft.wins[0].text == "shipped v2"
    assert draft.risks == []
    assert draft.next_steps == []


def test_multiple_sections_all_populated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    evidence = [
        _make_evidence("notes.md", 1, "shipped v2"),
        _make_evidence("risks.md", 5, "auth service down"),
        _make_evidence("plan.md", 10, "run load tests"),
    ]
    payload = {
        "summary": "Mixed week.",
        "wins": [{"text": "shipped v2", "source": "notes.md", "line_number": 1}],
        "risks": [{"text": "auth service down", "source": "risks.md", "line_number": 5}],
        "next_steps": [{"text": "run load tests", "source": "plan.md", "line_number": 10}],
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response(
        [_make_tool_use_block(payload)]
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        draft = provider.generate_weekly_update(focus=None, evidence=evidence)

    assert len(draft.wins) == 1
    assert len(draft.risks) == 1
    assert len(draft.next_steps) == 1


# ---------------------------------------------------------------------------
# No tool_use block in response
# ---------------------------------------------------------------------------

def test_raises_when_no_tool_use_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response([_make_text_block("oops")])

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        with pytest.raises(ValueError, match="tool_use block"):
            provider.generate_weekly_update(focus=None, evidence=[_make_evidence()])


# ---------------------------------------------------------------------------
# Citation grounding enforcement
# ---------------------------------------------------------------------------

def test_raises_on_hallucinated_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    payload = {
        "summary": "Looks fine.",
        "wins": [{"text": "invented win", "source": "ghost.md", "line_number": 99}],
        "risks": [],
        "next_steps": [],
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_api_response(
        [_make_tool_use_block(payload)]
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        provider = ClaudeWeeklyUpdateProvider(model="claude-haiku-4-5-20251001")
        with pytest.raises(ValueError, match="ghost.md:99"):
            provider.generate_weekly_update(focus=None, evidence=[_make_evidence()])


def test_raises_on_malformed_grounded_item(monkeypatch: pytest.MonkeyPatch) -> None:
    evidence_locations = {("notes.md", 1)}
    with pytest.raises(ValueError, match="malformed"):
        _parse_grounded_items(["not-a-dict"], evidence_locations)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def test_build_prompt_includes_focus() -> None:
    evidence = [_make_evidence("notes.md", 1, "shipped v2")]
    prompt = _build_prompt("Q3 planning", evidence)
    assert "Q3 planning" in prompt
    assert "notes.md:1" in prompt
    assert "shipped v2" in prompt


def test_build_prompt_uses_default_focus_when_none() -> None:
    prompt = _build_prompt(None, [_make_evidence()])
    assert "current leadership activity" in prompt
