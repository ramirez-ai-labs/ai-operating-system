from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


def build_content_draft(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    """Build a grounded Brand OS content draft from local notes and work artifacts."""
    # Brand OS reuses the same local retrieval layer as Director OS. The only
    # difference is how the retrieved evidence is shaped into output sections.
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
        # Each section below is a different "lens" over the same evidence set.
        # That keeps the workflow simple for beginners: retrieve once, then
        # organize the evidence into a few useful output buckets.
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
            # Instead of rewriting the evidence, the MVP returns the original
            # grounded line so a beginner can always trace the output back to
            # exactly what was retrieved from local files.
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
