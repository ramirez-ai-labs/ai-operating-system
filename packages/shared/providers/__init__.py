"""
Provider abstractions for local and optional hybrid model execution.

There are two Claude provider classes — they serve different roles:

claude.py — ClaudeWeeklyUpdateProvider
    Implements the WeeklyUpdateProvider interface for Director OS synthesis.
    Uses forced tool use (tool_choice={"type": "tool"}) to guarantee structured
    output (wins/risks/next_steps with source citations). This is the production
    synthesis path called by the Director OS graph. Tests: test_provider_claude.py.

claude_provider.py — ClaudeProvider
    General-purpose Anthropic Messages API wrapper for MCP orchestration loops.
    Supports multi-turn tool call cycles, stub fallback when ANTHROPIC_API_KEY
    is absent, and structured error responses. Used by orchestrator_integration.py
    and the MCP tool-use loop. Tests: test_orchestrator_integration.py.

When adding a new workflow domain, inherit from WeeklyUpdateProvider (base.py)
and model your provider on claude.py — not on ClaudeProvider.
"""
