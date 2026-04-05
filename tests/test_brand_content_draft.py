from brand_os.workflows.content_draft import build_content_draft
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)


def test_brand_content_draft_builds_from_local_notes() -> None:
    """Brand OS should turn local notes into a grounded content draft."""
    result = build_content_draft(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai workflow",
            max_documents=5,
        )
    )
    assert isinstance(result, BrandContentDraftResponse)
    assert result.insight_summary
    assert result.post_outline
    assert result.evidence


def test_brand_content_draft_rejects_missing_local_notes() -> None:
    """Brand OS should fail clearly if there is no usable local source data."""
    try:
        build_content_draft(
            BrandContentDraftRequest(
                data_path="data/local_only/missing-brand",
                focus="podcast",
            )
        )
    except ValueError as exc:
        assert "data path does not exist" in str(exc).lower()
    else:
        raise AssertionError("Expected Brand OS draft generation to fail for a missing path.")
