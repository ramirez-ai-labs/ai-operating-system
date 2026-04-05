from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


def build_content_draft(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    """Build a grounded Brand OS content draft from local notes and work artifacts."""
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

    return BrandContentDraftResponse(
        insight_summary=_build_summary(request.focus, evidence),
        post_outline=_collect_items(
            evidence,
            ("insight", "win", "retrieval", "evaluation", "workflow"),
            3,
        ),
        podcast_angles=_collect_items(
            evidence,
            ("podcast", "theme", "discussion", "leadership", "operating"),
            2,
        ),
        repo_improvements=_collect_items(
            evidence,
            ("improve", "next", "validation", "filtering", "workflow"),
            3,
        ),
        evidence=evidence,
    )


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
    keywords: tuple[str, ...],
    limit: int,
) -> list[GroundedItem]:
    """Select grounded lines that can feed posts, podcast angles, or repo improvements."""
    results: list[GroundedItem] = []
    for item in evidence:
        lowered = item.excerpt.lower()
        if any(keyword in lowered for keyword in keywords):
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
