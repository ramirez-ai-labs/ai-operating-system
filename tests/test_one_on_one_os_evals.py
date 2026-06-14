"""Tests for the One-on-One OS evaluation library."""

from __future__ import annotations

from packages.shared.evaluations.one_on_one_os import (
    load_one_on_one_os_eval_cases,
    run_local_one_on_one_os_evaluations,
    score_one_on_one_expected_sources,
    score_one_on_one_grounding,
    score_one_on_one_section_minimums,
    score_one_on_one_source_diversity,
    score_one_on_one_summary_terms,
)


def test_load_one_on_one_os_eval_cases_returns_cases() -> None:
    cases = load_one_on_one_os_eval_cases()
    assert len(cases) >= 1
    for case in cases:
        assert case.id
        assert case.inputs.data_path


def test_run_local_one_on_one_os_evaluations_all_pass() -> None:
    results = run_local_one_on_one_os_evaluations()
    failed = [r["case_id"] for r in results if not r["passed"]]
    assert not failed, f"One-on-One OS eval cases failed: {failed}"


def test_score_summary_terms_passes() -> None:
    result = score_one_on_one_summary_terms(
        outputs={"meeting_summary": "One-on-One OS brief for meeting with Sarah."},
        reference_outputs={"required_summary_terms": ["One-on-One OS brief"]},
    )
    assert result["score"] is True


def test_score_summary_terms_fails_when_missing() -> None:
    result = score_one_on_one_summary_terms(
        outputs={"meeting_summary": "Generic meeting notes."},
        reference_outputs={"required_summary_terms": ["One-on-One OS brief"]},
    )
    assert result["score"] is False


def test_score_expected_sources_passes() -> None:
    result = score_one_on_one_expected_sources(
        outputs={"evidence": [{"source": "1on1_sarah_sre_lead.md", "line_number": 1}]},
        reference_outputs={"expected_evidence_sources": ["1on1_sarah_sre_lead.md"]},
    )
    assert result["score"] is True


def test_score_section_minimums_passes() -> None:
    result = score_one_on_one_section_minimums(
        outputs={
            "action_items": [{"text": "A1"}],
            "talking_points": [],
            "blockers": [],
            "kudos": [],
        },
        reference_outputs={"minimum_section_counts": {"action_items": 1}},
    )
    assert result["score"] is True


def test_score_section_minimums_fails() -> None:
    result = score_one_on_one_section_minimums(
        outputs={"action_items": [], "talking_points": [], "blockers": [], "kudos": []},
        reference_outputs={"minimum_section_counts": {"action_items": 1}},
    )
    assert result["score"] is False


def test_score_source_diversity_passes() -> None:
    result = score_one_on_one_source_diversity(
        outputs={
            "evidence": [{"source": "a.md"}, {"source": "b.md"}]
        },
        reference_outputs={"expected_min_source_count": 2},
    )
    assert result["score"] is True


def test_score_grounding_fails_when_source_missing() -> None:
    result = score_one_on_one_grounding(
        outputs={
            "action_items": [{"text": "Do thing", "source": "", "line_number": 3}],
            "talking_points": [],
            "blockers": [],
            "kudos": [],
        },
        reference_outputs={},
    )
    assert result["score"] is False
