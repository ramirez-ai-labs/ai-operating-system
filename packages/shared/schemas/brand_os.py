from pydantic import BaseModel, Field

from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


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


class BrandContentDraftResponse(BaseModel):
    """Grounded content draft returned from Brand OS."""

    insight_summary: str
    post_outline: list[GroundedItem]
    podcast_angles: list[GroundedItem]
    repo_improvements: list[GroundedItem]
    evidence: list[EvidenceItem]
