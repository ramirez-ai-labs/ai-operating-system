from brand_os.workflows.content_draft import build_content_draft
from packages.shared.evaluations.brand_os import (
    DEFAULT_BRAND_OS_EVALS_PATH,
    load_brand_os_eval_cases,
    run_local_brand_os_evaluations,
    score_brand_expected_empty_sections,
    score_brand_section_minimums,
    score_brand_section_prefix_purity,
    score_brand_summary_terms,
)
from packages.shared.schemas.brand_os import BrandContentDraftRequest


def test_load_brand_os_eval_cases_reads_checked_in_dataset() -> None:
    """The repo should ship a checked-in eval set for Brand OS."""
    cases = load_brand_os_eval_cases(DEFAULT_BRAND_OS_EVALS_PATH)
    assert cases
    assert cases[0].id == "local-first-content-baseline"
    assert any(case.id == "repo-improvement-focus" for case in cases)


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


def test_brand_section_prefix_purity_reports_cross_section_leaks() -> None:
    """Section purity scoring should catch prefixed items in the wrong Brand OS section."""
    result = score_brand_section_prefix_purity(
        outputs={
            "post_outline": [{"text": "Podcast: use this as an audio discussion opener."}],
            "podcast_angles": [{"text": "Podcast: compare local-first and cloud workflows."}],
            "repo_improvements": [{"text": "Improve: add a trace view for operator visibility."}],
        },
        reference_outputs={},
    )
    assert not result["score"]
    assert "post_outline" in result["comment"]


def test_brand_expected_empty_sections_reports_unexpected_content() -> None:
    """Sparse-case scoring should fail when sections expected to stay empty contain output."""
    result = score_brand_expected_empty_sections(
        outputs={"podcast_angles": [{"text": "Podcast: still present"}]},
        reference_outputs={"expected_empty_sections": ["podcast_angles"]},
    )
    assert not result["score"]
    assert "podcast_angles" in result["comment"]


def test_brand_content_draft_keeps_prefixed_items_in_matching_sections() -> None:
    """The Brand OS workflow should keep prefixed lines in the right sections."""
    result = build_content_draft(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai workflow",
            max_documents=5,
        )
    )
    assert all(item.text.startswith(("Insight:", "Workflow:")) for item in result.post_outline)
    assert all(item.text.startswith("Podcast:") for item in result.podcast_angles)
    assert all(item.text.startswith(("Improve:", "Next:")) for item in result.repo_improvements)
