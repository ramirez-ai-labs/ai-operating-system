from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


class BrandOSState(TypedDict, total=False):
    """State carried through the Brand OS content-draft graph."""

    request: BrandContentDraftRequest
    evidence: list[EvidenceItem]
    response: BrandContentDraftResponse


def run_content_draft_graph(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    """Execute the Brand OS content-draft graph and return the public response."""
    graph = _get_content_draft_graph()
    final_state = graph.invoke({"request": request})
    return final_state["response"]


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


def build_response(state: BrandOSState) -> BrandOSState:
    """Shape the retrieved evidence into the current Brand OS draft sections."""
    request = state["request"]
    evidence = state["evidence"]
    response = BrandContentDraftResponse(
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
    return {"response": response}


def _build_content_draft_graph():
    graph = StateGraph(BrandOSState)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("build_response", build_response)

    graph.add_edge(START, "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "build_response")
    graph.add_edge("build_response", END)
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

    competing_prefixes = {
        "post_outline": ("podcast:", "improve:", "next:"),
        "podcast_angles": ("insight:", "workflow:", "improve:", "next:"),
        "repo_improvements": ("insight:", "podcast:"),
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
