"""
Grounded MCP tool loop for AI-OS (Phase 9c).

Connects the Chief of Staff orchestrator to the Claude provider and filesystem
MCP server. Claude decides which files to list, search, and read; the loop
executes each call and continues until Claude submits its answer.

The loop is grounded the same way the domain workflows are:

- `read_file` returns numbered lines and the server records every line it
  serves, so the evidence is exactly what the model was shown.
- Every round uses `tool_choice: any`, so the model cannot end with free text.
  The only way to finish is `submit_grounded_synthesis`, whose items require
  `source` and `line_number` (the shared GROUNDED_ITEM_SCHEMA).
- Each submitted item must cite a line the server served, and its text must
  match that line (the shared `validate_grounded_item`). One bad item rejects
  the whole synthesis; the caller falls back to the deterministic workflow.

Usage:
    from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools

    response = run_with_mcp_tools(
        prompt="Prepare my weekly leadership update",
        data_path="data/local_only/projects",
    )
    if response.success:
        print(response.synthesis.items)   # every item cites file + line
    print(response.trace)                 # tool calls, rounds, token totals
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from packages.shared.mcp.filesystem_server import (
    FilesystemMCPServer,
    get_tool_definitions,
)
from packages.shared.providers.claude_provider import ClaudeProvider, ProviderResponse
from packages.shared.providers.grounding import GROUNDED_ITEM_SCHEMA, parse_grounded_items
from packages.shared.schemas.base import EvidenceItem
from packages.shared.schemas.orchestrator import McpSynthesis
from packages.shared.validation.grounding import validate_grounded_item

logger = logging.getLogger(__name__)

# Safety circuit breaker. If Claude keeps calling file tools without ever
# submitting, stop at this many rounds rather than looping and burning tokens.
MAX_TOOL_ROUNDS = 5

SUBMIT_TOOL_NAME = "submit_grounded_synthesis"
MAX_SUBMITTED_ITEMS = 12

SUBMIT_TOOL: dict[str, Any] = {
    "name": SUBMIT_TOOL_NAME,
    "description": (
        "Submit your final answer. Call this exactly once, after reading what you need. "
        "Every item must quote or closely paraphrase one line you were shown by "
        "read_file or search_content, and cite that line's file path (source) and line "
        "number (line_number) exactly as shown."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Two or three sentences summarizing the answer.",
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_SUBMITTED_ITEMS,
                "items": GROUNDED_ITEM_SCHEMA,
            },
        },
        "required": ["summary", "items"],
    },
}

MCP_SYSTEM_PROMPT = (
    "You are an AI assistant embedded in an evidence-grounded enterprise workflow system. "
    "Use list_files, search_content, and read_file to find the notes relevant to the "
    "request. read_file shows each line as '<line>| <text>'. When you have enough, call "
    f"{SUBMIT_TOOL_NAME}. Each item must come from a single line you were shown and cite "
    "that line's file path and line number exactly. Do not include anything you did not "
    "read. Do not take any action other than reading and submitting."
)


class _Submission(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    items: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_SUBMITTED_ITEMS)


@dataclass
class OrchestratedResponse:
    """
    Final response from the grounded MCP tool loop.

    `synthesis` is set only when the model submitted and every item passed
    grounding validation. Otherwise `success` is False and `error` says why.
    The `trace` field records which tools were called, with what inputs, and
    what they returned: the operator-visibility pattern.
    """

    content: str
    model: str
    provider: str
    total_tokens: int
    trace: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    synthesis: McpSynthesis | None = None


def validate_submission(
    tool_input: Any,
    served: list[EvidenceItem],
) -> McpSynthesis:
    """Validate a submitted synthesis against the lines the model was served.

    Raises ValueError naming the first problem. Returns the synthesis with
    `evidence` narrowed to the lines its items cite.
    """
    if not served:
        raise ValueError("model submitted without reading any file content")
    try:
        submission = _Submission.model_validate(tool_input)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or "input"
        raise ValueError(f"malformed submission: {location}: {first['msg']}") from exc

    lookup = {(item.source, item.line_number): item for item in served}
    items = parse_grounded_items(submission.items, set(lookup))
    for index, item in enumerate(items, start=1):
        try:
            validate_grounded_item(item, served)
        except ValueError as exc:
            raise ValueError(f"item {index} ({item.source}:{item.line_number}): {exc}") from exc

    cited = list(dict.fromkeys((item.source, item.line_number) for item in items))
    return McpSynthesis(
        summary=submission.summary,
        items=items,
        evidence=[lookup[key] for key in cited],
    )


def run_with_mcp_tools(
    prompt: str,
    data_path: str = "data/local_only",
    model: str | None = None,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> OrchestratedResponse:
    """
    Run a prompt through Claude with filesystem MCP tools, ending in a grounded submit.

    The loop:
        Round 1: send prompt + file tools + submit tool, tool_choice=any
        If Claude calls file tools:
            execute each via FilesystemMCPServer, append the assistant tool_use
            blocks and the tool_result blocks to the history, continue
        If Claude calls submit_grounded_synthesis:
            validate every item against the lines served so far and stop
        Until: a submission (valid or not), a provider failure, a reply with no
               tool call, or max_rounds

    Args:
        prompt:     The user request (e.g. "Prepare my weekly update")
        data_path:  Root path for the filesystem MCP server
        model:      Override the Claude model (default from config/models.yaml)
        max_rounds: Safety limit on tool call iterations

    Returns:
        OrchestratedResponse with the validated synthesis (or the failure reason),
        token totals, and full trace.
    """
    provider_kwargs = {"model": model} if model else {}
    provider = ClaudeProvider(**provider_kwargs)
    mcp_server = FilesystemMCPServer(root_path=data_path)
    tools = [*get_tool_definitions(), SUBMIT_TOOL]

    trace: dict[str, Any] = {
        "rounds": [],
        "mcp_tool_calls": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "data_path": data_path,
        "submitted": False,
    }

    # Seed the conversation with the user prompt once. Every subsequent round
    # extends this list by appending the assistant's tool_use block followed by
    # the tool_result block. The original prompt is never re-sent.
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    totals = {"input": 0, "output": 0}
    last_model = model or "unknown"

    def finish(*, error: str | None, synthesis: McpSynthesis | None = None):
        trace["total_input_tokens"] = totals["input"]
        trace["total_output_tokens"] = totals["output"]
        trace["tool_calls_total"] = len(trace["mcp_tool_calls"])
        trace["evidence_served"] = len(mcp_server.served_evidence())
        if error:
            trace["error"] = error
            logger.warning("MCP loop ended without a grounded synthesis: %s", error)
        return OrchestratedResponse(
            content=synthesis.summary if synthesis else "",
            model=last_model,
            provider="claude",
            total_tokens=totals["input"] + totals["output"],
            trace=trace,
            success=synthesis is not None,
            error=error,
            synthesis=synthesis,
        )

    for round_num in range(1, max_rounds + 1):
        round_trace: dict[str, Any] = {"round": round_num, "tool_calls": []}
        trace["rounds"].append(round_trace)
        logger.info("MCP round %d/%d", round_num, max_rounds)

        response: ProviderResponse = provider.complete(
            prompt="",
            context="",
            tools=tools,
            messages=messages,
            system_override=MCP_SYSTEM_PROMPT,
            tool_choice={"type": "any"},
        )
        totals["input"] += response.input_tokens
        totals["output"] += response.output_tokens
        last_model = response.model or last_model

        if not response.success:
            # The provider itself failed (no API key, SDK error, etc). Its
            # content is a stub/error message, not an answer.
            return finish(error=f"provider failure: {response.content}")

        submissions = [call for call in response.tool_calls if call["name"] == SUBMIT_TOOL_NAME]
        if submissions:
            trace["submitted"] = True
            round_trace["tool_calls"].append({"tool": SUBMIT_TOOL_NAME})
            try:
                synthesis = validate_submission(
                    submissions[0]["input"], mcp_server.served_evidence()
                )
            except ValueError as exc:
                return finish(error=f"submission rejected: {exc}")
            logger.info(
                "MCP loop complete: %d rounds, %d tool calls, %d grounded items",
                round_num,
                len(trace["mcp_tool_calls"]),
                len(synthesis.items),
            )
            return finish(error=None, synthesis=synthesis)

        if not response.tool_calls:
            # tool_choice=any makes this unreachable against the real API; the
            # stub provider and malformed responses still need a clean exit.
            return finish(error="model ended without calling a tool or submitting")

        tool_use_blocks: list[dict[str, Any]] = []
        tool_result_contents: list[dict[str, Any]] = []
        for tool_call in response.tool_calls:
            tool_name, tool_input, tool_id = tool_call["name"], tool_call["input"], tool_call["id"]
            logger.info("  MCP tool call: %s(%s)", tool_name, tool_input)
            tool_result = mcp_server.call_tool(tool_name, tool_input)

            call_record = {
                "id": tool_id,
                "tool": tool_name,
                "input": tool_input,
                "success": tool_result["success"],
                "result_preview": (tool_result["result"] or "")[:200],
                "error": tool_result["error"],
            }
            round_trace["tool_calls"].append(call_record)
            trace["mcp_tool_calls"].append(call_record)

            tool_use_blocks.append(
                {"type": "tool_use", "id": tool_id, "name": tool_name, "input": tool_input}
            )
            tool_result_contents.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": (
                        tool_result["result"]
                        if tool_result["success"]
                        else f"Error: {tool_result['error']}"
                    ),
                }
            )

        # The Anthropic API requires all tool_use blocks from a single
        # response in ONE assistant message, followed by all tool_result
        # blocks in ONE user message. Splitting them per-tool produces
        # consecutive assistant messages and triggers a 400 role-alternation
        # error on the next round when Claude returns parallel tool calls.
        messages.append({"role": "assistant", "content": tool_use_blocks})
        messages.append({"role": "user", "content": tool_result_contents})

    return finish(error=f"Exceeded maximum tool call rounds ({max_rounds}) without submitting")
