"""Tests for Phase 5e: Ollama-backed workflow classification with keyword fallback."""

import json
from unittest.mock import MagicMock, patch

from packages.shared.orchestration.chief_of_staff import (
    _classify_with_ollama,
    _select_workflow_keyword,
    route_request,
)
from packages.shared.schemas.orchestrator import OrchestratorRequest

# ---------------------------------------------------------------------------
# _classify_with_ollama unit tests (no real Ollama required)
# ---------------------------------------------------------------------------

def _mock_ollama_response(content: str):
    """Return a mock urlopen context manager that yields an Ollama chat response."""
    body = json.dumps({"message": {"content": content}}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_classify_brand_os_when_model_says_brand() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_ollama_response("brand_os")):
        workflow, rationale, routing_model = _classify_with_ollama(
            prompt="write a LinkedIn post",
            ollama_url="http://localhost:11434",
            model="llama3.2",
        )
    assert workflow == "brand_os.content_draft"
    assert "brand_os" in rationale
    assert routing_model == "ollama/llama3.2"


def test_classify_director_os_when_model_says_director() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_ollama_response("director_os")):
        workflow, rationale, routing_model = _classify_with_ollama(
            prompt="prepare my weekly status",
            ollama_url="http://localhost:11434",
            model="llama3.2",
        )
    assert workflow == "director_os.weekly_update"
    assert "director_os" in rationale
    assert routing_model == "ollama/llama3.2"


def test_classify_falls_back_to_keyword_when_ollama_unreachable() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        workflow, rationale, routing_model = _classify_with_ollama(
            prompt="podcast episode draft",
            ollama_url="http://localhost:11434",
            model="llama3.2",
        )
    assert workflow == "brand_os.content_draft"
    assert "unreachable" in routing_model
    assert "llama3.2" in routing_model


def test_classify_falls_back_to_director_default_when_ollama_unreachable() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        workflow, rationale, routing_model = _classify_with_ollama(
            prompt=None,
            ollama_url="http://localhost:11434",
            model="llama3.2",
        )
    assert workflow == "director_os.weekly_update"
    assert "default" in rationale
    assert "unreachable" in routing_model


def test_classify_treats_ambiguous_response_as_director_os() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_ollama_response("something else")):
        workflow, _, routing_model = _classify_with_ollama(
            prompt="random request",
            ollama_url="http://localhost:11434",
            model="llama3.2",
        )
    assert workflow == "director_os.weekly_update"
    assert routing_model == "ollama/llama3.2"


# ---------------------------------------------------------------------------
# _select_workflow_keyword unit tests
# ---------------------------------------------------------------------------

def test_keyword_router_picks_brand_os() -> None:
    workflow, rationale = _select_workflow_keyword("write a linkedin post")
    assert workflow == "brand_os.content_draft"
    assert "linkedin" in rationale


def test_keyword_router_picks_director_os() -> None:
    workflow, rationale = _select_workflow_keyword("leadership weekly update")
    assert workflow == "director_os.weekly_update"
    assert "leadership" in rationale


def test_keyword_router_defaults_to_director_os() -> None:
    workflow, rationale = _select_workflow_keyword(None)
    assert workflow == "director_os.weekly_update"
    assert "default" in rationale


# ---------------------------------------------------------------------------
# route_request integration: routing_model surfaces in trace
# ---------------------------------------------------------------------------

def test_trace_routing_model_reflects_ollama_classification() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_ollama_response("director_os")):
        response = route_request(
            OrchestratorRequest(
                prompt="project status summary",
                data_path="data/local_only/projects",
                max_documents=3,
            )
        )
    assert response.trace.routing_model == "ollama/llama3.2"


def test_trace_routing_model_shows_fallback_when_ollama_absent() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        response = route_request(
            OrchestratorRequest(
                prompt="weekly leadership update",
                data_path="data/local_only/projects",
                max_documents=3,
            )
        )
    assert "unreachable" in response.trace.routing_model


def test_trace_routing_model_is_explicit_when_workflow_forced() -> None:
    response = route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
            max_documents=3,
        )
    )
    assert response.trace.routing_model == "explicit"
