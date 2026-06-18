from __future__ import annotations

import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from interview_os.workflows.interview_brief import build_interview_brief
from one_on_one_os.workflows.meeting_brief import build_meeting_brief
from packages.shared.agents.researcher import ResearcherAgent
from packages.shared.agents.writer import WriterAgent
from packages.shared.mcp.orchestrator_integration import run_with_mcp_tools
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.interview_os import InterviewBriefRequest
from packages.shared.schemas.one_on_one_os import OneOnOneRequest
from packages.shared.schemas.orchestrator import (
    AgentCall,
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowTrace,
)

logger = logging.getLogger(__name__)

DIRECTOR_WORKFLOW = "director_os.weekly_update"
BRAND_WORKFLOW = "brand_os.content_draft"
INTERVIEW_WORKFLOW = "interview_os.brief"
ONE_ON_ONE_WORKFLOW = "one_on_one_os.brief"
DETERMINISTIC_SUMMARY_PREFIX = "Weekly update synthesized from local project evidence"
BRAND_ROUTING_KEYWORDS = (
    "podcast",
    "linkedin",
    "thought leadership",
    "brand",
    "content",
)
DIRECTOR_ROUTING_KEYWORDS = ("leadership", "weekly update", "operating review")
INTERVIEW_ROUTING_KEYWORDS = (
    "interview",
    "candidate",
    "hiring",
    "interviewer",
    "screening",
    "debrief",
)
ONE_ON_ONE_ROUTING_KEYWORDS = (
    "1:1",
    "1on1",
    "one-on-one",
    "direct report",
    "meeting prep",
    "check-in",
)

_ROUTING_SYSTEM_PROMPT = (
    "You are a workflow router. Reply with exactly one word — either "
    "'director_os', 'brand_os', 'interview_os', or 'one_on_one_os' — with no punctuation "
    "or explanation.\n"
    "Use 'brand_os' for: content creation, LinkedIn posts, podcasts, thought "
    "leadership, brand strategy, writing, or social media.\n"
    "Use 'interview_os' for: interview prep, candidate briefs, hiring questions, "
    "screening notes, or candidate research.\n"
    "Use 'one_on_one_os' for: 1:1 meeting prep, direct report check-ins, manager "
    "notes, action item tracking, team health, or meeting briefs.\n"
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
    effective_use_model = request.use_model if use_model_override is None else use_model_override
    if workflow == DIRECTOR_WORKFLOW:
        return build_weekly_update(
            WeeklyUpdateRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
                use_model=effective_use_model,
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
                use_model=effective_use_model,
                provider=request.provider,
                claude_model=request.claude_model,
                fallback_to_deterministic=request.fallback_to_deterministic,
            )
        )

    if workflow == INTERVIEW_WORKFLOW:
        return build_interview_brief(
            InterviewBriefRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
                use_model=effective_use_model,
                provider=request.provider,
                claude_model=request.claude_model,
                fallback_to_deterministic=request.fallback_to_deterministic,
            )
        )

    if workflow == ONE_ON_ONE_WORKFLOW:
        return build_meeting_brief(
            OneOnOneRequest(
                data_path=request.data_path,
                focus=request.focus or request.prompt,
                max_documents=request.max_documents,
                use_model=effective_use_model,
                provider=request.provider,
                claude_model=request.claude_model,
                fallback_to_deterministic=request.fallback_to_deterministic,
            )
        )

    raise ValueError(
        "Unsupported workflow. Current supported workflows: "
        f"{DIRECTOR_WORKFLOW}, {BRAND_WORKFLOW}, {INTERVIEW_WORKFLOW}, {ONE_ON_ONE_WORKFLOW}."
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

    routing_model_id = f"ollama/{model}"
    if content == "brand_os":
        return (
            BRAND_WORKFLOW,
            f"Selected {BRAND_WORKFLOW} via Ollama classification ({model}).",
            routing_model_id,
        )
    if content == "director_os":
        return (
            DIRECTOR_WORKFLOW,
            f"Selected {DIRECTOR_WORKFLOW} via Ollama classification ({model}).",
            routing_model_id,
        )
    if content == "interview_os":
        return (
            INTERVIEW_WORKFLOW,
            f"Selected {INTERVIEW_WORKFLOW} via Ollama classification ({model}).",
            routing_model_id,
        )
    if content == "one_on_one_os":
        return (
            ONE_ON_ONE_WORKFLOW,
            f"Selected {ONE_ON_ONE_WORKFLOW} via Ollama classification ({model}).",
            routing_model_id,
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
    for keyword in ONE_ON_ONE_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                ONE_ON_ONE_WORKFLOW,
                f"Selected {ONE_ON_ONE_WORKFLOW} because the prompt matched '{keyword}'.",
            )
    for keyword in INTERVIEW_ROUTING_KEYWORDS:
        if keyword in lowered:
            return (
                INTERVIEW_WORKFLOW,
                f"Selected {INTERVIEW_WORKFLOW} because the prompt matched '{keyword}'.",
            )
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

    usage = getattr(result, "provider_usage", {})
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    model_supported = True
    section_counts = result.section_counts

    if workflow == DIRECTOR_WORKFLOW:
        fallback_used = request.use_model and result.summary.startswith(
            DETERMINISTIC_SUMMARY_PREFIX
        )
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
    elif workflow in (BRAND_WORKFLOW, INTERVIEW_WORKFLOW, ONE_ON_ONE_WORKFLOW):
        model_used = bool(usage)
        fallback_used = request.use_model and not model_used
        provider_used = request.provider if model_used else None
        model_id_used = request.claude_model if model_used else None
    else:
        raise ValueError(
            f"_build_trace: unrecognised workflow {workflow!r}. "
            "Add an explicit branch for each new domain."
        )

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
