"""Grounded MCP tool loop (Phase 9c).

The model-directed MCP loop used to return free text that nothing validated.
It now ends only through `submit_grounded_synthesis`, and every submitted item
must cite a line the filesystem tools actually served and match that line's
text. All tests use a mocked provider; none reach a real model.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.mcp.filesystem_server import FilesystemMCPServer
from packages.shared.mcp.orchestrator_integration import (
    MCP_SYSTEM_PROMPT,
    SUBMIT_TOOL_NAME,
    run_with_mcp_tools,
    validate_submission,
)
from packages.shared.providers.claude_provider import ClaudeProvider, ProviderResponse

_PROVIDER_PATCH = "packages.shared.mcp.orchestrator_integration.ClaudeProvider"
_WIN = "Win: shipped the v2 billing export to all regions"
_RISK = "Risk: vendor contract renewal is blocked on legal review"


@pytest.fixture()
def notes(tmp_path: Path) -> Path:
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "week.md").write_text(
        f"# Week 18\n\n- {_WIN}\n- {_RISK}\n", encoding="utf-8"
    )
    return tmp_path


def _response(*tool_calls: dict, content: str = "", success: bool = True) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        model="claude-test",
        provider="claude",
        input_tokens=10,
        output_tokens=5,
        tool_calls=list(tool_calls),
        success=success,
    )


def _read(path: str, call_id: str = "r1") -> dict:
    return {"id": call_id, "name": "read_file", "input": {"path": path}}


def _submit(items: list[dict], summary: str = "Billing export shipped.") -> dict:
    return {"id": "s1", "name": SUBMIT_TOOL_NAME, "input": {"summary": summary, "items": items}}


def _run(notes: Path, *responses: ProviderResponse):
    provider = MagicMock(spec=ClaudeProvider)
    provider.complete.side_effect = list(responses)
    with patch(_PROVIDER_PATCH, return_value=provider):
        result = run_with_mcp_tools(prompt="what shipped?", data_path=str(notes))
    return result, provider


# ---------------------------------------------------------------------------
# Filesystem server: numbered lines + served-evidence record
# ---------------------------------------------------------------------------


def test_read_file_numbers_lines_and_records_them_as_evidence(notes: Path) -> None:
    server = FilesystemMCPServer(root_path=notes)
    result = server.call_tool("read_file", {"path": "projects/week.md"})

    assert result["success"]
    assert f"   3| - {_WIN}" in result["result"]
    served = {(ev.source, ev.line_number): ev.excerpt for ev in server.served_evidence()}
    # Blank lines are not citable; list markers are stripped like keyword retrieval.
    assert served == {
        ("projects/week.md", 1): "# Week 18",
        ("projects/week.md", 3): _WIN,
        ("projects/week.md", 4): _RISK,
    }


def test_search_content_records_only_the_matching_lines(notes: Path) -> None:
    server = FilesystemMCPServer(root_path=notes)
    server.call_tool("search_content", {"path": "projects", "query": "vendor"})
    assert [(ev.source, ev.line_number) for ev in server.served_evidence()] == [
        ("projects/week.md", 4)
    ]


def test_list_files_serves_no_citable_evidence(notes: Path) -> None:
    server = FilesystemMCPServer(root_path=notes)
    server.call_tool("list_files", {"path": "projects"})
    assert server.served_evidence() == []


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


def test_valid_submission_returns_grounded_synthesis(notes: Path) -> None:
    result, _ = _run(
        notes,
        _response(_read("projects/week.md")),
        _response(
            _submit(
                [
                    {"text": _WIN, "source": "projects/week.md", "line_number": 3},
                    {"text": _RISK, "source": "projects/week.md", "line_number": 4},
                ]
            )
        ),
    )

    assert result.success, result.error
    assert result.synthesis.summary == "Billing export shipped."
    assert [item.line_number for item in result.synthesis.items] == [3, 4]
    # Evidence is narrowed to the cited lines, not everything served.
    assert [(ev.source, ev.line_number) for ev in result.synthesis.evidence] == [
        ("projects/week.md", 3),
        ("projects/week.md", 4),
    ]
    assert result.trace["evidence_served"] == 3
    assert result.total_tokens == 30


def test_every_round_forces_a_tool_call_and_offers_submit(notes: Path) -> None:
    _, provider = _run(
        notes,
        _response(_read("projects/week.md")),
        _response(_submit([{"text": _WIN, "source": "projects/week.md", "line_number": 3}])),
    )

    for call in provider.complete.call_args_list:
        kwargs = call.kwargs
        assert kwargs["tool_choice"] == {"type": "any"}
        assert kwargs["system_override"] == MCP_SYSTEM_PROMPT
        names = [tool["name"] for tool in kwargs["tools"]]
        assert names == ["list_files", "read_file", "search_content", SUBMIT_TOOL_NAME]
    submit_schema = provider.complete.call_args.kwargs["tools"][-1]["input_schema"]
    item_schema = submit_schema["properties"]["items"]["items"]
    assert item_schema["required"] == ["text", "source", "line_number"]


@pytest.mark.parametrize(
    ("items", "reason"),
    [
        # Cites a line that exists in the file but was never served.
        ([{"text": _WIN, "source": "projects/other.md", "line_number": 3}], "not in the retrieved"),
        ([{"text": _WIN, "source": "projects/week.md", "line_number": 99}], "not in the retrieved"),
        # Right citation, invented text.
        (
            [{"text": "Revenue doubled after the launch", "source": "projects/week.md",
              "line_number": 3}],
            "semantically anchored",
        ),
        # One good item does not rescue a bad one.
        (
            [
                {"text": _WIN, "source": "projects/week.md", "line_number": 3},
                {"text": "Invented claim about headcount", "source": "projects/week.md",
                 "line_number": 4},
            ],
            "item 2",
        ),
        ([], "malformed submission"),
        ([{"text": _WIN, "source": "projects/week.md", "line_number": "three"}], "non-numeric"),
    ],
)
def test_invalid_submission_is_rejected_with_reason(notes: Path, items, reason) -> None:
    result, _ = _run(notes, _response(_read("projects/week.md")), _response(_submit(items)))

    assert result.success is False
    assert result.synthesis is None
    assert result.content == ""
    assert reason in result.error
    assert result.error.startswith("submission rejected")


def test_submission_without_reading_anything_is_rejected(notes: Path) -> None:
    result, _ = _run(
        notes,
        _response(_submit([{"text": _WIN, "source": "projects/week.md", "line_number": 3}])),
    )
    assert result.success is False
    assert "without reading any file content" in result.error


def test_provider_failure_ends_the_loop(notes: Path) -> None:
    result, _ = _run(notes, _response(content="[ClaudeProvider error] boom", success=False))
    assert result.success is False
    assert result.error.startswith("provider failure")


def test_stub_provider_without_api_key_cannot_produce_a_synthesis(notes, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = run_with_mcp_tools(prompt="what shipped?", data_path=str(notes))
    assert result.success is False
    assert result.synthesis is None


def test_validate_submission_unit(notes: Path) -> None:
    server = FilesystemMCPServer(root_path=notes)
    server.call_tool("read_file", {"path": "projects/week.md"})
    synthesis = validate_submission(
        {"summary": "ok", "items": [{"text": _RISK, "source": "projects/week.md",
                                     "line_number": 4}]},
        server.served_evidence(),
    )
    assert synthesis.items[0].text == _RISK


# ---------------------------------------------------------------------------
# /orchestrate surface
# ---------------------------------------------------------------------------

client = TestClient(app)


def test_orchestrate_returns_grounded_mcp_result(monkeypatch) -> None:
    line = "Win: shipped the internal status dashboard refresh for leadership review."
    provider = MagicMock(spec=ClaudeProvider)
    provider.complete.side_effect = [
        _response(_read("director_week_14.md")),
        _response(_submit([{"text": line, "source": "director_week_14.md", "line_number": 3}])),
    ]
    with patch(_PROVIDER_PATCH, return_value=provider):
        response = client.post(
            "/orchestrate",
            json={
                "prompt": "weekly update",
                "data_path": "data/local_only/projects",
                "use_mcp": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mcp_result"]["items"][0] == {
        "text": line,
        "source": "director_week_14.md",
        "line_number": 3,
    }
    assert body["mcp_synthesis"] == "Billing export shipped."
    assert body["trace"]["mcp_fallback_reason"] is None


def test_orchestrate_drops_rejected_mcp_synthesis_and_says_why(monkeypatch) -> None:
    provider = MagicMock(spec=ClaudeProvider)
    provider.complete.side_effect = [
        _response(_read("director_week_14.md")),
        _response(_submit([{"text": "Invented", "source": "director_week_14.md",
                            "line_number": 3}])),
    ]
    with patch(_PROVIDER_PATCH, return_value=provider):
        body = client.post(
            "/orchestrate",
            json={
                "prompt": "weekly update",
                "data_path": "data/local_only/projects",
                "use_mcp": True,
            },
        ).json()

    assert body["mcp_result"] is None
    assert body["mcp_synthesis"] is None
    assert body["trace"]["mcp_fallback_reason"].startswith("submission rejected")
    # The deterministic workflow result is still returned.
    assert body["result"]["evidence"]


def test_operator_console_escapes_api_content() -> None:
    html = (Path(__file__).resolve().parents[1] / "apps/api/templates/console.html").read_text(
        encoding="utf-8"
    )
    assert "function esc(" in html
    for raw in (
        "+ body.mcp_synthesis +",
        "+ body.formatted_content +",
        "+ body.rationale +",
        "${errMsg}",
        "${summary}",
        "${text}",
    ):
        assert raw not in html, f"unescaped API content in console: {raw}"
