"""
Shared grounding-validation primitives for all domain validators.

validate_grounded_item, text_is_supported_by_evidence, and meaningful_tokens
were previously copy-pasted into each of the four validation/*.py files. A
single change point here ensures grounding rules stay consistent across
Director OS, Brand OS, Interview OS, and One-on-One OS.
"""
from __future__ import annotations

from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


def validate_grounded_item(item: GroundedItem, evidence: list[EvidenceItem]) -> None:
    """Require each output item to point to a real evidence line."""
    if not item.text.strip():
        raise ValueError("Grounded output items must include text.")

    # Validation uses the evidence list as the source of truth. If an output
    # item points to a source line that is not in the response evidence, the
    # workflow should fail instead of returning an unsupported claim.
    evidence_lookup = {(ev.source, ev.line_number): ev for ev in evidence}
    matched_evidence = evidence_lookup.get((item.source, item.line_number))
    if matched_evidence is None:
        raise ValueError("Grounded output items must reference existing evidence.")

    if not text_is_supported_by_evidence(item.text, matched_evidence.excerpt):
        raise ValueError(
            "Grounded output items must stay semantically anchored to their cited evidence."
        )


def text_is_supported_by_evidence(item_text: str, evidence_excerpt: str) -> bool:
    """Require meaningful lexical overlap between output text and cited evidence.

    This check is intentionally lightweight. It is not trying to "understand"
    language perfectly; it is just making sure the output still resembles the
    evidence it claims to be grounded in.
    """
    item_tokens = set(meaningful_tokens(item_text))
    evidence_tokens = set(meaningful_tokens(evidence_excerpt))

    if not item_tokens or not evidence_tokens:
        return False

    overlap = item_tokens & evidence_tokens
    if len(overlap) < min(2, len(item_tokens)):
        return False

    return len(overlap) / len(item_tokens) >= 0.5


def meaningful_tokens(text: str) -> list[str]:
    """Normalize text into meaningful tokens for lightweight grounding checks.

    Only longer alphanumeric tokens are kept so common filler words such as
    "the" or punctuation do not dominate the overlap calculation.
    """
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return [token for token in cleaned.split() if len(token) > 3]
