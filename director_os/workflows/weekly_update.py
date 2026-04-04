from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.director_os import (
    EvidenceItem,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
)
from packages.shared.validation.weekly_update import validate_weekly_update


def build_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Assemble a weekly update from retrieved local evidence."""
    evidence = retrieve_relevant_documents(
        base_path=request.data_path,
        query=request.focus,
        limit=request.max_documents,
    )

    if not evidence:
        raise ValueError(
            "No relevant local documents were found. Add markdown files under the data path or adjust the focus."
        )

    # The MVP uses deterministic extraction rules so the workflow stays easy to inspect.
    response = WeeklyUpdateResponse(
        summary=_build_summary(request.focus, evidence),
        wins=_collect_sentences(evidence, ("win", "shipped", "completed", "launched"), 3),
        risks=_collect_sentences(evidence, ("risk", "blocked", "delay", "issue"), 3),
        next_steps=_collect_sentences(evidence, ("next", "follow-up", "plan", "action"), 3),
        evidence=evidence,
    )

    return validate_weekly_update(response)


def _build_summary(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Create a concise operator-facing summary anchored to the top evidence sources."""
    focus_text = focus or "current leadership activity"
    top_sources = ", ".join(item.title for item in evidence[:2])
    return (
        f"Weekly update synthesized from local project evidence about {focus_text}. "
        f"Primary supporting context came from {top_sources}."
    )


def _collect_sentences(
    evidence: list[EvidenceItem],
    keywords: tuple[str, ...],
    limit: int,
) -> list[str]:
    """Pull matching excerpts into a specific output section such as wins or risks."""
    results: list[str] = []
    for item in evidence:
        lowered = item.excerpt.lower()
        if any(keyword in lowered for keyword in keywords):
            results.append(item.excerpt)
        if len(results) >= limit:
            break
    return results
