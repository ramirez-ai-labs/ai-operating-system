from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.observability.langsmith import (
    get_langsmith_tracing_context,
    traceable,
)
from packages.shared.retrieval.backend import retrieve_relevant_documents
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse
from packages.shared.validation.one_on_one_os import validate_meeting_brief

logger = logging.getLogger(__name__)


class OneOnOneOSState(TypedDict, total=False):
    """State carried through the One-on-One OS brief graph."""

    request: OneOnOneRequest
    evidence: list[EvidenceItem]
    response: OneOnOneResponse
    used_model: bool
    fallback_attempted: bool
    provider_usage: dict[str, int]


@traceable(name="one_on_one_os.run_one_on_one_graph", run_type="chain")
def run_one_on_one_graph(request: OneOnOneRequest) -> OneOnOneResponse:
    """Execute the One-on-One OS graph and return the public response."""
    graph = _get_one_on_one_graph()
    with get_langsmith_tracing_context():
        final_state = graph.invoke(
            {
                "request": request,
                "used_model": request.use_model,
                "fallback_attempted": False,
            }
        )
    return final_state["response"]


@traceable(name="one_on_one_os.retrieve_evidence", run_type="chain")
def retrieve_evidence(state: OneOnOneOSState) -> OneOnOneOSState:
    """Collect local evidence One-on-One OS is allowed to use."""
    request = state["request"]
    query = request.focus or request.direct_report
    evidence = retrieve_relevant_documents(
        base_path=request.data_path,
        query=query,
        limit=request.max_documents,
    )
    if not evidence:
        raise ValueError(
            "No relevant local documents were found. "
            "Add 1:1 notes under the data path or adjust the focus."
        )
    return {"evidence": evidence}


@traceable(name="one_on_one_os.build_response", run_type="chain")
def build_response(state: OneOnOneOSState) -> OneOnOneOSState:
    """Shape retrieved evidence into the One-on-One OS brief sections."""
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
                "One-on-One OS model synthesis failed — falling back to deterministic path: %s",
                exc,
            )

    response = _build_deterministic_response(request, evidence)
    return {"response": response, "used_model": False}


@traceable(name="one_on_one_os.validate_response", run_type="chain")
def validate_response(state: OneOnOneOSState) -> OneOnOneOSState:
    """Validate the current response and trigger deterministic fallback when allowed."""
    response = state["response"]
    request = state["request"]
    try:
        validated = validate_meeting_brief(response)
        return {"response": validated}
    except ValueError:
        if not state.get("used_model", False) or not request.fallback_to_deterministic:
            raise
        return {"fallback_attempted": True}


def route_after_validation(
    state: OneOnOneOSState,
) -> Literal["build_response", END]:
    """Retry with deterministic path if model output failed validation."""
    if state.get("fallback_attempted", False) and state.get("used_model", False):
        return "build_response"
    return END


def _build_model_response(
    request: OneOnOneRequest,
    evidence: list[EvidenceItem],
) -> tuple[OneOnOneResponse, dict[str, int]]:
    provider = _build_provider(request)
    response = provider.generate_one_on_one_brief(request.focus, evidence)
    return response, provider.get_last_usage()


def _build_provider(request: OneOnOneRequest):
    """Select the synthesis provider. Patchable in tests and evals."""
    if request.provider != "claude":
        raise ValueError(
            "One-on-One OS model synthesis only supports provider='claude' "
            f"(requires ANTHROPIC_API_KEY). Got: {request.provider!r}. "
            "Set use_model=False for deterministic synthesis, or keep "
            "fallback_to_deterministic=True (the default) to fall back automatically."
        )
    from packages.shared.providers.one_on_one_os import ClaudeOneOnOneProvider
    return ClaudeOneOnOneProvider(model=request.claude_model)


def _build_deterministic_response(
    request: OneOnOneRequest,
    evidence: list[EvidenceItem],
) -> OneOnOneResponse:
    return OneOnOneResponse(
        meeting_summary=_build_summary(request, evidence),
        action_items=_collect_items(
            evidence,
            section_name="action_items",
            allowed_prefixes=("Action:", "TODO:", "Follow-up:"),
            keywords=("action", "follow-up", "todo", "commit", "will", "by "),
            limit=4,
        ),
        talking_points=_collect_items(
            evidence,
            section_name="talking_points",
            allowed_prefixes=("Talking Point:", "Topic:", "Discuss:"),
            keywords=("discuss", "cover", "review", "check in", "talking"),
            limit=4,
        ),
        blockers=_collect_items(
            evidence,
            section_name="blockers",
            allowed_prefixes=("Blocker:", "Blocked:", "Blocking:"),
            keywords=("blocker", "blocked", "blocking", "waiting on", "pending", "no response"),
            limit=3,
        ),
        kudos=_collect_items(
            evidence,
            section_name="kudos",
            allowed_prefixes=("Kudos:", "Win:", "Recognition:"),
            keywords=("kudos", "recognition", "great work", "shoutout", "achieved", "delivered"),
            limit=3,
        ),
        evidence=evidence,
    )


def _build_summary(request: OneOnOneRequest, evidence: list[EvidenceItem]) -> str:
    direct_report = request.direct_report or "the direct report"
    top_titles = list(dict.fromkeys(item.title for item in evidence))
    return (
        f"One-on-One OS brief for meeting with {direct_report}. "
        f"Grounded from local notes: {', '.join(top_titles[:2])}."
    )


def _collect_items(
    evidence: list[EvidenceItem],
    *,
    section_name: str,
    allowed_prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
    limit: int,
) -> list[GroundedItem]:
    """Select grounded lines that match a brief section by prefix or keyword."""
    results: list[GroundedItem] = []
    seen: set[str] = set()
    for item in evidence:
        lowered = item.excerpt.lower()
        if _matches_one_on_one_section(
            lowered_excerpt=lowered,
            section_name=section_name,
            allowed_prefixes=allowed_prefixes,
            keywords=keywords,
        ) and item.excerpt not in seen:
            seen.add(item.excerpt)
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


# Explicit prefixes per section, used to keep an excerpt claimed by one
# section's prefix from also leaking into another section via keyword
# fallback (e.g. a "Blocker:" line matching another section's loose keyword).
_ONE_ON_ONE_SECTION_PREFIXES: dict[str, tuple[str, ...]] = {
    "action_items": ("action:", "todo:", "follow-up:"),
    "talking_points": ("talking point:", "topic:", "discuss:"),
    "blockers": ("blocker:", "blocked:", "blocking:"),
    "kudos": ("kudos:", "win:", "recognition:"),
}


def _matches_one_on_one_section(
    *,
    lowered_excerpt: str,
    section_name: str,
    allowed_prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
) -> bool:
    """Prefer explicit section prefixes before falling back to loose keyword matching."""
    normalized_prefixes = tuple(p.lower() for p in allowed_prefixes)
    if any(lowered_excerpt.startswith(p) for p in normalized_prefixes):
        return True

    for other_section, other_prefixes in _ONE_ON_ONE_SECTION_PREFIXES.items():
        if other_section != section_name and any(
            lowered_excerpt.startswith(p) for p in other_prefixes
        ):
            return False

    return any(keyword in lowered_excerpt for keyword in keywords)


def _build_one_on_one_graph():
    graph = StateGraph(OneOnOneOSState)
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


def _get_one_on_one_graph():
    return _ONE_ON_ONE_GRAPH


_ONE_ON_ONE_GRAPH = _build_one_on_one_graph()
