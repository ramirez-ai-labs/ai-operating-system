from fastapi import FastAPI, HTTPException

from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.schemas.director_os import (
    ErrorResponse,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
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
        # The API layer stays intentionally thin. The real workflow logic lives
        # in Director OS so it can be tested without starting FastAPI.
        return build_weekly_update(request)
    except ValueError as exc:
        # Validation and retrieval failures are returned as client-facing 400 errors.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
