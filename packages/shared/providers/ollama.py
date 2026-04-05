from __future__ import annotations

import json
from urllib import error, request

from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem, WeeklyUpdateDraft


class OllamaWeeklyUpdateProvider(WeeklyUpdateProvider):
    """Minimal Ollama adapter for structured local synthesis."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_weekly_update(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> WeeklyUpdateDraft:
        """Call Ollama's generate endpoint and parse structured JSON output."""
        prompt = _build_prompt(focus, evidence)
        # Ask Ollama for JSON so the workflow can keep using typed Python
        # objects instead of trying to parse free-form prose.
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "wins": {"type": "array", "items": _grounded_item_schema()},
                    "risks": {"type": "array", "items": _grounded_item_schema()},
                    "next_steps": {"type": "array", "items": _grounded_item_schema()},
                },
                "required": ["summary", "wins", "risks", "next_steps"],
            },
        }

        http_request = request.Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise ValueError(
                f"Unable to reach Ollama at {self.base_url}. "
                "Confirm Ollama is running and reachable."
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned a non-JSON response.") from exc

        raw_response = body.get("response", "")
        if not raw_response:
            raise ValueError("Ollama returned an empty response.")

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned invalid JSON for the weekly update draft.") from exc

        return WeeklyUpdateDraft(
            summary=parsed.get("summary", ""),
            wins=_parse_grounded_items(parsed.get("wins", []), evidence),
            risks=_parse_grounded_items(parsed.get("risks", []), evidence),
            next_steps=_parse_grounded_items(parsed.get("next_steps", []), evidence),
        )


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Keep the Ollama prompt explicit, grounded, and low-verbosity."""
    focus_text = focus or "current leadership activity"
    # Each evidence line includes the source file and line number so the model
    # can stay grounded and the caller can trace outputs back to local notes.
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""
You are generating a concise leadership weekly update.

Rules:
- Use only the evidence provided below.
- Keep the summary to one or two sentences.
- Do not invent wins, risks, or next steps.
- Every item in wins, risks, and next_steps must cite the exact source and line_number
  of the supporting evidence item you used.
- Keep each item tightly worded to the cited evidence instead of broad paraphrases.
- Return JSON only.

Focus:
{focus_text}

Evidence:
{evidence_lines}
""".strip()


def _grounded_item_schema() -> dict[str, object]:
    """Describe a grounded output item for Ollama's JSON mode."""
    return {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "source": {"type": "string"},
            "line_number": {"type": "integer"},
        },
        "required": ["text", "source", "line_number"],
    }


def _parse_grounded_items(
    items: list[dict[str, object]],
    evidence: list[EvidenceItem],
) -> list[GroundedItem]:
    """Parse model-returned grounded items and reject unknown evidence references."""
    evidence_locations = {(item.source, item.line_number) for item in evidence}
    grounded: list[GroundedItem] = []

    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ValueError("Ollama returned malformed grounded items.")

        grounded_item = GroundedItem(
            text=str(raw_item.get("text", "")),
            source=str(raw_item.get("source", "")),
            line_number=int(raw_item.get("line_number", 0)),
        )
        if (grounded_item.source, grounded_item.line_number) not in evidence_locations:
            raise ValueError("Ollama cited evidence that was not part of the retrieved context.")
        grounded.append(grounded_item)

    return grounded
