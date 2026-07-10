"""
Shared grounding primitives for all domain providers.

Both the JSON schema fragment (GROUNDED_ITEM_SCHEMA) and the validation
function (parse_grounded_items) were previously copy-pasted into each of the
five provider files. A single change point here ensures grounding rules stay
consistent across Director OS, Brand OS, Interview OS, One-on-One OS, and
the Ollama provider.
"""
from __future__ import annotations

from packages.shared.schemas.director_os import EvidenceItem, GroundedItem  # noqa: F401

GROUNDED_ITEM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "source": {"type": "string", "description": "Exact source filename from the evidence."},
        "line_number": {"type": "integer", "description": "Exact line_number from the evidence."},
    },
    "required": ["text", "source", "line_number"],
}


def parse_grounded_items(
    items: list[dict[str, object]],
    evidence_locations: set[tuple[str, int]],
) -> list[GroundedItem]:
    """
    Parse model-returned grounded items and reject any citation not in evidence.

    Args:
        items:              raw dicts from the model's tool_use output
        evidence_locations: set of (source, line_number) pairs built from the
                            retrieved EvidenceItem list — pre-built by the
                            caller so it can be reused across multiple sections

    Raises:
        ValueError: if an item is not a dict, or cites a source/line that does
                    not appear in the retrieved evidence
    """
    grounded: list[GroundedItem] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("Model returned a malformed grounded item.")
        # `.get(..., 0)` only substitutes the default when the key is absent —
        # an explicit `"line_number": null` still yields None here, and
        # int(None) raises TypeError rather than the ValueError callers
        # expect. Normalize both cases explicitly.
        raw_line_number = raw.get("line_number")
        try:
            line_number = int(raw_line_number) if raw_line_number is not None else 0
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Model returned a non-numeric line_number: {raw_line_number!r}"
            ) from exc
        item = GroundedItem(
            text=str(raw.get("text", "")),
            source=str(raw.get("source", "")),
            line_number=line_number,
        )
        if (item.source, item.line_number) not in evidence_locations:
            raise ValueError(
                f"Model cited evidence not in the retrieved context: "
                f"{item.source}:{item.line_number}"
            )
        grounded.append(item)
    return grounded
