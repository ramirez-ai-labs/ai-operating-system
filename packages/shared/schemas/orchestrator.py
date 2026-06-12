from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.shared.schemas.brand_os import BrandContentDraftResponse
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
        description="Local directory under data/local_only containing notes or project artifacts.",
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
    provider: Literal["ollama", "claude"] = Field(
        default="ollama",
        description=(
            "Model provider for Director OS synthesis when use_model is enabled. "
            "Claude requires ANTHROPIC_API_KEY and remains opt-in."
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
    use_mcp: bool = Field(
        default=False,
        description=(
            "Run the filesystem MCP retrieval loop alongside the workflow. "
            "When True, Claude reads project files via tool calls and the "
            "mcp_tool_calls trace is populated in the response. "
            "Requires ANTHROPIC_API_KEY."
        ),
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Claude model ID used for Director OS synthesis when provider is "
            "'claude' and for MCP-backed synthesis when use_mcp is True."
        ),
    )


class WorkflowTrace(BaseModel):
    """Operator-facing execution metadata for a routed workflow run."""

    # These fields are intentionally simple so they can be rendered directly in
    # an API response or future UI without extra transformation logic.
    data_path: str
    focus_used: str | None
    evidence_count: int
    evidence_sources: list[str]
    model_requested: bool
    model_supported: bool
    model_used: bool
    provider_used: str | None
    model_id_used: str | None
    fallback_used: bool
    section_counts: dict[str, int]
    validation_summary: str
    # Populated when use_mcp=True. Each entry records the tool name, input,
    # success flag, and a preview of what was retrieved — gives operators
    # full visibility into what the agent read before synthesizing.
    mcp_tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Response returned from the lightweight Chief of Staff routing layer."""

    selected_workflow: str
    rationale: str
    trace: WorkflowTrace
    result: WeeklyUpdateResponse | BrandContentDraftResponse
