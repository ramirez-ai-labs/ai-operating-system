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
- local retrieval from markdown files
- validation logic
- optional Ollama provider support
- sample local project data
- tests for core weekly-update behavior
- GitHub Actions CI and release workflows

The repository does not yet include:

- a true orchestrator layer
- a `Brand OS` workflow
- a local UI
- strong evidence lineage per output item
- broader evaluation coverage

## Guiding Principles

All phases should preserve the core project standards:

- local-first by default
- cost-conscious execution
- grounded outputs
- deterministic workflows where practical
- human-in-the-loop review
- simple, inspectable architecture

## Phase 1: Stabilize the Director OS MVP

### Objective

Turn the current `Director OS` weekly update slice into a reliable and defensible foundation.

### Deliverables

- Update `AGENTS.md` so it reflects the actual implemented repository state
- Commit and stabilize the current CI/CD workflows
- Improve evidence quality in retrieval
- Filter headings and non-action lines from returned evidence
- Attach explicit source references to output items where practical
- Strengthen validation rules for evidence-backed output
- Add more local sample data to test multi-file retrieval
- Expand tests for retrieval ranking, provider failures, and validation edge cases

### Exit Criteria

- `README.md` and `AGENTS.md` are aligned with the real codebase
- `Director OS` output is consistently grounded in meaningful evidence
- CI passes on branch and pull request workflows
- The MVP can be run locally from documented quickstart steps without guesswork

## Phase 2: Add the Shared Orchestration Layer

### Objective

Introduce a small, explicit orchestration layer that begins to match the “Chief of Staff” architecture described in the README.

### Deliverables

- Add a lightweight orchestration module for workflow selection
- Define routing rules for choosing the correct workflow based on request intent
- Keep orchestration deterministic and easy to inspect
- Document the orchestrator contract and request flow
- Add tests for routing and failure behavior

### Exit Criteria

- Requests flow through an explicit orchestrator layer
- Workflow selection is testable and deterministic
- The architecture more closely matches the README without adding unnecessary abstraction

## Phase 3: Add the First Brand OS Workflow

### Objective

Prove that the shared core can support a second domain without duplicating architecture.

### Deliverables

- Add one `Brand OS` workflow
- Reuse shared retrieval, schemas, validation, and provider logic
- Define clear Brand OS inputs and structured outputs
- Add sample local content or notes for Brand OS testing
- Add focused tests for the new workflow

### Exit Criteria

- AI-OS supports at least two real workflows across different domains
- Shared infrastructure is reused instead of copied
- The “multi-domain operating system” story is now supported by actual code

## Phase 4: Improve Model Reliability and Evaluation

### Objective

Make local-model-backed generation more reliable and easier to trust.

### Deliverables

- Define deterministic fallback behavior when Ollama is unavailable
- Improve provider error handling and output parsing
- Add evaluation cases for weak retrieval, malformed model output, and unsupported claims
- Add more realistic sample datasets for both `Director OS` and `Brand OS`
- Strengthen validator behavior for source-aware output checks

### Exit Criteria

- Ollama-backed generation is usable in normal local development
- Failure modes are readable and well-tested
- The validator meaningfully improves output trustworthiness

## Phase 5: Add a Lightweight Local UI

### Objective

Expose workflow execution in a way that supports both usability and project credibility.

### Deliverables

- Add a local UI under `apps/web`
- Show workflow request, selected path, evidence, validation outcome, and final output
- Keep the UI focused on traceability rather than “agents chatting”
- Support desktop-first local operation with simple run instructions

### Exit Criteria

- A user can run the system locally through a UI
- The UI improves traceability and operator control
- The project becomes easier to demo and evaluate

## Phase 6: Harden the Project for Ongoing Growth

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
2. Update `AGENTS.md` to reflect the real implementation state
3. Improve evidence quality and evidence lineage in `Director OS`
4. Add more sample data and stronger tests
5. Introduce the small orchestrator layer
6. Add the first `Brand OS` workflow

## Definition of Success

This project should be considered successful when it can clearly demonstrate:

- local-first operation
- cost-conscious AI workflows
- grounded, evidence-based outputs
- deterministic or well-bounded orchestration
- at least two useful domain workflows
- strong operator visibility and control

That is the standard that turns AI-OS from an interesting repo into a serious working system.
