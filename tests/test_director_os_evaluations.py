import os

from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.evaluations.director_os import (
    DEFAULT_DIRECTOR_OS_EVALS_PATH,
    load_director_os_eval_cases,
    run_local_director_os_evaluations,
    score_section_minimums,
    score_section_prefix_purity,
    score_summary_terms,
)
from packages.shared.schemas.director_os import WeeklyUpdateRequest


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


def test_score_section_prefix_purity_reports_cross_section_leaks() -> None:
    """Section purity scoring should catch prefixed items in the wrong section."""
    result = score_section_prefix_purity(
        outputs={
            "wins": [{"text": "Win: shipped the dashboard refresh."}],
            "risks": [{"text": "Risk: a vendor approval is still pending."}],
            "next_steps": [{"text": "Risk: one launch milestone may slip into next week."}],
        },
        reference_outputs={},
    )
    assert not result["score"]
    assert "next_steps" in result["comment"]


def test_deterministic_weekly_update_keeps_prefixed_items_in_matching_sections() -> None:
    """The deterministic draft should not leak risk-prefixed lines into next steps."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            max_documents=10,
        )
    )
    assert all(item.text.startswith("Win:") for item in result.wins)
    assert all(item.text.startswith("Risk:") for item in result.risks)
    assert all(item.text.startswith("Next:") for item in result.next_steps)
