from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowTrace,
)

DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"


def route_request(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route an incoming request to the correct domain workflow."""
    # Workflow selection happens first. A caller can either explicitly pick a
    # workflow or let the orchestrator infer one from the prompt text.
    workflow = request.workflow or _select_workflow(request.prompt)

    if workflow == "director_os.weekly_update":
        # The orchestrator adapts generic request input into the explicit
        # Director OS schema. This keeps routing logic separate from workflow logic.
        workflow_request = WeeklyUpdateRequest(
            data_path=request.data_path,
            focus=request.focus or request.prompt,
            max_documents=request.max_documents,
            use_model=request.use_model,
            fallback_to_deterministic=request.fallback_to_deterministic,
            ollama_url=request.ollama_url,
            ollama_model=request.ollama_model,
        )
        result = build_weekly_update(workflow_request)
    elif workflow == "brand_os.content_draft":
        # Brand OS uses a different request schema, but the pattern is the same:
        # convert the generic orchestrator input into a workflow-specific contract.
        workflow_request = BrandContentDraftRequest(
            data_path=request.data_path,
            focus=request.focus or request.prompt,
            max_documents=request.max_documents,
        )
        result = build_content_draft(workflow_request)
    else:
        raise ValueError(
            "Unsupported workflow. Current supported workflows: "
            "director_os.weekly_update, brand_os.content_draft."
        )

    return OrchestratorResponse(
        selected_workflow=workflow,
        rationale=_build_rationale(request, workflow),
        trace=_build_trace(request, workflow, result),
        result=result,
    )


def _select_workflow(prompt: str | None) -> str:
    """Choose a workflow using simple keyword rules that are easy to inspect."""
    lowered = (prompt or "").lower()
    # These rules are intentionally simple. The MVP favors readability over a
    # "smart" classifier so a beginner can see exactly why a workflow was chosen.
    if any(
        keyword in lowered
        for keyword in ("content", "linkedin", "podcast", "thought leadership", "brand")
    ):
        return "brand_os.content_draft"
    if any(keyword in lowered for keyword in ("weekly update", "leadership", "operating review")):
        return "director_os.weekly_update"
    return "director_os.weekly_update"


def _build_rationale(request: OrchestratorRequest, workflow: str) -> str:
    """Explain why the orchestrator picked the current workflow."""
    if request.workflow:
        return f"Workflow explicitly requested: {workflow}."
    return f"Selected {workflow} from request intent and focus."


def _build_trace(
    request: OrchestratorRequest,
    workflow: str,
    result,
) -> WorkflowTrace:
    """Summarize the execution path in a shape that operators can inspect easily."""
    evidence_sources = list(dict.fromkeys(item.source for item in result.evidence))
    focus_used = request.focus or request.prompt

    if workflow == "director_os.weekly_update":
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
