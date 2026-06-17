from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from one_on_one_os.workflows.meeting_brief import build_meeting_brief
from packages.shared.schemas.one_on_one_os import OneOnOneRequest

DEFAULT_ONE_ON_ONE_OS_EVALS_PATH = (
    Path(__file__).resolve().parents[3]
    / "evaluations"
    / "one_on_one_os"
    / "meeting_brief_cases.json"
)
DEFAULT_ONE_ON_ONE_OS_EVAL_DATASET = "one-on-one-os-brief"


class MinimumOneOnOneSectionCounts(BaseModel):
    """Minimum grounded-item counts expected from a One-on-One OS brief."""

    action_items: int = 0
    talking_points: int = 0
    blockers: int = 0
    kudos: int = 0


class OneOnOneBriefEvalReference(BaseModel):
    """Reference expectations for a single One-on-One OS brief case."""

    required_summary_terms: list[str] = Field(default_factory=list)
    expected_evidence_sources: list[str] = Field(default_factory=list)
    minimum_section_counts: MinimumOneOnOneSectionCounts = Field(
        default_factory=MinimumOneOnOneSectionCounts
    )
    expected_min_source_count: int = 1


class OneOnOneBriefEvalCase(BaseModel):
    """Serializable evaluation case for the One-on-One OS brief workflow."""

    id: str
    description: str
    inputs: OneOnOneRequest
    reference_outputs: OneOnOneBriefEvalReference


def load_one_on_one_os_eval_cases(
    path: Path | str = DEFAULT_ONE_ON_ONE_OS_EVALS_PATH,
) -> list[OneOnOneBriefEvalCase]:
    """Load the checked-in local evaluation cases for One-on-One OS."""
    eval_path = Path(path)
    raw_cases = json.loads(eval_path.read_text(encoding="utf-8"))
    return [OneOnOneBriefEvalCase.model_validate(item) for item in raw_cases]


def run_one_on_one_os_eval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the public One-on-One OS workflow entrypoint for local evaluations."""
    request = OneOnOneRequest.model_validate(inputs)
    response = build_meeting_brief(request)
    return response.model_dump()


def score_one_on_one_summary_terms(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the meeting summary mentions expected operator-facing terms."""
    required_terms = reference_outputs.get("required_summary_terms", [])
    summary = outputs.get("meeting_summary", "").lower()
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


def score_one_on_one_expected_sources(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the brief is grounded in the expected source files."""
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


def score_one_on_one_section_minimums(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that each One-on-One OS section meets its minimum item count."""
    minimums = MinimumOneOnOneSectionCounts.model_validate(
        reference_outputs.get("minimum_section_counts", {})
    )
    expected_counts = minimums.model_dump()
    observed_counts = {
        "action_items": len(outputs.get("action_items", [])),
        "talking_points": len(outputs.get("talking_points", [])),
        "blockers": len(outputs.get("blockers", [])),
        "kudos": len(outputs.get("kudos", [])),
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


def score_one_on_one_source_diversity(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the brief draws from enough distinct files when a case expects it."""
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


def score_one_on_one_grounding(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that every item in every section is grounded with a source and line_number."""
    ungrounded: list[str] = []
    for section in ("action_items", "talking_points", "blockers", "kudos"):
        for item in outputs.get(section, []):
            if not item.get("source") or not item.get("line_number"):
                ungrounded.append(f"{section}: {item.get('text', '')[:60]}")
    return {
        "key": "all_items_grounded",
        "score": not ungrounded,
        "comment": (
            "All output items carry source and line_number citations."
            if not ungrounded
            else f"Ungrounded items found: {'; '.join(ungrounded)}"
        ),
    }


ONE_ON_ONE_OS_EVALUATORS = [
    score_one_on_one_summary_terms,
    score_one_on_one_expected_sources,
    score_one_on_one_section_minimums,
    score_one_on_one_source_diversity,
    score_one_on_one_grounding,
]

# Semantic retrieval (chroma) ranks individual lines by embedding similarity, not by keyword
# prefix match. expected_sources_present and section_minimums_met are calibrated against
# keyword retrieval behaviour and are excluded here. Grounding, summary terms, and source
# diversity remain valid quality signals for semantic retrieval.
ONE_ON_ONE_OS_CHROMA_EVALUATORS = [
    score_one_on_one_summary_terms,
    score_one_on_one_source_diversity,
    score_one_on_one_grounding,
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


def sync_langsmith_one_on_one_os_dataset(
    *,
    client=None,
    cases: list[OneOnOneBriefEvalCase] | None = None,
    dataset_name: str = DEFAULT_ONE_ON_ONE_OS_EVAL_DATASET,
):
    """Replace the LangSmith dataset with the checked-in One-on-One OS cases."""
    from langsmith import Client

    langsmith_client = client or Client()
    eval_cases = cases or load_one_on_one_os_eval_cases()
    try:
        langsmith_client.delete_dataset(dataset_name=dataset_name)
    except Exception:
        pass

    dataset = langsmith_client.create_dataset(
        dataset_name,
        description="Checked-in One-on-One OS brief evaluation cases.",
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


def run_langsmith_one_on_one_os_evaluations(
    *,
    cases: list[OneOnOneBriefEvalCase] | None = None,
    upload_results: bool = True,
    experiment_prefix: str = "one-on-one-os-brief",
):
    """Run the checked-in One-on-One OS evaluation cases through LangSmith when configured."""
    from langsmith import Client, evaluate

    client = Client()
    dataset = sync_langsmith_one_on_one_os_dataset(client=client, cases=cases)
    return evaluate(
        run_one_on_one_os_eval_target,
        data=dataset,
        evaluators=ONE_ON_ONE_OS_EVALUATORS,
        experiment_prefix=experiment_prefix,
        metadata={
            "workflow": "one_on_one_os.brief",
            "dataset_name": DEFAULT_ONE_ON_ONE_OS_EVAL_DATASET,
        },
        max_concurrency=1,
        upload_results=upload_results,
        client=client,
    )


def run_local_one_on_one_os_evaluations(
    cases: list[OneOnOneBriefEvalCase] | None = None,
    *,
    evaluators: list | None = None,
) -> list[dict[str, Any]]:
    """Run the checked-in One-on-One OS evaluation cases without remote dependencies."""
    eval_cases = cases or load_one_on_one_os_eval_cases()
    active_evaluators = evaluators if evaluators is not None else ONE_ON_ONE_OS_EVALUATORS
    results: list[dict[str, Any]] = []
    for case in eval_cases:
        outputs = run_one_on_one_os_eval_target(case.inputs.model_dump())
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
    "ONE_ON_ONE_OS_CHROMA_EVALUATORS",
    "ONE_ON_ONE_OS_EVALUATORS",
    "OneOnOneBriefEvalCase",
    "OneOnOneBriefEvalReference",
    "DEFAULT_ONE_ON_ONE_OS_EVAL_DATASET",
    "DEFAULT_ONE_ON_ONE_OS_EVALS_PATH",
    "load_one_on_one_os_eval_cases",
    "run_one_on_one_os_eval_target",
    "run_langsmith_one_on_one_os_evaluations",
    "run_local_one_on_one_os_evaluations",
    "score_one_on_one_expected_sources",
    "score_one_on_one_grounding",
    "score_one_on_one_section_minimums",
    "score_one_on_one_source_diversity",
    "score_one_on_one_summary_terms",
    "sync_langsmith_one_on_one_os_dataset",
]
