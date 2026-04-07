from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
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
    return OrchestratorResponse(
        selected_workflow=workflow,
        rationale=rationale,
        trace=_build_trace(request, workflow, result),
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
                ollama_url=request.ollama_url,
                ollama_model=request.ollama_model,
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
    else:
        fallback_used = False
        section_counts = {
            "post_outline": len(result.post_outline),
            "podcast_angles": len(result.podcast_angles),
            "repo_improvements": len(result.repo_improvements),
        }
        model_supported = False
        model_used = False

    return WorkflowTrace(
        data_path=request.data_path,
        focus_used=focus_used,
        evidence_count=len(result.evidence),
        evidence_sources=evidence_sources,
        model_requested=request.use_model,
        model_supported=model_supported,
        model_used=model_used,
        fallback_used=fallback_used,
        section_counts=section_counts,
        validation_summary=(
            f"Grounded output assembled from {len(result.evidence)} evidence items "
            f"across {len(evidence_sources)} source files."
        ),
    )
