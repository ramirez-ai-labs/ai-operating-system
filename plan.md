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
- sample local project data
- tests for core weekly-update, orchestration, and Brand OS behavior
- GitHub Actions CI and release workflows

The repository does not yet include:

- a local UI
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
- Current run modes:
  - on-demand local evals with `python scripts/run_director_os_evals.py`
  - on-demand LangSmith evals with `python scripts/run_director_os_evals.py --langsmith`
- Remaining work: broaden the evaluation cases, wire the eval flow into CI intentionally, and extend the same pattern to more workflows

## Phase 4: Expand the Chief of Staff and Brand OS on the Shared Graph Foundation

### Objective

Use the shared foundation to support multi-domain routing while keeping workflows explicit and bounded.

### Deliverables

- Refactor the Chief of Staff routing layer so it can select between graph-backed workflows
- Bring `Brand OS` onto the same shared graph-oriented architecture where practical
- Reuse shared retrieval, schemas, validation, and provider logic across domains
- Add more realistic sample datasets for both `Director OS` and `Brand OS`
- Expand tests for routing, domain selection, and domain-specific failure behavior

### Exit Criteria

- AI-OS supports at least two real workflows across different domains on a shared foundation
- Routing remains explicit, testable, and explainable
- The multi-domain AI-OS story is supported by actual code instead of docs alone

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

1. Commit the CI/CD and SDLC workflow changes currently in progress
2. Align `README.md`, `AGENTS.md`, and `plan.md` around AI-OS as the product and `LangGraph` / `LangChain` / `LangSmith` as implementation infrastructure
3. Improve evidence quality, path safety, and evidence lineage in `Director OS`
4. Stabilize and document the implemented `LangGraph` workflow foundation in `Director OS`
5. Expand the `Director OS` evaluation set and decide how much of it should run in CI
6. Expand the shared graph-oriented foundation across the Chief of Staff and `Brand OS`

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
