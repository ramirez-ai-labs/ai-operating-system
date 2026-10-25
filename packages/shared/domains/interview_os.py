from __future__ import annotations

from pydantic import Field

from packages.shared.domains.spec import DomainSpec, DomainTool, DomainToolInput
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse
from packages.shared.schemas.orchestrator import OrchestratorRequest

ROUTING_HINT = (
    "interview prep, candidate briefs, hiring questions, screening notes, or candidate research"
)


class InterviewBriefToolInput(DomainToolInput):
    data_path: str = Field(
        default="data/local_only/interviews",
        description="Directory under data/local_only with candidate notes and role briefs.",
    )
    candidate_name: str | None = Field(
        default=None,
        description="Candidate name, included in the brief summary when provided.",
    )
    role: str | None = Field(
        default=None,
        description="Role being interviewed for; focuses question and talking-point selection.",
    )


def _run(request: InterviewBriefRequest) -> InterviewBriefResponse:
    # Imported at call time so loading the registry does not load LangGraph.
    from interview_os.workflows.interview_brief import build_interview_brief

    return build_interview_brief(request)


def _build_request(request: OrchestratorRequest, use_model: bool) -> InterviewBriefRequest:
    return InterviewBriefRequest(
        data_path=request.data_path,
        focus=request.focus or request.prompt,
        max_documents=request.max_documents,
        use_model=use_model,
        provider=request.provider,
        claude_model=request.claude_model,
        fallback_to_deterministic=request.fallback_to_deterministic,
    )


def _model_used(_request: OrchestratorRequest, result: InterviewBriefResponse) -> bool:
    # Claude-only domains record provider_usage only when the model path ran.
    return bool(result.provider_usage)


SPEC = DomainSpec(
    domain="interview_os",
    workflow_id="interview_os.brief",
    routing_hint=ROUTING_HINT,
    tool=DomainTool(
        name="interview_os_brief",
        description=(
            "Build a candidate interview brief — key questions, talking points, and red "
            "flags — from local hiring notes. Every item cites its source file and line "
            f"number. Use for: {ROUTING_HINT}."
        ),
        input_model=InterviewBriefToolInput,
    ),
    request_model=InterviewBriefRequest,
    response_model=InterviewBriefResponse,
    run=_run,
    build_request=_build_request,
    model_used=_model_used,
    api_path="/interview-os/brief",
    supported_providers=("claude",),
    routing_keywords=(
        "interview",
        "candidate",
        "hiring",
        "interviewer",
        "screening",
        "debrief",
    ),
    keyword_priority=20,
)
