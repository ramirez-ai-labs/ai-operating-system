from packages.shared.schemas.director_os import WeeklyUpdateResponse


def validate_weekly_update(response: WeeklyUpdateResponse) -> WeeklyUpdateResponse:
    if not response.evidence:
        raise ValueError("Weekly update responses must include at least one evidence item.")

    if len(response.summary.split()) > 35:
        raise ValueError("Weekly update summary must stay concise.")

    if not any((response.wins, response.risks, response.next_steps)):
        raise ValueError(
            "Weekly update must include at least one actionable section populated from evidence."
        )

    return response
