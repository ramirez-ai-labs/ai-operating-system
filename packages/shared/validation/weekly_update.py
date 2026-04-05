from packages.shared.schemas.director_os import GroundedItem, WeeklyUpdateResponse


def validate_weekly_update(response: WeeklyUpdateResponse) -> WeeklyUpdateResponse:
    """Enforce basic guardrails so the workflow returns usable, grounded output."""
    if not response.evidence:
        raise ValueError("Weekly update responses must include at least one evidence item.")

    if len(response.summary.split()) > 35:
        raise ValueError("Weekly update summary must stay concise.")

    # At least one actionable section must be populated from retrieved evidence.
    if not any((response.wins, response.risks, response.next_steps)):
        raise ValueError(
            "Weekly update must include at least one actionable section populated from evidence."
        )

    for item in response.wins + response.risks + response.next_steps:
        _validate_grounded_item(item, response)

    return response


def _validate_grounded_item(
    item: GroundedItem,
    response: WeeklyUpdateResponse,
) -> None:
    """Require each output item to point to a real evidence line."""
    if not item.text.strip():
        raise ValueError("Grounded output items must include text.")

    # Validation uses the evidence list as the source of truth. If an output
    # item points to a source line that is not in the response evidence, the
    # workflow should fail instead of returning an unsupported claim.
    evidence_lookup = {
        (evidence.source, evidence.line_number): evidence for evidence in response.evidence
    }
    evidence = evidence_lookup.get((item.source, item.line_number))
    if evidence is None:
        raise ValueError("Grounded output items must reference existing evidence.")

    if not _text_is_supported_by_evidence(item.text, evidence.excerpt):
        raise ValueError(
            "Grounded output items must stay semantically anchored to their cited evidence."
        )


def _text_is_supported_by_evidence(item_text: str, evidence_excerpt: str) -> bool:
    """Require meaningful lexical overlap between output text and cited evidence."""
    item_tokens = set(_meaningful_tokens(item_text))
    evidence_tokens = set(_meaningful_tokens(evidence_excerpt))

    if not item_tokens or not evidence_tokens:
        return False

    overlap = item_tokens & evidence_tokens
    if len(overlap) < min(2, len(item_tokens)):
        return False

    overlap_ratio = len(overlap) / len(item_tokens)
    return overlap_ratio >= 0.5


def _meaningful_tokens(text: str) -> list[str]:
    """Normalize text into meaningful tokens for lightweight grounding checks."""
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return [token for token in cleaned.split() if len(token) > 3]
