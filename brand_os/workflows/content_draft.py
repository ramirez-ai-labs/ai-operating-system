from packages.shared.graphs.brand_os import run_content_draft_graph
from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse


def build_content_draft(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
    """Run the Brand OS content-draft graph behind the stable public API."""
    return run_content_draft_graph(request)
