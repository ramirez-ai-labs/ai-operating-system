from packages.shared.orchestration.chief_of_staff import route_request
from packages.shared.schemas.orchestrator import OrchestratorRequest


def test_orchestrator_routes_director_os_prompt() -> None:
    """Leadership-style prompts should route to the Director OS weekly update workflow."""
    response = route_request(
        OrchestratorRequest(
            prompt="Prepare my leadership weekly update",
            data_path="data/local_only/projects",
            max_documents=5,
        )
    )
    assert response.selected_workflow == "director_os.weekly_update"
    assert response.result.wins


def test_orchestrator_supports_explicit_workflow_override() -> None:
    """Callers should be able to pick the workflow directly when they know the target."""
    response = route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            prompt="Ignore the prompt and use the explicit workflow",
            data_path="data/local_only/projects",
        )
    )
    assert response.selected_workflow == "director_os.weekly_update"
    assert "explicitly requested" in response.rationale.lower()


def test_orchestrator_rejects_unknown_workflow() -> None:
    """Unsupported workflow ids should fail fast instead of silently routing elsewhere."""
    try:
        route_request(
            OrchestratorRequest(
                workflow="brand_os.content_draft",
                data_path="data/local_only/projects",
            )
        )
    except ValueError as exc:
        assert "unsupported workflow" in str(exc).lower()
    else:
        raise AssertionError("Expected orchestrator to reject an unknown workflow.")
