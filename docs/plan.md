# AI-OS Project Plan

## Purpose

This plan defines the execution path for turning AI-OS from a strong early MVP into a complete, credible local-first AI operating system.

The plan is intentionally phased.
Each phase has:

- a clear objective
- concrete deliverables
- explicit exit criteria

This is meant to keep the project grounded, avoid scope creep, and preserve alignment with the README and AGENTS guidance.

## Current State

The repository currently includes:

- project documentation in `README.md` with Mermaid architecture diagram and "Why Claude" section
- four workflow domains on a shared LangGraph foundation:
  - `Director OS`  -  evidence-grounded weekly leadership updates with Claude tool use, prompt caching, Ollama fallback, and deterministic baseline
  - `Brand OS`  -  content drafts (LinkedIn posts, podcast angles, repo improvements) from local brand notes; Claude-backed synthesis path available
  - `Interview OS`  -  candidate prep briefs (key questions, talking points, red flags) from local interview notes; Claude-backed synthesis path available
  - `One-on-One OS`  -  meeting briefs for 1:1s (action items, talking points, blockers, kudos) from direct-report notes; Claude-backed synthesis path available
- a Chief of Staff orchestration layer with Ollama LLM classification routing and keyword fallback, supporting all four domains
- ChromaDB semantic retrieval backed by Ollama `nomic-embed-text` embeddings, with flat-file fallback
- a `ResearcherAgent → WriterAgent` multi-agent pipeline for audience-targeted content formatting
- prompt caching on the Claude provider with cache metrics surfaced in every `WorkflowTrace`
- an in-process Claude filesystem tool loop for MCP-style local retrieval traces
- a standalone MCP server under `apps/mcp` exposing all four workflow domains as tools for Claude Desktop / Claude Code
- realistic enterprise scenario datasets under `data/local_only/` for all four domains
- a local operator console at `/` with provider selection, target audience, `use_mcp` toggle, cache hit display, and agent pipeline visualization
- `validate_response` node + `route_after_validation` conditional edge in all four domain graphs; model output that fails validation falls back to deterministic path
- shared grounding primitives in `packages/shared/providers/grounding.py`; `GROUNDED_ITEM_SCHEMA` and `parse_grounded_items` are the single source of truth across all providers
- `BaseResponse` base schema in `packages/shared/schemas/base.py` enforcing `evidence`, `provider_usage`, and `section_counts` across all four domain schemas
- ChromaDB staleness detection: per-path pre-flight document count before querying; clear warning + keyword fallback when collection exists but has no docs for the requested `data_root`
- unified `scripts/run_evals.py` dispatcher auto-discovering domains from `packages/shared/evaluations/`; `--domain`, `--backend`, `--langsmith`, `--ci` flags replace 12 standalone scripts
- `config/models.yaml` as the single source of truth for default model IDs, read by `packages/shared/config/models.py`; the validated default is test-enforced
- 402 tests passing (6 skipped without API keys); local evals for all four domains and the planner routing/planning set in CI; chroma evals skip gracefully when index absent
- optional LangSmith tracing with `@traceable` on all graph nodes across all four domains
- issue templates, `CONTRIBUTING.md`, branch protection on `main`

The repository also includes:

- a Next.js frontend under `apps/web` with domain tabs, workflow form, results pane, and trace pane (shipped Phase 8, PRs #104–105), plus a Plan tab for `/plan` (Sprint 29); type-checked and built in CI

## Guiding Principles

All phases should preserve the core project standards:

- local-first by default
- cost-conscious execution
- grounded outputs
- deterministic workflows where practical
- agentic behavior only where it materially improves outcomes
- human-in-the-loop review
- simple, inspectable architecture
- framework choices that remain subordinate to the AI-OS product model

## Phase 1: Stabilize the Director OS MVP and Align the Docs

### Objective

Turn the current `Director OS` weekly update slice into a reliable and defensible foundation while aligning the docs with the actual repo and intended framework direction.

### Deliverables

- Update `README.md`, `AGENTS.md`, and `plan.md` so they describe AI-OS as the product and the `lang*` stack as implementation infrastructure
- Commit and stabilize the current CI/CD workflows
- Improve evidence quality in retrieval
- Filter headings and non-action lines from returned evidence
- Constrain local data access to approved local roots for the MVP
- Attach explicit source references to output items where practical
- Strengthen validation rules for evidence-backed output, especially for model-assisted drafts
- Add more local sample data to test multi-file retrieval
- Expand tests for retrieval ranking, provider failures, and validation edge cases

### Exit Criteria

- `README.md` and `AGENTS.md` are aligned with the real codebase
- The roadmap reflects the LangGraph-first implementation direction without turning the repo into a framework demo
- `Director OS` output is consistently grounded in meaningful evidence
- CI passes on branch and pull request workflows
- The MVP can be run locally from documented quickstart steps without guesswork

### Status

- Implemented: docs are largely aligned around AI-OS as the product and the `lang*` stack as infrastructure
- Implemented: CI/CD workflows, evidence grounding, multi-file retrieval, explicit evidence lineage, and stronger validation
- Implemented: local sample datasets for `Director OS` and `Brand OS`
- Remaining work: keep the roadmap and contributor docs current as the repo expands beyond the first workflows

## Phase 2: LangGraph Workflow Foundation for Director OS

### Objective

Complete and stabilize the first explicit `LangGraph` workflow foundation for `Director OS` while keeping the API contract and AI-OS terminology stable.

### Deliverables

- Define a `Director OS` graph with explicit nodes such as request intake, retrieval, draft generation, validation, and final response assembly
- Keep the first graph primarily deterministic, with model use remaining optional and bounded
- Keep the current FastAPI routes stable so the graph remains an internal implementation detail rather than an API redesign
- Add tests for graph state transitions, failure behavior, and deterministic fallback paths
- Document the graph at the workflow level, not as a framework showcase

### Exit Criteria

- `Director OS` runs through an explicit graph with inspectable state transitions
- The public API and product language remain AI-OS-centered
- The refactor improves control and observability without increasing conceptual noise

### Status

- Implemented for `Director OS`: explicit graph nodes for retrieval, draft generation, response assembly, validation, and deterministic fallback
- Implemented: the first `Brand OS` workflow now uses the same shared graph-oriented pattern

## Phase 3: Add LangSmith Tracing and Evaluation

### Objective

Add workflow visibility and quality measurement so agentic behavior can be introduced without losing trust or inspectability.

### Deliverables

- Wire `LangSmith` tracing into the main `Director OS` workflow path
- Capture workflow-level traces for retrieval, draft generation, validation, and fallback behavior
- Define evaluation cases for strong retrieval, weak retrieval, malformed model output, and unsupported claims
- Create a small repeatable local eval dataset for `Director OS`
- Document how traces and evals support AI-OS workflow development

### Exit Criteria

- A `Director OS` run can be traced end-to-end
- Workflow changes can be compared against a stable evaluation set
- Observability improves confidence without reframing the repo as a LangSmith demo

### Status

- Implemented for `Director OS`: optional LangSmith tracing, a checked-in evaluation set, and a CLI runner
- Implemented for `Brand OS`: a checked-in local evaluation set and a CLI runner
- Current run modes:
  - on-demand local evals with `python scripts/run_director_os_evals.py`
  - on-demand LangSmith evals with `python scripts/run_director_os_evals.py --langsmith`
- Current enforcement:
  - local evals run in CI through `python scripts/run_director_os_evals.py`
  - Brand OS local evals run in CI through `python scripts/run_brand_os_evals.py`
  - LangSmith-backed evals remain on-demand only
- Remaining work: broaden evaluation coverage in both domains and extend the same pattern to more workflows

## Phase 4: Expand the Chief of Staff and Brand OS on the Shared Graph Foundation

### Objective

Use the shared foundation to support multi-domain routing while keeping workflows explicit and bounded.

### Deliverables

- Refactor the Chief of Staff routing layer so it selects between graph-backed workflows with clearer rationale and traceability
- Reuse shared retrieval, schemas, validation, and provider logic across domains
- Add more workflow-specific tests around routing decisions and failure behavior
- Add more realistic sample datasets for both `Director OS` and `Brand OS`

### Exit Criteria

- AI-OS supports at least two real workflows across different domains on a shared foundation
- Routing remains explicit, testable, and explainable
- The multi-domain AI-OS story is supported by actual code instead of docs alone

### Status

- Implemented: Chief of Staff routing plus graph-backed `Director OS`, `Brand OS`, `Interview OS`, and `One-on-One OS` workflows on the shared foundation
- Remaining work: decide where additional graph-backed domains add enough value to justify the pattern-match work

## Phase 5: Improve Model Reliability and Bounded Agentic Behavior

### Objective

Make model-assisted and selectively agentic behavior more reliable without weakening grounding or operator trust.

### Deliverables

- Define deterministic fallback behavior when Ollama is unavailable
- Improve provider error handling and structured output parsing
- Fix or replace weak evidence attachment strategies in the model-assisted path
- Introduce bounded agentic steps only where they materially improve the workflow
- Expand eval coverage for weak retrieval, malformed model output, unsupported claims, and agentic branch behavior

### Exit Criteria

- Ollama-backed generation is usable in normal local development
- Agentic branches remain bounded, observable, and easy to disable
- The validator meaningfully improves output trustworthiness

### Status

- Implemented: deterministic fallback when Ollama is unavailable
- Implemented: provider error handling in both Ollama and Claude adapters
- Implemented: structured output validation via the shared validator
- Implemented: bounded agentic steps via the `ResearcherAgent → WriterAgent` pipeline (Phase 5g, Sprint 7)
- Implemented: broader eval coverage for weak retrieval and malformed model output (Sprints 14–17)
- Implemented: automated test coverage for provider adapters and MCP orchestration paths (Sprint 3, PR #52; Sprint 10a, PR #70)

## Phase 5b: Claude Provider and Layered LLM Architecture

### Objective

Introduce Anthropic Claude as a first-class provider alongside Ollama, and establish a layered LLM architecture where local models handle routing and cost-sensitive tasks while Claude handles synthesis and structured output.

### Deliverables

- Add `ClaudeWeeklyUpdateProvider` implementing the existing `WeeklyUpdateProvider` interface via Anthropic SDK tool use
- Add `provider` field to `WeeklyUpdateRequest` with `"ollama"` and `"claude"` options
- Add `claude_model` field to `WeeklyUpdateRequest`, defaulting to `claude-haiku-4-5-20251001` for cost-conscious operation
- Extract `_build_provider` factory in the Director OS graph to support clean provider injection and test patching
- Add `--provider claude` flag to the eval runner to run the full eval set against the Claude provider
- Add Claude-specific eval tests that skip cleanly when `ANTHROPIC_API_KEY` is not set
- Add `.env.example` documenting all required environment variables for local setup
- Wire `ANTHROPIC_API_KEY` and `LANGSMITH_API_KEY` through `.env` for local development

### Layered LLM Design

| Layer | Model | Purpose |
| --- | --- | --- |
| Intent routing / classification | Ollama `llama3.2` (local) | Replace keyword if/else with LLM classification  -  free, fast, zero data egress |
| Semantic embeddings | Ollama `nomic-embed-text` (local) | ChromaDB index generation  -  unified local model dependency, zero cost |
| Structured synthesis | Claude Haiku (API) | Tool use, citation grounding, structured output  -  primary synthesis path |
| Complex / premium synthesis | Claude Sonnet / Opus (API) | Multi-document, extended thinking, high-stakes  -  on demand |
| Offline fallback synthesis | Ollama `llama3.2` (local) | When `ANTHROPIC_API_KEY` absent  -  system stays functional for local dev and airgapped demos |

### Exit Criteria

- Claude and Ollama are interchangeable providers behind the same `WeeklyUpdateProvider` interface
- The operator console exposes provider selection so the layered architecture is visible and demonstrable
- Claude evals pass the same scorers as the deterministic baseline
- Local setup requires only filling in `.env` from `.env.example`  -  no undocumented steps

### Status

- Implemented: `packages/shared/providers/claude.py` with Anthropic SDK tool use for structured output
- Implemented: `provider` and `claude_model` fields on `WeeklyUpdateRequest`
- Implemented: `_build_provider` factory in `packages/shared/graphs/director_os.py`
- Implemented: `--provider claude` flag on `scripts/run_director_os_evals.py`
- Implemented: `scripts/run_director_os_evals_claude.py`  -  dedicated eval runner producing signal/safety scores, token counts, and real Claude response text
- Implemented: Claude-specific tests in `tests/test_director_os_evaluations.py`
- Implemented: `.env.example` with all required keys
- Implemented: provider selection is now wired through the Chief of Staff orchestrator for Director OS synthesis
- Implemented: `evaluations/director_os/results_claude.json` committed in PR #44  -  **but output shows deterministic fallback, not live Claude API responses.** Re-running `scripts/run_director_os_evals_claude.py` with `ANTHROPIC_API_KEY` and committing the result is the single remaining action for JD requirements #1 and #4.
- Implemented: live Claude eval results committed in `evaluations/director_os/results_claude.json` (PR #56)  -  3/3 cases, 100% signal and safety
- Implemented: operator console provider dropdown (Sprint 9, PR #62)
- Implemented: Claude Haiku is the default synthesis provider (Sprint 6)
- Remaining: move Ollama to routing/classification layer (Phase 5e  -  now complete, see below)
- Remaining: move Ollama to embedding layer for ChromaDB (Phase 5d  -  now complete, see Sprint 5)

## Phase 5c: MCP Server  -  Expose AI-OS Workflows as Tools

### Objective

Build an MCP (Model Context Protocol) server that exposes Director OS and Brand OS workflows as callable tools, making AI-OS composable with any MCP-compatible host including Claude Desktop, Claude Code, and enterprise integrations.

### Background

MCP is Anthropic's open standard for connecting AI models to external tools and data sources. An FDE deliverable in the field is exactly this: an MCP server a customer team can drop into their environment and immediately wire to Claude. Building one here proves the pattern end-to-end.

### Deliverables

- Add `apps/mcp/server.py` implementing an MCP server using the `mcp` Python SDK
- Expose `director_os_weekly_update` as an MCP tool backed by the existing `build_weekly_update` workflow
- Expose `brand_os_content_draft` as an MCP tool backed by the existing `build_content_draft` workflow
- Keep tool input schemas derived from the existing Pydantic request models  -  no parallel schema definitions
- Add `claude_desktop_config.json` example so the server can be wired to Claude Desktop in one step
- Add tests covering tool registration, schema correctness, and round-trip tool invocation
- Document the MCP server in `README.md` alongside the existing API entry points

### Exit Criteria

- The MCP server starts and registers both tools without errors
- A Claude Desktop or Claude Code session can invoke `director_os_weekly_update` and receive a grounded structured response
- Tool schemas match the Pydantic request contracts  -  no drift
- Tests pass in CI without requiring a live Claude connection

### Status

- Implemented: `apps/mcp/server.py` standalone MCP server using the `mcp` Python SDK  -  shipped in PR #50
- Implemented: `director_os_weekly_update` and `brand_os_content_draft` both registered as MCP tools
- Implemented: `packages/shared/mcp/filesystem_server.py` exposes read-only local filesystem tools
- Implemented: `packages/shared/mcp/orchestrator_integration.py` runs a bounded Claude tool-use loop and surfaces `mcp_tool_calls` in `/orchestrate` traces
- Implemented: `mcp` SDK added to `pyproject.toml`
- Implemented: `claude_desktop_config.json` example for one-step Claude Desktop wiring
- Implemented: `tests/test_mcp_server.py` and `tests/test_claude_mcp.py`  -  all server-level tests passing
- Implemented: MCP server documented in `README.md` alongside existing API entry points (Sprint 4, PR #60)

## Phase 5d: ChromaDB  -  Upgrade Retrieval to Semantic Vector Search

### Objective

Replace the current flat-file keyword retrieval in `packages/shared/retrieval/local_files.py` with ChromaDB-backed semantic search, making evidence retrieval more accurate and the RAG story credible for enterprise use cases.

### Context

The current retrieval layer reads markdown files and filters by keyword match. This works for the MVP but breaks down with larger or noisier document sets  -  exactly the kind of data an enterprise customer brings. ChromaDB with Ollama-generated embeddings gives semantic similarity search without requiring a cloud vector database or a separate Python embedding dependency, preserving the local-first posture and unifying the local model stack under Ollama.

### Deliverables

- Add `packages/shared/retrieval/chroma.py` implementing the same retrieval interface as `local_files.py`
- Use ChromaDB with a local persistent store under `data/chroma/` (gitignored)
- Use Ollama `nomic-embed-text` for embedding generation  -  unified local model dependency, no `sentence-transformers` required
- Add an ingestion script `scripts/ingest_local_data.py` that indexes `data/local_only/` into ChromaDB
- Keep the existing flat-file retrieval as a fallback when no ChromaDB index exists or Ollama is unavailable
- Add `chromadb` to `pyproject.toml` dependencies (no `sentence-transformers`  -  embeddings via Ollama)
- Add tests for semantic retrieval quality against the existing sample data
- Update `.env.example` with a `RETRIEVAL_BACKEND` variable (`local_files` or `chroma`)

### Exit Criteria

- Running `python scripts/ingest_local_data.py` indexes local documents into ChromaDB
- The Director OS workflow uses ChromaDB retrieval when `RETRIEVAL_BACKEND=chroma` is set
- Semantic search returns more relevant evidence than keyword matching for the existing eval cases
- CI passes with the flat-file backend as the default (no ChromaDB dependency for basic tests)

### Status

- Complete  -  shipped Sprint 5 (PR #57). ChromaDB with Ollama `nomic-embed-text` embeddings; flat-file fallback when index absent or Ollama unavailable. Activate with `RETRIEVAL_BACKEND=chroma` after running the ingest script.

## Phase 5e: Tiered Model Architecture  -  Ollama to Routing Layer

### Objective

Move Ollama from its current position as a parallel synthesis provider to its correct role in the tiered architecture: intent routing and semantic embeddings. Claude Haiku becomes the default synthesis path. This completes the layered LLM design described in Phase 5b and makes the cost story demonstrable end-to-end.

### Deliverables

- Replace keyword `if/else` routing in `packages/shared/orchestration/chief_of_staff.py` with an Ollama classification call  -  send the prompt with a compact system message, receive `director_os` or `brand_os` back
- Change the default `provider` on `OrchestratorRequest` from `"ollama"` to `"claude"`
- Change the operator console default from `provider=ollama` to `provider=claude`
- Demote Ollama synthesis to explicit fallback: used only when `ANTHROPIC_API_KEY` is absent or synthesis provider is explicitly set to `"ollama"`
- Update `WorkflowTrace` to surface which routing model was used alongside the synthesis model

### Exit Criteria

- The default `/orchestrate` call uses Ollama for routing and Claude Haiku for synthesis
- When `ANTHROPIC_API_KEY` is absent the system falls back to Ollama synthesis transparently
- The trace shows the routing model and synthesis model separately so the tier split is visible to operators

### Status

- Complete  -  shipped Sprint 6 + Phase 5e follow-up. `chief_of_staff.py` calls Ollama `/api/chat` with a compact classification prompt; falls back to keyword routing when Ollama is unreachable. `WorkflowTrace.routing_model` reflects the actual path taken (`"ollama/llama3.2"`, `"keyword-match (ollama/... unreachable)"`, or `"explicit"`).

## Phase 5f: MCP Agentic Loop as Default Path + Prompt Caching

### Objective

Add opt-in MCP-first synthesis (`use_mcp=True`) so the Director OS experience can route through the Claude filesystem tool loop instead of the standard graph retrieval path. Add Anthropic prompt caching to cut repeated-context costs by 80-90% and surface cache savings in the operator trace.

### Deliverables

- Wire `orchestrator_integration.py` into the default Director OS path when `ANTHROPIC_API_KEY` is set  -  Claude decides what to read via tool calls rather than the keyword scorer pre-selecting
- Add `cache_control` to the evidence block in `packages/shared/providers/claude.py`  -  mark the evidence list as a cacheable prefix
- Extend `WorkflowTrace` with `cache_read_tokens` and `cache_creation_tokens` fields populated from the Anthropic response usage block
- Operator console renders "Cache hit: X tokens saved" when `cache_read_tokens > 0`
- Keep `use_mcp=False` path available for environments where stdio MCP is not viable

### Exit Criteria

- Running `/orchestrate` with an API key shows Claude tool calls in the trace by default
- A second identical request shows non-zero `cache_read_tokens` in the trace
- The operator console surfaces both pieces of information without requiring raw JSON inspection

### Status

- Complete  -  shipped Sprint 6. `cache_control: {"type": "ephemeral"}` on the system prompt in `packages/shared/providers/claude.py`; `cache_read_input_tokens` and `cache_creation_input_tokens` surface in every `WorkflowTrace`. Operator console renders cache hit/primed metrics.  -  [#60](https://github.com/ramirez-ai-labs/ai-operating-system/pull/60) / [#61](https://github.com/ramirez-ai-labs/ai-operating-system/pull/61)

## Phase 5g: Multi-Agent Researcher → Writer

### Objective

Add a two-agent workflow demonstrating Claude-to-Claude orchestration. A researcher agent retrieves and synthesizes evidence using filesystem tools; a writer agent takes the synthesis and formats it for a specific target audience. The pattern matters more than the use case  -  it shows multi-agent orchestration at the level an Anthropic FE needs to explain and demo to enterprise customers.

### Deliverables

- `packages/shared/agents/researcher.py`  -  Claude with filesystem MCP tools; returns a structured synthesis of retrieved evidence
- `packages/shared/agents/writer.py`  -  Claude takes researcher output and formats for a specified audience: `linkedin_post`, `executive_brief`, or `team_update`
- New `target_audience` field on `OrchestratorRequest`  -  when set, Chief of Staff routes through researcher → writer pipeline instead of the single-agent path
- New `/orchestrate` trace fields: `agent_calls` list showing researcher and writer invocations with token counts
- Tests covering the handoff contract between researcher and writer

### Exit Criteria

- `POST /orchestrate` with `target_audience=executive_brief` returns a formatted brief with a visible two-agent trace
- The researcher and writer are independent Claude instances with separate system prompts and tool access
- The pattern is documented in `README.md` as the multi-agent example

### Status

- Complete  -  shipped Sprint 7. `ResearcherAgent` uses Claude tool use to return a structured `ResearchSynthesis`; `WriterAgent` formats it for `linkedin_post`, `executive_brief`, or `team_update`. Both agents record per-invocation token counts (including cache fields) in `AgentCall` entries on the `WorkflowTrace`.  -  [#60](https://github.com/ramirez-ai-labs/ai-operating-system/pull/60) / [#61](https://github.com/ramirez-ai-labs/ai-operating-system/pull/61)

## Phase 5h: Realistic Demo Data + "Why Claude" Framing

### Objective

Replace the 5 toy markdown files with a realistic enterprise scenario and add a "Why Claude" section to `README.md` that explains what this system does that cannot be done as cleanly with another LLM.

### Deliverables

- Replace `data/local_only/projects/` with a realistic quarterly planning scenario: platform migration in progress, cross-team dependencies, budget cycle pressures, open risks
- Replace `data/local_only/brand/` with a realistic brand scenario: upcoming conference talk, podcast pipeline, LinkedIn content backlog
- Add `README.md` "Why Claude" section covering: forced tool use for hallucination-resistant citation grounding, MCP for composability with any Claude-compatible host, prompt caching for enterprise cost control, multi-agent for workflow separation
- Update the architecture diagram in `README.md` to show the tiered model layers (Ollama routing → Ollama embeddings → Claude synthesis → Claude writer)

### Exit Criteria

- A hiring manager or enterprise customer running the demo gets back output that tells a recognizable story
- The README explains the Claude-specific design decisions rather than describing them as generic LLM patterns

### Status

- Complete  -  shipped Sprint 8. Realistic quarterly planning scenario under `data/local_only/projects/`; realistic brand scenario under `data/local_only/brand/`. "Why Claude" section and Mermaid architecture diagram added to `README.md`.  -  [#59](https://github.com/ramirez-ai-labs/ai-operating-system/pull/59)

## Phase 6: Add a Lightweight Local UI and Optional Langflow Demo Layer

### Objective

Expose workflow execution in a way that supports both usability and project credibility without turning the repo into a framework showcase.

### Deliverables

- Add a local UI under `apps/web`
- Show workflow request, selected path, evidence, validation outcome, trace summary, and final output
- Keep the UI focused on traceability rather than “agents chatting”
- Support desktop-first local operation with simple run instructions
- Optionally add `Langflow` exports or demo flows for visual exploration without making them the canonical workflow definitions

### Exit Criteria

- A user can run the system locally through a UI
- The UI improves traceability and operator control
- Any Langflow usage supports demos and prototyping without displacing the core codebase

### Status

- Implemented: operator console at `/` through `apps/api` with provider selector, target audience dropdown, cache hit metrics, agent pipeline card (researcher → writer with per-agent token counts), and formatted content card
- Shipped in Sprint 9  -  [#62](https://github.com/ramirez-ai-labs/ai-operating-system/pull/62)
- Implemented: dedicated `apps/web` Next.js frontend with domain tabs, workflow form, results pane, and trace pane  -  [#104](https://github.com/ramirez-ai-labs/ai-operating-system/pull/104), [#105](https://github.com/ramirez-ai-labs/ai-operating-system/pull/105)

## Phase 7: Harden the Project for Ongoing Growth

### Objective

Turn the MVP into a sustainable open-source project with a repeatable engineering workflow.

### Deliverables

- Add branch protection requirements for `main`
- Add issue templates for features, bugs, and workflow improvements
- Add a contributor workflow document
- Improve release tagging and artifact handling
- Add milestone definitions or roadmap tracking for future phases

### Exit Criteria

- The project has a clear SDLC path for future contributors
- Quality checks and review standards are enforced consistently
- The repository is easier to maintain as scope increases

### Status

- Implemented: GitHub topics set (`anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai`)
- Implemented: `pytest --cov` runs in CI with coverage artifact upload
- Implemented: FastAPI / Starlette compatibility pinned (`starlette<1.0.0`)
- Implemented: branch protection on `main`, `.github/ISSUE_TEMPLATE/` (feature, bug, workflow), `CONTRIBUTING.md`
- Implemented: `v1.0` release tag cut (Sprint 9)

## Phase 9: From Router to Orchestrator

### Objective

Turn the Chief of Staff from a single-hop router into an orchestration layer: given a goal, decide which domain workflows to run, in what order, and with what inputs, then merge their grounded outputs — while keeping every invariant the domain workflows already guarantee (evidence grounding, deterministic fallback, CI-gated evals, no required API keys).

### Background

Today each request reaches exactly one domain, and the domain list is hardcoded across the router, the trace builder, the response union, and the API. The one model-directed path (the MCP tool loop) returns free-form text that skips grounding validation. Requests are stateless, routing accuracy is unscored, and local markdown is the only data source. The fixed domain workflows are the right foundation; Phase 9 adds the layer above them.

### Deliverables

Each item ships as its own PR, in order — later items depend on earlier ones.

- **9a  -  Domain registry.** Each domain registers its request/response schema, routing description, graph entry point, and trace builder in one place. The router, `_build_trace`, `OrchestratorResponse`, the API, and the MCP server read from the registry. Adding a domain touches the domain's own files plus one registration.
- **9b  -  Planner/supervisor graph + routing evals.** A LangGraph supervisor that breaks a goal into a plan of domain calls, runs independent steps in parallel (`Send`), and merges grounded outputs with per-step citations intact. The default planner is local (rules or Ollama); Claude is opt-in. Ships with a routing and planning eval set (routing accuracy, plan correctness) gated in CI.
- **9c  -  Grounded MCP tool loop.** The model-directed tool loop ends in the same forced-tool grounding schema and `validate_response` node as the domain workflows, with deterministic fallback. Removes the one exception to the grounding invariant.
- **9d  -  Saved state + human approval.** LangGraph checkpointing (SQLite) for resumable runs, `interrupt()` for operator approval before final output, run history surfaced in `apps/web`.
- **9e  -  External MCP data sources.** AI-OS consumes external MCP servers (GitHub first) as retrieval sources, not only exposes its own tools.
- **9f  -  Hosted demo.** A deployed read-only demo on synthetic data plus a short walkthrough video, linked from the top of the README.

### Exit Criteria

- A single goal can fan out to multiple domains, and the merged response still passes grounding validation item by item
- Routing and planning accuracy are measured and gated in CI
- No response path returns uncited content
- A run can pause for approval and resume from a checkpoint
- The system still runs end to end with no API keys

### Status

- Prerequisites (Sprint 23, [#114](https://github.com/ramirez-ai-labs/ai-operating-system/pull/114)): model IDs centralized in `config/models.yaml` with the validated default test-enforced, MCP server startup no longer imports LangGraph/ChromaDB (fixes cold-start connect timeouts), README and SHOWCASE scope wording aligned with what the system does today.
- 9a implemented (Sprint 24, [#115](https://github.com/ramirez-ai-labs/ai-operating-system/pull/115)): `packages/shared/domains/` registry. Each `DomainSpec` pairs a model-facing `DomainTool` (name, description, narrow input schema, `to_tool_definition()`) with operator-facing routing, request-building, and trace rules. The router prompt (byte-identical to the previous hand-written one), keyword fallback, `_run_workflow`, `_build_trace`, API routes, and MCP tools are all derived from it. Tool definitions are snapshotted in `tests/snapshots/domain_tool_definitions.json` so description changes show up as reviewable diffs.
- 9b implemented (Sprint 25): `POST /plan`. There are three planners: `rules` (the deterministic default), `ollama`, and `claude`. The model planners receive `tool_definitions()` and plan by making parallel tool calls; every call is validated against its domain's `DomainToolInput`, and any failure falls back to `rules` with a recorded reason. A LangGraph supervisor fans steps out with `Send`, re-validates grounding at merge (`validation/plan.py`), and returns ok / partial / error. A routing and planning eval set of 19 cases is CI-gated on the 14 the rules planner should solve. The rules planner scores 0% on the 5 keyword-free and over-split cases, which is the target for the model planners.
- Exit criteria met by 9b: one goal fans out to multiple domains and the merged response passes grounding validation item by item; routing and planning accuracy are measured and gated in CI; the system still runs end to end with no API keys.
- 9c implemented (Sprint 27, [#118](https://github.com/ramirez-ai-labs/ai-operating-system/pull/118)): the MCP tool loop runs with `tool_choice: any` and can only finish through `submit_grounded_synthesis`. `read_file` returns numbered lines, the filesystem server records every line it serves, and each submitted item must cite a served `(source, line_number)` and pass `validate_grounded_item`. One bad item drops the whole synthesis; `trace.mcp_fallback_reason` records why, and the deterministic workflow result is returned. `OrchestratorResponse.mcp_result` carries the validated items and the cited evidence. The legacy console now escapes all API content.
- Exit criterion met by 9c: no response path returns uncited content.
- Next: 9d checkpointing + human approval.
- Deferred: a fifth workflow domain (Recruiting OS). It adds breadth on the existing pattern; Phase 9 adds the orchestration depth the project is missing. With 9a in place, adding a domain no longer touches the router, API, or MCP server.

## Recommended Immediate Next Steps

Sprints 1–30 are complete. v1.2.0 is tagged and released. All four workflow domains (Director OS, Brand OS, Interview OS, One-on-One OS) have full Claude provider parity, ChromaDB eval coverage, LangSmith observability, `validate_response` + fallback routing, committed live eval results (100% pass rate each), and CI eval gates. A planner/supervisor (`POST /plan`) runs multi-domain goals in parallel, and the MCP tool loop can only return grounded content. 402 tests passing (6 skipped without API keys).

**Sprint 20  -  Debt paydown (complete, PRs #93–97):**
Shared grounding primitives extracted to `grounding.py`. Orchestrator circuit breaker and trace token flush. Ghost token capture on fallback path. `section_counts` moved into domain schemas. `_COMPETING_PREFIXES` constant. `_get_chroma_client()` singleton.

**Sprint 21  -  Validation + fallback parity (complete, PRs #98–99):**
`validate_response` node wired into Brand OS, Interview OS, and One-on-One OS graphs matching Director OS invariant. Provider-fallback tests added for all Claude-only domains.

**Sprint 22  -  ChromaDB staleness + eval dispatcher + BaseResponse (complete, PRs #100–102):**
ChromaDB per-path staleness detection. Unified `scripts/run_evals.py` dispatcher. `BaseResponse` schema contract enforced across all four domains.

**Phase 8  -  Next.js frontend (complete, PRs #104–105).**

**Sprint 23  -  Model config + MCP startup + scope wording (complete, PR #114):**
Single source of truth for model IDs in `config/models.yaml`. MCP server defers workflow imports so `initialize` answers before the client's connect timeout. README/SHOWCASE wording matches current scope.

**Sprint 24  -  Phase 9a domain registry (complete, PR #115):**
`packages/shared/domains/` is the single list of domains. Router, trace builder, API routes, and MCP tools derive from it; model-facing tool definitions are snapshotted and their input schemas exclude operator settings.

**Sprint 25  -  Phase 9b planner/supervisor + routing evals (complete, PR #116):**
`POST /plan` with rules, Ollama, and Claude planners over the registry's tool definitions; parallel `Send` fan-out; merge-time grounding validation; 19-case routing/planning eval set in CI.

**Sprint 26  -  Live-call guard + section-aware retrieval (complete, PR #117):**
Eval runners never call the Anthropic API without `--allow-live`, whatever `.env` contains. Keyword retrieval drops stopwords and boosts each domain's own section labels, so weak or missing focus no longer fails with "must include at least one populated section". The "prep my week" plan now runs end to end with `status: ok`.

**Sprint 27  -  Phase 9c grounded MCP tool loop (complete, PR #118):**
The MCP loop ends only through a forced, schema-checked submit; every item is validated against the lines the model read, or the synthesis is dropped with a recorded reason. No response path returns uncited content.

**Sprint 28  -  Retrieval and planner hardening (complete, PRs #119–123):**
File order only breaks ties in keyword retrieval. Chroma retrieval honors each domain's section labels and cites query-relative paths, and the unified runner scores Chroma runs with each domain's Chroma evaluators. The Ollama planner falls back to `rules` on timeouts, and tests block live Ollama calls. The `llama3.2` planner baseline is committed.

**Sprint 29  -  Frontend fix + Plan tab (complete, PR #126):**
`apps/web/src/lib/` (the API client and types every component imports) had never been committed: the Python `.gitignore` rule `lib/` matched it, so the frontend failed to build from any clone. The folder is restored and un-ignored, a CI job now type-checks and builds the frontend, the Auto tab renders validated MCP items, and a Plan tab runs `/plan` from the browser.

**Sprint 30  -  Planner input tightening (complete, PR #128):**
`DomainToolInput` rejects a `data_path` that is not an existing directory, so an invented folder fails at planning and falls back to `rules` instead of failing at execution. The check lives on the shared tool input, so the standalone MCP server gets it too. `max_documents` already rejects values outside 1–20 and is unchanged.

**Ollama planner baseline (`evaluations/planner/results_ollama.json`):**
`llama3.2` (3B) scores 5/19, and 0/5 on the keyword-free and over-split cases, below the rules planner's 14/14 on the cases it supports. Of its plans:
- 6 fell back to `rules` (non-integer or zero `max_documents`, or no tool call)
- 4 called an extra domain
- 2 used invented data paths that only failed at execution
- every semantic case routed to the wrong domain

The fallback and merge-time validation behaved as designed: no invalid plan ran, and no step with bad input was reported `ok`. Two gaps showed up:
- `data_path` validation checked only the `data/local_only/` prefix, not that the folder exists, so planning-only evals passed with invented paths. Fixed in Sprint 30.
- A 3B model is not a viable planner. The keyword-free cases need a stronger model, such as Claude, to beat `rules`.

**Phase 9  -  recommended next:**

1. **Score the planners against the tightened inputs.** Rerun the `llama3.2` baseline (local, free) so its committed results reflect the existence check, then score the Claude planner on all 19 cases (opt-in, `--allow-live`).
2. **9d checkpointing + human approval.** SQLite checkpointer, `interrupt()` before final output, and run history in `apps/web`.
3. **When you choose to spend:** rerun the live Claude domain evals with `--allow-live`, and exercise the MCP loop once against the real API. The committed `results_claude.json` files predate the Sprint 26 retrieval change, and the 9c loop has been tested only with mocked responses.

See [Phase 9](#phase-9-from-router-to-orchestrator) above.

## Definition of Success

This project should be considered successful when it can clearly demonstrate:

- local-first operation
- cost-conscious AI workflows
- grounded, evidence-based outputs
- deterministic or well-bounded orchestration
- selective agentic behavior where it genuinely improves outcomes
- at least two useful domain workflows
- strong operator visibility and control

That is the standard that turns AI-OS from an interesting repo into a serious working system.
