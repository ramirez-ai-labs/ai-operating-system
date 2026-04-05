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


def build_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Assemble a weekly update from retrieved local evidence."""
    # Step 1: gather the local evidence that the workflow is allowed to use.
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
    draft = _build_draft(request, evidence)

    # Step 3: attach the evidence list to the structured draft before the
    # validator checks that every output item is properly grounded.
    response = WeeklyUpdateResponse(
        summary=draft.summary,
        wins=draft.wins,
        risks=draft.risks,
        next_steps=draft.next_steps,
        evidence=evidence,
    )

    try:
        return validate_weekly_update(response)
    except ValueError:
        if not request.use_model or not request.fallback_to_deterministic:
            raise

    fallback_draft = _build_deterministic_draft(request.focus, evidence)
    fallback_response = WeeklyUpdateResponse(
        summary=fallback_draft.summary,
        wins=fallback_draft.wins,
        risks=fallback_draft.risks,
        next_steps=fallback_draft.next_steps,
        evidence=evidence,
    )
    return validate_weekly_update(fallback_response)


def _build_draft(
    request: WeeklyUpdateRequest,
    evidence: list[EvidenceItem],
) -> WeeklyUpdateDraft:
    """Select the deterministic or model-assisted draft path for the workflow."""
    return (
        _build_model_draft(request, evidence)
        if request.use_model
        else _build_deterministic_draft(request.focus, evidence)
    )


def _build_deterministic_draft(
    focus: str | None,
    evidence: list[EvidenceItem],
) -> WeeklyUpdateDraft:
    """Build a predictable draft directly from evidence lines."""
    # This path is easy to reason about because every output line comes
    # straight from retrieved evidence instead of model generation.
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
    # Provider construction is kept local to the workflow so later we can swap
    # in a different provider without changing the API layer.
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

    # Fallback keeps the workflow reliable when Ollama is unavailable or returns
    # an under-specified response.
    return _build_deterministic_draft(request.focus, evidence)


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
) -> list[GroundedItem]:
    """Pull grounded excerpts into a specific output section such as wins or risks."""
    results: list[GroundedItem] = []
    for item in evidence:
        lowered = item.excerpt.lower()
        if any(keyword in lowered for keyword in keywords):
            # Each returned item keeps the source line so later validation can
            # prove the output came from real evidence.
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


def _validate_model_draft(draft: WeeklyUpdateDraft) -> None:
    """Reject weak model drafts so they do not bypass the deterministic baseline."""
    # Model output is optional in this project, so it only wins if it is at
    # least as usable as the deterministic baseline.
    if not draft.summary.strip():
        raise ValueError("Model-generated weekly update summary cannot be empty.")

    if not any((draft.wins, draft.risks, draft.next_steps)):
        raise ValueError(
            "Model-generated weekly update must include at least one actionable section."
        )
