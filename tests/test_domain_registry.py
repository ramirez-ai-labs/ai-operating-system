"""Contract tests for the domain registry (packages/shared/domains).

These encode the domain-addition checklist from CLAUDE.md as assertions: a
domain that is registered but missing its evals, CI step, API route, MCP tool,
or response-union entry fails here instead of in review.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import typing
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.api.main import app
from apps.mcp.server import create_server
from packages.shared.domains import (
    DOMAINS,
    _validate,
    default_domain,
    domain_for_routing_token,
    get_domain,
    keyword_routing_order,
    tool_definitions,
)
from packages.shared.domains.spec import DomainToolInput
from packages.shared.orchestration.chief_of_staff import (
    _ROUTING_SYSTEM_PROMPT,
    _select_workflow_keyword,
)
from packages.shared.schemas.base import BaseResponse
from packages.shared.schemas.orchestrator import OrchestratorResponse

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "tests" / "snapshots" / "domain_tool_definitions.json"

# Settings that belong to the operator's request, never to a model's tool call.
OPERATOR_ONLY_FIELDS = {
    "provider",
    "claude_model",
    "ollama_model",
    "ollama_url",
    "use_model",
    "fallback_to_deterministic",
}

SPECS = list(DOMAINS.values())
SPEC_IDS = [spec.domain for spec in SPECS]


def test_registry_contains_the_four_domains_in_registration_order() -> None:
    assert list(DOMAINS) == [
        "director_os.weekly_update",
        "brand_os.content_draft",
        "interview_os.brief",
        "one_on_one_os.brief",
    ]


def test_registry_is_read_only() -> None:
    with pytest.raises(TypeError):
        DOMAINS["new.workflow"] = SPECS[0]  # type: ignore[index]
    with pytest.raises(dataclasses.FrozenInstanceError):
        SPECS[0].api_path = "/elsewhere"  # type: ignore[misc]


@pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
def test_response_model_inherits_base_response(spec) -> None:
    assert issubclass(spec.response_model, BaseResponse)


def test_orchestrator_response_union_matches_registry() -> None:
    union = OrchestratorResponse.model_fields["result"].annotation
    assert set(typing.get_args(union)) == {spec.response_model for spec in SPECS}


@pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
def test_domain_has_evals_and_ci_gate(spec) -> None:
    assert (REPO_ROOT / "packages" / "shared" / "evaluations" / f"{spec.domain}.py").is_file()
    assert list((REPO_ROOT / "evaluations" / spec.domain).glob("*_cases.json"))
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert f"scripts/run_{spec.domain}_evals.py" in ci


@pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
def test_domain_is_served_by_the_api(spec) -> None:
    routes = {(route.path, method) for route in app.routes for method in route.methods or ()}
    assert (spec.api_path, "POST") in routes


def test_mcp_server_exposes_exactly_the_registered_tools() -> None:
    tools = asyncio.run(create_server().list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == {spec.tool.name for spec in SPECS}
    for spec in SPECS:
        assert by_name[spec.tool.name].description == spec.tool.description


def test_routing_prompt_offers_every_domain_and_puts_the_default_last() -> None:
    for spec in SPECS:
        assert f"'{spec.domain}'" in _ROUTING_SYSTEM_PROMPT
        assert spec.routing_hint in _ROUTING_SYSTEM_PROMPT
    last_line = _ROUTING_SYSTEM_PROMPT.splitlines()[-1]
    assert last_line.startswith(f"Use '{default_domain().domain}' for everything else")


def test_routing_tokens_map_back_to_their_domains() -> None:
    for spec in SPECS:
        assert domain_for_routing_token(spec.domain) is spec
    assert domain_for_routing_token("engineering_os") is None


def test_keyword_fallback_checks_more_specific_domains_first() -> None:
    order = [spec.domain for spec in keyword_routing_order()]
    assert order == ["one_on_one_os", "interview_os", "brand_os", "director_os"]
    # "1:1" outranks "interview"; "interview" outranks "leadership".
    assert _select_workflow_keyword("1:1 about interview loops")[0] == "one_on_one_os.brief"
    assert _select_workflow_keyword("leadership interview debrief")[0] == "interview_os.brief"


def test_unknown_workflow_lists_registered_ones() -> None:
    with pytest.raises(ValueError, match="Unsupported workflow") as exc:
        get_domain("engineering_os.repo_review")
    for workflow_id in DOMAINS:
        assert workflow_id in str(exc.value)


def test_tool_definitions_match_committed_snapshot() -> None:
    committed = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert tool_definitions() == committed, (
        "Model-facing tool definitions changed. If intended, regenerate with "
        "`python -m packages.shared.domains --write` and commit the diff."
    )


@pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
def test_tool_input_schema_hides_operator_settings(spec) -> None:
    properties = set(spec.tool.to_tool_definition()["input_schema"]["properties"])
    assert {"focus", "data_path", "max_documents"} <= properties
    assert not properties & OPERATOR_ONLY_FIELDS


@pytest.mark.parametrize("spec", SPECS, ids=SPEC_IDS)
def test_tool_input_default_data_path_is_valid(spec) -> None:
    assert spec.tool.input_model().data_path.startswith("data/local_only/")


@pytest.mark.parametrize(
    "data_path",
    ["data/local_only/projects", "data/local_only", "data\\local_only\\brand"],
)
def test_tool_input_accepts_paths_under_allowed_root(data_path: str) -> None:
    assert DomainToolInput(data_path=data_path).data_path == data_path


@pytest.mark.parametrize(
    "data_path",
    [
        "data/local_only/../../etc",
        "/etc/passwd",
        "C:/Windows",
        "data/other",
        "data/local_only_backup",
        "projects",
    ],
)
def test_tool_input_rejects_paths_outside_allowed_root(data_path: str) -> None:
    with pytest.raises(ValidationError):
        DomainToolInput(data_path=data_path)


def test_validate_rejects_inconsistent_registries() -> None:
    director, brand = DOMAINS["director_os.weekly_update"], DOMAINS["brand_os.content_draft"]

    with pytest.raises(ValueError, match="Duplicate domain keyword_priority"):
        _validate((director, dataclasses.replace(brand, keyword_priority=40)))
    with pytest.raises(ValueError, match="exactly one default"):
        _validate((dataclasses.replace(director, is_default=False), brand))
    with pytest.raises(ValueError, match="exactly one default"):
        _validate((director, dataclasses.replace(brand, is_default=True)))
    with pytest.raises(ValueError, match="must start with domain"):
        _validate((director, dataclasses.replace(brand, workflow_id="other.content_draft")))
