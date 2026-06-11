"""
General-purpose Claude provider for AI-OS.

Wraps the Anthropic Messages API with tool_use support for MCP-based
orchestration. This is distinct from ClaudeWeeklyUpdateProvider (claude.py),
which implements the WeeklyUpdateProvider interface for structured update
synthesis. This provider is used by the MCP orchestration loop.

Usage (direct):
    from packages.shared.providers.claude_provider import ClaudeProvider
    provider = ClaudeProvider()
    result = provider.complete(prompt="Summarize this project status.", context=docs)

Usage (via orchestrator):
    Set ANTHROPIC_API_KEY in your .env. The provider initialises automatically
    and falls back to stub mode when the key is absent — no code changes needed.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    import anthropic as _anthropic_sdk
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    logger.warning(
        "anthropic package not installed. "
        "Run: pip install anthropic  "
        "Claude provider will fall back to stub mode."
    )


# Default model: Haiku is fast and cheap for dev/eval iteration.
# Swap to claude-sonnet-4-6 for higher-quality production output.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_MAX_TOKENS = 1024


@dataclass
class ProviderResponse:
    """Structured response returned by ClaudeProvider."""

    content: str
    model: str
    provider: str = "claude"
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ClaudeProvider:
    """
    Wraps the Anthropic Messages API for use inside AI-OS MCP workflows.

    Design principles:
    - Grounded outputs: system prompt enforces evidence-based responses
    - Structured responses: short, actionable, signal over noise
    - Human-in-the-loop: no autonomous action — synthesis only
    - Deterministic fallback: returns stub when SDK unavailable or key missing

    Tool use (MCP integration):
        Pass tool definitions via the `tools` parameter. The provider returns
        tool_calls in ProviderResponse when Claude invokes a tool. The
        orchestrator is responsible for executing tool calls and feeding results
        back via a follow-up complete() call with updated messages.
    """

    _SYSTEM_PROMPT = """You are an AI assistant embedded in a structured enterprise workflow system.

Your role is to synthesize retrieved evidence into concise, actionable output.

Rules:
- Base every claim on the retrieved context provided. Do not invent facts.
- Keep responses short and structured. Signal over noise.
- If evidence is insufficient to answer, say so explicitly.
- Do not take autonomous actions. Synthesis only.
- Format output as requested by the workflow (JSON, markdown, plain text).
"""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client: Any = None

        if _SDK_AVAILABLE and self._api_key:
            self._client = _anthropic_sdk.Anthropic(api_key=self._api_key)
            logger.info("ClaudeProvider initialised — model=%s", self.model)
        else:
            if not _SDK_AVAILABLE:
                logger.warning("ClaudeProvider: SDK not available, using stub.")
            elif not self._api_key:
                logger.warning(
                    "ClaudeProvider: ANTHROPIC_API_KEY not set. "
                    "Add it to your .env to enable live Claude calls."
                )

    def complete(
        self,
        prompt: str,
        context: str = "",
        tools: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        system_override: str | None = None,
    ) -> ProviderResponse:
        """
        Send a completion request to Claude.

        Args:
            prompt:          The user-facing request / task description.
            context:         Retrieved evidence to ground the response.
                             Injected into the user message before the prompt.
            tools:           MCP tool definitions (JSON schema format).
                             When provided, Claude may return tool_calls.
            messages:        Full message history for multi-turn flows.
                             When provided, prompt and context are appended as
                             a final user turn only if they are non-empty.
            system_override: Replace the default system prompt. Use sparingly.

        Returns:
            ProviderResponse with content, token counts, and any tool_calls.
        """
        if self._client is None:
            return self._stub_response(prompt)

        if messages:
            msgs = list(messages)
            user_content = self._build_user_content(prompt, context)
            # Only append a new user turn when there is actual content to add.
            # In multi-round tool loops the history already ends with a
            # tool_result user block; appending an empty turn would cause a
            # consecutive-roles error from the Anthropic API.
            if user_content:
                msgs.append({"role": "user", "content": user_content})
        else:
            msgs = [{"role": "user", "content": self._build_user_content(prompt, context)}]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_override or self._SYSTEM_PROMPT,
            "messages": msgs,
        }

        if tools:
            kwargs["tools"] = tools

        try:
            response = self._client.messages.create(**kwargs)
            return self._parse_response(response)
        except Exception as exc:
            logger.error("ClaudeProvider.complete() failed: %s", exc)
            return self._error_response(str(exc))

    def is_available(self) -> bool:
        """Returns True when the provider can make live API calls."""
        return self._client is not None

    @staticmethod
    def _build_user_content(prompt: str, context: str) -> str:
        if context:
            return (
                f"<retrieved_context>\n{context}\n</retrieved_context>\n\n"
                f"{prompt}"
            )
        return prompt

    @staticmethod
    def _parse_response(response: Any) -> ProviderResponse:
        """
        Parse the Anthropic Messages API response.

        Handles both text blocks and tool_use blocks. Tool calls are extracted
        and returned separately so the orchestrator can execute them via MCP.
        """
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return ProviderResponse(
            content="\n".join(text_parts),
            model=response.model,
            provider="claude",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            tool_calls=tool_calls,
            raw=response,
        )

    @staticmethod
    def _stub_response(prompt: str) -> ProviderResponse:
        return ProviderResponse(
            content=(
                "[ClaudeProvider stub] API key not configured. "
                f"Received prompt: {prompt[:80]}..."
            ),
            model="stub",
            provider="claude-stub",
        )

    @staticmethod
    def _error_response(error: str) -> ProviderResponse:
        return ProviderResponse(
            content=f"[ClaudeProvider error] {error}",
            model="error",
            provider="claude-error",
        )


def get_provider(
    use_claude: bool | None = None,
    model: str = DEFAULT_MODEL,
) -> ClaudeProvider:
    """
    Return a configured ClaudeProvider instance.

    Selection logic:
    1. If ANTHROPIC_API_KEY is set → live Claude (unless explicitly overridden)
    2. If key is absent → stub (caller should fall back to Ollama path)

    Args:
        use_claude: Force live (True) or stub (False). Default: auto-detect.
        model:      Override the default model string.
    """
    if use_claude is False:
        return ClaudeProvider(api_key="")

    return ClaudeProvider(model=model)
