from __future__ import annotations

import json
from urllib import error, request

from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import EvidenceItem, WeeklyUpdateDraft


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
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "wins": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "next_steps": {"type": "array", "items": {"type": "string"}},
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
                f"Unable to reach Ollama at {self.base_url}. Confirm Ollama is running and reachable."
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

        return WeeklyUpdateDraft.model_validate(parsed)


def _build_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Keep the Ollama prompt explicit, grounded, and low-verbosity."""
    focus_text = focus or "current leadership activity"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""
You are generating a concise leadership weekly update.

Rules:
- Use only the evidence provided below.
- Keep the summary to one or two sentences.
- Do not invent wins, risks, or next steps.
- Return JSON only.

Focus:
{focus_text}

Evidence:
{evidence_lines}
""".strip()
