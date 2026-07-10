from packages.shared.schemas.director_os import WeeklyUpdateResponse
from packages.shared.validation.grounding import validate_grounded_item


def validate_weekly_update(response: WeeklyUpdateResponse) -> WeeklyUpdateResponse:
    """Enforce basic guardrails so the workflow returns usable, grounded output."""
    # Validation is the final quality gate. By this point the workflow has
    # already produced a response, and this function decides whether it is safe
    # enough to return to the caller.
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
        validate_grounded_item(item, response.evidence)

    return response
