from packages.shared.providers.ollama import OllamaWeeklyUpdateProvider
from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.director_os import (
    EvidenceItem,
    WeeklyUpdateDraft,
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
            "No relevant local documents were found. "
            "Add markdown files under the data path or adjust the focus."
        )

    # The deterministic path remains the default so the MVP stays stable even
    # without a local model runtime. Ollama is opt-in for the next phase.
    draft = (
        _build_model_draft(request, evidence)
        if request.use_model
        else _build_deterministic_draft(request.focus, evidence)
    )

    response = WeeklyUpdateResponse(
        summary=draft.summary,
        wins=draft.wins,
        risks=draft.risks,
        next_steps=draft.next_steps,
        evidence=evidence,
    )

    return validate_weekly_update(response)


def _build_deterministic_draft(
    focus: str | None,
    evidence: list[EvidenceItem],
) -> WeeklyUpdateDraft:
    """Build a predictable draft directly from evidence lines."""
    return WeeklyUpdateDraft(
        summary=_build_summary(focus, evidence),
        wins=_collect_sentences(evidence, ("win", "shipped", "completed", "launched"), 3),
        risks=_collect_sentences(evidence, ("risk", "blocked", "delay", "issue"), 3),
        next_steps=_collect_sentences(evidence, ("next", "follow-up", "plan", "action"), 3),
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
    return provider.generate_weekly_update(request.focus, evidence)


def _build_summary(focus: str | None, evidence: list[EvidenceItem]) -> str:
    """Create a concise operator-facing summary anchored to the top evidence sources."""
    focus_text = focus or "current leadership activity"
    # Deduplicate titles because line-level evidence can now yield several
    # entries from the same source file.
    top_source_titles = list(dict.fromkeys(item.title for item in evidence))
    top_sources = ", ".join(top_source_titles[:2])
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
