from packages.shared.evaluations.brand_os import (
    DEFAULT_BRAND_OS_EVALS_PATH,
    load_brand_os_eval_cases,
    run_local_brand_os_evaluations,
    score_brand_section_minimums,
    score_brand_summary_terms,
)


def test_load_brand_os_eval_cases_reads_checked_in_dataset() -> None:
    """The repo should ship a small checked-in eval set for Brand OS."""
    cases = load_brand_os_eval_cases(DEFAULT_BRAND_OS_EVALS_PATH)
    assert cases
    assert cases[0].id == "local-first-content-baseline"


def test_local_brand_os_evaluations_pass_against_sample_data() -> None:
    """The checked-in brand notes should satisfy the current Brand OS eval set."""
    results = run_local_brand_os_evaluations()
    assert results
    assert all(result["passed"] for result in results)


def test_brand_summary_term_scoring_reports_missing_terms() -> None:
    """Summary scoring should flag when Brand OS misses a required phrase."""
    result = score_brand_summary_terms(
        outputs={"insight_summary": "Brand OS draft synthesized from local evidence."},
        reference_outputs={"required_summary_terms": ["local-first ai workflow"]},
    )
    assert not result["score"]
    assert "local-first ai workflow" in result["comment"]


def test_brand_section_minimum_scoring_reports_thin_sections() -> None:
    """Section-count scoring should make sparse Brand OS output obvious."""
    result = score_brand_section_minimums(
        outputs={
            "post_outline": [],
            "podcast_angles": [{}],
            "repo_improvements": [],
        },
        reference_outputs={
            "minimum_section_counts": {
                "post_outline": 1,
                "podcast_angles": 2,
                "repo_improvements": 1,
            }
        },
    )
    assert not result["score"]
    assert "post_outline" in result["comment"]
    assert "podcast_angles" in result["comment"]
