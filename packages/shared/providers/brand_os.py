from __future__ import annotations

import os

from packages.shared.providers.grounding import GROUNDED_ITEM_SCHEMA, parse_grounded_items
from packages.shared.schemas.brand_os import BrandContentDraftResponse
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem

_TOOL_NAME = "generate_brand_content_draft"

_SYSTEM_PROMPT = (
    "You are an expert AI content strategist and technical writer. "
    "Your job is to synthesize brand and technical evidence into a structured content draft. "
    "Every output item must cite an exact source filename and line_number from the evidence. "
    "Do not invent post outlines, podcast angles, or repo improvements that are not directly "
    "supported by the evidence."
)


_TOOL_SCHEMA: dict[str, object] = {
    "name": _TOOL_NAME,
    "description": (
        "Generate a structured brand content draft from the provided evidence. "
        "Every item in post_outline, podcast_angles, and repo_improvements must cite a source "
        "and line_number that appears in the evidence — do not invent citations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "insight_summary": {
                "type": "string",
                "description": (
                    "One or two sentence summary of the key brand insights, grounded in evidence."
                ),
            },
            "post_outline": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Post or article outline items, cited from evidence.",
            },
            "podcast_angles": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Podcast discussion angles or themes, cited from evidence.",
            },
            "repo_improvements": {
                "type": "array",
                "items": GROUNDED_ITEM_SCHEMA,
                "description": "Repository or workflow improvement ideas, cited from evidence.",
            },
        },
        "required": ["insight_summary", "post_outline", "podcast_angles", "repo_improvements"],
    },
}


class ClaudeBrandContentDraftProvider:
    """Anthropic Claude adapter for structured brand content draft synthesis via tool use."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._last_usage: dict[str, int] = {}

    def get_last_usage(self) -> dict[str, int]:
        return self._last_usage

    def generate_brand_content_draft(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> BrandContentDraftResponse:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Export the key or set use_model=False for deterministic synthesis."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_prompt(focus, evidence)

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
            raise ValueError(
                "Claude did not return a tool_use block for the brand content draft."
            )

        parsed = tool_use_block.input
        evidence_locations = {(item.source, item.line_number) for item in evidence}

        return BrandContentDraftResponse(
            insight_summary=parsed.get("insight_summary", ""),
            post_outline=parse_grounded_items(
                parsed.get("post_outline", []), evidence_locations
            ),
            podcast_angles=parse_grounded_items(
                parsed.get("podcast_angles", []), evidence_locations
            ),
            repo_improvements=parse_grounded_items(
                parsed.get("repo_improvements", []), evidence_locations
            ),
            evidence=evidence,
        )


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    focus_text = focus or "brand content and technical insights"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""Generate a structured brand content draft from the evidence below.

Rules:
- Use only the evidence provided. Do not invent post outlines, podcast angles, or repo improvements.
- Every item must cite the exact source filename and line_number from the evidence list.
- Keep the insight_summary to one or two sentences.

Focus: {focus_text}

Evidence:
{evidence_lines}"""


