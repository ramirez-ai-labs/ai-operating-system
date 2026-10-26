from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse
from packages.shared.validation.grounding import validate_grounded_item


def validate_interview_brief(
    response: InterviewBriefResponse,
    request: InterviewBriefRequest | None = None,
) -> InterviewBriefResponse:
    """Enforce basic guardrails so Interview OS returns usable, grounded briefs.

    `request` only shapes the empty-brief error message; it never relaxes a check.
    """
    if not response.evidence:
        raise ValueError("Interview OS responses must include at least one evidence item.")

    if len(response.candidate_summary.split()) > 35:
        raise ValueError("Interview OS candidate_summary must stay concise.")

    if not any((response.key_questions, response.talking_points, response.red_flags)):
        raise ValueError(_empty_brief_message(request))

    all_items = response.key_questions + response.talking_points + response.red_flags
    for item in all_items:
        validate_grounded_item(item, response.evidence)

    return response


def _empty_brief_message(request: InterviewBriefRequest | None) -> str:
    """Point the caller at the fix that applies to the request they actually sent."""
    prefix = "Interview brief must include at least one populated section. "
    if request is not None and (request.focus or request.candidate_name or request.role):
        return (
            prefix
            + "No retrieved line matched a question, talking point, or red flag for this "
            "focus, candidate_name, and role. Broaden them or raise max_documents."
        )
    return (
        prefix
        + "Set focus, candidate_name, or role so retrieval can target the right notes, "
        "or raise max_documents."
    )
