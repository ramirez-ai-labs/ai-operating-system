from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from langsmith import Client, evaluate
from pydantic import BaseModel, Field

from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.providers.base import WeeklyUpdateProvider
from packages.shared.schemas.director_os import GroundedItem, WeeklyUpdateDraft, WeeklyUpdateRequest

DEFAULT_DIRECTOR_OS_EVAL_PROJECT = "ai-os"
DEFAULT_DIRECTOR_OS_EVAL_DATASET = "director-os-weekly-update"
DEFAULT_DIRECTOR_OS_EVALS_PATH = (
    Path(__file__).resolve().parents[3] / "evaluations" / "director_os" / "weekly_update_cases.json"
)
DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"


class MinimumSectionCounts(BaseModel):
    """Minimum grounded-item counts expected from a workflow run."""

    wins: int = 0
    risks: int = 0
    next_steps: int = 0


class WeeklyUpdateEvalReference(BaseModel):
    """Reference expectations for a single Director OS evaluation case."""

    required_summary_terms: list[str] = Field(default_factory=list)
    expected_evidence_sources: list[str] = Field(default_factory=list)
    minimum_section_counts: MinimumSectionCounts = Field(
        default_factory=MinimumSectionCounts
    )
    expected_min_source_count: int = 1
    expected_deterministic_summary: bool = False


class WeeklyUpdateEvalCase(BaseModel):
    """Serializable evaluation case for the Director OS weekly-update workflow."""

    id: str
    description: str
    inputs: WeeklyUpdateRequest
    reference_outputs: WeeklyUpdateEvalReference
    provider_scenario: str | None = None


class _FailingProvider(WeeklyUpdateProvider):
    def generate_weekly_update(self, focus, evidence):
        raise ValueError("Ollama is unavailable")


class _WeakProvider(WeeklyUpdateProvider):
    def generate_weekly_update(self, focus, evidence):
        return WeeklyUpdateDraft(summary="", wins=[], risks=[], next_steps=[])


class _UnsupportedClaimProvider(WeeklyUpdateProvider):
    def generate_weekly_update(self, focus, evidence):
        return WeeklyUpdateDraft(
            summary="Model-assisted weekly update from grounded evidence.",
            wins=[
                GroundedItem(
                    text="Win: created a new hiring plan and budget proposal.",
                    source=evidence[0].source,
                    line_number=evidence[0].line_number,
                )
            ],
            risks=[],
            next_steps=[],
        )


PROVIDER_SCENARIOS: dict[str, type[WeeklyUpdateProvider]] = {
    "provider_failure": _FailingProvider,
    "weak_model_output": _WeakProvider,
    "unsupported_grounded_claim": _UnsupportedClaimProvider,
}


def load_director_os_eval_cases(
    path: Path | str = DEFAULT_DIRECTOR_OS_EVALS_PATH,
) -> list[WeeklyUpdateEvalCase]:
    """Load the checked-in local evaluation cases for Director OS."""
    eval_path = Path(path)
    raw_cases = json.loads(eval_path.read_text(encoding="utf-8"))
    return [WeeklyUpdateEvalCase.model_validate(item) for item in raw_cases]


@contextmanager
def _override_weekly_update_provider(provider_scenario: str | None):
    """Swap the graph's provider adapter for a deterministic fake scenario when requested."""
    if not provider_scenario:
        yield
        return

    provider_cls = PROVIDER_SCENARIOS[provider_scenario]
    from packages.shared.graphs import director_os as graph_module

    original_provider = graph_module.OllamaWeeklyUpdateProvider
    graph_module.OllamaWeeklyUpdateProvider = lambda base_url, model: provider_cls()
    try:
        yield
    finally:
        graph_module.OllamaWeeklyUpdateProvider = original_provider


def _build_eval_inputs(case: WeeklyUpdateEvalCase) -> dict[str, Any]:
    """Serialize a case into the input payload used by local and LangSmith evals."""
    payload = case.inputs.model_dump()
    if case.provider_scenario:
        payload["provider_scenario"] = case.provider_scenario
    return payload


def run_director_os_eval_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the public Director OS workflow entrypoint for LangSmith or local evals."""
    payload = dict(inputs)
    provider_scenario = payload.pop("provider_scenario", None)
    request = WeeklyUpdateRequest.model_validate(payload)
    with _override_weekly_update_provider(provider_scenario):
        response = build_weekly_update(request)
    return response.model_dump()


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


def score_summary_terms(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the summary mentions the expected operator-facing terms."""
    required_terms = reference_outputs.get("required_summary_terms", [])
    summary = outputs.get("summary", "").lower()
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


def score_expected_sources(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the retrieved evidence includes the sources the case depends on."""
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


def score_section_minimums(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the workflow returns enough structured items for each section."""
    minimums = MinimumSectionCounts.model_validate(
        reference_outputs.get("minimum_section_counts", {})
    )
    expected_counts = minimums.model_dump()
    observed_counts = {
        "wins": len(outputs.get("wins", [])),
        "risks": len(outputs.get("risks", [])),
        "next_steps": len(outputs.get("next_steps", [])),
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


def score_source_diversity(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that the workflow can pull from multiple files when the case expects it."""
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


def score_section_prefix_purity(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check that sectioned items stay in the section their prefix implies."""
    expected_prefixes = {
        "wins": "win:",
        "risks": "risk:",
        "next_steps": "next:",
    }
    mismatches: list[str] = []
    for section_name, expected_prefix in expected_prefixes.items():
        for item in outputs.get(section_name, []):
            text = item.get("text", "").strip().lower()
            if text and ":" in text and not text.startswith(expected_prefix):
                mismatches.append(f"{section_name} -> {item.get('text', '')}")
    return {
        "key": "section_prefix_purity",
        "score": not mismatches,
        "comment": (
            "Section prefixes stayed aligned with their output sections."
            if not mismatches
            else "Misclassified section items: " + "; ".join(mismatches)
        ),
    }


def score_expected_summary_mode(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Check whether the case produced the deterministic summary shape when expected."""
    expects_deterministic = bool(reference_outputs.get("expected_deterministic_summary", False))
    summary = outputs.get("summary", "")
    is_deterministic = summary.startswith(DETERMINISTIC_SUMMARY_PREFIX)
    return {
        "key": "expected_summary_mode",
        "score": is_deterministic if expects_deterministic else True,
        "comment": (
            "Deterministic summary fallback was observed as expected."
            if expects_deterministic and is_deterministic
            else (
                "Case did not require deterministic fallback."
                if not expects_deterministic
                else "Expected a deterministic fallback summary but saw a different summary shape."
            )
        ),
    }


DIRECTOR_OS_EVALUATORS = [
    score_summary_terms,
    score_expected_sources,
    score_section_minimums,
    score_source_diversity,
    score_section_prefix_purity,
    score_expected_summary_mode,
]


def run_local_director_os_evaluations(
    cases: list[WeeklyUpdateEvalCase] | None = None,
) -> list[dict[str, Any]]:
    """Run the checked-in evaluation cases without requiring LangSmith connectivity."""
    eval_cases = cases or load_director_os_eval_cases()
    results: list[dict[str, Any]] = []
    with _langsmith_tracing_disabled():
        for case in eval_cases:
            outputs = run_director_os_eval_target(_build_eval_inputs(case))
            reference_outputs = case.reference_outputs.model_dump()
            evaluator_results = [
                evaluator(outputs=outputs, reference_outputs=reference_outputs)
                for evaluator in DIRECTOR_OS_EVALUATORS
            ]
            results.append(
                {
                    "case_id": case.id,
                    "description": case.description,
                    "inputs": _build_eval_inputs(case),
                    "outputs": outputs,
                    "results": evaluator_results,
                    "passed": all(item["score"] for item in evaluator_results),
                }
            )
    return results


def sync_langsmith_director_os_dataset(
    *,
    client: Client | None = None,
    cases: list[WeeklyUpdateEvalCase] | None = None,
    dataset_name: str = DEFAULT_DIRECTOR_OS_EVAL_DATASET,
):
    """Replace the LangSmith dataset with the checked-in Director OS cases."""
    langsmith_client = client or Client()
    eval_cases = cases or load_director_os_eval_cases()
    try:
        langsmith_client.delete_dataset(dataset_name=dataset_name)
    except Exception:
        pass

    dataset = langsmith_client.create_dataset(
        dataset_name,
        description="Checked-in Director OS weekly-update evaluation cases.",
    )
    langsmith_client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": _build_eval_inputs(case),
                "outputs": case.reference_outputs.model_dump(),
                "metadata": {
                    "case_id": case.id,
                    "description": case.description,
                },
            }
            for case in eval_cases
        ],
    )
    return dataset


def run_langsmith_director_os_evaluations(
    *,
    cases: list[WeeklyUpdateEvalCase] | None = None,
    upload_results: bool = True,
    experiment_prefix: str = "director-os-weekly-update",
):
    """Run the checked-in evaluation cases through LangSmith when configured."""
    client = Client()
    dataset = sync_langsmith_director_os_dataset(client=client, cases=cases)
    return evaluate(
        run_director_os_eval_target,
        data=dataset,
        evaluators=DIRECTOR_OS_EVALUATORS,
        experiment_prefix=experiment_prefix,
        metadata={
            "workflow": "director_os.weekly_update",
            "dataset_name": DEFAULT_DIRECTOR_OS_EVAL_DATASET,
        },
        max_concurrency=1,
        upload_results=upload_results,
        client=client,
    )


__all__ = [
    "DEFAULT_DIRECTOR_OS_EVAL_DATASET",
    "DEFAULT_DIRECTOR_OS_EVAL_PROJECT",
    "DEFAULT_DIRECTOR_OS_EVALS_PATH",
    "DETERMINISTIC_SUMMARY_PREFIX",
    "DIRECTOR_OS_EVALUATORS",
    "WeeklyUpdateEvalCase",
    "WeeklyUpdateEvalReference",
    "load_director_os_eval_cases",
    "run_director_os_eval_target",
    "run_langsmith_director_os_evaluations",
    "run_local_director_os_evaluations",
    "score_expected_sources",
    "score_expected_summary_mode",
    "score_section_minimums",
    "score_section_prefix_purity",
    "score_source_diversity",
    "score_summary_terms",
    "sync_langsmith_director_os_dataset",
]
