from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.retrieval.backend import retrieve_relevant_documents
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse

logger = logging.getLogger(__name__)


class OneOnOneOSState(TypedDict, total=False):
    """State carried through the One-on-One OS brief graph."""

    request: OneOnOneRequest
    evidence: list[EvidenceItem]
    response: OneOnOneResponse
    used_model: bool
    fallback_attempted: bool
    provider_usage: dict[str, int]


def run_one_on_one_graph(request: OneOnOneRequest) -> OneOnOneResponse:
    """Execute the One-on-One OS graph and return the public response."""
    graph = _get_one_on_one_graph()
    final_state = graph.invoke(
        {
            "request": request,
            "used_model": request.use_model,
            "fallback_attempted": False,
        }
    )
    return final_state["response"]


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
            return {"fallback_attempted": True}

    response = _build_deterministic_response(request, evidence)
    return {"response": response, "used_model": False}


def route_after_build(
    state: OneOnOneOSState,
) -> Literal["build_response", END]:
    """Retry with deterministic path if model synthesis failed and fallback is allowed."""
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
            f"One-on-One OS model synthesis requires provider='claude'. "
            f"Got: {request.provider!r}. Ollama synthesis is not available for One-on-One OS."
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
            allowed_prefixes=("Action:", "TODO:", "Follow-up:"),
            keywords=("action", "follow-up", "todo", "commit", "will", "by "),
            limit=4,
        ),
        talking_points=_collect_items(
            evidence,
            allowed_prefixes=("Talking Point:", "Topic:", "Discuss:"),
            keywords=("discuss", "cover", "review", "check in", "talking"),
            limit=4,
        ),
        blockers=_collect_items(
            evidence,
            allowed_prefixes=("Blocker:", "Blocked:", "Blocking:"),
            keywords=("blocker", "blocked", "blocking", "waiting on", "pending", "no response"),
            limit=3,
        ),
        kudos=_collect_items(
            evidence,
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
    allowed_prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
    limit: int,
) -> list[GroundedItem]:
    """Select grounded lines that match a brief section by prefix or keyword."""
    results: list[GroundedItem] = []
    seen: set[str] = set()
    for item in evidence:
        lowered = item.excerpt.lower()
        norm_prefixes = tuple(p.lower() for p in allowed_prefixes)
        prefix_match = any(lowered.startswith(p) for p in norm_prefixes)
        keyword_match = any(kw in lowered for kw in keywords)
        if (prefix_match or keyword_match) and item.excerpt not in seen:
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


def _build_one_on_one_graph():
    graph = StateGraph(OneOnOneOSState)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("build_response", build_response)
    graph.add_edge(START, "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "build_response")
    graph.add_conditional_edges(
        "build_response",
        route_after_build,
        {
            "build_response": "build_response",
            END: END,
        },
    )
    return graph.compile()


def _get_one_on_one_graph():
    return _ONE_ON_ONE_GRAPH


_ONE_ON_ONE_GRAPH = _build_one_on_one_graph()
