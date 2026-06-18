from packages.shared.schemas.director_os import GroundedItem
from packages.shared.schemas.interview_os import InterviewBriefResponse


def validate_interview_brief(response: InterviewBriefResponse) -> InterviewBriefResponse:
    """Enforce basic guardrails so Interview OS returns usable, grounded briefs."""
    if not response.evidence:
        raise ValueError("Interview OS responses must include at least one evidence item.")

    if len(response.candidate_summary.split()) > 35:
        raise ValueError("Interview OS candidate_summary must stay concise.")

    if not any((response.key_questions, response.talking_points, response.red_flags)):
        raise ValueError(
            "Interview brief must include at least one populated section."
        )

    all_items = response.key_questions + response.talking_points + response.red_flags
    for item in all_items:
        _validate_grounded_item(item, response)

    return response


def _validate_grounded_item(
    item: GroundedItem,
    response: InterviewBriefResponse,
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
