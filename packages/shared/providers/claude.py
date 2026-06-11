from __future__ import annotations

import os

from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem, WeeklyUpdateDraft

_TOOL_NAME = "generate_weekly_update"

_GROUNDED_ITEM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "source": {"type": "string", "description": "Exact source filename from the evidence."},
        "line_number": {"type": "integer", "description": "Exact line_number from the evidence."},
    },
    "required": ["text", "source", "line_number"],
}

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
                "items": _GROUNDED_ITEM_SCHEMA,
                "description": "Completed work or positive outcomes cited from evidence.",
            },
            "risks": {
                "type": "array",
                "items": _GROUNDED_ITEM_SCHEMA,
                "description": "Blockers, delays, or open concerns cited from evidence.",
            },
            "next_steps": {
                "type": "array",
                "items": _GROUNDED_ITEM_SCHEMA,
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

        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": prompt}],
        )

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
            wins=_parse_grounded_items(parsed.get("wins", []), evidence_locations),
            risks=_parse_grounded_items(parsed.get("risks", []), evidence_locations),
            next_steps=_parse_grounded_items(parsed.get("next_steps", []), evidence_locations),
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


def _parse_grounded_items(
    items: list[dict[str, object]],
    evidence_locations: set[tuple[str, int]],
) -> list[GroundedItem]:
    grounded: list[GroundedItem] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("Claude returned a malformed grounded item.")
        item = GroundedItem(
            text=str(raw.get("text", "")),
            source=str(raw.get("source", "")),
            line_number=int(raw.get("line_number", 0)),
        )
        if (item.source, item.line_number) not in evidence_locations:
            raise ValueError(
                f"Claude cited evidence not in the retrieved context: "
                f"{item.source}:{item.line_number}"
            )
        grounded.append(item)
    return grounded
