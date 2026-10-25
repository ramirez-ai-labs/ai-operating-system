from __future__ import annotations

import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

from packages.shared.agents.researcher import ResearcherAgent
from packages.shared.agents.writer import WriterAgent
from packages.shared.domains import (
    DOMAINS,
    DomainSpec,
    default_domain,
    domain_for_routing_token,
    get_domain,
    keyword_routing_order,
)
from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools
from packages.shared.schemas.orchestrator import (
    AgentCall,
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowTrace,
)

logger = logging.getLogger(__name__)


def _build_routing_system_prompt() -> str:
    """Build the one-word classification prompt from the domain registry.

    Each registered domain contributes its routing token and routing hint, so
    the prompt can never list a domain that is not registered or miss one that is.
    """
    specs = list(DOMAINS.values())
    tokens = [f"'{spec.domain}'" for spec in specs]
    either = ", ".join(tokens[:-1]) + f", or {tokens[-1]}"
    lines = [
        "You are a workflow router. Reply with exactly one word — either "
        f"{either} — with no punctuation or explanation."
    ]
    lines += [
        f"Use '{spec.domain}' for: {spec.routing_hint}."
        for spec in specs
        if not spec.is_default
    ]
    default = default_domain()
    lines.append(f"Use '{default.domain}' for everything else: {default.routing_hint}.")
    return "\n".join(lines)


_ROUTING_SYSTEM_PROMPT = _build_routing_system_prompt()


def route_request(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route an incoming request to the correct domain workflow."""
    if request.workflow:
        workflow = request.workflow
        rationale = f"Workflow explicitly requested: {workflow}."
        routing_model = "explicit"
    else:
        workflow, rationale, routing_model = _select_workflow(request)

    # When use_mcp=True, run the MCP retrieval loop first so Claude reads
    # project files via tool calls and produces the primary synthesis.
    # _run_workflow then runs with use_model forced off — we only need its
    # structured evidence and section counts, not a redundant model call.
    mcp_tool_calls: list[dict] = []
    mcp_synthesis: str | None = None
    if request.use_mcp:
        mcp_response = run_with_mcp_tools(
            prompt=request.prompt or request.focus or "Synthesize project status",
            data_path=request.data_path,
            model=request.claude_model,
        )
        mcp_tool_calls = mcp_response.trace.get("mcp_tool_calls", [])
        if mcp_response.success:
            mcp_synthesis = mcp_response.content

    result = _run_workflow(
        request,
        workflow,
        use_model_override=False if request.use_mcp else None,
    )

    # Researcher → writer multi-agent pipeline. Only runs when target_audience
    # is set. Both agents require ANTHROPIC_API_KEY — the ValueError raised by
    # each agent if the key is absent propagates to the caller, which is the
    # correct behavior since this path is explicitly opt-in.
    formatted_content: str | None = None
    agent_calls: list[AgentCall] = []
    if request.target_audience:
        researcher = ResearcherAgent(model=request.claude_model)
        synthesis, researcher_call = researcher.synthesize(
            focus=request.focus or request.prompt,
            evidence=result.evidence,
        )
        agent_calls.append(researcher_call)

        writer = WriterAgent(model=request.claude_model)
        formatted_content, writer_call = writer.format(
            synthesis=synthesis,
            target_audience=request.target_audience,
        )
        agent_calls.append(writer_call)

    return OrchestratorResponse(
        selected_workflow=workflow,
        rationale=rationale,
        trace=_build_trace(
            request,
            workflow,
            result,
            mcp_tool_calls=mcp_tool_calls,
            agent_calls=agent_calls,
            routing_model=routing_model,
        ),
        result=result,
        formatted_content=formatted_content,
        mcp_synthesis=mcp_synthesis,
    )


def _run_workflow(
    request: OrchestratorRequest,
    workflow: str,
    use_model_override: bool | None = None,
):
    """Adapt the generic request into the selected workflow contract and execute it."""
    spec = get_domain(workflow)
    effective_use_model = request.use_model if use_model_override is None else use_model_override
    return spec.run(spec.build_request(request, effective_use_model))


def _select_workflow(request: OrchestratorRequest) -> tuple[str, str, str]:
    """Choose a workflow using Ollama classification with keyword fallback.

    Returns (workflow, rationale, routing_model_id) so the trace can surface
    which routing path was taken — LLM classification or keyword rules.
    """
    workflow, rationale, routing_model = _classify_with_ollama(
        prompt=request.prompt,
        ollama_url=request.ollama_url,
        model=request.ollama_model,
    )
    return workflow, rationale, routing_model


def _classify_with_ollama(
    prompt: str | None,
    ollama_url: str,
    model: str,
) -> tuple[str, str, str]:
    """Call Ollama to classify the prompt. Falls back to keyword rules on any failure."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt or "summarize project status"},
        ],
        "stream": False,
    }).encode("utf-8")

    http_req = urllib_request.Request(
        url=f"{ollama_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(http_req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["message"]["content"].strip().lower()
    except urllib_error.URLError as exc:
        logger.warning(
            "Ollama unreachable at %s (%s) — falling back to keyword routing",
            ollama_url, exc,
        )
        workflow, rationale = _select_workflow_keyword(prompt)
        return workflow, rationale, f"keyword-match (ollama/{model} unreachable)"
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error(
            "Ollama returned unexpected response (%s) — falling back to keyword routing",
            exc,
        )
        workflow, rationale = _select_workflow_keyword(prompt)
        return workflow, rationale, f"keyword-match (ollama/{model} malformed response)"
    except Exception as exc:
        logger.error(
            "Unexpected error during Ollama routing: %s — falling back to keyword routing",
            exc, exc_info=True,
        )
        workflow, rationale = _select_workflow_keyword(prompt)
        return workflow, rationale, f"keyword-match (ollama/{model} error)"

    spec = domain_for_routing_token(content)
    if spec is not None:
        return (
            spec.workflow_id,
            f"Selected {spec.workflow_id} via Ollama classification ({model}).",
            f"ollama/{model}",
        )
    # Model did not return a recognised token — fall back to keyword rules.
    logger.warning(
        "Ollama returned unexpected routing token %r — falling back to keyword routing",
        content,
    )
    workflow, rationale = _select_workflow_keyword(prompt)
    return workflow, rationale, f"keyword-match (ollama/{model} unexpected token)"


def _select_workflow_keyword(prompt: str | None) -> tuple[str, str]:
    """Keyword fallback router — used when Ollama is unavailable."""
    lowered = (prompt or "").lower()
    for spec in keyword_routing_order():
        for keyword in spec.routing_keywords:
            if keyword in lowered:
                return (
                    spec.workflow_id,
                    f"Selected {spec.workflow_id} because the prompt matched '{keyword}'.",
                )
    default = default_domain()
    return default.workflow_id, f"Selected {default.workflow_id} as the default workflow."


def _build_trace(
    request: OrchestratorRequest,
    workflow: str,
    result,
    mcp_tool_calls: list[dict] | None = None,
    agent_calls: list[AgentCall] | None = None,
    routing_model: str = "keyword-match",
) -> WorkflowTrace:
    """Summarize the execution path in a shape that operators can inspect easily."""
    spec: DomainSpec = get_domain(workflow)
    evidence_sources = list(dict.fromkeys(item.source for item in result.evidence))
    focus_used = request.focus or request.prompt

    usage = getattr(result, "provider_usage", {})
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)

    # Each domain decides how to tell whether its model path produced the
    # result (e.g. Director OS checks the deterministic summary prefix).
    model_used = spec.model_used(request, result)
    fallback_used = request.use_model and not model_used
    if model_used:
        provider_used = request.provider
        model_id_used = (
            request.claude_model if request.provider == "claude" else request.ollama_model
        )
    else:
        provider_used = None
        model_id_used = None

    return WorkflowTrace(
        data_path=request.data_path,
        focus_used=focus_used,
        evidence_count=len(result.evidence),
        evidence_sources=evidence_sources,
        model_requested=request.use_model,
        model_supported=True,
        model_used=model_used,
        provider_used=provider_used,
        model_id_used=model_id_used,
        fallback_used=fallback_used,
        section_counts=result.section_counts,
        validation_summary=(
            f"Grounded output assembled from {len(result.evidence)} evidence items "
            f"across {len(evidence_sources)} source files."
        ),
        routing_model=routing_model,
        mcp_tool_calls=mcp_tool_calls or [],
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_creation,
        agent_calls=agent_calls or [],
    )
