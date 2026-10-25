"""Routing and planning evaluations for the planner/supervisor (Phase 9b).

Each case gives a goal and the domain workflows a correct plan should contain
(a multiset: order does not matter, repeats do). Scorers check:

- `workflows_match`       — the plan calls exactly the expected workflows
- `within_max_steps`      — the plan respects the step bound
- `tool_inputs_valid`     — every step's input passes its domain's DomainToolInput
- `model_planned`         — (model planners only) no silent fallback to rules
- `status_matches` / `all_steps_grounded` — (execute cases) the plan runs end to
  end and every step's output passes merge-time grounding validation

Cases tagged `rules_supported: false` are goals with no routing keywords
("help me get ready for my conversation with Priya"). The rules planner is not
expected to solve them and they are skipped on the local backend; they are
where a model planner earns its cost, and they run with `--backend claude` or
`--backend ollama`.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from packages.shared.domains import get_domain
from packages.shared.schemas.planner import Plan, PlannerKind, PlanRequest

logger = logging.getLogger(__name__)

DEFAULT_PLANNER_EVALS_PATH = (
    Path(__file__).resolve().parents[3] / "evaluations" / "planner" / "planning_cases.json"
)

# Opt in to `scripts/run_evals.py --backend ollama`.
SUPPORTS_OLLAMA_BACKEND = True


class PlannerEvalCase(BaseModel):
    """One goal and the plan it should produce."""

    id: str
    description: str
    goal: str
    expected_workflows: list[str]
    tags: list[str] = Field(default_factory=list)
    rules_supported: bool = True
    planner: PlannerKind = "rules"
    max_steps: int = 5
    # Run the plan end to end (slower) and score status + grounding.
    execute: bool = False
    expected_status: str = "ok"


def load_planner_eval_cases(
    path: Path | str = DEFAULT_PLANNER_EVALS_PATH,
) -> list[PlannerEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [PlannerEvalCase.model_validate(item) for item in raw_cases]


def apply_provider_override(
    cases: list[PlannerEvalCase],
    provider: str,
) -> list[PlannerEvalCase]:
    """Switch every case (including rules-unsupported ones) to a model planner."""
    return [case.model_copy(update={"planner": provider}) for case in cases]


def score_workflows_match(plan: Plan, case: PlannerEvalCase) -> dict[str, Any]:
    actual = Counter(step.workflow_id for step in plan.steps)
    expected = Counter(case.expected_workflows)
    missing = sorted((expected - actual).elements())
    extra = sorted((actual - expected).elements())
    return {
        "key": "workflows_match",
        "score": actual == expected,
        "comment": (
            "Plan calls exactly the expected workflows."
            if actual == expected
            else f"missing={missing} extra={extra}"
        ),
    }


def score_within_max_steps(plan: Plan, case: PlannerEvalCase) -> dict[str, Any]:
    within = len(plan.steps) <= case.max_steps
    return {
        "key": "within_max_steps",
        "score": within,
        "comment": f"{len(plan.steps)} steps (max {case.max_steps}).",
    }


def score_tool_inputs_valid(plan: Plan, case: PlannerEvalCase) -> dict[str, Any]:
    problems: list[str] = []
    for step in plan.steps:
        try:
            get_domain(step.workflow_id).tool.input_model.model_validate(step.tool_input)
        except (ValueError, ValidationError) as exc:
            problems.append(f"step {step.step_id}: {exc}")
    return {
        "key": "tool_inputs_valid",
        "score": not problems,
        "comment": "All step inputs validate." if not problems else "; ".join(problems),
    }


def score_model_planned(plan: Plan, case: PlannerEvalCase) -> dict[str, Any]:
    return {
        "key": "model_planned",
        "score": plan.fallback_reason is None,
        "comment": (
            f"Planned by {plan.planner_used}."
            if plan.fallback_reason is None
            else f"Fell back to rules: {plan.fallback_reason}"
        ),
    }


def summarize_planner_results(
    cases: list[PlannerEvalCase],
    plans: list[Plan],
) -> dict[str, float]:
    """Aggregate plan quality: exact-match rate plus workflow precision and recall."""
    true_positive = false_positive = false_negative = exact = 0
    for case, plan in zip(cases, plans, strict=True):
        actual = Counter(step.workflow_id for step in plan.steps)
        expected = Counter(case.expected_workflows)
        true_positive += sum((actual & expected).values())
        false_positive += sum((actual - expected).values())
        false_negative += sum((expected - actual).values())
        exact += actual == expected
    total = len(cases) or 1
    return {
        "cases": len(cases),
        "exact_match_rate": round(exact / total, 3),
        "workflow_precision": round(true_positive / ((true_positive + false_positive) or 1), 3),
        "workflow_recall": round(true_positive / ((true_positive + false_negative) or 1), 3),
    }


def run_local_planner_evaluations(
    cases: list[PlannerEvalCase],
) -> list[dict[str, Any]]:
    """Plan (and optionally execute) each case and score it."""
    # Imported here so loading eval cases does not compile the supervisor graph.
    from packages.shared.graphs.planner import run_plan_graph
    from packages.shared.orchestration.planner import make_plan

    eligible = [case for case in cases if case.planner != "rules" or case.rules_supported]
    skipped = len(cases) - len(eligible)
    if skipped:
        logger.info(
            "Skipping %d rules-unsupported planner case(s); run them with a model backend.",
            skipped,
        )

    results: list[dict[str, Any]] = []
    plans: list[Plan] = []
    for case in eligible:
        request = PlanRequest(goal=case.goal, planner=case.planner, max_steps=case.max_steps)
        response = run_plan_graph(request) if case.execute else None
        plan = response.plan if response else make_plan(request)[0]
        plans.append(plan)

        scores = [
            score_workflows_match(plan, case),
            score_within_max_steps(plan, case),
            score_tool_inputs_valid(plan, case),
        ]
        if case.planner != "rules":
            scores.append(score_model_planned(plan, case))
        if response is not None:
            errors = [f"step {s.step_id}: {s.error}" for s in response.steps if s.error]
            scores.append(
                {
                    "key": "status_matches",
                    "score": response.status == case.expected_status,
                    "comment": f"status={response.status} (expected {case.expected_status}).",
                }
            )
            scores.append(
                {
                    "key": "all_steps_grounded",
                    "score": not errors,
                    "comment": response.validation_summary if not errors else "; ".join(errors),
                }
            )

        results.append(
            {
                "case_id": case.id,
                "planner_used": plan.planner_used,
                "plan": [step.workflow_id for step in plan.steps],
                "results": scores,
                "passed": all(score["score"] for score in scores),
            }
        )

    logger.info("Planner summary: %s", summarize_planner_results(eligible, plans))
    return results


__all__ = [
    "DEFAULT_PLANNER_EVALS_PATH",
    "PlannerEvalCase",
    "apply_provider_override",
    "load_planner_eval_cases",
    "run_local_planner_evaluations",
    "summarize_planner_results",
]
