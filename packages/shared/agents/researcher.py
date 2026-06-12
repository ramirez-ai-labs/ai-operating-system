"""Researcher agent — first stage of the multi-agent researcher → writer pipeline.

The researcher reads retrieved evidence and uses Claude's tool-use API to produce
a structured synthesis: narrative, key findings, and risk signals. This output
becomes the handoff document the writer agent formats for a specific audience.

Keeping the researcher separate from the writer means each agent has a single
job and the handoff contract is explicit and testable without a live API key.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from packages.shared.schemas.director_os import EvidenceItem
from packages.shared.schemas.orchestrator import AgentCall

if TYPE_CHECKING:
    pass

_TOOL_NAME = "research_synthesis"

_SYNTHESIS_TOOL: dict = {
    "name": _TOOL_NAME,
    "description": (
        "Synthesize retrieved evidence into a structured research brief. "
        "key_findings must each cite a specific observation from the evidence. "
        "risk_signals should surface blockers or concerns visible in the evidence. "
        "Do not add findings that are not supported by the provided evidence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative": {
                "type": "string",
                "description": (
                    "2-3 sentence synthesis narrative that ties the evidence together "
                    "and answers the focus question."
                ),
            },
            "key_findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 specific, evidence-grounded findings.",
            },
            "risk_signals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Risks, blockers, or concerns surfaced in the evidence.",
            },
        },
        "required": ["narrative", "key_findings"],
    },
}

_SYSTEM_PROMPT = (
    "You are a research analyst. Your job is to read retrieved project evidence "
    "and extract the most important findings and risk signals. "
    "Be specific — each finding must be grounded in the evidence provided. "
    "Do not speculate beyond what the evidence shows."
)


class ResearchSynthesis:
    """Structured output from the researcher agent."""

    def __init__(
        self,
        narrative: str,
        key_findings: list[str],
        risk_signals: list[str],
    ) -> None:
        self.narrative = narrative
        self.key_findings = key_findings
        self.risk_signals = risk_signals


class ResearcherAgent:
    """Claude agent that synthesizes evidence into structured research findings."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model

    def synthesize(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> tuple[ResearchSynthesis, AgentCall]:
        """Run the researcher over retrieved evidence and return findings + usage.

        Returns a tuple of (ResearchSynthesis, AgentCall) so the caller can
        attach the AgentCall to the WorkflowTrace without coupling to the
        Anthropic SDK response shape.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for the researcher agent. "
                "Set the key or omit target_audience to use the deterministic path."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = _build_researcher_prompt(focus, evidence)

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
            tools=[_SYNTHESIS_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": prompt}],
        )

        usage = response.usage
        agent_call = AgentCall(
            agent="researcher",
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )
        if tool_block is None:
            raise ValueError("Researcher agent did not return a tool_use block.")

        parsed = tool_block.input
        return (
            ResearchSynthesis(
                narrative=parsed.get("narrative", ""),
                key_findings=list(parsed.get("key_findings", [])),
                risk_signals=list(parsed.get("risk_signals", [])),
            ),
            agent_call,
        )


def _build_researcher_prompt(focus: str | None, evidence: list[EvidenceItem]) -> str:
    focus_text = focus or "current project activity"
    evidence_lines = "\n".join(
        f"- {item.source}:{item.line_number} | {item.excerpt}" for item in evidence
    )
    return f"""Synthesize the following evidence into a structured research brief.

Focus: {focus_text}

Evidence:
{evidence_lines}"""
