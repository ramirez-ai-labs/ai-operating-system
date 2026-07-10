from packages.shared.schemas.one_on_one_os import OneOnOneResponse
from packages.shared.validation.grounding import validate_grounded_item


def validate_meeting_brief(response: OneOnOneResponse) -> OneOnOneResponse:
    """Enforce basic guardrails so One-on-One OS returns usable, grounded briefs."""
    if not response.evidence:
        raise ValueError("One-on-One OS responses must include at least one evidence item.")

    if len(response.meeting_summary.split()) > 35:
        raise ValueError("One-on-One OS meeting_summary must stay concise.")

    if not any((response.action_items, response.talking_points, response.blockers, response.kudos)):
        raise ValueError(
            "Meeting brief must include at least one populated section."
        )

    all_items = (
        response.action_items + response.talking_points + response.blockers + response.kudos
    )
    for item in all_items:
        validate_grounded_item(item, response.evidence)

    return response
