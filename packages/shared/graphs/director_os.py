from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.observability.langsmith import (
    get_langsmith_tracing_context,
    traceable,
)
from packages.shared.providers.ollama import OllamaWeeklyUpdateProvider
from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.director_os import (
    EvidenceItem,
    GroundedItem,
    WeeklyUpdateDraft,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
)
from packages.shared.validation.weekly_update import validate_weekly_update


class DirectorOSState(TypedDict, total=False):
    """State carried through the Director OS weekly update graph."""

    request: WeeklyUpdateRequest
    evidence: list[EvidenceItem]
    draft: WeeklyUpdateDraft
    response: WeeklyUpdateResponse
    used_model: bool
    fallback_attempted: bool


@traceable(name="director_os.run_weekly_update_graph", run_type="chain")
def run_weekly_update_graph(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Execute the Director OS weekly update graph and return the final response."""
    graph = _get_weekly_update_graph()
    with get_langsmith_tracing_context():
        final_state = graph.invoke(
            {
                "request": request,
                "used_model": request.use_model,
                "fallback_attempted": False,
            }
        )
    return final_state["response"]


@traceable(name="director_os.retrieve_evidence", run_type="chain")
def retrieve_evidence(state: DirectorOSState) -> DirectorOSState:
    """Collect the local evidence that the workflow is allowed to use."""
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


@traceable(name="director_os.build_draft", run_type="chain")
def build_draft(state: DirectorOSState) -> DirectorOSState:
    """Build a deterministic or model-assisted draft for the weekly update."""
    request = state["request"]
    evidence = state["evidence"]
    if request.use_model and not state.get("fallback_attempted", False):
        draft = _build_model_draft(request, evidence)
        return {"draft": draft, "used_model": True}

    draft = _build_deterministic_draft(request.focus, evidence)
    return {"draft": draft, "used_model": False}


@traceable(name="director_os.assemble_response", run_type="chain")
def assemble_response(state: DirectorOSState) -> DirectorOSState:
    """Attach evidence to the current draft before validation."""
    draft = state["draft"]
    evidence = state["evidence"]
    response = WeeklyUpdateResponse(
        summary=draft.summary,
        wins=draft.wins,
        risks=draft.risks,
        next_steps=draft.next_steps,
        evidence=evidence,
    )
    return {"response": response}


@traceable(name="director_os.validate_response", run_type="chain")
def validate_response(state: DirectorOSState) -> DirectorOSState:
    """Validate the current response and trigger deterministic fallback when allowed."""
    response = state["response"]
    request = state["request"]
    try:
        validated = validate_weekly_update(response)
        return {"response": validated}
    except ValueError:
        if not state.get("used_model", False) or not request.fallback_to_deterministic:
            raise
        return {"fallback_attempted": True}


def route_after_validation(
    state: DirectorOSState,
) -> Literal["deterministic_fallback", END]:
    """Choose whether to retry with the deterministic path or finish the run."""
    if state.get("fallback_attempted", False) and state.get("used_model", False):
        return "deterministic_fallback"
    return END


def _build_weekly_update_graph():
    graph = StateGraph(DirectorOSState)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("build_draft", build_draft)
    graph.add_node("assemble_response", assemble_response)
    graph.add_node("validate_response", validate_response)
    graph.add_node("deterministic_fallback", _run_deterministic_fallback)

    graph.add_edge(START, "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "build_draft")
    graph.add_edge("build_draft", "assemble_response")
    graph.add_edge("assemble_response", "validate_response")
    graph.add_conditional_edges(
        "validate_response",
        route_after_validation,
        {
            "deterministic_fallback": "deterministic_fallback",
            END: END,
        },
    )
    graph.add_edge("deterministic_fallback", "assemble_response")
    return graph.compile()


@traceable(name="director_os.deterministic_fallback", run_type="chain")
def _run_deterministic_fallback(state: DirectorOSState) -> DirectorOSState:
    """Replace the current draft with the deterministic baseline."""
    request = state["request"]
    evidence = state["evidence"]
    draft = _build_deterministic_draft(request.focus, evidence)
    return {"draft": draft, "used_model": False}


def _build_deterministic_draft(
    focus: str | None,
    evidence: list[EvidenceItem],
) -> WeeklyUpdateDraft:
    """Build a predictable draft directly from evidence lines."""
    return WeeklyUpdateDraft(
        summary=_build_summary(focus, evidence),
        wins=_collect_sentences(
            evidence,
            section_name="wins",
            explicit_prefix="Win:",
            keywords=("win", "shipped", "completed", "launched"),
            limit=3,
        ),
        risks=_collect_sentences(
            evidence,
            section_name="risks",
            explicit_prefix="Risk:",
            keywords=("risk", "blocked", "delay", "issue"),
            limit=3,
        ),
        next_steps=_collect_sentences(
            evidence,
            section_name="next_steps",
            explicit_prefix="Next:",
            keywords=("next", "follow-up", "plan", "action"),
            limit=3,
        ),
    )


def _build_model_draft(
    request: WeeklyUpdateRequest,
    evidence: list[EvidenceItem],
) -> WeeklyUpdateDraft:
    """Use the configured local provider to synthesize a structured draft."""
    provider = OllamaWeeklyUpdateProvider(
        base_url=request.ollama_url,
        model=request.ollama_model,
    )
    try:
        draft = provider.generate_weekly_update(request.focus, evidence)
        _validate_model_draft(draft)
        return draft
    except ValueError:
        if not request.fallback_to_deterministic:
            raise
    return _build_deterministic_draft(request.focus, evidence)


def _build_summary(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Create a concise operator-facing summary anchored to the top evidence sources."""
    focus_text = focus or "current leadership activity"
    top_source_titles = list(dict.fromkeys(item.title for item in evidence))
    top_sources = ", ".join(top_source_titles[:2])
    return (
        f"Weekly update synthesized from local project evidence about {focus_text}. "
        f"Primary supporting context came from {top_sources}."
    )


def _collect_sentences(
    evidence: list[EvidenceItem],
    *,
    section_name: str,
    explicit_prefix: str,
    keywords: tuple[str, ...],
    limit: int,
) -> list[GroundedItem]:
    """Pull grounded excerpts into a specific output section such as wins or risks."""
    results: list[GroundedItem] = []
    for item in evidence:
        lowered = item.excerpt.lower()
        if _matches_section(
            excerpt=item.excerpt,
            lowered_excerpt=lowered,
            section_name=section_name,
            explicit_prefix=explicit_prefix,
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


def _matches_section(
    *,
    excerpt: str,
    lowered_excerpt: str,
    section_name: str,
    explicit_prefix: str,
    keywords: tuple[str, ...],
) -> bool:
    """Prefer explicit section prefixes before falling back to loose keyword matching."""
    normalized_prefix = explicit_prefix.lower()
    if lowered_excerpt.startswith(normalized_prefix):
        return True

    competing_prefixes = {
        "wins": "win:",
        "risks": "risk:",
        "next_steps": "next:",
    }
    for competing_section, competing_prefix in competing_prefixes.items():
        if competing_section != section_name and lowered_excerpt.startswith(competing_prefix):
            return False

    return any(keyword in lowered_excerpt for keyword in keywords)


def _validate_model_draft(draft: WeeklyUpdateDraft) -> None:
    """Reject weak model drafts so they do not bypass the deterministic baseline."""
    if not draft.summary.strip():
        raise ValueError("Model-generated weekly update summary cannot be empty.")

    if not any((draft.wins, draft.risks, draft.next_steps)):
        raise ValueError(
            "Model-generated weekly update must include at least one actionable section."
        )


def _get_weekly_update_graph():
    return _WEEKLY_UPDATE_GRAPH


_WEEKLY_UPDATE_GRAPH = _build_weekly_update_graph()
