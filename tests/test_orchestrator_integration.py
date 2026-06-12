"""
Unit tests for run_with_mcp_tools and ClaudeProvider
(packages/shared/mcp/orchestrator_integration.py and
packages/shared/providers/claude_provider.py).

All tests mock the Anthropic SDK — no API key or network required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.mcp.orchestrator_integration import (
    MAX_TOOL_ROUNDS,
    run_with_mcp_tools,
)
from packages.shared.providers.claude_provider import (
    ClaudeProvider,
    ProviderResponse,
    get_provider,
)

_SDK_PATCH = "packages.shared.providers.claude_provider._anthropic_sdk.Anthropic"
_PROVIDER_PATCH = "packages.shared.mcp.orchestrator_integration.ClaudeProvider"
_MCP_PATCH = "packages.shared.mcp.orchestrator_integration.FilesystemMCPServer"


# ---------------------------------------------------------------------------
# ClaudeProvider — stub mode (no API key)
# ---------------------------------------------------------------------------

def test_provider_stub_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ClaudeProvider()
    assert not provider.is_available()
    result = provider.complete(prompt="hello")
    assert "stub" in result.content
    assert result.provider == "claude-stub"


def test_get_provider_returns_stub_when_forced() -> None:
    provider = get_provider(use_claude=False)
    assert not provider.is_available()


# ---------------------------------------------------------------------------
# ClaudeProvider — live path (mocked SDK)
# ---------------------------------------------------------------------------

def _make_text_response(
    text: str,
    model: str = "claude-haiku-4-5-20251001",
) -> MagicMock:
    block = SimpleNamespace(type="text", text=text)
    resp = MagicMock()
    resp.content = [block]
    resp.model = model
    resp.usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    return resp


def _make_tool_use_response(
    tool_id: str,
    tool_name: str,
    tool_input: dict,
    model: str = "claude-haiku-4-5-20251001",
) -> MagicMock:
    block = SimpleNamespace(type="tool_use", id=tool_id, name=tool_name, input=tool_input)
    resp = MagicMock()
    resp.content = [block]
    resp.model = model
    resp.usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    return resp


def test_provider_complete_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response("Great summary.")

    with patch(_SDK_PATCH, return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        result = provider.complete(prompt="summarize", context="some docs")

    assert result.content == "Great summary."
    assert result.provider == "claude"
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_provider_complete_extracts_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_use_response(
        "tool_1", "list_directory", {"path": "data/"}
    )

    with patch(_SDK_PATCH, return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        result = provider.complete(prompt="list files", tools=[{"name": "list_directory"}])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "list_directory"
    assert result.tool_calls[0]["input"] == {"path": "data/"}


def test_provider_complete_returns_error_response_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("rate limit")

    with patch(_SDK_PATCH, return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        result = provider.complete(prompt="test")

    assert "rate limit" in result.content
    assert result.provider == "claude-error"


def test_provider_context_injected_with_xml_delimiters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response("ok")

    with patch(_SDK_PATCH, return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        provider.complete(prompt="summarize", context="retrieved docs")

    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "<retrieved_context>" in user_content
    assert "retrieved docs" in user_content


# ---------------------------------------------------------------------------
# run_with_mcp_tools — happy path (text on first round)
# ---------------------------------------------------------------------------

def test_run_with_mcp_tools_returns_on_first_text_response(tmp_path) -> None:
    mock_provider = MagicMock(spec=ClaudeProvider)
    mock_provider.complete.return_value = ProviderResponse(
        content="Here is your summary.",
        model="claude-haiku-4-5-20251001",
        provider="claude",
        input_tokens=20,
        output_tokens=10,
    )

    with patch(_PROVIDER_PATCH, return_value=mock_provider):
        result = run_with_mcp_tools(prompt="weekly update", data_path=str(tmp_path))

    assert result.success is True
    assert result.content == "Here is your summary."
    assert result.total_tokens == 30
    assert mock_provider.complete.call_count == 1


# ---------------------------------------------------------------------------
# run_with_mcp_tools — tool call round-trip
# ---------------------------------------------------------------------------

def test_run_with_mcp_tools_executes_one_tool_round(tmp_path) -> None:
    (tmp_path / "notes.md").write_text("- shipped v2")

    tool_response = ProviderResponse(
        content="",
        model="claude-haiku-4-5-20251001",
        provider="claude",
        input_tokens=10,
        output_tokens=5,
        tool_calls=[{"id": "t1", "name": "list_directory", "input": {"path": str(tmp_path)}}],
    )
    text_response = ProviderResponse(
        content="Done.",
        model="claude-haiku-4-5-20251001",
        provider="claude",
        input_tokens=15,
        output_tokens=8,
    )

    mock_provider = MagicMock(spec=ClaudeProvider)
    mock_provider.complete.side_effect = [tool_response, text_response]

    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"success": True, "result": "notes.md", "error": None}

    with (
        patch(_PROVIDER_PATCH, return_value=mock_provider),
        patch(_MCP_PATCH, return_value=mock_mcp),
    ):
        result = run_with_mcp_tools(prompt="list files", data_path=str(tmp_path))

    assert result.success is True
    assert result.content == "Done."
    assert len(result.trace["mcp_tool_calls"]) == 1
    assert result.trace["mcp_tool_calls"][0]["tool"] == "list_directory"
    assert mock_provider.complete.call_count == 2


# ---------------------------------------------------------------------------
# run_with_mcp_tools — max rounds exceeded
# ---------------------------------------------------------------------------

def test_run_with_mcp_tools_fails_at_max_rounds(tmp_path) -> None:
    always_tool = ProviderResponse(
        content="",
        model="claude-haiku-4-5-20251001",
        provider="claude",
        input_tokens=5,
        output_tokens=5,
        tool_calls=[{"id": "t1", "name": "list_directory", "input": {"path": str(tmp_path)}}],
    )

    mock_provider = MagicMock(spec=ClaudeProvider)
    mock_provider.complete.return_value = always_tool

    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"success": True, "result": "ok", "error": None}

    with (
        patch(_PROVIDER_PATCH, return_value=mock_provider),
        patch(_MCP_PATCH, return_value=mock_mcp),
    ):
        result = run_with_mcp_tools(
            prompt="go", data_path=str(tmp_path), max_rounds=MAX_TOOL_ROUNDS
        )

    assert result.success is False
    assert "maximum tool call rounds" in (result.error or "")
    assert mock_provider.complete.call_count == MAX_TOOL_ROUNDS
