from packages.shared.schemas.brand_os import BrandContentDraftResponse
from packages.shared.validation.grounding import validate_grounded_item


def validate_brand_content_draft(
    response: BrandContentDraftResponse,
) -> BrandContentDraftResponse:
    """Enforce basic guardrails so Brand OS returns usable, grounded content drafts."""
    if not response.evidence:
        raise ValueError("Brand OS responses must include at least one evidence item.")

    if len(response.insight_summary.split()) > 35:
        raise ValueError("Brand OS insight_summary must stay concise.")

    if not any((response.post_outline, response.podcast_angles, response.repo_improvements)):
        raise ValueError(
            "Brand OS content draft must include at least one populated section."
        )

    all_items = response.post_outline + response.podcast_angles + response.repo_improvements
    for item in all_items:
        validate_grounded_item(item, response.evidence)

    return response
