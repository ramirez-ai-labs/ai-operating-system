from __future__ import annotations

import os

from packages.shared.providers.grounding import GROUNDED_ITEM_SCHEMA, parse_grounded_items
from packages.shared.schemas.director_os import EvidenceItem
from packages.shared.schemas.interview_os import InterviewBriefResponse

_TOOL_NAME = "generate_interview_brief"

_SYSTEM_PROMPT = (
    "You are an expert technical interviewer and hiring advisor. "
    "Your job is to synthesize candidate and role evidence into a structured interview brief. "
    "Every output item must cite an exact source filename and line_number from the evidence. "
    "Do not invent questions, talking points, or red flags that are not directly supported "
    "by the evidence."
)


_TOOL_SCHEMA: dict[str, object] = {
    "name": _TOOL_NAME,
    "description": (
        "Generate a structured interview brief from the provided candidate and role evidence. "
        "Every item in key_questions, talking_points, and red_flags must cite a source and "
        "line_number that appears in the evidence — do not invent citations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "candidate_summary": {
                "type": "string",
                "description": (
                    "One or two sentence summary of the candidate and role, grounded in evidence."
                ),
            },
            "key_questions": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Interview questions to ask, cited from evidence.",
            },
            "talking_points": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Topics to cover or highlights to discuss, cited from evidence.",
            },
            "red_flags": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Concerns, gaps, or risks to probe, cited from evidence.",
            },
        },
        "required": ["candidate_summary", "key_questions", "talking_points", "red_flags"],
    },
}


class ClaudeInterviewBriefProvider:
    """Anthropic Claude adapter for structured interview brief synthesis via tool use."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._last_usage: dict[str, int] = {}

    def get_last_usage(self) -> dict[str, int]:
        return self._last_usage

    def generate_interview_brief(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> InterviewBriefResponse:
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
            raise ValueError("Claude did not return a tool_use block for the interview brief.")

        parsed = tool_use_block.input
        evidence_locations = {(item.source, item.line_number) for item in evidence}

        return InterviewBriefResponse(
            candidate_summary=parsed.get("candidate_summary", ""),
            key_questions=parse_grounded_items(
                parsed.get("key_questions", []), evidence_locations
            ),
            talking_points=parse_grounded_items(
                parsed.get("talking_points", []), evidence_locations
            ),
            red_flags=parse_grounded_items(parsed.get("red_flags", []), evidence_locations),
            evidence=evidence,
        )


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    focus_text = focus or "candidate interview preparation"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""Generate a structured interview brief from the evidence below.

Rules:
- Use only the evidence provided. Do not invent questions, talking points, or red flags.
- Every item must cite the exact source filename and line_number from the evidence list.
- Keep the candidate_summary to one or two sentences.

Focus: {focus_text}

Evidence:
{evidence_lines}"""


