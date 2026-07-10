from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from interview_os.workflows.interview_brief import build_interview_brief
from packages.shared.schemas.interview_os import InterviewBriefRequest

DEFAULT_INTERVIEW_OS_EVALS_PATH = (
    Path(__file__).resolve().parents[3]
    / "evaluations"
    / "interview_os"
    / "interview_cases.json"
)
DEFAULT_INTERVIEW_OS_EVAL_DATASET = "interview-os-brief"


class MinimumInterviewSectionCounts(BaseModel):
    """Minimum grounded-item counts expected from an Interview OS brief."""

    key_questions: int = 0
    talking_points: int = 0
    red_flags: int = 0


class InterviewBriefEvalReference(BaseModel):
    """Reference expectations for a single Interview OS brief case."""

    required_summary_terms: list[str] = Field(default_factory=list)
    expected_evidence_sources: list[str] = Field(default_factory=list)
    minimum_section_counts: MinimumInterviewSectionCounts = Field(
        default_factory=MinimumInterviewSectionCounts
    )
    expected_min_source_count: int = 1


class InterviewBriefEvalCase(BaseModel):
    """Serializable evaluation case for the Interview OS brief workflow."""

    id: str
    description: str
    inputs: InterviewBriefRequest
    reference_outputs: InterviewBriefEvalReference


def load_interview_os_eval_cases(
    path: Path | str = DEFAULT_INTERVIEW_OS_EVALS_PATH,
) -> list[InterviewBriefEvalCase]:
    """Load the checked-in local evaluation cases for Interview OS."""
    eval_path = Path(path)
    raw_cases = json.loads(eval_path.read_text(encoding="utf-8"))
    return [InterviewBriefEvalCase.model_validate(item) for item in raw_cases]


def apply_provider_override(
    cases: list[InterviewBriefEvalCase],
    provider: str,
) -> list[InterviewBriefEvalCase]:
    """Return cases with use_model=True and the given provider set.

    Interview OS is Claude-only, so every case is eligible (unlike Director OS,
    there are no Ollama-scenario cases to skip).
    """
    return [
        case.model_copy(
            update={
                "inputs": case.inputs.model_copy(
                    update={"use_model": True, "provider": provider}
                )
            }
        )
        for case in cases
    ]


def run_interview_os_eval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the public Interview OS workflow entrypoint for local evaluations."""
    request = InterviewBriefRequest.model_validate(inputs)
    response = build_interview_brief(request)
    return response.model_dump()


def score_interview_summary_terms(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the candidate summary mentions expected operator-facing terms."""
    required_terms = reference_outputs.get("required_summary_terms", [])
    summary = outputs.get("candidate_summary", "").lower()
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


def score_interview_expected_sources(
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


def score_interview_section_minimums(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that each Interview OS section meets its minimum item count."""
    minimums = MinimumInterviewSectionCounts.model_validate(
        reference_outputs.get("minimum_section_counts", {})
    )
    expected_counts = minimums.model_dump()
    observed_counts = {
        "key_questions": len(outputs.get("key_questions", [])),
        "talking_points": len(outputs.get("talking_points", [])),
        "red_flags": len(outputs.get("red_flags", [])),
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


def score_interview_source_diversity(
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


def score_interview_grounding(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that every item in every section is grounded with a source and line_number."""
    ungrounded: list[str] = []
    for section in ("key_questions", "talking_points", "red_flags"):
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


INTERVIEW_OS_EVALUATORS = [
    score_interview_summary_terms,
    score_interview_expected_sources,
    score_interview_section_minimums,
    score_interview_source_diversity,
    score_interview_grounding,
]

# Semantic retrieval (chroma) ranks individual lines by embedding similarity, not by keyword
# prefix match. expected_sources_present and section_minimums_met are calibrated against
# keyword retrieval behaviour and are excluded here. Grounding, summary terms, and source
# diversity remain valid quality signals for semantic retrieval.
INTERVIEW_OS_CHROMA_EVALUATORS = [
    score_interview_summary_terms,
    score_interview_source_diversity,
    score_interview_grounding,
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


def sync_langsmith_interview_os_dataset(
    *,
    client=None,
    cases: list[InterviewBriefEvalCase] | None = None,
    dataset_name: str = DEFAULT_INTERVIEW_OS_EVAL_DATASET,
):
    """Replace the LangSmith dataset with the checked-in Interview OS cases."""
    from langsmith import Client

    langsmith_client = client or Client()
    eval_cases = cases or load_interview_os_eval_cases()
    try:
        langsmith_client.delete_dataset(dataset_name=dataset_name)
    except Exception:
        pass

    dataset = langsmith_client.create_dataset(
        dataset_name,
        description="Checked-in Interview OS brief evaluation cases.",
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


def run_langsmith_interview_os_evaluations(
    *,
    cases: list[InterviewBriefEvalCase] | None = None,
    upload_results: bool = True,
    experiment_prefix: str = "interview-os-brief",
):
    """Run the checked-in Interview OS evaluation cases through LangSmith when configured."""
    from langsmith import Client, evaluate

    client = Client()
    dataset = sync_langsmith_interview_os_dataset(client=client, cases=cases)
    return evaluate(
        run_interview_os_eval_target,
        data=dataset,
        evaluators=INTERVIEW_OS_EVALUATORS,
        experiment_prefix=experiment_prefix,
        metadata={
            "workflow": "interview_os.brief",
            "dataset_name": DEFAULT_INTERVIEW_OS_EVAL_DATASET,
        },
        max_concurrency=1,
        upload_results=upload_results,
        client=client,
    )


def run_local_interview_os_evaluations(
    cases: list[InterviewBriefEvalCase] | None = None,
    *,
    evaluators: list | None = None,
) -> list[dict[str, Any]]:
    """Run the checked-in Interview OS evaluation cases without remote dependencies."""
    eval_cases = cases or load_interview_os_eval_cases()
    active_evaluators = evaluators if evaluators is not None else INTERVIEW_OS_EVALUATORS
    results: list[dict[str, Any]] = []
    with _langsmith_tracing_disabled():
        for case in eval_cases:
            outputs = run_interview_os_eval_target(case.inputs.model_dump())
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
    "INTERVIEW_OS_CHROMA_EVALUATORS",
    "INTERVIEW_OS_EVALUATORS",
    "InterviewBriefEvalCase",
    "InterviewBriefEvalReference",
    "DEFAULT_INTERVIEW_OS_EVAL_DATASET",
    "DEFAULT_INTERVIEW_OS_EVALS_PATH",
    "apply_provider_override",
    "load_interview_os_eval_cases",
    "run_interview_os_eval_target",
    "run_langsmith_interview_os_evaluations",
    "run_local_interview_os_evaluations",
    "score_interview_expected_sources",
    "score_interview_grounding",
    "score_interview_section_minimums",
    "score_interview_source_diversity",
    "score_interview_summary_terms",
    "sync_langsmith_interview_os_dataset",
]
