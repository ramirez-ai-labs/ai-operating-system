from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowTrace,
)

DIRECTOR_WORKFLOW = "director_os.weekly_update"
BRAND_WORKFLOW = "brand_os.content_draft"
DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"
BRAND_ROUTING_KEYWORDS = (
    "podcast",
    "linkedin",
    "thought leadership",
    "brand",
    "content",
)
DIRECTOR_ROUTING_KEYWORDS = ("leadership", "weekly update", "operating review")


def route_request(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route an incoming request to the correct domain workflow."""
    if request.workflow:
        workflow = request.workflow
        rationale = f"Workflow explicitly requested: {workflow}."
    else:
        workflow, rationale = _select_workflow(request.prompt)

    result = _run_workflow(request, workflow)

    # When use_mcp=True, run the MCP retrieval loop so Claude reads project
    # files via tool calls. The tool call log is surfaced in the trace so
    # operators can see exactly what the agent read before synthesizing.
    mcp_tool_calls: list[dict] = []
    if request.use_mcp:
        mcp_response = run_with_mcp_tools(
            prompt=request.prompt or request.focus or "Synthesize project status",
            data_path=request.data_path,
            model=request.claude_model,
        )
        mcp_tool_calls = mcp_response.trace.get("mcp_tool_calls", [])

    return OrchestratorResponse(
        selected_workflow=workflow,
        rationale=rationale,
        trace=_build_trace(request, workflow, result, mcp_tool_calls=mcp_tool_calls),
        result=result,
    )


def _run_workflow(request: OrchestratorRequest, workflow: str):
    """Adapt the generic request into the selected workflow contract and execute it."""
    if workflow == DIRECTOR_WORKFLOW:
        return build_weekly_update(
            WeeklyUpdateRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
                use_model=request.use_model,
                fallback_to_deterministic=request.fallback_to_deterministic,
                # Keep provider choice at the workflow boundary so routing can
                # stay deterministic while synthesis remains explicitly opt-in.
                provider=request.provider,
                ollama_url=request.ollama_url,
                ollama_model=request.ollama_model,
                claude_model=request.claude_model,
            )
        )

    if workflow == BRAND_WORKFLOW:
        return build_content_draft(
            BrandContentDraftRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
            )
        )

    raise ValueError(
        "Unsupported workflow. Current supported workflows: "
        f"{DIRECTOR_WORKFLOW}, {BRAND_WORKFLOW}."
    )


def _select_workflow(prompt: str | None) -> tuple[str, str]:
    """Choose a workflow using simple keyword rules that remain easy to inspect."""
    lowered = (prompt or "").lower()
    for keyword in BRAND_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                BRAND_WORKFLOW,
                f"Selected {BRAND_WORKFLOW} because the prompt matched '{keyword}'.",
            )

    for keyword in DIRECTOR_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                DIRECTOR_WORKFLOW,
                f"Selected {DIRECTOR_WORKFLOW} because the prompt matched '{keyword}'.",
            )

    return DIRECTOR_WORKFLOW, f"Selected {DIRECTOR_WORKFLOW} as the default workflow."


def _build_trace(
    request: OrchestratorRequest,
    workflow: str,
    result,
    mcp_tool_calls: list[dict] | None = None,
) -> WorkflowTrace:
    """Summarize the execution path in a shape that operators can inspect easily."""
    evidence_sources = list(dict.fromkeys(item.source for item in result.evidence))
    focus_used = request.focus or request.prompt

    if workflow == DIRECTOR_WORKFLOW:
        fallback_used = request.use_model and result.summary.startswith(
            DETERMINISTIC_SUMMARY_PREFIX
        )
        section_counts = {
            "wins": len(result.wins),
            "risks": len(result.risks),
            "next_steps": len(result.next_steps),
        }
        model_supported = True
        model_used = request.use_model and not fallback_used
        if model_used:
            provider_used = request.provider
            model_id_used = (
                request.claude_model if request.provider == "claude"
                else request.ollama_model
            )
        else:
            provider_used = None
            model_id_used = None
    else:
        fallback_used = False
        section_counts = {
            "post_outline": len(result.post_outline),
            "podcast_angles": len(result.podcast_angles),
            "repo_improvements": len(result.repo_improvements),
        }
        model_supported = False
        model_used = False
        provider_used = None
        model_id_used = None

    return WorkflowTrace(
        data_path=request.data_path,
        focus_used=focus_used,
        evidence_count=len(result.evidence),
        evidence_sources=evidence_sources,
        model_requested=request.use_model,
        model_supported=model_supported,
        model_used=model_used,
        provider_used=provider_used,
        model_id_used=model_id_used,
        fallback_used=fallback_used,
        section_counts=section_counts,
        validation_summary=(
            f"Grounded output assembled from {len(result.evidence)} evidence items "
            f"across {len(evidence_sources)} source files."
        ),
        mcp_tool_calls=mcp_tool_calls or [],
    )
