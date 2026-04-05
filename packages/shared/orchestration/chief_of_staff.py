from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
)


def route_request(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route an incoming request to the correct domain workflow."""
    workflow = request.workflow or _select_workflow(request.prompt)

    if workflow != "director_os.weekly_update":
        raise ValueError(
            "Unsupported workflow. Current supported workflow: director_os.weekly_update."
        )

    # The orchestrator currently adapts generic request input into the explicit
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
    return OrchestratorResponse(
        selected_workflow=workflow,
        rationale=_build_rationale(request, workflow),
        result=result,
    )


def _select_workflow(prompt: str | None) -> str:
    """Choose a workflow using simple keyword rules that are easy to inspect."""
    lowered = (prompt or "").lower()
    if any(keyword in lowered for keyword in ("weekly update", "leadership", "operating review")):
        return "director_os.weekly_update"
    return "director_os.weekly_update"


def _build_rationale(request: OrchestratorRequest, workflow: str) -> str:
    """Explain why the orchestrator picked the current workflow."""
    if request.workflow:
        return f"Workflow explicitly requested: {workflow}."
    return f"Selected {workflow} from request intent and focus."
