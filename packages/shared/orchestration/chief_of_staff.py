from __future__ import annotations

import json
from urllib import request as urllib_request

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.agents.researcher import ResearcherAgent
from packages.shared.agents.writer import WriterAgent
from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.orchestrator import (
    AgentCall,
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowTrace,
)

DIRECTOR_WORKFLOW = "director_os.weekly_update"
BRAND_WORKFLOW = "brand_os.content_draft"
DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"
BRAND_ROUTING_KEYWORDS = (
    "podcast",
    "linkedin",
    "thought leadership",
    "brand",
    "content",
)
DIRECTOR_ROUTING_KEYWORDS = ("leadership", "weekly update", "operating review")

_ROUTING_SYSTEM_PROMPT = (
    "You are a workflow router. Reply with exactly one word — either "
    "'director_os' or 'brand_os' — with no punctuation or explanation.\n"
    "Use 'brand_os' for: content creation, LinkedIn posts, podcasts, thought "
    "leadership, brand strategy, writing, or social media.\n"
    "Use 'director_os' for everything else: status updates, project reviews, "
    "leadership summaries, risk tracking, or weekly updates."
)


def route_request(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route an incoming request to the correct domain workflow."""
    if request.workflow:
        workflow = request.workflow
        rationale = f"Workflow explicitly requested: {workflow}."
        routing_model = "explicit"
    else:
        workflow, rationale, routing_model = _select_workflow(request)

    result = _run_workflow(request, workflow)

    # When use_mcp=True, run the MCP retrieval loop so Claude reads project
    # files via tool calls. The tool call log is surfaced in the trace so
    # operators can see exactly what the agent read before synthesizing.
    mcp_tool_calls: list[dict] = []
    if request.use_mcp:
        mcp_response = run_with_mcp_tools(
            prompt=request.prompt or request.focus or "Synthesize project status",
            data_path=request.data_path,
            model=request.claude_model,
        )
        mcp_tool_calls = mcp_response.trace.get("mcp_tool_calls", [])

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
    )


def _run_workflow(request: OrchestratorRequest, workflow: str):
    """Adapt the generic request into the selected workflow contract and execute it."""
    if workflow == DIRECTOR_WORKFLOW:
        return build_weekly_update(
            WeeklyUpdateRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
                use_model=request.use_model,
                fallback_to_deterministic=request.fallback_to_deterministic,
                # Keep provider choice at the workflow boundary so routing can
                # stay deterministic while synthesis remains explicitly opt-in.
                provider=request.provider,
                ollama_url=request.ollama_url,
                ollama_model=request.ollama_model,
                claude_model=request.claude_model,
            )
        )

    if workflow == BRAND_WORKFLOW:
        return build_content_draft(
            BrandContentDraftRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
            )
        )

    raise ValueError(
        "Unsupported workflow. Current supported workflows: "
        f"{DIRECTOR_WORKFLOW}, {BRAND_WORKFLOW}."
    )


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
    except Exception:
        return _select_workflow_keyword(prompt) + (f"keyword-match (ollama/{model} unreachable)",)

    routing_model_id = f"ollama/{model}"
    if "brand" in content:
        return (
            BRAND_WORKFLOW,
            f"Selected {BRAND_WORKFLOW} via Ollama classification ({model}).",
            routing_model_id,
        )
    return (
        DIRECTOR_WORKFLOW,
        f"Selected {DIRECTOR_WORKFLOW} via Ollama classification ({model}).",
        routing_model_id,
    )


def _select_workflow_keyword(prompt: str | None) -> tuple[str, str]:
    """Keyword fallback router — used when Ollama is unavailable."""
    lowered = (prompt or "").lower()
    for keyword in BRAND_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                BRAND_WORKFLOW,
                f"Selected {BRAND_WORKFLOW} because the prompt matched '{keyword}'.",
            )
    for keyword in DIRECTOR_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                DIRECTOR_WORKFLOW,
                f"Selected {DIRECTOR_WORKFLOW} because the prompt matched '{keyword}'.",
            )
    return DIRECTOR_WORKFLOW, f"Selected {DIRECTOR_WORKFLOW} as the default workflow."


def _build_trace(
    request: OrchestratorRequest,
    workflow: str,
    result,
    mcp_tool_calls: list[dict] | None = None,
    agent_calls: list[AgentCall] | None = None,
    routing_model: str = "keyword-match",
) -> WorkflowTrace:
    """Summarize the execution path in a shape that operators can inspect easily."""
    evidence_sources = list(dict.fromkeys(item.source for item in result.evidence))
    focus_used = request.focus or request.prompt

    if workflow == DIRECTOR_WORKFLOW:
        fallback_used = request.use_model and result.summary.startswith(
            DETERMINISTIC_SUMMARY_PREFIX
        )
        section_counts = {
            "wins": len(result.wins),
            "risks": len(result.risks),
            "next_steps": len(result.next_steps),
        }
        model_supported = True
        model_used = request.use_model and not fallback_used
        if model_used:
            provider_used = request.provider
            model_id_used = (
                request.claude_model if request.provider == "claude"
                else request.ollama_model
            )
        else:
            provider_used = None
            model_id_used = None

        # Surface prompt-cache savings when the Claude provider was used.
        usage = getattr(result, "provider_usage", {})
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_creation = usage.get("cache_creation_input_tokens", 0)
    else:
        fallback_used = False
        section_counts = {
            "post_outline": len(result.post_outline),
            "podcast_angles": len(result.podcast_angles),
            "repo_improvements": len(result.repo_improvements),
        }
        model_supported = False
        model_used = False
        provider_used = None
        model_id_used = None
        cache_read = 0
        cache_creation = 0

    return WorkflowTrace(
        data_path=request.data_path,
        focus_used=focus_used,
        evidence_count=len(result.evidence),
        evidence_sources=evidence_sources,
        model_requested=request.use_model,
        model_supported=model_supported,
        model_used=model_used,
        provider_used=provider_used,
        model_id_used=model_id_used,
        fallback_used=fallback_used,
        section_counts=section_counts,
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
