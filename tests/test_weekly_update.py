from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.retrieval.local_files import retrieve_relevant_documents
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse
from packages.shared.validation.weekly_update import validate_weekly_update


def test_retrieval_returns_sample_markdown() -> None:
    """The sample project note should be discoverable through local retrieval."""
    evidence = retrieve_relevant_documents(
        base_path="data/local_only/projects",
        query="leadership update",
        limit=5,
    )
    assert evidence
    assert evidence[0].source == "director_week_14.md"
    assert evidence[0].line_number >= 1


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


def test_validation_requires_evidence() -> None:
    """Validator should reject responses that are not grounded in retrieved evidence."""
    empty = WeeklyUpdateResponse(
        summary="Short summary",
        wins=[],
        risks=["A risk"],
        next_steps=[],
        evidence=[],
    )
    try:
        validate_weekly_update(empty)
    except ValueError as exc:
        assert "evidence" in str(exc).lower()
    else:
        raise AssertionError("Expected validation to fail without evidence.")
