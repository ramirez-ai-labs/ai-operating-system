from __future__ import annotations

import os

from packages.shared.providers.grounding import GROUNDED_ITEM_SCHEMA, parse_grounded_items
from packages.shared.schemas.director_os import EvidenceItem
from packages.shared.schemas.one_on_one_os import OneOnOneResponse

_TOOL_NAME = "generate_one_on_one_brief"

_SYSTEM_PROMPT = (
    "You are an expert engineering manager coach. "
    "Your job is to synthesize 1:1 notes into a structured meeting prep brief. "
    "Every output item must cite an exact source filename and line_number from the evidence. "
    "Do not invent action items, talking points, blockers, or kudos that are not directly "
    "supported by the evidence."
)


_TOOL_SCHEMA: dict[str, object] = {
    "name": _TOOL_NAME,
    "description": (
        "Generate a structured 1:1 meeting prep brief from the provided notes and evidence. "
        "Every item in action_items, talking_points, blockers, and kudos must cite a source "
        "and line_number that appears in the evidence — do not invent citations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "meeting_summary": {
                "type": "string",
                "description": (
                    "One or two sentence summary of the meeting context, grounded in evidence."
                ),
            },
            "action_items": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Committed actions from previous or current 1:1, cited from notes.",
            },
            "talking_points": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Topics to raise in the meeting, cited from notes.",
            },
            "blockers": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Things blocking the direct report, cited from notes.",
            },
            "kudos": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Recognition or positive callouts, cited from notes.",
            },
        },
        "required": ["meeting_summary", "action_items", "talking_points", "blockers", "kudos"],
    },
}


class ClaudeOneOnOneProvider:
    """Anthropic Claude adapter for structured 1:1 brief synthesis via tool use."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._last_usage: dict[str, int] = {}

    def get_last_usage(self) -> dict[str, int]:
        return self._last_usage

    def generate_one_on_one_brief(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> OneOnOneResponse:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Export the key or set use_model=False for deterministic synthesis."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_prompt(focus, evidence)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
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
            # subclasses, but the graph's fallback path only catches
            # ValueError. Normalize so a live API hiccup falls back to
            # deterministic synthesis instead of crashing the request.
            raise ValueError(f"Claude API call failed: {exc}") from exc

        if response.stop_reason == "max_tokens":
            raise ValueError(
                "Claude response was truncated at max_tokens before completing "
                "the tool call — the evidence set may be too large for this limit."
            )

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
            raise ValueError("Claude did not return a tool_use block for the 1:1 brief.")

        parsed = tool_use_block.input
        evidence_locations = {(item.source, item.line_number) for item in evidence}

        return OneOnOneResponse(
            meeting_summary=parsed.get("meeting_summary", ""),
            action_items=parse_grounded_items(
                parsed.get("action_items", []), evidence_locations
            ),
            talking_points=parse_grounded_items(
                parsed.get("talking_points", []), evidence_locations
            ),
            blockers=parse_grounded_items(parsed.get("blockers", []), evidence_locations),
            kudos=parse_grounded_items(parsed.get("kudos", []), evidence_locations),
            evidence=evidence,
        )


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    focus_text = focus or "1:1 meeting preparation"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""Generate a structured 1:1 meeting brief from the notes below.

Rules:
- Use only the evidence provided. Do not invent action items, blockers, or kudos.
- Every item must cite the exact source filename and line_number from the evidence list.
- Keep the meeting_summary to one or two sentences.

Focus: {focus_text}

Evidence:
{evidence_lines}"""


