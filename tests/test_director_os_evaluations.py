import os

import pytest

from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.evaluations.director_os import (
    DEFAULT_DIRECTOR_OS_EVALS_PATH,
    DETERMINISTIC_SUMMARY_PREFIX,
    load_director_os_eval_cases,
    run_director_os_eval_target,
    run_local_director_os_evaluations,
    score_expected_summary_mode,
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
    assert any(case.provider_scenario == "provider_failure" for case in cases)


def test_local_director_os_evaluations_pass_against_sample_data(monkeypatch) -> None:
    """The checked-in sample project notes should satisfy the current evaluation set."""
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    results = run_local_director_os_evaluations()
    assert results
    assert all(result["passed"] for result in results)
    assert os.getenv("LANGSMITH_TRACING") == "true"


def test_eval_target_supports_provider_failure_scenarios() -> None:
    """The eval target should support deterministic fake-provider scenarios without Ollama."""
    result = run_director_os_eval_target(
        {
            "data_path": "data/local_only/projects",
            "focus": "leadership update",
            "max_documents": 5,
            "use_model": True,
            "fallback_to_deterministic": True,
            "provider_scenario": "provider_failure",
        }
    )
    assert result["summary"].startswith(DETERMINISTIC_SUMMARY_PREFIX)
    assert result["wins"]


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


def test_score_expected_summary_mode_detects_missing_fallback() -> None:
    """Summary-mode scoring should flag cases that expected deterministic fallback."""
    result = score_expected_summary_mode(
        outputs={"summary": "Model-assisted weekly update from grounded evidence."},
        reference_outputs={"expected_deterministic_summary": True},
    )
    assert not result["score"]
    assert "deterministic fallback" in result["comment"].lower()


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


# --- Claude provider tests (require ANTHROPIC_API_KEY) ---

_claude_key_available = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live Claude tests",
)


@_claude_key_available
def test_claude_provider_returns_grounded_weekly_update() -> None:
    """Claude should produce a non-empty structured update grounded in local evidence."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="leadership update",
            max_documents=5,
            use_model=True,
            provider="claude",
        )
    )
    assert result.summary
    assert result.evidence
    assert any((result.wins, result.risks, result.next_steps))


@_claude_key_available
def test_claude_provider_citations_stay_within_retrieved_evidence() -> None:
    """Every grounded item Claude returns must cite a source that was in the evidence."""
    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            max_documents=5,
            use_model=True,
            provider="claude",
        )
    )
    evidence_locations = {(e.source, e.line_number) for e in result.evidence}
    all_items = result.wins + result.risks + result.next_steps
    for item in all_items:
        assert (item.source, item.line_number) in evidence_locations, (
            f"Claude cited {item.source}:{item.line_number} which is not in the retrieved evidence"
        )


@_claude_key_available
def test_claude_provider_eval_cases_pass_existing_scorers() -> None:
    """Eval cases run through the Claude provider should satisfy the checked-in scorers."""
    from scripts.run_director_os_evals import _apply_provider_override
    from packages.shared.evaluations.director_os import (
        load_director_os_eval_cases,
        run_local_director_os_evaluations,
    )
    all_cases = load_director_os_eval_cases()
    claude_cases = _apply_provider_override(all_cases, "claude")
    assert claude_cases, "Expected at least one non-scenario case for the Claude provider run"
    results = run_local_director_os_evaluations(claude_cases)
    failed = [r["case_id"] for r in results if not r["passed"]]
    assert not failed, f"Claude provider eval cases failed: {failed}"
