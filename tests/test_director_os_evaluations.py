import os

from packages.shared.evaluations.director_os import (
    DEFAULT_DIRECTOR_OS_EVALS_PATH,
    load_director_os_eval_cases,
    run_local_director_os_evaluations,
    score_section_minimums,
    score_summary_terms,
)


def test_load_director_os_eval_cases_reads_checked_in_dataset() -> None:
    """The repo should ship a small checked-in eval set for Director OS."""
    cases = load_director_os_eval_cases(DEFAULT_DIRECTOR_OS_EVALS_PATH)
    assert cases
    assert cases[0].id == "leadership-update-baseline"


def test_local_director_os_evaluations_pass_against_sample_data(monkeypatch) -> None:
    """The checked-in sample project notes should satisfy the current evaluation set."""
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    results = run_local_director_os_evaluations()
    assert results
    assert all(result["passed"] for result in results)
    assert os.getenv("LANGSMITH_TRACING") == "true"


def test_score_summary_terms_reports_missing_expected_terms() -> None:
    """Summary scoring should make it obvious when a case missed required language."""
    result = score_summary_terms(
        outputs={"summary": "Weekly update synthesized from local project evidence."},
        reference_outputs={"required_summary_terms": ["leadership update"]},
    )
    assert not result["score"]
    assert "leadership update" in result["comment"]


def test_score_section_minimums_reports_thin_sections() -> None:
    """Section-count scoring should flag when a response is too thin for the case."""
    result = score_section_minimums(
        outputs={"wins": [], "risks": [], "next_steps": [{}]},
        reference_outputs={
            "minimum_section_counts": {"wins": 1, "risks": 1, "next_steps": 2}
        },
    )
    assert not result["score"]
    assert "wins" in result["comment"]
    assert "next_steps" in result["comment"]
