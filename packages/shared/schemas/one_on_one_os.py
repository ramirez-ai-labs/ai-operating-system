from pydantic import BaseModel, Field

from packages.shared.schemas.base import BaseResponse
from packages.shared.schemas.director_os import GroundedItem


class OneOnOneRequest(BaseModel):
    """Input contract for the One-on-One OS meeting brief workflow."""

    data_path: str = Field(
        default="data/local_only/one_on_one",
        description="Local directory with 1:1 notes, action logs, and team health notes.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional focus — direct report name, topic area, or meeting context.",
    )
    direct_report: str | None = Field(
        default=None,
        description="Direct report name — included in the brief summary when provided.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items to retrieve.",
    )
    use_model: bool = Field(
        default=False,
        description="When True, use Claude to synthesize the brief from evidence.",
    )
    provider: str = Field(
        default="claude",
        description=(
            "Synthesis provider when use_model=True. Only 'claude' is supported "
            "for One-on-One OS — any other value raises ValueError and falls "
            "back to deterministic synthesis when fallback_to_deterministic=True."
        ),
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model ID for synthesis when provider='claude'.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description="Fall back to deterministic brief if model synthesis fails.",
    )


class OneOnOneResponse(BaseResponse):
    """Grounded 1:1 prep brief returned from One-on-One OS."""

    meeting_summary: str
    action_items: list[GroundedItem]
    talking_points: list[GroundedItem]
    blockers: list[GroundedItem]
    kudos: list[GroundedItem]
    # evidence and provider_usage are inherited from BaseResponse.

    @property
    def section_counts(self) -> dict[str, int]:
        return {
            "action_items": len(self.action_items),
            "talking_points": len(self.talking_points),
            "blockers": len(self.blockers),
            "kudos": len(self.kudos),
        }
