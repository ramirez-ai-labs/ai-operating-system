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
        description="Maximum number of evidence items to include in the response.",
    )
    use_model: bool = Field(
        default=False,
        description="Enable optional model-assisted synthesis instead of deterministic extraction.",
    )
    ollama_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for the local Ollama server when model synthesis is enabled.",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name used when model synthesis is enabled.",
    )


class EvidenceItem(BaseModel):
    """Minimal evidence payload returned from local retrieval."""
    source: str
    line_number: int
    title: str
    excerpt: str


class WeeklyUpdateResponse(BaseModel):
    """Structured weekly update returned to the operator."""
    summary: str
    wins: list[str]
    risks: list[str]
    next_steps: list[str]
    evidence: list[EvidenceItem]


class WeeklyUpdateDraft(BaseModel):
    """Intermediate structured draft generated before evidence is attached."""
    summary: str
    wins: list[str]
    risks: list[str]
    next_steps: list[str]


class ErrorResponse(BaseModel):
    """Simple error envelope for API failures."""
    detail: str
