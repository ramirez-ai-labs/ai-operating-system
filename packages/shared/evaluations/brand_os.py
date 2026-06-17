from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from brand_os.workflows.content_draft import build_content_draft
from packages.shared.schemas.brand_os import BrandContentDraftRequest

DEFAULT_BRAND_OS_EVALS_PATH = (
    Path(__file__).resolve().parents[3] / "evaluations" / "brand_os" / "content_draft_cases.json"
)
DEFAULT_BRAND_OS_EVAL_DATASET = "brand-os-content-draft"


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
    expected_empty_sections: list[str] = Field(default_factory=list)


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
    raw_cases = json.loads(eval_path.read_text(encoding="utf-8"))
    return [BrandContentDraftEvalCase.model_validate(item) for item in raw_cases]


def run_brand_os_eval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the public Brand OS workflow entrypoint for local evaluations."""
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


def score_brand_section_prefix_purity(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that Brand OS items stay in sections that match their prefixes."""
    allowed_prefixes = {
        "post_outline": ("insight:", "workflow:"),
        "podcast_angles": ("podcast:",),
        "repo_improvements": ("improve:", "next:"),
    }
    mismatches: list[str] = []
    for section_name, prefixes in allowed_prefixes.items():
        for item in outputs.get(section_name, []):
            text = item.get("text", "").strip().lower()
            if text and ":" in text and not any(text.startswith(prefix) for prefix in prefixes):
                mismatches.append(f"{section_name} -> {item.get('text', '')}")
    return {
        "key": "section_prefix_purity",
        "score": not mismatches,
        "comment": (
            "Brand OS section prefixes stayed aligned with their output sections."
            if not mismatches
            else "Misclassified Brand OS items: " + "; ".join(mismatches)
        ),
    }


def score_brand_expected_empty_sections(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that cases expecting sparse sections keep unrelated sections empty."""
    expected_empty_sections = reference_outputs.get("expected_empty_sections", [])
    unexpected_content = [
        section_name for section_name in expected_empty_sections if outputs.get(section_name)
    ]
    return {
        "key": "expected_empty_sections",
        "score": not unexpected_content,
        "comment": (
            "Expected sparse sections stayed empty."
            if not unexpected_content
            else "Sections expected to be empty contained output: "
            + ", ".join(unexpected_content)
        ),
    }


BRAND_OS_EVALUATORS = [
    score_brand_summary_terms,
    score_brand_expected_sources,
    score_brand_section_minimums,
    score_brand_source_diversity,
    score_brand_section_prefix_purity,
    score_brand_expected_empty_sections,
]

# Claude synthesizes by semantic meaning, not prefix rules, so prefix purity and empty-section
# constraints only apply to the deterministic path.
BRAND_OS_CLAUDE_EVALUATORS = [
    score_brand_summary_terms,
    score_brand_expected_sources,
    score_brand_section_minimums,
    score_brand_source_diversity,
]

# Semantic retrieval (chroma) ranks individual lines by embedding similarity, not by keyword
# prefix match. The prefix-based section scorers (expected_sources_present,
# section_minimums_met, section_prefix_purity) are calibrated against keyword retrieval
# behaviour and are not meaningful here — line-level chunks may not carry the expected
# prefix even when the right file is retrieved. Summary terms and source diversity remain
# valid quality signals for semantic retrieval.
BRAND_OS_CHROMA_EVALUATORS = [
    score_brand_summary_terms,
    score_brand_source_diversity,
]


@contextmanager
def _langsmith_tracing_disabled():
    """Temporarily disable workflow tracing for fully local eval runs."""
    previous_value = os.environ.get("LANGSMITH_TRACING")
    os.environ["LANGSMITH_TRACING"] = "false"
    try:
        yield
    finally:
        if previous_value is None:
            os.environ.pop("LANGSMITH_TRACING", None)
        else:
            os.environ["LANGSMITH_TRACING"] = previous_value


def sync_langsmith_brand_os_dataset(
    *,
    client=None,
    cases: list[BrandContentDraftEvalCase] | None = None,
    dataset_name: str = DEFAULT_BRAND_OS_EVAL_DATASET,
):
    """Replace the LangSmith dataset with the checked-in Brand OS cases."""
    from langsmith import Client

    langsmith_client = client or Client()
    eval_cases = cases or load_brand_os_eval_cases()
    try:
        langsmith_client.delete_dataset(dataset_name=dataset_name)
    except Exception:
        pass

    dataset = langsmith_client.create_dataset(
        dataset_name,
        description="Checked-in Brand OS content-draft evaluation cases.",
    )
    langsmith_client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": case.inputs.model_dump(),
                "outputs": case.reference_outputs.model_dump(),
                "metadata": {"case_id": case.id, "description": case.description},
            }
            for case in eval_cases
        ],
    )
    return dataset


def run_langsmith_brand_os_evaluations(
    *,
    cases: list[BrandContentDraftEvalCase] | None = None,
    upload_results: bool = True,
    experiment_prefix: str = "brand-os-content-draft",
):
    """Run the checked-in Brand OS evaluation cases through LangSmith when configured."""
    from langsmith import Client, evaluate

    client = Client()
    dataset = sync_langsmith_brand_os_dataset(client=client, cases=cases)
    return evaluate(
        run_brand_os_eval_target,
        data=dataset,
        evaluators=BRAND_OS_EVALUATORS,
        experiment_prefix=experiment_prefix,
        metadata={
            "workflow": "brand_os.content_draft",
            "dataset_name": DEFAULT_BRAND_OS_EVAL_DATASET,
        },
        max_concurrency=1,
        upload_results=upload_results,
        client=client,
    )


def run_local_brand_os_evaluations(
    cases: list[BrandContentDraftEvalCase] | None = None,
    *,
    evaluators: list | None = None,
) -> list[dict[str, Any]]:
    """Run the checked-in Brand OS evaluation cases without remote dependencies."""
    eval_cases = cases or load_brand_os_eval_cases()
    active_evaluators = evaluators if evaluators is not None else BRAND_OS_EVALUATORS
    results: list[dict[str, Any]] = []
    for case in eval_cases:
        outputs = run_brand_os_eval_target(case.inputs.model_dump())
        reference_outputs = case.reference_outputs.model_dump()
        evaluator_results = [
            evaluator(outputs=outputs, reference_outputs=reference_outputs)
            for evaluator in active_evaluators
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
    "BRAND_OS_CHROMA_EVALUATORS",
    "BRAND_OS_CLAUDE_EVALUATORS",
    "BRAND_OS_EVALUATORS",
    "BrandContentDraftEvalCase",
    "BrandContentDraftEvalReference",
    "DEFAULT_BRAND_OS_EVAL_DATASET",
    "DEFAULT_BRAND_OS_EVALS_PATH",
    "load_brand_os_eval_cases",
    "run_brand_os_eval_target",
    "run_langsmith_brand_os_evaluations",
    "run_local_brand_os_evaluations",
    "score_brand_expected_empty_sections",
    "score_brand_expected_sources",
    "score_brand_section_minimums",
    "score_brand_section_prefix_purity",
    "score_brand_source_diversity",
    "score_brand_summary_terms",
    "sync_langsmith_brand_os_dataset",
]
