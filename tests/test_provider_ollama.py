"""
Unit tests for OllamaWeeklyUpdateProvider (packages/shared/providers/ollama.py).

All tests mock urllib — no Ollama server required.
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.providers.ollama import OllamaWeeklyUpdateProvider
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


def _mock_urlopen(response_body: dict):
    """Return a context-manager mock that yields a readable response."""
    raw = json.dumps(response_body).encode()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=BytesIO(raw))
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _valid_ollama_body(wins=None, risks=None, next_steps=None) -> dict:
    draft = {
        "summary": "Solid week.",
        "wins": wins or [{"text": "shipped v2", "source": "notes.md", "line_number": 1}],
        "risks": risks or [],
        "next_steps": next_steps or [],
    }
    return {"response": json.dumps(draft)}


_PATCH = "packages.shared.providers.ollama.request.urlopen"
_BASE_URL = "http://localhost:11434"


def _provider() -> OllamaWeeklyUpdateProvider:
    return OllamaWeeklyUpdateProvider(base_url=_BASE_URL, model="llama3.2")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_returns_draft_on_valid_response() -> None:
    evidence = [_make_evidence()]
    with patch(_PATCH, return_value=_mock_urlopen(_valid_ollama_body())):
        draft = _provider().generate_weekly_update(focus=None, evidence=evidence)

    assert draft.summary == "Solid week."
    assert len(draft.wins) == 1
    assert draft.wins[0].source == "notes.md"


def test_all_sections_populated() -> None:
    evidence = [
        _make_evidence("notes.md", 1),
        _make_evidence("risks.md", 5, "auth down"),
        _make_evidence("plan.md", 10, "load test"),
    ]
    body = _valid_ollama_body(
        wins=[{"text": "shipped", "source": "notes.md", "line_number": 1}],
        risks=[{"text": "auth down", "source": "risks.md", "line_number": 5}],
        next_steps=[{"text": "load test", "source": "plan.md", "line_number": 10}],
    )
    with patch(_PATCH, return_value=_mock_urlopen(body)):
        draft = _provider().generate_weekly_update(focus="sprint", evidence=evidence)

    assert len(draft.risks) == 1
    assert len(draft.next_steps) == 1


# ---------------------------------------------------------------------------
# Network / server unavailable
# ---------------------------------------------------------------------------

def test_raises_on_url_error() -> None:
    from urllib.error import URLError

    with patch(_PATCH, side_effect=URLError("connection refused")):
        with pytest.raises(ValueError, match="Unable to reach Ollama"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


def test_raises_on_non_json_http_body() -> None:
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=BytesIO(b"not-json"))
    cm.__exit__ = MagicMock(return_value=False)

    with patch(_PATCH, return_value=cm):
        with pytest.raises(ValueError, match="non-JSON"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


def test_raises_on_empty_response_field() -> None:
    with patch(_PATCH, return_value=_mock_urlopen({"response": ""})):
        with pytest.raises(ValueError, match="empty response"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


def test_raises_on_invalid_json_in_response_field() -> None:
    with patch(_PATCH, return_value=_mock_urlopen({"response": "{bad json"})):
        with pytest.raises(ValueError, match="invalid JSON"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


# ---------------------------------------------------------------------------
# Citation grounding enforcement
# ---------------------------------------------------------------------------

def test_raises_on_citation_outside_evidence() -> None:
    body = _valid_ollama_body(
        wins=[{"text": "ghost win", "source": "ghost.md", "line_number": 99}]
    )
    with patch(_PATCH, return_value=_mock_urlopen(body)):
        with pytest.raises(ValueError, match="not in the retrieved context"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


def test_raises_on_malformed_item() -> None:
    body = {"response": json.dumps({
        "summary": "x",
        "wins": ["not-a-dict"],
        "risks": [],
        "next_steps": [],
    })}
    with patch(_PATCH, return_value=_mock_urlopen(body)):
        with pytest.raises(ValueError, match="malformed"):
            _provider().generate_weekly_update(focus=None, evidence=[_make_evidence()])


# ---------------------------------------------------------------------------
# URL trailing slash normalisation
# ---------------------------------------------------------------------------

def test_base_url_trailing_slash_is_stripped() -> None:
    provider = OllamaWeeklyUpdateProvider(base_url="http://localhost:11434/", model="llama3.2")
    assert provider.base_url == "http://localhost:11434"
