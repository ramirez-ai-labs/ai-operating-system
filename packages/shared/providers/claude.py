from __future__ import annotations

import os

from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.providers.grounding import GROUNDED_ITEM_SCHEMA, parse_grounded_items
from packages.shared.schemas.director_os import EvidenceItem, WeeklyUpdateDraft

_TOOL_NAME = "generate_weekly_update"

# The system prompt is stable across all calls for the same model. Marking it
# with cache_control lets Anthropic's prompt caching layer reuse the KV cache
# across requests, reducing latency and cost on repeated weekly update runs
# against the same data set.
_SYSTEM_PROMPT = (
    "You are a technical leadership assistant. "
    "Your job is to synthesize project evidence into structured, grounded weekly updates. "
    "Every output item must cite an exact source filename and line_number from the evidence. "
    "Do not invent wins, risks, or next steps that are not directly supported by the evidence."
)


_TOOL_SCHEMA: dict[str, object] = {
    "name": _TOOL_NAME,
    "description": (
        "Generate a structured weekly leadership update from the provided evidence. "
        "Every item in wins, risks, and next_steps must cite a source and line_number "
        "that appears in the evidence list — do not invent citations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One or two sentence leadership summary grounded in the evidence.",
            },
            "wins": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Completed work or positive outcomes cited from evidence.",
            },
            "risks": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Blockers, delays, or open concerns cited from evidence.",
            },
            "next_steps": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Planned actions or follow-ups cited from evidence.",
            },
        },
        "required": ["summary", "wins", "risks", "next_steps"],
    },
}


class ClaudeWeeklyUpdateProvider(WeeklyUpdateProvider):
    """Anthropic Claude adapter for structured weekly update synthesis via tool use."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._last_usage: dict[str, int] = {}

    def get_last_usage(self) -> dict[str, int]:
        """Return token counts from the most recent call, including cache fields."""
        return self._last_usage

    def generate_weekly_update(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> WeeklyUpdateDraft:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Export the key or use provider='ollama' for local synthesis."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_prompt(focus, evidence)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                # The system prompt is cached so repeated calls within the same
                # 5-minute cache window reuse the KV representation without
                # re-processing the instructions on every request.
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            # Rate limits, 5xx, and connection errors are not ValueError
            # subclasses, but every caller's fallback path only catches
            # ValueError. Normalize so a live API hiccup falls back to
            # deterministic synthesis instead of crashing the request.
            raise ValueError(f"Claude API call failed: {exc}") from exc

        if response.stop_reason == "max_tokens":
            raise ValueError(
                "Claude response was truncated at max_tokens before completing "
                "the tool call — the evidence set may be too large for this limit."
            )

        # Record usage so the orchestration layer can surface cache savings
        # in the WorkflowTrace without needing to know about this provider.
        usage = response.usage
        self._last_usage = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        }

        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise ValueError("Claude did not return a tool_use block for the weekly update.")

        parsed = tool_use_block.input
        evidence_locations = {(item.source, item.line_number) for item in evidence}

        return WeeklyUpdateDraft(
            summary=parsed.get("summary", ""),
            wins=parse_grounded_items(parsed.get("wins", []), evidence_locations),
            risks=parse_grounded_items(parsed.get("risks", []), evidence_locations),
            next_steps=parse_grounded_items(parsed.get("next_steps", []), evidence_locations),
        )


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    focus_text = focus or "current leadership activity"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""Generate a concise leadership weekly update from the evidence below.

Rules:
- Use only the evidence provided. Do not invent wins, risks, or next steps.
- Every item must cite the exact source filename and line_number from the evidence list.
- Keep the summary to one or two sentences.
- Keep each item tightly worded — do not paraphrase broadly.

Focus: {focus_text}

Evidence:
{evidence_lines}"""


