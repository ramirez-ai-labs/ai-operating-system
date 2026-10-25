"""Planner/supervisor graph (Phase 9b).

    make_plan ──Send×N──▶ run_step (parallel) ──▶ merge_results ──▶ END

`make_plan` produces a validated `Plan` (rules, Ollama, or Claude planner).
Each step fans out with LangGraph's `Send`, so independent domain workflows
run in the same superstep. `run_step` builds the domain request from the
step's tool input plus the operator's settings, runs the registered workflow,
and re-validates grounding. A failing step records its error and the rest of
the plan still completes; `merge_results` reports ok / partial / error.
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from packages.shared.domains import get_domain
from packages.shared.observability.langsmith import (
    get_langsmith_tracing_context,
    traceable,
)
from packages.shared.orchestration.chief_of_staff import build_trace
from packages.shared.orchestration.planner import make_plan
from packages.shared.schemas.orchestrator import OrchestratorRequest
from packages.shared.schemas.planner import (
    Plan,
    PlanRequest,
    PlanResponse,
    PlanStep,
    StepResult,
)
from packages.shared.validation.plan import grounded_items, validate_step_grounding

logger = logging.getLogger(__name__)


class PlannerState(TypedDict, total=False):
    """State carried through the supervisor graph."""

    request: PlanRequest
    plan: Plan
    planner_usage: dict[str, int]
    # Parallel run_step branches each append one result; the reducer merges them.
    step_results: Annotated[list[StepResult], operator.add]
    response: PlanResponse


class StepState(TypedDict):
    """Payload sent to one run_step branch."""

    request: PlanRequest
    step: PlanStep
    planner_used: str


@traceable(name="planner.run_plan_graph", run_type="chain")
def run_plan_graph(request: PlanRequest) -> PlanResponse:
    """Plan, execute every step, and return the merged, validated response."""
    with get_langsmith_tracing_context():
        final_state = _PLANNER_GRAPH.invoke({"request": request, "step_results": []})
    return final_state["response"]


@traceable(name="planner.make_plan", run_type="chain")
def plan_node(state: PlannerState) -> PlannerState:
    plan, usage = make_plan(state["request"])
    return {"plan": plan, "planner_usage": usage}


def dispatch_steps(state: PlannerState) -> list[Send]:
    """Fan out one run_step branch per plan step."""
    plan = state["plan"]
    return [
        Send(
            "run_step",
            {"request": state["request"], "step": step, "planner_used": plan.planner_used},
        )
        for step in plan.steps
    ]


@traceable(name="planner.run_step", run_type="chain")
def run_step(state: StepState) -> PlannerState:
    request, step = state["request"], state["step"]
    spec = get_domain(step.workflow_id)
    # Re-validate even though the planner already did: run_step is the boundary
    # where a tool input becomes a workflow call.
    tool_input = spec.tool.input_model.model_validate(step.tool_input)
    domain_request = spec.request_from_tool_input(tool_input, request.operator_settings())

    try:
        result = spec.run(domain_request)
        validate_step_grounding(result)
    except ValueError as exc:
        logger.warning("Plan step %d (%s) failed: %s", step.step_id, step.workflow_id, exc)
        return {
            "step_results": [
                StepResult(
                    step_id=step.step_id,
                    workflow_id=step.workflow_id,
                    status="error",
                    error=str(exc),
                )
            ]
        }

    trace_request = OrchestratorRequest(
        workflow=spec.workflow_id,
        data_path=tool_input.data_path,
        focus=tool_input.focus,
        max_documents=tool_input.max_documents,
        **request.operator_settings(),
    )
    trace = build_trace(
        trace_request, spec.workflow_id, result, routing_model=state["planner_used"]
    )
    return {
        "step_results": [
            StepResult(
                step_id=step.step_id,
                workflow_id=step.workflow_id,
                status="ok",
                trace=trace,
                result=result,
            )
        ]
    }


@traceable(name="planner.merge_results", run_type="chain")
def merge_results(state: PlannerState) -> PlannerState:
    request, plan = state["request"], state["plan"]
    steps = sorted(state.get("step_results", []), key=lambda result: result.step_id)

    ok_steps = [step for step in steps if step.status == "ok"]
    if ok_steps and len(ok_steps) == len(steps):
        status = "ok"
    elif ok_steps:
        status = "partial"
    else:
        status = "error"

    item_count = sum(len(grounded_items(step.result)) for step in ok_steps)
    evidence_count = sum(len(step.result.evidence) for step in ok_steps)
    summary = (
        f"{len(ok_steps)}/{len(steps)} steps returned grounded output; "
        f"{item_count} items validated against {evidence_count} evidence lines."
    )

    return {
        "response": PlanResponse(
            goal=request.goal,
            status=status,
            plan=plan,
            steps=steps,
            validation_summary=summary,
            planner_usage=state.get("planner_usage", {}),
        )
    }


def _build_planner_graph():
    graph = StateGraph(PlannerState)
    graph.add_node("make_plan", plan_node)
    graph.add_node("run_step", run_step)
    graph.add_node("merge_results", merge_results)
    graph.add_edge(START, "make_plan")
    graph.add_conditional_edges("make_plan", dispatch_steps, ["run_step"])
    graph.add_edge("run_step", "merge_results")
    graph.add_edge("merge_results", END)
    return graph.compile()


_PLANNER_GRAPH = _build_planner_graph()
