"""Tests for the planner/supervisor (Phase 9b).

No test here reaches a real model: the Claude planner is exercised through a
patched `_build_claude_provider`, and the Ollama planner through a patched
`urlopen`.
"""

from __future__ import annotations

import json
from collections import Counter
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.domains import DOMAINS
from packages.shared.evaluations.planner import (
    load_planner_eval_cases,
    run_local_planner_evaluations,
    summarize_planner_results,
)
from packages.shared.graphs.planner import run_plan_graph
from packages.shared.orchestration import planner as planner_module
from packages.shared.orchestration.planner import make_plan, plan_with_rules
from packages.shared.providers.claude_provider import ProviderResponse
from packages.shared.schemas.base import GroundedItem
from packages.shared.schemas.planner import OPERATOR_SETTING_FIELDS, PlanRequest

_PREP_MY_WEEK = (
    "Prep my week: leadership update, 1:1 brief for Priya, "
    "and a LinkedIn post on the platform migration"
)


def _workflows(plan) -> list[str]:
    return [step.workflow_id for step in plan.steps]


# ---------------------------------------------------------------------------
# Rules planner
# ---------------------------------------------------------------------------


def test_rules_planner_splits_goal_into_one_step_per_deliverable() -> None:
    plan = plan_with_rules(_PREP_MY_WEEK, max_steps=5)
    assert _workflows(plan) == [
        "director_os.weekly_update",
        "one_on_one_os.brief",
        "brand_os.content_draft",
    ]
    assert [step.step_id for step in plan.steps] == [1, 2, 3]
    assert plan.planner_used == "rules"
    assert plan.fallback_reason is None


def test_rules_planner_uses_each_domains_default_data_path() -> None:
    plan = plan_with_rules(_PREP_MY_WEEK, max_steps=5)
    data_paths = {step.workflow_id: step.tool_input["data_path"] for step in plan.steps}
    assert data_paths == {
        "director_os.weekly_update": "data/local_only/projects",
        "one_on_one_os.brief": "data/local_only/one_on_one",
        "brand_os.content_draft": "data/local_only/brand",
    }


def test_rules_planner_keeps_repeat_domains_with_different_focus() -> None:
    plan = plan_with_rules("1:1 prep for Marcus; 1:1 prep for Sarah", max_steps=5)
    assert _workflows(plan) == ["one_on_one_os.brief", "one_on_one_os.brief"]
    assert [step.tool_input["focus"] for step in plan.steps] == [
        "1:1 prep for Marcus",
        "1:1 prep for Sarah",
    ]


def test_rules_planner_drops_exact_duplicate_clauses() -> None:
    plan = plan_with_rules("1:1 prep for Marcus, 1:1 prep for Marcus", max_steps=5)
    assert _workflows(plan) == ["one_on_one_os.brief"]


def test_rules_planner_uses_default_domain_when_nothing_matches() -> None:
    plan = plan_with_rules("help me get ready for tomorrow", max_steps=5)
    assert _workflows(plan) == ["director_os.weekly_update"]
    assert plan.steps[0].tool_input["focus"] == "help me get ready for tomorrow"


def test_rules_planner_truncates_to_max_steps_and_says_so() -> None:
    plan = plan_with_rules(
        "1:1 prep for Marcus; 1:1 prep for Sarah; 1:1 prep for Priya", max_steps=2
    )
    assert len(plan.steps) == 2
    assert "truncated from 3 to 2" in plan.notes[0]


# ---------------------------------------------------------------------------
# Claude planner (patched provider — never a live call)
# ---------------------------------------------------------------------------


def _fake_claude(tool_calls, *, available=True, success=True):
    provider = MagicMock()
    provider.is_available.return_value = available
    provider.complete.return_value = ProviderResponse(
        content="" if success else "[ClaudeProvider error] boom",
        model="claude-test",
        input_tokens=120,
        output_tokens=40,
        tool_calls=[
            {"id": f"t{i}", "name": name, "input": args}
            for i, (name, args) in enumerate(tool_calls)
        ],
        success=success,
    )
    return provider


def _patch_claude(monkeypatch, provider) -> None:
    monkeypatch.setattr(planner_module, "_build_claude_provider", lambda _request: provider)


def test_claude_planner_turns_parallel_tool_calls_into_steps(monkeypatch) -> None:
    provider = _fake_claude(
        [
            ("one_on_one_os_brief", {"focus": "Priya promotion case", "direct_report": "Priya"}),
            ("interview_os_brief", {"focus": "Alex Chen", "candidate_name": "Alex Chen"}),
        ]
    )
    _patch_claude(monkeypatch, provider)

    plan, usage = make_plan(PlanRequest(goal="Get ready for Priya and Alex", planner="claude"))

    assert _workflows(plan) == ["one_on_one_os.brief", "interview_os.brief"]
    assert plan.planner_used.startswith("claude/")
    assert plan.fallback_reason is None
    assert plan.steps[0].tool_input["direct_report"] == "Priya"
    # Defaults from the domain's tool input model are filled in.
    assert plan.steps[1].tool_input["data_path"] == "data/local_only/interviews"
    assert usage == {"input_tokens": 120, "output_tokens": 40}


def test_claude_planner_is_offered_every_registered_domain_and_must_call_a_tool(
    monkeypatch,
) -> None:
    provider = _fake_claude([("director_os_weekly_update", {"focus": "status"})])
    _patch_claude(monkeypatch, provider)

    make_plan(PlanRequest(goal="status", planner="claude", max_steps=3))

    kwargs = provider.complete.call_args.kwargs
    assert [tool["name"] for tool in kwargs["tools"]] == [
        spec.tool.name for spec in DOMAINS.values()
    ]
    assert kwargs["tool_choice"] == {"type": "any"}
    assert "at most 3" in kwargs["system_override"]


@pytest.mark.parametrize(
    ("tool_calls", "reason"),
    [
        ([], "no tool calls"),
        ([("engineering_os_review", {})], "unknown tool"),
        ([("brand_os_content_draft", {"data_path": "../../etc"})], "invalid arguments"),
        ([("brand_os_content_draft", {"data_path": "/etc/passwd"})], "invalid arguments"),
        (
            [("brand_os_content_draft", {"data_path": "data/local_only/linkedin_posts"})],
            "not an existing directory",
        ),
        ([("director_os_weekly_update", {"max_documents": 500})], "invalid arguments"),
        ([("director_os_weekly_update", "not json")], "not valid JSON"),
        ([("director_os_weekly_update", {})] * 6, "max_steps is 5"),
    ],
)
def test_invalid_claude_plan_falls_back_to_rules_with_reason(
    monkeypatch, tool_calls, reason
) -> None:
    _patch_claude(monkeypatch, _fake_claude(tool_calls))

    plan, usage = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="claude"))

    assert plan.planner_requested == "claude"
    assert plan.planner_used == "rules"
    assert reason in plan.fallback_reason
    assert len(plan.steps) == 3
    # Tokens spent on the rejected plan are still reported.
    assert usage == {"input_tokens": 120, "output_tokens": 40}


def test_claude_planner_without_api_key_falls_back_without_calling(monkeypatch) -> None:
    provider = _fake_claude([], available=False)
    _patch_claude(monkeypatch, provider)

    plan, usage = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="claude"))

    provider.complete.assert_not_called()
    assert "ANTHROPIC_API_KEY" in plan.fallback_reason
    assert usage == {}


def test_claude_provider_failure_falls_back(monkeypatch) -> None:
    _patch_claude(monkeypatch, _fake_claude([], success=False))
    plan, _ = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="claude"))
    assert "Claude planner call failed" in plan.fallback_reason


def test_planner_failure_raises_when_fallback_disabled(monkeypatch) -> None:
    _patch_claude(monkeypatch, _fake_claude([("engineering_os_review", {})]))
    with pytest.raises(ValueError, match="claude planner failed: planner called unknown tool"):
        make_plan(
            PlanRequest(goal=_PREP_MY_WEEK, planner="claude", fallback_to_deterministic=False)
        )


# ---------------------------------------------------------------------------
# Ollama planner (patched urlopen — never a live call)
# ---------------------------------------------------------------------------


def _ollama_response(tool_calls: list[dict]):
    body = json.dumps(
        {
            "message": {"role": "assistant", "content": "", "tool_calls": tool_calls},
            "prompt_eval_count": 300,
            "eval_count": 25,
        }
    ).encode("utf-8")
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = lambda self: self
    response.__exit__ = MagicMock(return_value=False)
    return response


def test_ollama_planner_parses_tool_calls_with_dict_or_string_arguments() -> None:
    calls = [
        {"function": {"name": "brand_os_content_draft", "arguments": {"focus": "migration wins"}}},
        {"function": {"name": "director_os_weekly_update", "arguments": '{"focus": "risks"}'}},
    ]
    with patch("urllib.request.urlopen", return_value=_ollama_response(calls)) as urlopen:
        plan, usage = make_plan(PlanRequest(goal="share wins; status", planner="ollama"))

    assert _workflows(plan) == ["brand_os.content_draft", "director_os.weekly_update"]
    assert plan.planner_used == "ollama/llama3.2"
    assert usage == {"input_tokens": 300, "output_tokens": 25}

    sent = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
    assert [tool["function"]["name"] for tool in sent["tools"]] == [
        spec.tool.name for spec in DOMAINS.values()
    ]
    # Operator-only settings are never offered to the model.
    for tool in sent["tools"]:
        assert not set(tool["function"]["parameters"]["properties"]) & set(
            OPERATOR_SETTING_FIELDS
        )


def test_ollama_unreachable_falls_back_to_rules() -> None:
    with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
        plan, usage = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="ollama"))
    assert plan.planner_used == "rules"
    assert "Ollama unreachable" in plan.fallback_reason
    assert usage == {}


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timed out"), ConnectionResetError("Remote end closed connection")],
    ids=["read-timeout", "connection-reset"],
)
def test_ollama_transport_errors_fall_back_to_rules(error) -> None:
    # A read timeout is a bare TimeoutError, not a URLError. It used to escape
    # make_plan and fail the whole request on a slow Ollama host.
    with patch("urllib.request.urlopen", side_effect=error):
        plan, usage = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="ollama"))
    assert plan.planner_used == "rules"
    assert plan.planner_requested == "ollama"
    assert "Ollama unreachable" in plan.fallback_reason
    assert usage == {}


def test_ollama_text_only_reply_falls_back_to_rules() -> None:
    with patch("urllib.request.urlopen", return_value=_ollama_response([])):
        plan, _ = make_plan(PlanRequest(goal=_PREP_MY_WEEK, planner="ollama"))
    assert "no tool calls" in plan.fallback_reason


# ---------------------------------------------------------------------------
# Supervisor graph
# ---------------------------------------------------------------------------


def test_supervisor_runs_every_step_and_returns_grounded_results() -> None:
    response = run_plan_graph(
        PlanRequest(goal="Interview prep for Alex Chen and 1:1 with Sarah about blockers")
    )

    assert response.status == "ok"
    assert [step.workflow_id for step in response.steps] == [
        "interview_os.brief",
        "one_on_one_os.brief",
    ]
    for step in response.steps:
        assert step.status == "ok"
        assert step.result.evidence
        assert step.trace.routing_model == "rules"
        assert step.trace.evidence_count == len(step.result.evidence)
    assert "2/2 steps returned grounded output" in response.validation_summary


def test_supervisor_applies_operator_settings_to_every_step(monkeypatch) -> None:
    from one_on_one_os.workflows.meeting_brief import build_meeting_brief as real_build

    captured: dict[str, object] = {}

    def capture(request):
        captured["request"] = request
        return real_build(request)

    spec = DOMAINS["one_on_one_os.brief"]
    monkeypatch.setattr("one_on_one_os.workflows.meeting_brief.build_meeting_brief", capture)
    run_plan_graph(
        PlanRequest(
            goal="1:1 with Sarah about blockers",
            use_model=True,
            provider="ollama",
            claude_model="claude-test-model",
        )
    )
    request = captured["request"]
    assert isinstance(request, spec.request_model)
    assert request.use_model is True
    assert request.provider == "ollama"
    assert request.claude_model == "claude-test-model"
    assert request.focus == "1:1 with Sarah about blockers"


def test_failed_step_is_reported_and_other_steps_still_complete(monkeypatch) -> None:
    def failing_brief(_request):
        raise ValueError("Meeting brief must include at least one populated section.")

    monkeypatch.setattr(
        "one_on_one_os.workflows.meeting_brief.build_meeting_brief", failing_brief
    )
    response = run_plan_graph(PlanRequest(goal="Leadership weekly update and 1:1 with Priya"))

    assert response.status == "partial"
    by_workflow = {step.workflow_id: step for step in response.steps}
    assert by_workflow["director_os.weekly_update"].status == "ok"
    failed = by_workflow["one_on_one_os.brief"]
    assert failed.status == "error"
    assert "populated section" in failed.error
    assert failed.result is None


def test_merge_rejects_a_step_whose_output_is_not_grounded(monkeypatch) -> None:
    """Even if a workflow regresses, the merged response never carries an uncited item."""
    from director_os.workflows.weekly_update import build_weekly_update as real_build

    def tampered(request):
        response = real_build(request)
        response.wins.append(
            GroundedItem(text="Invented win with no source", source="nowhere.md", line_number=1)
        )
        return response

    monkeypatch.setattr("director_os.workflows.weekly_update.build_weekly_update", tampered)
    response = run_plan_graph(PlanRequest(goal="Prepare my leadership weekly update"))

    assert response.status == "error"
    assert response.steps[0].status == "error"
    assert "existing evidence" in response.steps[0].error


def test_supervisor_reports_planner_fallback_on_the_response(monkeypatch) -> None:
    _patch_claude(monkeypatch, _fake_claude([], available=False))
    response = run_plan_graph(
        PlanRequest(goal="Interview prep for Alex Chen and 1:1 with Sarah about blockers",
                    planner="claude")
    )
    assert response.plan.planner_requested == "claude"
    assert response.plan.planner_used == "rules"
    assert "ANTHROPIC_API_KEY" in response.plan.fallback_reason
    assert response.status == "ok"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

client = TestClient(app)


def test_plan_endpoint_returns_merged_response() -> None:
    response = client.post(
        "/plan",
        json={"goal": "Interview prep for Alex Chen and 1:1 with Sarah about blockers"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["plan"]["planner_used"] == "rules"
    assert len(body["steps"]) == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"goal": ""},
        {"goal": "status", "planner": "gpt"},
        {"goal": "status", "max_steps": 0},
        {"goal": "status", "max_steps": 9},
    ],
)
def test_plan_endpoint_rejects_invalid_requests(payload) -> None:
    assert client.post("/plan", json=payload).status_code == 422


def test_plan_endpoint_returns_400_when_planner_fails_without_fallback(monkeypatch) -> None:
    _patch_claude(monkeypatch, _fake_claude([], available=False))
    response = client.post(
        "/plan",
        json={"goal": "status", "planner": "claude", "fallback_to_deterministic": False},
    )
    assert response.status_code == 400
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Evals
# ---------------------------------------------------------------------------


def test_rules_planner_passes_every_rules_supported_eval_case() -> None:
    results = run_local_planner_evaluations(load_planner_eval_cases())
    failures = [r["case_id"] for r in results if not r["passed"]]
    assert not failures
    assert len(results) == sum(case.rules_supported for case in load_planner_eval_cases())


def test_eval_summary_reports_where_the_rules_planner_falls_short() -> None:
    """Scoring the rules planner on *every* case shows the gap a model planner should close."""
    cases = load_planner_eval_cases()
    plans = [plan_with_rules(case.goal, case.max_steps) for case in cases]
    summary = summarize_planner_results(cases, plans)

    unsupported = [case for case in cases if not case.rules_supported]
    assert unsupported, "keep semantic cases in the set so model planners are measured"
    assert summary["exact_match_rate"] < 1.0
    for case, plan in zip(cases, plans, strict=True):
        actual = Counter(step.workflow_id for step in plan.steps)
        assert (actual == Counter(case.expected_workflows)) == case.rules_supported, case.id
