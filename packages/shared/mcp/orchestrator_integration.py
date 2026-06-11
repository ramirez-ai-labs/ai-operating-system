"""
MCP-aware orchestration loop for AI-OS.

Connects the Chief of Staff orchestrator to the Claude provider and filesystem
MCP server. Handles the tool_use → execute → continue loop that turns Claude's
tool calls into real file retrievals.

Usage:
    from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools

    response = run_with_mcp_tools(
        prompt="Prepare my weekly leadership update",
        data_path="data/local_only/projects",
    )
    print(response.content)
    print(response.trace)  # includes mcp_tool_calls for operator visibility
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from packages.shared.providers.claude_provider import ClaudeProvider, ProviderResponse
from packages.shared.mcp.filesystem_server import (
    FilesystemMCPServer,
    get_tool_definitions,
    build_tool_result_message,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


@dataclass
class OrchestratedResponse:
    """
    Final response from the MCP-aware orchestration loop.

    The `trace` field surfaces what the agent did — which tools it called,
    what inputs it used, and what it retrieved. This is the operator
    visibility pattern: see exactly what happened when debugging.
    """

    content: str
    model: str
    provider: str
    total_tokens: int
    trace: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None


def run_with_mcp_tools(
    prompt: str,
    data_path: str = "data/local_only",
    model: str | None = None,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> OrchestratedResponse:
    """
    Run a prompt through Claude with filesystem MCP tools available.

    The loop:
        Round 1: Send prompt + tool definitions to Claude
        If Claude returns tool_calls:
            Execute each tool via FilesystemMCPServer
            Append assistant tool_use + tool_result blocks to message history
            Round N: Continue with updated history (no new user turn added)
        Until: Claude returns a text response (no more tool_calls)
               or max_rounds is reached

    Args:
        prompt:     The user request (e.g. "Prepare my weekly update")
        data_path:  Root path for the filesystem MCP server
        model:      Override the Claude model (default: haiku)
        max_rounds: Safety limit on tool call iterations

    Returns:
        OrchestratedResponse with content, token totals, and full trace
    """
    provider_kwargs = {"model": model} if model else {}
    provider = ClaudeProvider(**provider_kwargs)
    mcp_server = FilesystemMCPServer(root_path=data_path)
    tools = get_tool_definitions()

    trace: dict[str, Any] = {
        "rounds": [],
        "mcp_tool_calls": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "data_path": data_path,
    }

    # Seed messages with the initial user prompt. Subsequent rounds only append
    # assistant tool_use blocks and user tool_result blocks — no extra user turns.
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    total_input = 0
    total_output = 0

    for round_num in range(1, max_rounds + 1):
        round_trace: dict[str, Any] = {
            "round": round_num,
            "tool_calls": [],
            "text_produced": False,
        }

        logger.info("Orchestration round %d/%d", round_num, max_rounds)

        response: ProviderResponse = provider.complete(
            prompt="",
            context="",
            tools=tools,
            messages=messages,
        )

        total_input += response.input_tokens
        total_output += response.output_tokens

        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

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

                # Append assistant tool_use block then user tool_result block.
                # This is the Anthropic multi-turn tool_use format.
                messages.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                    ],
                })
                messages.append(build_tool_result_message(tool_id, tool_result))

            trace["rounds"].append(round_trace)
            continue

        if response.content:
            round_trace["text_produced"] = True
            trace["rounds"].append(round_trace)
            trace["total_input_tokens"] = total_input
            trace["total_output_tokens"] = total_output
            trace["tool_calls_total"] = len(trace["mcp_tool_calls"])

            logger.info(
                "Orchestration complete: %d rounds, %d tool calls, %d tokens",
                round_num,
                len(trace["mcp_tool_calls"]),
                total_input + total_output,
            )

            return OrchestratedResponse(
                content=response.content,
                model=response.model,
                provider=response.provider,
                total_tokens=total_input + total_output,
                trace=trace,
                success=True,
            )

        logger.warning("Round %d: empty response from Claude", round_num)
        trace["rounds"].append(round_trace)

    logger.error("Orchestration hit max rounds (%d) without completing", max_rounds)
    return OrchestratedResponse(
        content="",
        model="unknown",
        provider="claude",
        total_tokens=total_input + total_output,
        trace=trace,
        success=False,
        error=f"Exceeded maximum tool call rounds ({max_rounds})",
    )
