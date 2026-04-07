from packages.shared.orchestration.chief_of_staff import route_request
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem, WeeklyUpdateResponse
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
    assert "leadership" in response.rationale.lower()
    assert response.result.wins
    assert response.trace.evidence_count == len(response.result.evidence)
    assert response.trace.section_counts["wins"] == len(response.result.wins)
    assert not response.trace.fallback_used


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
    assert response.trace.focus_used == "Ignore the prompt and use the explicit workflow"


def test_orchestrator_routes_brand_os_prompt() -> None:
    """Brand-oriented prompts should route into the first Brand OS workflow."""
    response = route_request(
        OrchestratorRequest(
            prompt="Turn this work into a podcast and LinkedIn content draft",
            data_path="data/local_only/brand",
            max_documents=5,
        )
    )
    assert response.selected_workflow == "brand_os.content_draft"
    assert "podcast" in response.rationale.lower()
    assert response.result.post_outline
    assert not response.trace.model_supported
    assert response.trace.section_counts["post_outline"] == len(response.result.post_outline)


def test_orchestrator_defaults_to_director_when_prompt_is_missing() -> None:
    """A missing prompt should fall back to the default Director OS workflow."""
    response = route_request(
        OrchestratorRequest(
            prompt=None,
            data_path="data/local_only/projects",
            max_documents=5,
        )
    )
    assert response.selected_workflow == "director_os.weekly_update"
    assert "default workflow" in response.rationale.lower()


def test_orchestrator_reports_director_fallback_in_trace(monkeypatch) -> None:
    """The trace should make deterministic fallback visible to the operator."""
    from packages.shared.orchestration import chief_of_staff as orchestration_module

    def fake_weekly_update(_request):
        return WeeklyUpdateResponse(
            summary=(
                "Weekly update synthesized from local project evidence about leadership update. "
                "Primary supporting context came from Director Week 14."
            ),
            wins=[
                GroundedItem(
                    text=(
                        "Win: shipped the internal status dashboard refresh "
                        "for leadership review."
                    ),
                    source="director_week_14.md",
                    line_number=3,
                )
            ],
            risks=[],
            next_steps=[],
            evidence=[
                EvidenceItem(
                    source="director_week_14.md",
                    line_number=3,
                    title="Director Week 14",
                    excerpt=(
                        "Win: shipped the internal status dashboard refresh "
                        "for leadership review."
                    ),
                )
            ],
        )

    monkeypatch.setattr(orchestration_module, "build_weekly_update", fake_weekly_update)

    response = route_request(
        OrchestratorRequest(
            workflow="director_os.weekly_update",
            data_path="data/local_only/projects",
            focus="leadership update",
            use_model=True,
        )
    )
    assert response.trace.model_requested
    assert response.trace.fallback_used
    assert not response.trace.model_used



def test_orchestrator_rejects_unknown_workflow() -> None:
    """Unsupported workflow ids should fail fast instead of silently routing elsewhere."""
    try:
        route_request(
            OrchestratorRequest(
                workflow="engineering_os.repo_review",
                data_path="data/local_only/projects",
            )
        )
    except ValueError as exc:
        assert "unsupported workflow" in str(exc).lower()
    else:
        raise AssertionError("Expected orchestrator to reject an unknown workflow.")
