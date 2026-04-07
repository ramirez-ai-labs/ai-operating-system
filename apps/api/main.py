from fastapi import FastAPI, HTTPException

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.orchestration.chief_of_staff import route_request
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import (
    ErrorResponse,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
)
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
)

app = FastAPI(
    title="AI Operating System API",
    version="0.1.0",
    description="Minimal Director OS MVP for local weekly update generation.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health check for local development and smoke tests."""
    return {"status": "ok"}


@app.post(
    "/director-os/weekly-update",
    response_model=WeeklyUpdateResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Run the Director OS weekly update workflow against local project notes."""
    try:
        # FastAPI handles HTTP parsing and validation for us. After that, the
        # route simply hands the typed request object to the workflow layer.
        # The API layer stays intentionally thin. The real workflow logic lives
        # in Director OS so it can be tested without starting FastAPI.
        return build_weekly_update(request)
    except ValueError as exc:
        # Validation and retrieval failures are returned as client-facing 400 errors.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/brand-os/content-draft",
    response_model=BrandContentDraftResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_brand_content_draft(
    request: BrandContentDraftRequest,
) -> BrandContentDraftResponse:
    """Run the Brand OS content-draft workflow against local brand notes."""
    try:
        return build_content_draft(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/orchestrate",
    response_model=OrchestratorResponse,
    responses={400: {"model": ErrorResponse}},
)
def orchestrate(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route a request through the lightweight Chief of Staff layer."""
    try:
        # This endpoint shows the "AI-OS" idea at a higher level: the caller
        # sends one generic request, and the orchestrator decides which domain
        # workflow should handle it.
        return route_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
