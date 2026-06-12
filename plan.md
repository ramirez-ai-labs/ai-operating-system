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

- project documentation in `README.md`
- contribution and implementation guidance in `AGENTS.md`
- a minimal `Director OS` FastAPI MVP
- a lightweight Chief of Staff orchestration endpoint
- an explicit `LangGraph` workflow state graph for `Director OS`
- a first `Brand OS` workflow
- local retrieval from markdown files
- validation logic
- optional Ollama provider support
- optional `LangSmith` tracing for the `Director OS` graph
- a small checked-in local evaluation set for `Director OS`
- a minimal local operator console served from `apps/api`
- an in-process Claude filesystem tool loop for MCP-style local retrieval traces
- sample local project data
- tests for core weekly-update, orchestration, and Brand OS behavior
- GitHub Actions CI and release workflows

The repository does not yet include:

- a dedicated frontend app under `apps/web`
- a standalone MCP server under `apps/mcp`
- broader evaluation coverage
- a stable visual demo layer

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

- Implemented: Chief of Staff routing plus graph-backed `Director OS` and `Brand OS` workflows
- Remaining work: bring more workflows onto the shared foundation and decide where graph-backed execution is worth the extra complexity

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
- Remaining: bounded agentic steps beyond the current graph nodes
- Remaining: broader eval coverage for weak retrieval and malformed model output
- Remaining: strengthen automated test coverage for provider adapters and MCP orchestration paths, especially `packages/shared/providers/claude.py`, `packages/shared/providers/ollama.py`, and `packages/shared/mcp/orchestrator_integration.py`

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
| Routing and classification | Ollama (local) | Free, fast, good enough for intent routing |
| Synthesis and structured output | Claude Haiku 4.5 | Cost-effective, strong tool use and grounding |
| Optional premium synthesis | Claude Sonnet / Opus | On-demand for high-stakes or complex runs |

### Exit Criteria

- Claude and Ollama are interchangeable providers behind the same `WeeklyUpdateProvider` interface
- The operator console exposes provider selection so the layered architecture is visible and demonstrable
- Claude evals pass the same scorers as the deterministic baseline
- Local setup requires only filling in `.env` from `.env.example` — no undocumented steps

### Status

- Implemented: `packages/shared/providers/claude.py` with Anthropic SDK tool use for structured output
- Implemented: `provider` and `claude_model` fields on `WeeklyUpdateRequest`
- Implemented: `_build_provider` factory in `packages/shared/graphs/director_os.py`
- Implemented: `--provider claude` flag on `scripts/run_director_os_evals.py`
- Implemented: Claude-specific tests in `tests/test_director_os_evaluations.py`
- Implemented: `.env.example` with all required keys
- Implemented: provider selection is now wired through the Chief of Staff orchestrator for Director OS synthesis
- Remaining: operator console provider dropdown (UI toggle for Ollama vs Claude)

## Phase 5c: MCP Server — Expose AI-OS Workflows as Tools

### Objective

Build an MCP (Model Context Protocol) server that exposes Director OS and Brand OS workflows as callable tools, making AI-OS composable with any MCP-compatible host including Claude Desktop, Claude Code, and enterprise integrations.

### Background

MCP is Anthropic's open standard for connecting AI models to external tools and data sources. An FDE deliverable in the field is exactly this: an MCP server a customer team can drop into their environment and immediately wire to Claude. Building one here proves the pattern end-to-end.

### Deliverables

- Add `apps/mcp/server.py` implementing an MCP server using the `mcp` Python SDK
- Expose `director_os_weekly_update` as an MCP tool backed by the existing `build_weekly_update` workflow
- Expose `brand_os_content_draft` as an MCP tool backed by the existing `build_content_draft` workflow
- Keep tool input schemas derived from the existing Pydantic request models — no parallel schema definitions
- Add `claude_desktop_config.json` example so the server can be wired to Claude Desktop in one step
- Add tests covering tool registration, schema correctness, and round-trip tool invocation
- Document the MCP server in `README.md` alongside the existing API entry points

### Exit Criteria

- The MCP server starts and registers both tools without errors
- A Claude Desktop or Claude Code session can invoke `director_os_weekly_update` and receive a grounded structured response
- Tool schemas match the Pydantic request contracts — no drift
- Tests pass in CI without requiring a live Claude connection

### Status

- Partially implemented: `packages/shared/mcp/filesystem_server.py` exposes read-only local filesystem tools
- Partially implemented: `packages/shared/mcp/orchestrator_integration.py` runs a bounded Claude tool-use loop and surfaces `mcp_tool_calls` in `/orchestrate` traces
- Partially implemented: `tests/test_claude_mcp.py` covers provider stubs, filesystem tool behavior, path traversal blocking, and tool-result message shape
- Remaining: this is not yet a standalone MCP server. `apps/mcp/server.py`, `mcp` SDK packaging, workflow tools, Claude Desktop config, and server-level tests are still planned

## Phase 5d: ChromaDB — Upgrade Retrieval to Semantic Vector Search

### Objective

Replace the current flat-file keyword retrieval in `packages/shared/retrieval/local_files.py` with ChromaDB-backed semantic search, making evidence retrieval more accurate and the RAG story credible for enterprise use cases.

### Context

The current retrieval layer reads markdown files and filters by keyword match. This works for the MVP but breaks down with larger or noisier document sets — exactly the kind of data an enterprise customer brings. ChromaDB with sentence embeddings gives semantic similarity search without requiring a cloud vector database, preserving the local-first posture.

### Deliverables

- Add `packages/shared/retrieval/chroma.py` implementing the same retrieval interface as `local_files.py`
- Use ChromaDB with a local persistent store under `data/chroma/` (gitignored)
- Use a lightweight embedding model (e.g. `sentence-transformers/all-MiniLM-L6-v2`) as the default
- Add an ingestion script `scripts/ingest_local_data.py` that indexes `data/local_only/` into ChromaDB
- Keep the existing flat-file retrieval as a fallback when no ChromaDB index exists
- Add `chromadb` and `sentence-transformers` to `pyproject.toml` dependencies
- Add tests for semantic retrieval quality against the existing sample data
- Update `.env.example` with a `RETRIEVAL_BACKEND` variable (`local_files` or `chroma`)

### Exit Criteria

- Running `python scripts/ingest_local_data.py` indexes local documents into ChromaDB
- The Director OS workflow uses ChromaDB retrieval when `RETRIEVAL_BACKEND=chroma` is set
- Semantic search returns more relevant evidence than keyword matching for the existing eval cases
- CI passes with the flat-file backend as the default (no ChromaDB dependency for basic tests)

### Status

- Planned

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

- Implemented: a minimal local operator console is available at `/` through `apps/api`
- Remaining work: decide whether a dedicated `apps/web` experience is worth the extra surface area beyond the current trace-first console

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

## Recommended Immediate Next Steps

The best next sequence from the current repo state is:

1. Keep `README.md`, `AGENTS.md`, `plan.md`, and `CONTRIBUTING.md` aligned with the actual multi-domain implementation
2. Expand the `Director OS` evaluation set and decide how much of the same quality harness should be reused for `Brand OS`
3. Strengthen the shared orchestrator and decide which additional workflows deserve explicit graph-backed execution
4. Add more realistic local sample datasets for both domains
5. Deepen the operator experience beyond the current console only where it materially improves usability or debugging

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
