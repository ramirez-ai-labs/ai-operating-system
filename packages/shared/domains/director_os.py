from __future__ import annotations

from pydantic import Field

from packages.shared.domains.spec import DomainSpec, DomainTool, DomainToolInput
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse
from packages.shared.schemas.orchestrator import OrchestratorRequest

# The deterministic path's summary always starts with this prefix, so a result
# carrying it after use_model=True means the model path fell back.
DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"

ROUTING_HINT = (
    "status updates, project reviews, leadership summaries, risk tracking, or weekly updates"
)


class WeeklyUpdateToolInput(DomainToolInput):
    data_path: str = Field(
        default="data/local_only/projects",
        description="Directory under data/local_only containing project notes.",
    )


def _run(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    # Imported at call time so loading the registry does not load LangGraph.
    from director_os.workflows.weekly_update import build_weekly_update

    return build_weekly_update(request)


def _build_request(request: OrchestratorRequest, use_model: bool) -> WeeklyUpdateRequest:
    return WeeklyUpdateRequest(
        data_path=request.data_path,
        focus=request.focus or request.prompt,
        max_documents=request.max_documents,
        use_model=use_model,
        fallback_to_deterministic=request.fallback_to_deterministic,
        # Keep provider choice at the workflow boundary so routing can
        # stay deterministic while synthesis remains explicitly opt-in.
        provider=request.provider,
        ollama_url=request.ollama_url,
        ollama_model=request.ollama_model,
        claude_model=request.claude_model,
    )


def _model_used(request: OrchestratorRequest, result: WeeklyUpdateResponse) -> bool:
    return request.use_model and not result.summary.startswith(DETERMINISTIC_SUMMARY_PREFIX)


SPEC = DomainSpec(
    domain="director_os",
    workflow_id="director_os.weekly_update",
    routing_hint=ROUTING_HINT,
    tool=DomainTool(
        name="director_os_weekly_update",
        description=(
            "Build a weekly leadership update — wins, risks, and next steps — from "
            "local project notes. Every item cites its source file and line number. "
            f"Use for: {ROUTING_HINT}."
        ),
        input_model=WeeklyUpdateToolInput,
    ),
    request_model=WeeklyUpdateRequest,
    response_model=WeeklyUpdateResponse,
    run=_run,
    build_request=_build_request,
    model_used=_model_used,
    api_path="/director-os/weekly-update",
    supported_providers=("ollama", "claude"),
    routing_keywords=("leadership", "weekly update", "operating review"),
    keyword_priority=40,
    is_default=True,
)
