from pydantic import BaseModel, Field

from packages.shared.schemas.director_os import WeeklyUpdateResponse


class OrchestratorRequest(BaseModel):
    """Generic request accepted by the Chief of Staff orchestration layer."""

    prompt: str | None = Field(
        default=None,
        description="User request text used for simple workflow routing.",
    )
    workflow: str | None = Field(
        default=None,
        description="Optional explicit workflow id, such as director_os.weekly_update.",
    )
    data_path: str = Field(
        default="data/local_only/projects",
        description="Local directory containing notes or project artifacts.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional retrieval focus for the selected workflow.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items to retrieve.",
    )
    use_model: bool = Field(
        default=False,
        description="Enable model-assisted synthesis when supported by the selected workflow.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description="Allow deterministic fallback if model generation is unavailable or weak.",
    )
    ollama_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for the local Ollama server when model synthesis is enabled.",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name used when model synthesis is enabled.",
    )


class OrchestratorResponse(BaseModel):
    """Response returned from the lightweight Chief of Staff routing layer."""

    selected_workflow: str
    rationale: str
    result: WeeklyUpdateResponse
