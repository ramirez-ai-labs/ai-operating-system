from packages.shared.schemas.interview_os import InterviewBriefResponse
from packages.shared.validation.grounding import validate_grounded_item


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
        validate_grounded_item(item, response.evidence)

    return response
