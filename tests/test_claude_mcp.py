"""
Tests for the Claude provider and filesystem MCP server.

Designed to run in CI without an ANTHROPIC_API_KEY — all live API calls
are skipped when the key is absent. The stub path is always tested.

Run:
    pytest tests/test_claude_mcp.py -v

Run with live Claude calls (requires ANTHROPIC_API_KEY):
    ANTHROPIC_API_KEY=sk-ant-... pytest tests/test_claude_mcp.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from packages.shared.providers.claude_provider import (
    ClaudeProvider,
    ProviderResponse,
    get_provider,
)
from packages.shared.mcp.filesystem_server import (
    FilesystemMCPServer,
    get_tool_definitions,
    build_tool_result_message,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with sample project files."""
    projects = tmp_path / "projects"
    projects.mkdir()

    (projects / "weekly-notes.md").write_text(
        "# Week of June 2026\n\n"
        "## Key wins\n- Shipped MCP integration to staging\n"
        "## Blockers\n- API rate limits on external data source\n"
        "## Next steps\n- Production deployment review\n"
    )
    (projects / "roadmap.md").write_text(
        "# Q3 Roadmap\n\n"
        "- Claude provider integration (done)\n"
        "- MCP filesystem server (done)\n"
        "- Enterprise deployment guide (in progress)\n"
    )

    brand = tmp_path / "brand"
    brand.mkdir()
    (brand / "podcast-ideas.md").write_text(
        "# Podcast ideas\n\n"
        "- Episode: MCP for enterprise AI\n"
        "- Episode: LLM evaluation at scale\n"
    )

    return tmp_path


@pytest.fixture()
def mcp_server(temp_data_dir: Path) -> FilesystemMCPServer:
    return FilesystemMCPServer(root_path=temp_data_dir)


# ---------------------------------------------------------------------------
# Claude provider — stub path (no API key required)
# ---------------------------------------------------------------------------

class TestClaudeProviderStub:
    def test_stub_is_available_without_key(self) -> None:
        provider = ClaudeProvider(api_key="")
        assert not provider.is_available()

    def test_stub_returns_provider_response(self) -> None:
        provider = ClaudeProvider(api_key="")
        result = provider.complete(prompt="Test prompt")
        assert isinstance(result, ProviderResponse)
        assert "stub" in result.provider.lower() or "error" in result.provider.lower()

    def test_stub_content_contains_provider_signal(self) -> None:
        provider = ClaudeProvider(api_key="")
        result = provider.complete(prompt="What are this week's blockers?")
        assert "ClaudeProvider" in result.content

    def test_get_provider_returns_claude_provider(self) -> None:
        provider = get_provider()
        assert isinstance(provider, ClaudeProvider)

    def test_get_provider_opt_out_returns_stub(self) -> None:
        provider = get_provider(use_claude=False)
        assert isinstance(provider, ClaudeProvider)
        assert not provider.is_available()


# ---------------------------------------------------------------------------
# Claude provider — live path (skipped without API key)
# ---------------------------------------------------------------------------

LIVE = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live Claude tests",
)


class TestClaudeProviderLive:
    @LIVE
    def test_live_completion_returns_text(self) -> None:
        provider = ClaudeProvider()
        assert provider.is_available(), "API key set but provider not available"
        result = provider.complete(
            prompt="Reply with exactly one word: hello",
        )
        assert isinstance(result, ProviderResponse)
        assert len(result.content) > 0
        assert result.input_tokens > 0
        assert result.output_tokens > 0

    @LIVE
    def test_live_completion_with_context(self) -> None:
        provider = ClaudeProvider()
        result = provider.complete(
            prompt="What is the main blocker mentioned?",
            context="Project status: The main blocker is API rate limits on the data pipeline.",
        )
        assert "rate" in result.content.lower() or "api" in result.content.lower()

    @LIVE
    def test_live_tool_definitions_accepted(self) -> None:
        """Claude accepts the MCP tool definitions without error."""
        provider = ClaudeProvider()
        tools = get_tool_definitions()
        result = provider.complete(
            prompt="List available tools only, do not call any.",
            tools=tools,
        )
        assert isinstance(result, ProviderResponse)
        assert result.content or result.tool_calls


# ---------------------------------------------------------------------------
# Filesystem MCP server
# ---------------------------------------------------------------------------

class TestFilesystemMCPServer:
    def test_list_files_returns_file_names(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("list_files", {"path": "projects"})
        assert result["success"]
        assert "weekly-notes.md" in result["result"]
        assert "roadmap.md" in result["result"]

    def test_list_files_with_pattern(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("list_files", {"path": "projects", "pattern": "*.md"})
        assert result["success"]
        assert "weekly-notes.md" in result["result"]

    def test_read_file_returns_content(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("read_file", {"path": "projects/weekly-notes.md"})
        assert result["success"]
        assert "Key wins" in result["result"]
        assert "Blockers" in result["result"]

    def test_read_file_not_found(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("read_file", {"path": "projects/nonexistent.md"})
        assert not result["success"]
        assert result["error"] is not None

    def test_search_content_finds_match(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool(
            "search_content",
            {"path": "projects", "query": "Blockers"},
        )
        assert result["success"]
        assert "weekly-notes.md" in result["result"]

    def test_search_content_no_match(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool(
            "search_content",
            {"path": "projects", "query": "xyzzy_not_present"},
        )
        assert result["success"]
        assert "No matches" in result["result"]

    def test_path_traversal_blocked(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("read_file", {"path": "../../../etc/passwd"})
        assert not result["success"]

    def test_unknown_tool_returns_error(self, mcp_server: FilesystemMCPServer) -> None:
        result = mcp_server.call_tool("delete_file", {"path": "anything"})
        assert not result["success"]
        assert "Unknown tool" in result["error"]

    def test_tool_definitions_schema_valid(self) -> None:
        tools = get_tool_definitions()
        assert len(tools) == 3
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema


# ---------------------------------------------------------------------------
# Tool result message builder
# ---------------------------------------------------------------------------

class TestBuildToolResultMessage:
    def test_success_result_shape(self) -> None:
        msg = build_tool_result_message(
            "tc_001",
            {"success": True, "result": "File contents here", "error": None},
        )
        assert msg["role"] == "user"
        block = msg["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "tc_001"
        assert block["content"] == "File contents here"

    def test_error_result_shape(self) -> None:
        msg = build_tool_result_message(
            "tc_002",
            {"success": False, "result": "", "error": "File not found"},
        )
        block = msg["content"][0]
        assert "Error:" in block["content"]
        assert "File not found" in block["content"]
