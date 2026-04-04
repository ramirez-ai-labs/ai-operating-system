from pydantic import BaseModel, Field


class WeeklyUpdateRequest(BaseModel):
    """Input contract for the Phase 1 Director OS workflow."""
    data_path: str = Field(
        default="data/local_only/projects",
        description="Local directory containing markdown notes for synthesis.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional retrieval focus, such as a project or workstream.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of local documents to include as evidence.",
    )


class EvidenceItem(BaseModel):
    """Minimal evidence payload returned from local retrieval."""
    source: str
    title: str
    excerpt: str


class WeeklyUpdateResponse(BaseModel):
    """Structured weekly update returned to the operator."""
    summary: str
    wins: list[str]
    risks: list[str]
    next_steps: list[str]
    evidence: list[EvidenceItem]


class ErrorResponse(BaseModel):
    """Simple error envelope for API failures."""
    detail: str
