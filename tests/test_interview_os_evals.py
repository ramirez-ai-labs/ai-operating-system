"""
Tests for the Interview OS evaluation library.

Exercises the scorer functions and the local eval runner against the
checked-in interview_cases.json without an API key or Ollama.
"""

from __future__ import annotations

from packages.shared.evaluations.interview_os import (
    load_interview_os_eval_cases,
    run_local_interview_os_evaluations,
    score_interview_expected_sources,
    score_interview_grounding,
    score_interview_section_minimums,
    score_interview_source_diversity,
    score_interview_summary_terms,
)


def test_load_interview_os_eval_cases_returns_cases() -> None:
    cases = load_interview_os_eval_cases()
    assert len(cases) >= 1
    for case in cases:
        assert case.id
        assert case.inputs.data_path


def test_run_local_interview_os_evaluations_all_pass() -> None:
    results = run_local_interview_os_evaluations()
    failed = [r["case_id"] for r in results if not r["passed"]]
    assert not failed, f"Interview OS eval cases failed: {failed}"


def test_score_summary_terms_passes_when_all_present() -> None:
    result = score_interview_summary_terms(
        outputs={"candidate_summary": "Interview OS brief for the candidate applying for role."},
        reference_outputs={"required_summary_terms": ["Interview OS brief", "candidate"]},
    )
    assert result["score"] is True


def test_score_summary_terms_fails_when_term_missing() -> None:
    result = score_interview_summary_terms(
        outputs={"candidate_summary": "Some summary without the magic phrase."},
        reference_outputs={"required_summary_terms": ["Interview OS brief"]},
    )
    assert result["score"] is False
    assert "Interview OS brief" in result["comment"]


def test_score_expected_sources_passes_when_all_retrieved() -> None:
    result = score_interview_expected_sources(
        outputs={"evidence": [{"source": "candidate_profile_alex_chen.md", "line_number": 1}]},
        reference_outputs={"expected_evidence_sources": ["candidate_profile_alex_chen.md"]},
    )
    assert result["score"] is True


def test_score_section_minimums_passes_when_met() -> None:
    result = score_interview_section_minimums(
        outputs={"key_questions": [{"text": "Q1"}], "talking_points": [], "red_flags": []},
        reference_outputs={"minimum_section_counts": {"key_questions": 1}},
    )
    assert result["score"] is True


def test_score_section_minimums_fails_when_not_met() -> None:
    result = score_interview_section_minimums(
        outputs={"key_questions": [], "talking_points": [], "red_flags": []},
        reference_outputs={"minimum_section_counts": {"key_questions": 1}},
    )
    assert result["score"] is False


def test_score_source_diversity_passes_when_enough_sources() -> None:
    result = score_interview_source_diversity(
        outputs={
            "evidence": [
                {"source": "a.md", "line_number": 1},
                {"source": "b.md", "line_number": 2},
            ]
        },
        reference_outputs={"expected_min_source_count": 2},
    )
    assert result["score"] is True


def test_score_grounding_fails_when_item_missing_source() -> None:
    result = score_interview_grounding(
        outputs={
            "key_questions": [{"text": "Q?", "source": "", "line_number": 5}],
            "talking_points": [],
            "red_flags": [],
        },
        reference_outputs={},
    )
    assert result["score"] is False
