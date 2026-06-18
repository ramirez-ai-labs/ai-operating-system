from typing import Literal

from pydantic import BaseModel, Field

from packages.shared.schemas.base import (
    BaseRequest,
    BaseResponse,
    EvidenceItem,
    GroundedItem,
)

# Re-exported so all existing callers of
# `from packages.shared.schemas.director_os import EvidenceItem, GroundedItem`
# continue to work unchanged.
__all__ = [
    "EvidenceItem",
    "GroundedItem",
    "BaseRequest",
    "BaseResponse",
    "WeeklyUpdateRequest",
    "WeeklyUpdateResponse",
    "WeeklyUpdateDraft",
    "ErrorResponse",
]


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


class WeeklyUpdateResponse(BaseResponse):
    """Structured weekly update returned to the operator."""

    summary: str
    wins: list[GroundedItem]
    risks: list[GroundedItem]
    next_steps: list[GroundedItem]
    # evidence and provider_usage are inherited from BaseResponse.

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
