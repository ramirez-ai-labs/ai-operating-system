from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.director_os import (
    GroundedItem,
    WeeklyUpdateDraft,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
)
from packages.shared.validation.weekly_update import validate_weekly_update


def test_retrieval_returns_sample_markdown() -> None:
    """The sample project note should be discoverable through local retrieval."""
    evidence = retrieve_relevant_documents(
        base_path="data/local_only/projects",
        query="leadership update",
        limit=5,
    )
    assert evidence
    assert evidence[0].source in {
        "director_week_14.md",
        "director_week_15.md",
    }
    assert evidence[0].line_number >= 1
    assert not evidence[0].excerpt.startswith("#")


def test_retrieval_returns_multiple_lines_from_one_file() -> None:
    """A single note should be able to contribute multiple evidence items."""
    evidence = retrieve_relevant_documents(
        base_path="data/local_only/projects",
        query="risk next leadership",
        limit=10,
    )
    excerpts = {item.excerpt for item in evidence}
    assert "Risk: one platform dependency is delayed pending vendor confirmation." in excerpts
    assert "Next: prepare a concise weekly update for the leadership sync on Friday." in excerpts


def test_weekly_update_builds_from_local_data() -> None:
    """The main workflow should return a structured response from sample input data."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership update",
            max_documents=5,
        )
    )
    assert isinstance(result, WeeklyUpdateResponse)
    assert result.evidence
    assert result.summary
    assert result.wins
    assert result.wins[0].source == "director_week_14.md"
    assert result.wins[0].line_number >= 1


def test_weekly_update_without_focus_uses_full_note() -> None:
    """Without a query, the workflow should still populate multiple sections from local notes."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            max_documents=10,
        )
    )
    assert result.wins
    assert result.risks
    assert result.next_steps
    assert {item.source for item in result.wins}.issubset(
        {"director_week_13.md", "director_week_14.md", "director_week_15.md"}
    )


def test_weekly_update_model_path_uses_provider(monkeypatch) -> None:
    """The next phase should support model-assisted synthesis without breaking the API contract."""

    class FakeProvider(WeeklyUpdateProvider):
        def generate_weekly_update(self, focus, evidence):
            return WeeklyUpdateDraft(
                summary="Model-assisted weekly update from grounded evidence.",
                wins=[
                    GroundedItem(
                        text="Win: provider synthesized the wins section.",
                        source=evidence[0].source,
                        line_number=evidence[0].line_number,
                    )
                ],
                risks=[
                    GroundedItem(
                        text="Risk: provider synthesized the risks section.",
                        source=evidence[1].source,
                        line_number=evidence[1].line_number,
                    )
                ],
                next_steps=[
                    GroundedItem(
                        text="Next: provider synthesized the next steps section.",
                        source=evidence[2].source,
                        line_number=evidence[2].line_number,
                    )
                ],
            )

    from director_os.workflows import weekly_update as workflow_module

    monkeypatch.setattr(
        workflow_module,
        "OllamaWeeklyUpdateProvider",
        lambda base_url, model: FakeProvider(),
    )

    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership update",
            max_documents=5,
            use_model=True,
        )
    )
    assert result.summary.startswith("Model-assisted")
    assert result.wins
    assert result.risks
    assert result.next_steps


def test_validation_requires_evidence() -> None:
    """Validator should reject responses that are not grounded in retrieved evidence."""
    empty = WeeklyUpdateResponse(
        summary="Short summary",
        wins=[],
        risks=[
            GroundedItem(
                text="A risk",
                source="missing.md",
                line_number=1,
            )
        ],
        next_steps=[],
        evidence=[],
    )
    try:
        validate_weekly_update(empty)
    except ValueError as exc:
        assert "evidence" in str(exc).lower()
    else:
        raise AssertionError("Expected validation to fail without evidence.")


def test_validation_rejects_missing_evidence_reference() -> None:
    """Validator should reject output items that point to non-existent evidence lines."""
    response = WeeklyUpdateResponse(
        summary="Short summary",
        wins=[
            GroundedItem(
                text="Win: did a thing",
                source="missing.md",
                line_number=99,
            )
        ],
        risks=[],
        next_steps=[],
        evidence=[
            {
                "source": "director_week_14.md",
                "line_number": 3,
                "title": "Director Week 14",
                "excerpt": (
                    "Win: shipped the internal status dashboard "
                    "refresh for leadership review."
                ),
            }
        ],
    )
    try:
        validate_weekly_update(response)
    except ValueError as exc:
        assert "reference existing evidence" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for an invalid evidence reference.")


def test_retrieval_prefers_newer_matching_notes() -> None:
    """Later files should edge out older ones when the relevance score is similar."""
    evidence = retrieve_relevant_documents(
        base_path="data/local_only/projects",
        query="leadership summary",
        limit=5,
    )
    assert evidence
    assert evidence[0].source == "director_week_15.md"


def test_weekly_update_draws_from_multiple_files() -> None:
    """The workflow should be able to synthesize a weekly update from several project notes."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership operating review",
            max_documents=10,
        )
    )
    sources = {item.source for item in result.evidence}
    assert "director_week_15.md" in sources
    assert len(sources) >= 2
