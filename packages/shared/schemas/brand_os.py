from pydantic import BaseModel, Field

from packages.shared.schemas.base import BaseResponse
from packages.shared.schemas.director_os import GroundedItem


class BrandContentDraftRequest(BaseModel):
    """Input contract for the first Brand OS workflow."""

    data_path: str = Field(
        default="data/local_only/brand",
        description="Local directory containing notes or draft material for Brand OS.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional retrieval focus, such as a theme or recent project topic.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items to include in the response.",
    )
    use_model: bool = Field(
        default=False,
        description="When True, use Claude to synthesize the content draft from evidence.",
    )
    provider: str = Field(
        default="claude",
        description=(
            "Synthesis provider when use_model=True. Only 'claude' is supported "
            "for Brand OS — any other value raises ValueError and falls back to "
            "deterministic synthesis when fallback_to_deterministic=True."
        ),
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model ID for synthesis when provider='claude'.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description="Fall back to deterministic draft if model synthesis fails.",
    )


class BrandContentDraftResponse(BaseResponse):
    """Grounded content draft returned from Brand OS."""

    insight_summary: str
    post_outline: list[GroundedItem]
    podcast_angles: list[GroundedItem]
    repo_improvements: list[GroundedItem]
    # evidence and provider_usage are inherited from BaseResponse.

    @property
    def section_counts(self) -> dict[str, int]:
        return {
            "post_outline": len(self.post_outline),
            "podcast_angles": len(self.podcast_angles),
            "repo_improvements": len(self.repo_improvements),
        }
