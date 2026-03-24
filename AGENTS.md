# AGENTS.md

## Purpose

This repository defines and will implement **AI Operating System (AI-OS)**, a local-first, multi-agent AI system for technical leadership, project operations, and personal brand workflows.

Primary goals:

- Support structured multi-agent workflows rather than generic chatbot behavior.
- Help the operator synthesize evidence, surface risks, and produce actionable outputs.
- Keep data local by default and avoid unnecessary network dependencies.
- Preserve modularity across orchestrator, domain agents, retrieval, validation, and provider layers.
- Make outputs grounded, concise, and reviewable before external use.

This repo should be treated as an operational AI system for serious day-to-day use, not a demo app, toy assistant, or content-only generator.

## Current Repository State

The repository may begin with only lightweight documentation and may not yet contain the implementation structure described in planning materials.

Implications:

- Do not claim an app, API, workflow, package, or directory exists unless it is actually present in the repo.
- Treat architecture described in docs as intended direction, not current implementation reality.
- When adding code, keep documentation aligned with what now exists.
- Keep implementation claims modest and specific.

## Product Direction

AI-OS is intended to help a technical leader operate across multiple domains:

- **Director OS**: project management, team insight synthesis, weekly updates, risk and blocker visibility.
- **Brand OS**: content generation from real work, podcast and workshop ideation, open source positioning, and thought leadership support.
- **Engineering OS**: a plausible future extension, but not something to imply as implemented unless it exists.

The system is not autonomous. It should behave as a constrained, reviewable decision-support tool with strong evidence and validation requirements.

## Expected Repo Shape

As the project is built out, the repo may center around a structure similar to:

```text
/ai-os
  /apps
    /web
    /api

  /packages
    /shared
      /prompts
      /schemas
      /retrieval
      /validation
      /providers

  /director_os
    agents/
    workflows/

  /brand_os
    agents/
    workflows/

  /data
    /local_only
      /projects
      /notes
      /repos
      /podcast

  /config
    models.yaml
    routing.yaml
```

Interpretation:

- `apps/web`: user-facing interface, likely for local operation and structured workflow entry points.
- `apps/api`: orchestration, workflow execution, retrieval access, provider routing, and validation hooks.
- `packages/shared`: shared prompts, schemas, retrieval logic, validation utilities, and model-provider abstractions.
- `director_os` and `brand_os`: domain-specific agents and workflows with strict responsibilities.
- `data/local_only`: local inputs and working material; treat as private and sensitive by default.
- `config`: model routing, provider policy, and workflow configuration.

If the actual repo evolves differently, follow the real structure rather than forcing this layout.

## System Expectations

Changes should reinforce the intended architecture:

- A central orchestrator or chief-of-staff layer that interprets user requests and routes work.
- Domain agents with narrow, explicit roles.
- A retrieval layer that limits outputs to grounded context.
- A provider layer that supports local models first and external models only when explicitly configured.
- A validator layer that rejects unsupported, overly verbose, or weakly grounded outputs.

Do not collapse these concerns into vague agent behavior. Preserve explicit boundaries where they improve trust, debugging, or maintainability.

## Collaborator Profile

Assume the repository owner is:

- an experienced software engineer
- a technical leader using AI for leverage, not novelty
- comfortable with local infra, backend systems, and agent design
- privacy-conscious and skeptical of unsupported claims
- optimizing for signal, leverage, and operational consistency

Implications for how you should assist:

- Skip beginner explanations unless asked.
- Prefer concrete implementation and crisp tradeoff statements.
- Optimize for grounded outputs, privacy, and maintainable workflows.
- Treat trustworthiness, traceability, and operator control as first-class concerns.

## Working Style

When contributing to this repo:

- Be concise, direct, and technically precise.
- Prefer small, composable pieces over large opaque agent frameworks.
- Keep workflows deterministic and easy to inspect.
- Favor explicit schemas, contracts, and routing rules over hidden prompt magic.
- Make evidence, validation, and output quality part of the implementation, not just documentation.

## Engineering Standards

### General

- Favor clarity over cleverness.
- Keep modules focused and small.
- Use descriptive names for agents, workflows, prompts, schemas, and provider abstractions.
- Add short comments only where intent or control flow would otherwise be non-obvious.
- Avoid unnecessary abstractions, especially around orchestration and retrieval.

### Python and Backend

- Prefer Python for orchestration and backend logic unless the repo clearly establishes another standard.
- Use explicit types and schemas for agent inputs, outputs, and workflow state where practical.
- Validate untrusted input at the boundary.
- Keep agent interfaces straightforward and testable.
- Prefer plain functions and simple modules unless classes clearly improve state management or composition.

### Frontend

- Keep UI focused on workflow clarity, evidence visibility, and operator review.
- Avoid chat-first UX if the product is better represented as structured workflows and result panes.
- Preserve privacy expectations in the interface; do not imply cloud sync or background sharing unless implemented.

### Configuration

- Keep model routing, provider settings, and workflow policy configurable.
- Never hardcode secrets, tokens, or private filesystem paths that should be environment- or config-driven.
- Treat model/provider configuration as validated input, not trusted code.

## Agent and Workflow Standards

- Each agent should have a narrow role and a clear contract.
- Prefer deterministic handoffs over free-form multi-agent autonomy.
- Keep prompts grounded in retrieved context and explicit task framing.
- Require evidence references or source attribution where the workflow makes factual claims.
- Add validation steps for unsupported claims, excessive verbosity, and missing evidence.
- Preserve human review before publishing content or acting on sensitive conclusions.

## Privacy and Security Standards

- Default to local-only operation wherever possible.
- Never commit secrets, credentials, tokens, or private datasets.
- Treat notes, meeting summaries, repos, podcast drafts, and personal documents as sensitive.
- Do not log raw private source material unless explicitly required and safely scoped.
- Be careful with any feature that introduces internet access, external APIs, telemetry, or cloud inference.
- Make any non-local provider usage explicit in config and docs.

## Grounding and Output Quality

- Outputs should be evidence-based, not speculative.
- Do not present guesses as findings.
- Keep responses short, actionable, and high-signal.
- Prefer source-linked or source-labeled summaries when the workflow supports it.
- If evidence is weak, incomplete, or conflicting, say so clearly.

## Reliability and Operations

- Favor repeatable workflows over agentic improvisation.
- Make failures legible: invalid inputs, missing context, provider errors, and validation failures should be easy to diagnose.
- Preserve enough metadata to trace how an output was produced without exposing sensitive underlying content.
- Keep local setup and execution simple and reproducible.

## Testing and Verification

- Add tests for non-trivial workflow routing, retrieval logic, validation rules, schemas, and provider adapters.
- Cover important failure paths, not just happy paths.
- Prefer lightweight tests that protect deterministic behavior.
- If tests are not added yet, perform focused local checks and document any verification gaps.

## Documentation Rules

- Keep `README.md` aligned with the real implementation state.
- Clearly distinguish current functionality from planned architecture.
- When adding workflows or agents, document their role, inputs, outputs, and constraints.
- When adding configuration, document defaults, privacy implications, and any external dependencies.

## What To Avoid

- generic chatbot framing that ignores the structured system design
- autonomous-agent claims that overstate actual control or capability
- placeholder architecture docs presented as completed implementation
- hidden network dependencies or silent cloud fallbacks
- verbose outputs with weak evidence
- broad agent responsibilities that blur ownership and validation
- unnecessary framework or orchestration complexity

## Agent Instruction Summary

If you are an AI agent working in this repository:

- Treat this repo as a local-first, multi-agent operating system for leadership and content workflows.
- Keep documentation honest about what is implemented versus planned.
- Prioritize privacy, grounded outputs, deterministic behavior, and human review.
- Make small, defensible changes that improve trustworthiness and maintainability.
- Prefer explicit workflows, retrieval boundaries, and validation over vague agent autonomy.
