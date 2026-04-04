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
    return {"status": "ok"}


@app.post(
    "/director-os/weekly-update",
    response_model=WeeklyUpdateResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    try:
        return build_weekly_update(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
