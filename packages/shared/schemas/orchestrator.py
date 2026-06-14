from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.shared.schemas.brand_os import BrandContentDraftResponse
from packages.shared.schemas.director_os import WeeklyUpdateResponse
from packages.shared.schemas.interview_os import InterviewBriefResponse
from packages.shared.schemas.one_on_one_os import OneOnOneResponse


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
        # Claude is the default synthesis provider. The workflow automatically
        # falls back to deterministic output when ANTHROPIC_API_KEY is absent,
        # so no code change is required when the key is not available.
        default="claude",
        description=(
            "Model provider for Director OS synthesis when use_model is enabled. "
            "Falls back to deterministic output when ANTHROPIC_API_KEY is absent."
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
            "Run the filesystem MCP retrieval loop as the primary synthesis path. "
            "When True, Claude reads project files via tool calls and produces the "
            "synthesis — the result is returned in mcp_synthesis on the response. "
            "The regular workflow still runs to produce structured evidence and "
            "section counts, but its model-assisted synthesis is skipped to avoid "
            "burning tokens on two calls. Requires ANTHROPIC_API_KEY. "
            "MCP always uses the Claude provider regardless of the provider field."
        ),
    )
    claude_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Claude model ID used for Director OS synthesis when provider is "
            "'claude', for MCP-backed synthesis when use_mcp is True, and for "
            "researcher and writer agents when target_audience is set."
        ),
    )
    target_audience: str | None = Field(
        default=None,
        description=(
            "When set, triggers the researcher → writer multi-agent pipeline after "
            "the normal workflow. The researcher synthesizes evidence into structured "
            "findings; the writer formats them for the audience. "
            "Supported values: 'linkedin_post', 'executive_brief', 'team_update'."
        ),
    )


class AgentCall(BaseModel):
    """Token-level record of a single agent invocation in a multi-agent run."""

    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class WorkflowTrace(BaseModel):
    """Operator-facing execution metadata for a routed workflow run."""

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
    # "keyword-match" until Ollama classification replaces the keyword router.
    routing_model: str = "keyword-match"
    # Prompt-caching fields — populated when Claude provider is used.
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    # Populated when use_mcp=True. Each entry records the tool name, input,
    # success flag, and a preview of what was retrieved.
    mcp_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    # Populated when target_audience is set. Records researcher and writer
    # agent invocations with token counts for operator visibility.
    agent_calls: list[AgentCall] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Response returned from the lightweight Chief of Staff routing layer."""

    selected_workflow: str
    rationale: str
    trace: WorkflowTrace
    result: (
        WeeklyUpdateResponse | BrandContentDraftResponse | InterviewBriefResponse | OneOnOneResponse
    )
    # Populated when target_audience is set — the writer agent's audience-
    # formatted output alongside the structured workflow result.
    formatted_content: str | None = None
    # Populated when use_mcp=True — Claude's free-form synthesis after reading
    # project files via MCP tool calls. This is the primary synthesis output
    # when MCP is enabled; the structured result field contains evidence and
    # section counts from the deterministic workflow path.
    mcp_synthesis: str | None = None
