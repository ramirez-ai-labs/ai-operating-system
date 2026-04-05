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
    evidence_locations = {
        (evidence.source, evidence.line_number) for evidence in response.evidence
    }
    if (item.source, item.line_number) not in evidence_locations:
        raise ValueError("Grounded output items must reference existing evidence.")
