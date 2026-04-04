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
