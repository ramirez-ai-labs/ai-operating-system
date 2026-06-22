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


class WeeklyUpdateRequest(BaseRequest):
    """Input contract for the Director OS weekly update workflow.

    Inherits the standard field set from BaseRequest (data_path, focus,
    max_documents, use_model, provider, claude_model, fallback_to_deterministic).
    Director OS overrides data_path and provider defaults, and adds the two
    Ollama-specific fields that only this domain supports.
    """

    # Director OS reads from the projects directory by default.
    data_path: str = Field(
        default="data/local_only/projects",
        description=(
            "Local directory under data/local_only containing markdown notes "
            "for synthesis."
        ),
    )
    # Director OS is the only domain that supports Ollama synthesis, so the
    # provider type is narrowed and the default is "ollama" rather than "claude".
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
