from __future__ import annotations

from pydantic import Field

from packages.shared.domains.spec import DomainSpec, DomainTool, DomainToolInput
from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse
from packages.shared.schemas.orchestrator import OrchestratorRequest

ROUTING_HINT = (
    "content creation, LinkedIn posts, podcasts, thought leadership, brand strategy, "
    "writing, or social media"
)


class ContentDraftToolInput(DomainToolInput):
    data_path: str = Field(
        default="data/local_only/brand",
        description="Directory under data/local_only containing brand and work notes.",
    )


def _run(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    # Imported at call time so loading the registry does not load LangGraph.
    from brand_os.workflows.content_draft import build_content_draft

    return build_content_draft(request)


def _build_request(request: OrchestratorRequest, use_model: bool) -> BrandContentDraftRequest:
    return BrandContentDraftRequest(
        data_path=request.data_path,
        focus=request.focus or request.prompt,
        max_documents=request.max_documents,
        use_model=use_model,
        provider=request.provider,
        claude_model=request.claude_model,
        fallback_to_deterministic=request.fallback_to_deterministic,
    )


def _model_used(_request: OrchestratorRequest, result: BrandContentDraftResponse) -> bool:
    # Claude-only domains record provider_usage only when the model path ran.
    return bool(result.provider_usage)


SPEC = DomainSpec(
    domain="brand_os",
    workflow_id="brand_os.content_draft",
    routing_hint=ROUTING_HINT,
    tool=DomainTool(
        name="brand_os_content_draft",
        description=(
            "Draft content — post outlines, podcast angles, and repo improvement notes — "
            "from local technical work notes. Every item cites its source file and line "
            f"number. Use for: {ROUTING_HINT}."
        ),
        input_model=ContentDraftToolInput,
    ),
    request_model=BrandContentDraftRequest,
    response_model=BrandContentDraftResponse,
    run=_run,
    build_request=_build_request,
    model_used=_model_used,
    api_path="/brand-os/content-draft",
    supported_providers=("claude",),
    routing_keywords=("podcast", "linkedin", "thought leadership", "brand", "content"),
    keyword_priority=30,
)
