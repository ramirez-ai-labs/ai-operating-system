"""Merge-time grounding validation for plan steps.

Each domain graph already validates its own response. The supervisor checks
again when merging, against the same shared grounding rules, so the merged plan
response can never carry an uncited item — even if a workflow is swapped,
patched, or regresses. The check is generic: it collects every GroundedItem
field on any domain response, so new domains need no changes here.
"""

from __future__ import annotations

from packages.shared.schemas.base import BaseResponse, GroundedItem
from packages.shared.validation.grounding import validate_grounded_item


def grounded_items(result: BaseResponse) -> list[GroundedItem]:
    """Every GroundedItem in a domain response, across all of its list sections."""
    items: list[GroundedItem] = []
    for field_name in type(result).model_fields:
        value = getattr(result, field_name)
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, GroundedItem))
    return items


def validate_step_grounding(result: BaseResponse) -> int:
    """Validate one step's result. Returns the number of grounded items checked."""
    if not result.evidence:
        raise ValueError("Step result has no evidence.")
    items = grounded_items(result)
    if not items:
        raise ValueError("Step result has no grounded items.")
    for item in items:
        validate_grounded_item(item, result.evidence)
    return len(items)
