from pydantic import BaseModel, Field

from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


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


class InterviewBriefResponse(BaseModel):
    """Grounded interview prep brief returned from Interview OS."""

    candidate_summary: str
    key_questions: list[GroundedItem]
    talking_points: list[GroundedItem]
    red_flags: list[GroundedItem]
    evidence: list[EvidenceItem]
