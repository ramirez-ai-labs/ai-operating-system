from pydantic import BaseModel, Field

from packages.shared.schemas.base import BaseResponse
from packages.shared.schemas.director_os import GroundedItem


class InterviewBriefRequest(BaseModel):
    """Input contract for the Interview OS brief workflow."""

    data_path: str = Field(
        default="data/local_only/interviews",
        description="Local directory with candidate notes, role briefs, and interview guides.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional retrieval focus, such as a candidate name, role, or skill area.",
    )
    candidate_name: str | None = Field(
        default=None,
        description="Candidate name for context — included in the brief summary when provided.",
    )
    role: str | None = Field(
        default=None,
        description="Role being interviewed for — focuses question and talking-point selection.",
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
        description="Synthesis provider when use_model=True. 'claude' or 'ollama'.",
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model ID for synthesis when provider='claude'.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description="Fall back to deterministic brief if model synthesis fails.",
    )


class InterviewBriefResponse(BaseResponse):
    """Grounded interview prep brief returned from Interview OS."""

    candidate_summary: str
    key_questions: list[GroundedItem]
    talking_points: list[GroundedItem]
    red_flags: list[GroundedItem]
    # evidence and provider_usage are inherited from BaseResponse.

    @property
    def section_counts(self) -> dict[str, int]:
        return {
            "key_questions": len(self.key_questions),
            "talking_points": len(self.talking_points),
            "red_flags": len(self.red_flags),
        }
