"""Planner: turn a goal into a plan of domain tool calls (Phase 9b).

Three planners share one output contract (`Plan`):

- **rules** (default) — deterministic. Splits the goal into clauses and routes
  each with the same keyword rules as the Chief of Staff router. Needs no
  model, so the planner works in CI and with no API keys.
- **ollama** / **claude** — the model receives every registered domain as a
  tool (`tool_definitions()` from the domain registry) and plans by making
  parallel tool calls. Planning *is* tool selection.

A model plan is never trusted as-is. Every call must name a registered tool,
its arguments must validate against that domain's narrow `DomainToolInput`
(which rejects `data_path` outside data/local_only/ and has no provider/model
fields), and the plan must stay within `max_steps`. Any failure — no API key,
Ollama unreachable, malformed output, an invalid call — falls back to the
rules planner when `fallback_to_deterministic=True`, and the reason is
recorded on the plan.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib import request as urllib_request

from pydantic import ValidationError

from packages.shared.domains import default_domain, domain_for_tool_name, tool_definitions
from packages.shared.orchestration.chief_of_staff import match_keyword
from packages.shared.schemas.planner import Plan, PlanRequest, PlanStep

logger = logging.getLogger(__name__)

# Clause boundaries for the rules planner: separators and joining words that
# usually start a new deliverable ("X, Y and Z", "X; then Y").
_CLAUSE_SPLIT = re.compile(r"[;\n]+|,|&|\s+(?:and|then|plus|also)\s+", flags=re.IGNORECASE)

PLANNER_SYSTEM_PROMPT = (
    "You are the AI-OS planner. Break the operator's goal into calls to the workflow "
    "tools provided. Call one tool per distinct deliverable the goal asks for. If the "
    "goal names several people or topics for the same kind of deliverable, call that "
    "tool once for each. Set `focus` to the specific person, project, or topic for that "
    "deliverable. Leave `data_path` at its default unless the goal names a folder. Make "
    "all calls in a single response and do not reply with text. Use at most {max_steps} "
    "calls."
)


class PlannerError(Exception):
    """A model planner could not produce a valid plan. Carries any tokens already spent."""

    def __init__(self, message: str, usage: dict[str, int] | None = None) -> None:
        super().__init__(message)
        self.usage = usage or {}


def make_plan(request: PlanRequest) -> tuple[Plan, dict[str, int]]:
    """Build a plan for the request. Returns (plan, planner token usage)."""
    if request.planner == "rules":
        return plan_with_rules(request.goal, request.max_steps), {}

    try:
        calls, planner_id, usage = _MODEL_PLANNERS[request.planner](request)
        try:
            steps = steps_from_tool_calls(calls, request.max_steps, planner_id)
        except PlannerError as exc:
            # The model call succeeded and spent tokens; keep them on the record.
            exc.usage = usage
            raise
    except PlannerError as exc:
        if not request.fallback_to_deterministic:
            raise ValueError(f"{request.planner} planner failed: {exc}") from exc
        logger.warning(
            "%s planner failed (%s) — falling back to rules planner", request.planner, exc
        )
        plan = plan_with_rules(request.goal, request.max_steps)
        return (
            plan.model_copy(
                update={"planner_requested": request.planner, "fallback_reason": str(exc)}
            ),
            exc.usage,
        )

    plan = Plan(
        goal=request.goal,
        steps=steps,
        planner_requested=request.planner,
        planner_used=planner_id,
    )
    return plan, usage


def plan_with_rules(goal: str, max_steps: int) -> Plan:
    """Deterministic planner: one step per clause that matches a domain's keywords."""
    steps: list[PlanStep] = []
    notes: list[str] = []
    seen: set[tuple[str, str]] = set()

    for raw_clause in _CLAUSE_SPLIT.split(goal):
        clause = raw_clause.strip(" .:-")
        match = match_keyword(clause)
        if not clause or match is None:
            continue
        spec, keyword = match
        key = (spec.workflow_id, clause.lower())
        if key in seen:
            continue
        seen.add(key)
        steps.append(
            _rules_step(
                step_id=len(steps) + 1,
                spec=spec,
                focus=clause,
                rationale=f"Clause {clause!r} matched {keyword!r}.",
            )
        )

    if not steps:
        spec = default_domain()
        steps.append(
            _rules_step(
                step_id=1,
                spec=spec,
                focus=goal.strip(),
                rationale="No clause matched a domain keyword; using the default workflow.",
            )
        )

    if len(steps) > max_steps:
        notes.append(f"Plan truncated from {len(steps)} to {max_steps} steps (max_steps).")
        steps = steps[:max_steps]

    return Plan(
        goal=goal,
        steps=steps,
        planner_requested="rules",
        planner_used="rules",
        notes=notes,
    )


def _rules_step(*, step_id: int, spec, focus: str, rationale: str) -> PlanStep:
    tool_input = spec.tool.input_model(focus=focus)
    return PlanStep(
        step_id=step_id,
        workflow_id=spec.workflow_id,
        tool_name=spec.tool.name,
        tool_input=tool_input.model_dump(),
        rationale=rationale,
    )


def steps_from_tool_calls(
    calls: list[tuple[str, Any]],
    max_steps: int,
    planner_id: str,
) -> list[PlanStep]:
    """Validate a model's tool calls and turn them into plan steps.

    Raises PlannerError on the first problem; the caller decides whether to
    fall back. Nothing a model returns reaches a workflow without passing the
    domain's DomainToolInput validation.
    """
    if not calls:
        raise PlannerError("planner returned no tool calls")
    if len(calls) > max_steps:
        raise PlannerError(f"planner returned {len(calls)} steps; max_steps is {max_steps}")

    steps: list[PlanStep] = []
    for index, (name, arguments) in enumerate(calls, start=1):
        spec = domain_for_tool_name(name)
        if spec is None:
            raise PlannerError(f"planner called unknown tool {name!r}")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError as exc:
                raise PlannerError(f"arguments for {name!r} are not valid JSON") from exc
        if not isinstance(arguments, dict):
            raise PlannerError(f"arguments for {name!r} must be an object")
        try:
            tool_input = spec.tool.input_model.model_validate(arguments)
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(part) for part in first["loc"]) or "input"
            raise PlannerError(
                f"invalid arguments for {name!r}: {location}: {first['msg']}"
            ) from exc
        steps.append(
            PlanStep(
                step_id=index,
                workflow_id=spec.workflow_id,
                tool_name=spec.tool.name,
                tool_input=tool_input.model_dump(),
                rationale=f"Chosen by {planner_id}.",
            )
        )
    return steps


def _plan_with_claude(request: PlanRequest) -> tuple[list[tuple[str, Any]], str, dict[str, int]]:
    provider = _build_claude_provider(request)
    planner_id = f"claude/{request.claude_model}"
    if not provider.is_available():
        raise PlannerError("Claude planner unavailable: ANTHROPIC_API_KEY is not set")

    response = provider.complete(
        prompt=request.goal,
        tools=tool_definitions(),
        system_override=PLANNER_SYSTEM_PROMPT.format(max_steps=request.max_steps),
        tool_choice={"type": "any"},
    )
    usage = {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens}
    if not response.success:
        raise PlannerError(f"Claude planner call failed: {response.content}", usage)
    calls = [(call["name"], call["input"]) for call in response.tool_calls]
    logger.info("Claude planner proposed %d step(s)", len(calls))
    return calls, planner_id, usage


def _build_claude_provider(request: PlanRequest):
    """Construct the Claude provider. Patchable in tests and evals."""
    from packages.shared.providers.claude_provider import ClaudeProvider

    return ClaudeProvider(model=request.claude_model)


def _plan_with_ollama(request: PlanRequest) -> tuple[list[tuple[str, Any]], str, dict[str, int]]:
    planner_id = f"ollama/{request.ollama_model}"
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tool_definitions()
    ]
    payload = json.dumps(
        {
            "model": request.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": PLANNER_SYSTEM_PROMPT.format(max_steps=request.max_steps),
                },
                {"role": "user", "content": request.goal},
            ],
            "tools": tools,
            "stream": False,
        }
    ).encode("utf-8")
    http_request = urllib_request.Request(
        url=f"{request.ollama_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(http_request, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except OSError as exc:
        # URLError covers refused connections, but a read timeout is a bare
        # TimeoutError and a dropped connection a ConnectionResetError. All are
        # OSError, and all must fall back to rules rather than fail the request.
        raise PlannerError(f"Ollama unreachable at {request.ollama_url}: {exc!r}") from exc
    except json.JSONDecodeError as exc:
        raise PlannerError("Ollama returned a non-JSON response") from exc

    usage = {
        "input_tokens": int(body.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(body.get("eval_count", 0) or 0),
    }
    try:
        raw_calls = body["message"].get("tool_calls") or []
        calls = [
            (call["function"]["name"], call["function"].get("arguments", {}))
            for call in raw_calls
        ]
    except (KeyError, TypeError, AttributeError) as exc:
        raise PlannerError("Ollama response is missing message.tool_calls", usage) from exc
    return calls, planner_id, usage


_MODEL_PLANNERS = {
    "claude": _plan_with_claude,
    "ollama": _plan_with_ollama,
}
