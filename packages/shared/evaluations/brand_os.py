from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from brand_os.workflows.content_draft import build_content_draft
from packages.shared.schemas.brand_os import BrandContentDraftRequest

DEFAULT_BRAND_OS_EVALS_PATH = (
    Path(__file__).resolve().parents[3] / "evaluations" / "brand_os" / "content_draft_cases.json"
)


class MinimumBrandSectionCounts(BaseModel):
    """Minimum grounded-item counts expected from a Brand OS draft."""

    post_outline: int = 0
    podcast_angles: int = 0
    repo_improvements: int = 0


class BrandContentDraftEvalReference(BaseModel):
    """Reference expectations for a single Brand OS content-draft case."""

    required_summary_terms: list[str] = Field(default_factory=list)
    expected_evidence_sources: list[str] = Field(default_factory=list)
    minimum_section_counts: MinimumBrandSectionCounts = Field(
        default_factory=MinimumBrandSectionCounts
    )
    expected_min_source_count: int = 1


class BrandContentDraftEvalCase(BaseModel):
    """Serializable evaluation case for the Brand OS content-draft workflow."""

    id: str
    description: str
    inputs: BrandContentDraftRequest
    reference_outputs: BrandContentDraftEvalReference


def load_brand_os_eval_cases(
    path: Path | str = DEFAULT_BRAND_OS_EVALS_PATH,
) -> list[BrandContentDraftEvalCase]:
    """Load the checked-in local evaluation cases for Brand OS."""
    eval_path = Path(path)
    # The eval data lives in JSON so it stays easy to review and edit without
    # learning a separate dataset tool or service.
    raw_cases = json.loads(eval_path.read_text(encoding="utf-8"))
    return [BrandContentDraftEvalCase.model_validate(item) for item in raw_cases]


def run_brand_os_eval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the public Brand OS workflow entrypoint for local evaluations."""
    # The eval target goes through the same public request model as normal app
    # code. That keeps evals honest: they exercise the same input boundary a
    # real caller would use.
    request = BrandContentDraftRequest.model_validate(inputs)
    response = build_content_draft(request)
    return response.model_dump()


def score_brand_summary_terms(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the Brand OS summary mentions the expected operator-facing terms."""
    required_terms = reference_outputs.get("required_summary_terms", [])
    summary = outputs.get("insight_summary", "").lower()
    missing_terms = [term for term in required_terms if term.lower() not in summary]
    return {
        "key": "summary_terms_present",
        "score": not missing_terms,
        "comment": (
            "All required summary terms were present."
            if not missing_terms
            else f"Missing summary terms: {', '.join(missing_terms)}"
        ),
    }


def score_brand_expected_sources(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the content draft is grounded in the expected source files."""
    expected_sources = set(reference_outputs.get("expected_evidence_sources", []))
    actual_sources = {item["source"] for item in outputs.get("evidence", [])}
    missing_sources = sorted(expected_sources - actual_sources)
    return {
        "key": "expected_sources_present",
        "score": not missing_sources,
        "comment": (
            "All expected evidence sources were retrieved."
            if not missing_sources
            else f"Missing expected sources: {', '.join(missing_sources)}"
        ),
    }


def score_brand_section_minimums(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that each Brand OS section is populated strongly enough for the case."""
    minimums = MinimumBrandSectionCounts.model_validate(
        reference_outputs.get("minimum_section_counts", {})
    )
    expected_counts = minimums.model_dump()
    observed_counts = {
        "post_outline": len(outputs.get("post_outline", [])),
        "podcast_angles": len(outputs.get("podcast_angles", [])),
        "repo_improvements": len(outputs.get("repo_improvements", [])),
    }
    failing_sections = [
        section
        for section, required_count in expected_counts.items()
        if observed_counts[section] < required_count
    ]
    return {
        "key": "section_minimums_met",
        "score": not failing_sections,
        "comment": (
            "All minimum section counts were met."
            if not failing_sections
            else (
                "Sections below the expected minimums: "
                + ", ".join(
                    f"{section} ({observed_counts[section]}/{expected_counts[section]})"
                    for section in failing_sections
                )
            )
        ),
    }


def score_brand_source_diversity(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that Brand OS can pull from enough distinct files when a case expects it."""
    required_minimum = int(reference_outputs.get("expected_min_source_count", 1))
    actual_sources = {item["source"] for item in outputs.get("evidence", [])}
    actual_count = len(actual_sources)
    return {
        "key": "source_diversity_met",
        "score": actual_count >= required_minimum,
        "comment": (
            f"Observed {actual_count} unique evidence sources."
            if actual_count >= required_minimum
            else (
                f"Observed only {actual_count} unique evidence sources; "
                f"expected at least {required_minimum}."
            )
        ),
    }


BRAND_OS_EVALUATORS = [
    score_brand_summary_terms,
    score_brand_expected_sources,
    score_brand_section_minimums,
    score_brand_source_diversity,
]


def run_local_brand_os_evaluations(
    cases: list[BrandContentDraftEvalCase] | None = None,
) -> list[dict[str, Any]]:
    """Run the checked-in Brand OS evaluation cases without remote dependencies."""
    eval_cases = cases or load_brand_os_eval_cases()
    results: list[dict[str, Any]] = []
    for case in eval_cases:
        # Each case is run independently and scored by a small set of explicit
        # evaluators. This keeps failures easy to explain during development.
        outputs = run_brand_os_eval_target(case.inputs.model_dump())
        reference_outputs = case.reference_outputs.model_dump()
        evaluator_results = [
            evaluator(outputs=outputs, reference_outputs=reference_outputs)
            for evaluator in BRAND_OS_EVALUATORS
        ]
        results.append(
            {
                "case_id": case.id,
                "description": case.description,
                "inputs": case.inputs.model_dump(),
                "outputs": outputs,
                "results": evaluator_results,
                "passed": all(item["score"] for item in evaluator_results),
            }
        )
    return results


__all__ = [
    "BRAND_OS_EVALUATORS",
    "BrandContentDraftEvalCase",
    "BrandContentDraftEvalReference",
    "DEFAULT_BRAND_OS_EVALS_PATH",
    "load_brand_os_eval_cases",
    "run_brand_os_eval_target",
    "run_local_brand_os_evaluations",
    "score_brand_expected_sources",
    "score_brand_section_minimums",
    "score_brand_source_diversity",
    "score_brand_summary_terms",
]
