from packages.shared.graphs.director_os import run_weekly_update_graph
from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import GroundedItem, WeeklyUpdateDraft, WeeklyUpdateRequest


def test_director_os_graph_runs_end_to_end() -> None:
    """The graph-backed Director OS workflow should return the same public response shape."""
    result = run_weekly_update_graph(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership update",
            max_documents=5,
        )
    )
    assert result.summary
    assert result.evidence
    assert result.wins


def test_director_os_graph_falls_back_from_ungrounded_model_output(monkeypatch) -> None:
    """The graph should retry with the deterministic path when model output fails validation."""

    class UngroundedProvider(WeeklyUpdateProvider):
        def generate_weekly_update(self, focus, evidence):
            return WeeklyUpdateDraft(
                summary="Model-assisted weekly update from grounded evidence.",
                wins=[
                    GroundedItem(
                        text="Win: calibrated the observatory telescope for a lunar survey.",
                        source=evidence[0].source,
                        line_number=evidence[0].line_number,
                    )
                ],
                risks=[],
                next_steps=[],
            )

    from packages.shared.graphs import director_os as graph_module

    monkeypatch.setattr(
        graph_module,
        "OllamaWeeklyUpdateProvider",
        lambda base_url, model: UngroundedProvider(),
    )

    result = run_weekly_update_graph(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership update",
            max_documents=5,
            use_model=True,
        )
    )
    assert result.summary.startswith("Weekly update synthesized from local project evidence")
    assert result.wins
