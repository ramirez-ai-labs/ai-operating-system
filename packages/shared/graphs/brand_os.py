from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.observability.langsmith import (
    get_langsmith_tracing_context,
    traceable,
)
from packages.shared.retrieval.backend import retrieve_relevant_documents
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem
from packages.shared.validation.brand_os import validate_brand_content_draft

logger = logging.getLogger(__name__)


class BrandOSState(TypedDict, total=False):
    """State carried through the Brand OS content-draft graph."""

    request: BrandContentDraftRequest
    evidence: list[EvidenceItem]
    response: BrandContentDraftResponse
    used_model: bool
    fallback_attempted: bool
    provider_usage: dict[str, int]


@traceable(name="brand_os.run_content_draft_graph", run_type="chain")
def run_content_draft_graph(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    """Execute the Brand OS content-draft graph and return the public response."""
    graph = _get_content_draft_graph()
    with get_langsmith_tracing_context():
        final_state = graph.invoke(
            {
                "request": request,
                "used_model": request.use_model,
                "fallback_attempted": False,
            }
        )
    return final_state["response"]


@traceable(name="brand_os.retrieve_evidence", run_type="chain")
def retrieve_evidence(state: BrandOSState) -> BrandOSState:
    """Collect the local evidence Brand OS is allowed to use."""
    request = state["request"]
    evidence = retrieve_relevant_documents(
        base_path=request.data_path,
        query=request.focus,
        limit=request.max_documents,
    )
    if not evidence:
        raise ValueError(
            "No relevant local documents were found. "
            "Add markdown files under the data path or adjust the focus."
        )
    return {"evidence": evidence}


@traceable(name="brand_os.build_response", run_type="chain")
def build_response(state: BrandOSState) -> BrandOSState:
    """Shape retrieved evidence into Brand OS draft sections."""
    request = state["request"]
    evidence = state["evidence"]

    if request.use_model and not state.get("fallback_attempted", False):
        try:
            response, usage = _build_model_response(request, evidence)
            response.provider_usage = usage
            return {"response": response, "used_model": True, "provider_usage": usage}
        except ValueError as exc:
            if not request.fallback_to_deterministic:
                raise
            logger.warning(
                "Brand OS model synthesis failed — falling back to deterministic path: %s", exc
            )

    response = _build_deterministic_response(request, evidence)
    return {"response": response, "used_model": False}


@traceable(name="brand_os.validate_response", run_type="chain")
def validate_response(state: BrandOSState) -> BrandOSState:
    """Validate the current response and trigger deterministic fallback when allowed."""
    response = state["response"]
    request = state["request"]
    try:
        validated = validate_brand_content_draft(response)
        return {"response": validated}
    except ValueError:
        if not state.get("used_model", False) or not request.fallback_to_deterministic:
            raise
        return {"fallback_attempted": True}


def route_after_validation(
    state: BrandOSState,
) -> Literal["build_response", END]:
    """Retry with deterministic path if model output failed validation."""
    if state.get("fallback_attempted", False) and state.get("used_model", False):
        return "build_response"
    return END


def _build_model_response(
    request: BrandContentDraftRequest,
    evidence: list[EvidenceItem],
) -> tuple[BrandContentDraftResponse, dict[str, int]]:
    """Use Claude to synthesize a structured content draft from evidence."""
    provider = _build_provider(request)
    response = provider.generate_brand_content_draft(request.focus, evidence)
    return response, provider.get_last_usage()


def _build_provider(request: BrandContentDraftRequest):
    """Select the synthesis provider. Patchable in tests and evals."""
    if request.provider != "claude":
        raise ValueError(
            "Brand OS model synthesis only supports provider='claude' "
            f"(requires ANTHROPIC_API_KEY). Got: {request.provider!r}. "
            "Set use_model=False for deterministic synthesis, or keep "
            "fallback_to_deterministic=True (the default) to fall back automatically."
        )
    from packages.shared.providers.brand_os import ClaudeBrandContentDraftProvider

    return ClaudeBrandContentDraftProvider(model=request.claude_model)


def _build_deterministic_response(
    request: BrandContentDraftRequest,
    evidence: list[EvidenceItem],
) -> BrandContentDraftResponse:
    return BrandContentDraftResponse(
        insight_summary=_build_summary(request.focus, evidence),
        post_outline=_collect_items(
            evidence,
            section_name="post_outline",
            allowed_prefixes=("Insight:", "Workflow:"),
            keywords=("insight", "win", "retrieval", "evaluation", "workflow"),
            limit=3,
        ),
        podcast_angles=_collect_items(
            evidence,
            section_name="podcast_angles",
            allowed_prefixes=("Podcast:",),
            keywords=("podcast", "theme", "discussion", "leadership", "operating"),
            limit=2,
        ),
        repo_improvements=_collect_items(
            evidence,
            section_name="repo_improvements",
            allowed_prefixes=("Improve:", "Next:"),
            keywords=("improve", "next", "validation", "filtering"),
            limit=3,
        ),
        evidence=evidence,
    )


def _build_content_draft_graph():
    graph = StateGraph(BrandOSState)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("build_response", build_response)
    graph.add_node("validate_response", validate_response)

    graph.add_edge(START, "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "build_response")
    graph.add_edge("build_response", "validate_response")
    graph.add_conditional_edges(
        "validate_response",
        route_after_validation,
        {
            "build_response": "build_response",
            END: END,
        },
    )
    return graph.compile()


def _build_summary(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Summarize the most relevant source material for a Brand OS draft."""
    focus_text = focus or "recent technical work"
    top_titles = list(dict.fromkeys(item.title for item in evidence))
    return (
        f"Brand OS draft synthesized from local evidence about {focus_text}. "
        f"Primary supporting context came from {', '.join(top_titles[:2])}."
    )


def _collect_items(
    evidence: list[EvidenceItem],
    *,
    section_name: str,
    allowed_prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
    limit: int,
) -> list[GroundedItem]:
    """Select grounded lines that can feed posts, podcast angles, or repo improvements."""
    results: list[GroundedItem] = []
    for item in evidence:
        lowered = item.excerpt.lower()
        if _matches_brand_section(
            lowered_excerpt=lowered,
            section_name=section_name,
            allowed_prefixes=allowed_prefixes,
            keywords=keywords,
        ):
            results.append(
                GroundedItem(
                    text=item.excerpt,
                    source=item.source,
                    line_number=item.line_number,
                )
            )
        if len(results) >= limit:
            break
    return results


def _matches_brand_section(
    *,
    lowered_excerpt: str,
    section_name: str,
    allowed_prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
) -> bool:
    """Prefer explicit Brand OS prefixes before falling back to looser keywords."""
    normalized_prefixes = tuple(prefix.lower() for prefix in allowed_prefixes)
    if any(lowered_excerpt.startswith(prefix) for prefix in normalized_prefixes):
        return True

    # Director OS prefixes (win:, risk:, decision:) are excluded from all Brand OS
    # sections — they belong to project notes, not brand content classification.
    _dos = ("win:", "risk:", "decision:")
    competing_prefixes = {
        "post_outline": ("podcast:", "improve:", "next:") + _dos,
        "podcast_angles": ("insight:", "workflow:", "improve:", "next:") + _dos,
        "repo_improvements": ("insight:", "podcast:") + _dos,
    }
    if any(
        lowered_excerpt.startswith(prefix)
        for prefix in competing_prefixes.get(section_name, ())
    ):
        return False

    return any(keyword in lowered_excerpt for keyword in keywords)


def _get_content_draft_graph():
    return _CONTENT_DRAFT_GRAPH


_CONTENT_DRAFT_GRAPH = _build_content_draft_graph()
