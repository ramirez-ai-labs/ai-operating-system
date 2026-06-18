import packages.shared.graphs.director_os as graph_module
from packages.shared.graphs.director_os import _build_model_draft, run_weekly_update_graph
from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import (
    EvidenceItem,
    GroundedItem,
    WeeklyUpdateDraft,
    WeeklyUpdateRequest,
)


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


_FAKE_EVIDENCE = [
    EvidenceItem(source="notes.md", line_number=1, title="Note", excerpt="Win: shipped v2")
]

_FAKE_USAGE = {"input_tokens": 42, "output_tokens": 7}


def test_ghost_tokens_captured_when_validate_rejects_draft(monkeypatch) -> None:
    """Usage from a successful API call must be returned even when _validate_model_draft rejects."""

    class WeakDraftProvider(WeeklyUpdateProvider):
        def generate_weekly_update(self, focus, evidence):
            # Returns a draft with no sections — _validate_model_draft will raise.
            return WeeklyUpdateDraft(summary="ok", wins=[], risks=[], next_steps=[])

        def get_last_usage(self):
            return _FAKE_USAGE

    monkeypatch.setattr(graph_module, "_build_provider", lambda req: WeakDraftProvider())

    request = WeeklyUpdateRequest(
        data_path="data/local_only/projects",
        use_model=True,
        fallback_to_deterministic=True,
    )
    _, usage = _build_model_draft(request, _FAKE_EVIDENCE)
    assert usage == _FAKE_USAGE


def test_ghost_tokens_captured_when_generate_raises_after_api_call(monkeypatch) -> None:
    """Usage set before a ValueError in generate_weekly_update must survive the fallback."""

    class FailAfterCallProvider(WeeklyUpdateProvider):
        def __init__(self):
            self._usage: dict[str, int] = {}

        def generate_weekly_update(self, focus, evidence):
            # Simulates: API call succeeds, usage recorded, then response parsing fails.
            self._usage = _FAKE_USAGE
            raise ValueError("bad response from model")

        def get_last_usage(self):
            return self._usage

    monkeypatch.setattr(graph_module, "_build_provider", lambda req: FailAfterCallProvider())

    request = WeeklyUpdateRequest(
        data_path="data/local_only/projects",
        use_model=True,
        fallback_to_deterministic=True,
    )
    _, usage = _build_model_draft(request, _FAKE_EVIDENCE)
    assert usage == _FAKE_USAGE
