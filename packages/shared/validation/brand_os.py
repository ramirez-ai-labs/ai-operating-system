from packages.shared.schemas.brand_os import BrandContentDraftResponse
from packages.shared.schemas.director_os import GroundedItem


def validate_brand_content_draft(
    response: BrandContentDraftResponse,
) -> BrandContentDraftResponse:
    """Enforce basic guardrails so Brand OS returns usable, grounded content drafts."""
    if not response.evidence:
        raise ValueError("Brand OS responses must include at least one evidence item.")

    if len(response.insight_summary.split()) > 35:
        raise ValueError("Brand OS insight_summary must stay concise.")

    if not any((response.post_outline, response.podcast_angles, response.repo_improvements)):
        raise ValueError(
            "Brand OS content draft must include at least one populated section."
        )

    all_items = response.post_outline + response.podcast_angles + response.repo_improvements
    for item in all_items:
        _validate_grounded_item(item, response)

    return response


def _validate_grounded_item(
    item: GroundedItem,
    response: BrandContentDraftResponse,
) -> None:
    """Require each output item to point to a real evidence line."""
    if not item.text.strip():
        raise ValueError("Grounded output items must include text.")

    evidence_lookup = {
        (ev.source, ev.line_number): ev for ev in response.evidence
    }
    evidence = evidence_lookup.get((item.source, item.line_number))
    if evidence is None:
        raise ValueError("Grounded output items must reference existing evidence.")

    if not _text_is_supported_by_evidence(item.text, evidence.excerpt):
        raise ValueError(
            "Grounded output items must stay semantically anchored to their cited evidence."
        )


def _text_is_supported_by_evidence(item_text: str, evidence_excerpt: str) -> bool:
    item_tokens = set(_meaningful_tokens(item_text))
    evidence_tokens = set(_meaningful_tokens(evidence_excerpt))
    if not item_tokens or not evidence_tokens:
        return False
    overlap = item_tokens & evidence_tokens
    if len(overlap) < min(2, len(item_tokens)):
        return False
    return len(overlap) / len(item_tokens) >= 0.5


def _meaningful_tokens(text: str) -> list[str]:
    cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
    return [t for t in cleaned.split() if len(t) > 3]
