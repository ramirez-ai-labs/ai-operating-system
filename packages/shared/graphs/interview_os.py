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
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse

logger = logging.getLogger(__name__)


class InterviewOSState(TypedDict, total=False):
    """State carried through the Interview OS brief graph."""

    request: InterviewBriefRequest
    evidence: list[EvidenceItem]
    response: InterviewBriefResponse
    used_model: bool
    fallback_attempted: bool
    provider_usage: dict[str, int]


@traceable(name="interview_os.run_interview_brief_graph", run_type="chain")
def run_interview_brief_graph(request: InterviewBriefRequest) -> InterviewBriefResponse:
    """Execute the Interview OS brief graph and return the public response."""
    graph = _get_interview_brief_graph()
    with get_langsmith_tracing_context():
        final_state = graph.invoke(
            {
                "request": request,
                "used_model": request.use_model,
                "fallback_attempted": False,
            }
        )
    return final_state["response"]


@traceable(name="interview_os.retrieve_evidence", run_type="chain")
def retrieve_evidence(state: InterviewOSState) -> InterviewOSState:
    """Collect local evidence Interview OS is allowed to use."""
    request = state["request"]
    query = request.focus or request.candidate_name or request.role
    evidence = retrieve_relevant_documents(
        base_path=request.data_path,
        query=query,
        limit=request.max_documents,
    )
    if not evidence:
        raise ValueError(
            "No relevant local documents were found. "
            "Add markdown files under the data path or adjust the focus."
        )
    return {"evidence": evidence}


@traceable(name="interview_os.build_response", run_type="chain")
def build_response(state: InterviewOSState) -> InterviewOSState:
    """Shape retrieved evidence into the Interview OS brief sections (deterministic path)."""
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
                "Interview OS model synthesis failed — falling back to deterministic path: %s", exc
            )
            return {"fallback_attempted": True}

    response = _build_deterministic_response(request, evidence)
    return {"response": response, "used_model": False}


def route_after_build(
    state: InterviewOSState,
) -> Literal["build_response", END]:
    """Retry with deterministic path if model synthesis failed and fallback is allowed."""
    if state.get("fallback_attempted", False) and state.get("used_model", False):
        return "build_response"
    return END


def _build_model_response(
    request: InterviewBriefRequest,
    evidence: list[EvidenceItem],
) -> tuple[InterviewBriefResponse, dict[str, int]]:
    """Use Claude to synthesize a structured brief from evidence."""
    provider = _build_provider(request)
    response = provider.generate_interview_brief(request.focus, evidence)
    return response, provider.get_last_usage()


def _build_provider(request: InterviewBriefRequest):
    """Select the synthesis provider. Patchable in tests and evals."""
    if request.provider != "claude":
        raise ValueError(
            f"Interview OS model synthesis requires provider='claude'. "
            f"Got: {request.provider!r}. Ollama synthesis is not available for Interview OS."
        )
    from packages.shared.providers.interview_os import ClaudeInterviewBriefProvider
    return ClaudeInterviewBriefProvider(model=request.claude_model)


def _build_deterministic_response(
    request: InterviewBriefRequest,
    evidence: list[EvidenceItem],
) -> InterviewBriefResponse:
    return InterviewBriefResponse(
        candidate_summary=_build_summary(request, evidence),
        key_questions=_collect_items(
            evidence,
            allowed_prefixes=("Question:", "Q:"),
            keywords=("question", "ask", "explore", "probe", "assess"),
            limit=4,
        ),
        talking_points=_collect_items(
            evidence,
            allowed_prefixes=("Talking Point:", "Topic:", "Discuss:"),
            keywords=("discuss", "cover", "highlight", "mention", "experience", "background"),
            limit=4,
        ),
        red_flags=_collect_items(
            evidence,
            allowed_prefixes=("Red Flag:", "Concern:", "Risk:", "Watch:"),
            keywords=("concern", "risk", "gap", "flag", "watch", "unclear", "missing"),
            limit=3,
        ),
        evidence=evidence,
    )


def _build_summary(request: InterviewBriefRequest, evidence: list[EvidenceItem]) -> str:
    candidate = request.candidate_name or "the candidate"
    role = request.role or "the role"
    top_titles = list(dict.fromkeys(item.title for item in evidence))
    return (
        f"Interview OS brief for {candidate} applying for {role}. "
        f"Grounded from local evidence: {', '.join(top_titles[:2])}."
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


def _build_interview_brief_graph():
    graph = StateGraph(InterviewOSState)
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


def _get_interview_brief_graph():
    return _INTERVIEW_BRIEF_GRAPH


_INTERVIEW_BRIEF_GRAPH = _build_interview_brief_graph()
