from __future__ import annotations

from pydantic import Field

from packages.shared.domains.spec import DomainSpec, DomainTool, DomainToolInput
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse
from packages.shared.schemas.orchestrator import OrchestratorRequest

ROUTING_HINT = (
    "1:1 meeting prep, direct report check-ins, manager notes, action item tracking, "
    "team health, or meeting briefs"
)


class MeetingBriefToolInput(DomainToolInput):
    data_path: str = Field(
        default="data/local_only/one_on_one",
        description="Directory under data/local_only with 1:1 notes and action logs.",
    )
    direct_report: str | None = Field(
        default=None,
        description="Direct report name, included in the brief summary when provided.",
    )


def _run(request: OneOnOneRequest) -> OneOnOneResponse:
    # Imported at call time so loading the registry does not load LangGraph.
    from one_on_one_os.workflows.meeting_brief import build_meeting_brief

    return build_meeting_brief(request)


def _build_request(request: OrchestratorRequest, use_model: bool) -> OneOnOneRequest:
    return OneOnOneRequest(
        data_path=request.data_path,
        focus=request.focus or request.prompt,
        max_documents=request.max_documents,
        use_model=use_model,
        provider=request.provider,
        claude_model=request.claude_model,
        fallback_to_deterministic=request.fallback_to_deterministic,
    )


def _model_used(_request: OrchestratorRequest, result: OneOnOneResponse) -> bool:
    # Claude-only domains record provider_usage only when the model path ran.
    return bool(result.provider_usage)


SPEC = DomainSpec(
    domain="one_on_one_os",
    workflow_id="one_on_one_os.brief",
    routing_hint=ROUTING_HINT,
    tool=DomainTool(
        name="one_on_one_os_brief",
        description=(
            "Build a 1:1 meeting brief — action items, talking points, blockers, and "
            "kudos — from local direct-report notes. Every item cites its source file "
            f"and line number. Use for: {ROUTING_HINT}."
        ),
        input_model=MeetingBriefToolInput,
    ),
    request_model=OneOnOneRequest,
    response_model=OneOnOneResponse,
    run=_run,
    build_request=_build_request,
    model_used=_model_used,
    api_path="/one-on-one/brief",
    supported_providers=("claude",),
    routing_keywords=("1:1", "1on1", "one-on-one", "direct report", "meeting prep", "check-in"),
    keyword_priority=10,
)
