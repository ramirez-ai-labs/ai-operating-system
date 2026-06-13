from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.retrieval.backend import retrieve_relevant_documents
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse


class InterviewOSState(TypedDict, total=False):
    """State carried through the Interview OS brief graph."""

    request: InterviewBriefRequest
    evidence: list[EvidenceItem]
    response: InterviewBriefResponse


def run_interview_brief_graph(request: InterviewBriefRequest) -> InterviewBriefResponse:
    """Execute the Interview OS brief graph and return the public response."""
    graph = _get_interview_brief_graph()
    final_state = graph.invoke({"request": request})
    return final_state["response"]


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


def build_response(state: InterviewOSState) -> InterviewOSState:
    """Shape retrieved evidence into the Interview OS brief sections."""
    request = state["request"]
    evidence = state["evidence"]
    response = InterviewBriefResponse(
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
    return {"response": response}


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
    graph.add_edge("build_response", END)
    return graph.compile()


def _get_interview_brief_graph():
    return _INTERVIEW_BRIEF_GRAPH


_INTERVIEW_BRIEF_GRAPH = _build_interview_brief_graph()
