from typing import Literal

from pydantic import BaseModel, Field


class WeeklyUpdateRequest(BaseModel):
    """Input contract for the Phase 1 Director OS workflow."""
    data_path: str = Field(
        default="data/local_only/projects",
        description=(
            "Local directory under data/local_only containing markdown notes "
            "for synthesis."
        ),
    )
    focus: str | None = Field(
        default=None,
        description="Optional retrieval focus, such as a project or workstream.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items to include in the response.",
    )
    use_model: bool = Field(
        default=False,
        description="Enable optional model-assisted synthesis instead of deterministic extraction.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description=(
            "When model synthesis fails or returns weak output, fall back to the "
            "deterministic workflow instead of raising an error."
        ),
    )
    provider: Literal["ollama", "claude"] = Field(
        default="ollama",
        description=(
            "Model provider for synthesis. 'claude' requires ANTHROPIC_API_KEY to be set."
        ),
    )
    ollama_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for the local Ollama server when provider is 'ollama'.",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name used when provider is 'ollama'.",
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model ID used when provider is 'claude'.",
    )


class EvidenceItem(BaseModel):
    """Minimal evidence payload returned from local retrieval."""
    source: str
    line_number: int
    title: str
    excerpt: str


class GroundedItem(BaseModel):
    """Output item tied to a specific supporting evidence location."""
    text: str
    source: str
    line_number: int


class WeeklyUpdateResponse(BaseModel):
    """Structured weekly update returned to the operator."""
    summary: str
    wins: list[GroundedItem]
    risks: list[GroundedItem]
    next_steps: list[GroundedItem]
    evidence: list[EvidenceItem]
    # Populated by the Claude provider when use_model=True and provider="claude".
    # Carries cache_read_input_tokens and cache_creation_input_tokens so the
    # orchestration layer can surface them in WorkflowTrace without coupling to
    # provider internals.
    provider_usage: dict[str, int] = Field(default_factory=dict)

    @property
    def section_counts(self) -> dict[str, int]:
        return {
            "wins": len(self.wins),
            "risks": len(self.risks),
            "next_steps": len(self.next_steps),
        }


class WeeklyUpdateDraft(BaseModel):
    """Intermediate structured draft generated before evidence is attached."""
    summary: str
    wins: list[GroundedItem]
    risks: list[GroundedItem]
    next_steps: list[GroundedItem]


class ErrorResponse(BaseModel):
    """Simple error envelope for API failures."""
    detail: str
