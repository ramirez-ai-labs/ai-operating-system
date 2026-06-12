"""Writer agent — second stage of the multi-agent researcher → writer pipeline.

The writer takes the researcher's structured synthesis and formats it for a
specific target audience. It is a pure formatting step: it has no access to
the raw evidence and cannot add new facts — only shape what the researcher
already extracted.

Keeping formatting strictly downstream of synthesis means hallucination risk
is bounded: the writer can only rephrase, not invent.
"""
from __future__ import annotations

import os

from packages.shared.agents.researcher import ResearchSynthesis
from packages.shared.schemas.orchestrator import AgentCall

_AUDIENCE_INSTRUCTIONS: dict[str, str] = {
    "linkedin_post": (
        "Write a LinkedIn post (150-250 words). "
        "Lead with the most compelling finding. "
        "Use a professional but conversational tone. "
        "End with a 1-sentence call to action or reflection. "
        "No bullet points — flowing paragraphs only."
    ),
    "executive_brief": (
        "Write an executive brief (100-150 words). "
        "Lead with the key outcome or risk in the first sentence. "
        "Follow with 2-3 supporting points. "
        "Close with the single most important next action. "
        "Use active voice and eliminate jargon."
    ),
    "team_update": (
        "Write a team standup-style update. "
        "Use 3-5 bullet points. "
        "Each bullet should start with a status word: Done, In Progress, Blocked, or Next. "
        "Keep each bullet to one line. "
        "Prioritize action items and blockers over background context."
    ),
}

_SYSTEM_PROMPT = (
    "You are a technical writer who formats research findings for specific audiences. "
    "You work only with the synthesis provided — do not add facts, metrics, or claims "
    "that are not present in the input. Your job is clarity and audience fit, not research."
)

SUPPORTED_AUDIENCES = frozenset(_AUDIENCE_INSTRUCTIONS)


class WriterAgent:
    """Claude agent that formats a research synthesis for a target audience."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model

    def format(
        self,
        synthesis: ResearchSynthesis,
        target_audience: str,
    ) -> tuple[str, AgentCall]:
        """Format the synthesis for the target audience and return content + usage.

        Returns (formatted_content: str, AgentCall) so the caller can attach
        both to the OrchestratorResponse without importing the Anthropic SDK.
        """
        if target_audience not in SUPPORTED_AUDIENCES:
            raise ValueError(
                f"Unsupported target_audience '{target_audience}'. "
                f"Supported values: {sorted(SUPPORTED_AUDIENCES)}."
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for the writer agent. "
                "Set the key or omit target_audience to use the deterministic path."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_writer_prompt(synthesis, target_audience)

        response = client.messages.create(
            model=self.model,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        usage = response.usage
        agent_call = AgentCall(
            agent="writer",
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

        content = next(
            (b.text for b in response.content if hasattr(b, "text")), ""
        )
        return content, agent_call


def _build_writer_prompt(synthesis: ResearchSynthesis, target_audience: str) -> str:
    findings_block = "\n".join(f"- {f}" for f in synthesis.key_findings)
    risks_block = (
        "\n".join(f"- {r}" for r in synthesis.risk_signals)
        if synthesis.risk_signals
        else "None identified."
    )
    instructions = _AUDIENCE_INSTRUCTIONS[target_audience]

    return f"""Format the following research synthesis for: {target_audience}

Formatting instructions:
{instructions}

Research synthesis:
Narrative: {synthesis.narrative}

Key findings:
{findings_block}

Risk signals:
{risks_block}"""
