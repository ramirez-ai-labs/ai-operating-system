import inspect
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from packages.shared.domains import DOMAINS, DomainSpec
from packages.shared.orchestration.chief_of_staff import route_request
from packages.shared.schemas.director_os import ErrorResponse
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
)

app = FastAPI(
    title="AI Operating System API",
    version="0.1.0",
    description="Local-first multi-domain AI-OS API for workflow execution and orchestration.",
)

# Allow the Next.js dev server (localhost:3000) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_CONSOLE_HTML_PATH = Path(__file__).parent / "templates" / "console.html"


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health check for local development and smoke tests."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def operator_console() -> HTMLResponse:
    """Serve a minimal operator-facing console for trace-first local workflow inspection."""
    return HTMLResponse(_CONSOLE_HTML_PATH.read_text(encoding="utf-8"))


def _register_domain_route(spec: DomainSpec) -> None:
    """Expose one registered domain workflow as a typed POST route.

    The API layer stays intentionally thin: FastAPI parses and validates the
    request against the domain's request model, then hands the typed object to
    the workflow. The real workflow logic lives in the domain graph so it can be
    tested without starting FastAPI.
    """

    def run_domain_workflow(request):
        try:
            return spec.run(request)
        except ValueError as exc:
            # Validation and retrieval failures are returned as client-facing 400 errors.
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # FastAPI reads the signature to build request validation and the OpenAPI
    # schema, so give the shared handler this domain's concrete types.
    run_domain_workflow.__signature__ = inspect.Signature(
        parameters=[
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=spec.request_model,
            )
        ],
        return_annotation=spec.response_model,
    )

    app.add_api_route(
        spec.api_path,
        run_domain_workflow,
        methods=["POST"],
        response_model=spec.response_model,
        responses={400: {"model": ErrorResponse}},
        name=spec.tool.name,
        summary=f"Run {spec.workflow_id}",
        description=spec.tool.description,
    )


for _spec in DOMAINS.values():
    _register_domain_route(_spec)


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
