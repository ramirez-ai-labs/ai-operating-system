# AGENTS.md

## Purpose

This repository defines and will implement **AI Operating System (AI-OS)**, a local-first multi-agent system designed to help technical leaders operate effectively across structured work domains.

Primary goals:

- Provide a grounded, privacy-conscious AI operating layer for leadership and knowledge work.
- Support domain-specific workflows such as `Director OS` and `Brand OS`.
- Keep local-first operation as the default posture, with optional hybrid model/provider support only when explicitly enabled.
- Produce structured, evidence-based outputs rather than generic chatbot responses.
- Keep the implementation modular, auditable, and practical to operate.

This repo should be treated as a reusable local-first agent system, not a generic demo app or marketing site.

## Current Repository State

The repository now contains both project documentation and an implemented Phase 1 MVP slice.

Current implemented areas include:

- a local FastAPI service under `apps/api`
- a `Director OS` weekly update workflow
- shared schemas, retrieval, validation, and provider abstractions under `packages/shared`
- sample local project data under `data/local_only/projects`
- focused tests for the current workflow
- lightweight GitHub Actions CI/CD workflows

The broader architecture described in `README.md` is still only partially implemented.

Implications:

- Do not claim a file, feature, workflow, or deployment path exists unless it is actually present in the repo.
- When adding implementation, keep the README and the codebase aligned in the same change when practical.
- If the README describes planned files that do not exist yet, treat them as intended targets rather than current reality.
- Use `plan.md` as the phased roadmap for sequencing future work.

## Expected Repo Shape

As the project is built out, the repo will likely center around a structure similar to:

```text
/
├── README.md
├── AGENTS.md
├── apps/
│   ├── web/
│   └── api/
├── packages/
│   └── shared/
├── director_os/
├── brand_os/
├── config/
└── data/
```

Interpretation:

- `apps/api`: local orchestration and backend logic.
- `apps/web`: optional local UI focused on workflow traceability and operator visibility.
- `packages/shared`: prompts, schemas, retrieval, validation, and provider abstractions shared across domains.
- `director_os/` and `brand_os/`: domain-specific agents and workflows.
- `config/`: model and routing configuration.
- `data/`: local-only working data and inputs.

## Collaborator Profile

Assume the repository owner is:

- an experienced software engineer
- an AI/LLM platform builder
- an infrastructure-minded operator
- security-conscious
- comfortable with local AI stacks, APIs, and backend systems

Implications for how you should assist:

- Do not explain basic AI, API, Python, or TypeScript concepts unless asked.
- Prefer precise implementation choices over generic brainstorming.
- Surface privacy, cost, reliability, and evaluation tradeoffs clearly.
- Treat retrieval quality, validation, and grounded output as first-class concerns.
- Keep recommendations credible for a production-minded local AI system.

## Working Style

When contributing to this repo:

- Be concise, direct, and technically grounded.
- Prefer implementation over extended planning when the next step is clear.
- Keep the codebase lean and modular; avoid unnecessary abstractions.
- Favor deterministic, inspectable workflows over opaque autonomy.
- Prefer simple request flows and small components that are easy to reason about and debug.

## Product Expectations

Changes should reinforce the core product described in `README.md`:

- `Director OS` for project management, team insight, and executive reporting
- `Brand OS` for content, open source positioning, and thought leadership workflows
- an orchestrator that routes tasks across domain agents
- retrieval-backed, evidence-based outputs
- local-first execution with optional provider extensibility
- a validation layer that checks quality and unsupported claims

Supporting concerns should include:

- privacy by default
- local execution as the baseline mode
- bounded cost and explicit opt-in for external providers
- grounded responses with source-aware reasoning when evidence is available
- readable workflow state and traceability

## Engineering Standards

### General

- Favor clarity over cleverness.
- Use descriptive names for variables, helpers, types, config fields, and workflow steps.
- Keep modules focused and small.
- Add short comments only where the code would otherwise be non-obvious.
- Avoid framework-heavy patterns that do not add clear value.

### Implementation

- Use TypeScript or Python where they fit the implementation slice; do not force both without justification.
- Prefer explicit request, response, and config types or schemas for public interfaces.
- Validate untrusted input at the boundary.
- Keep orchestrators, retrieval helpers, provider adapters, and validators straightforward and testable.
- Avoid overusing classes when plain functions and typed objects are sufficient.

### Configuration

- Use environment variables or config files for configuration.
- Keep examples and templates realistic but safe.
- Never hardcode secrets, API keys, or private endpoints that should be configurable.
- Treat model registry, routing rules, and data source configuration as untrusted input and validate accordingly.

## Privacy and Security Standards

- Never commit secrets, credentials, or tokens.
- Keep local data local by default.
- Do not log prompts, personal notes, message bodies, API keys, auth headers, or secret values unless explicitly required for a local-only debugging workflow and clearly documented.
- Validate file paths, provider endpoints, and data-source selection carefully.
- Keep default behavior restrictive, especially for external providers or any workflow that could expose private context.
- Flag prompt leakage, data exfiltration, auth bypass, and cost-escalation risks explicitly when relevant.

## Cost and Safety Standards

- Preserve local-first, cost-conscious operation as the default posture unless explicitly asked to relax it.
- Prefer safe defaults that minimize accidental external API traffic.
- Keep prompt, context, and output bounds enforceable where practical.
- Do not enable paid providers by default without clear justification and documentation.
- Make any relaxed-cost behavior explicit in config and docs.

## Reliability and Operations

- Include clear workflow visibility and readable error responses for operator use.
- Preserve traceability across orchestrator, retrieval, provider, and validator steps.
- Prefer deterministic validation and readable failure modes over opaque abstractions.
- Consider timeout handling, malformed input, weak retrieval results, and provider failure cases.
- Keep local development and execution instructions simple and reproducible.

## Testing and Verification

- Add tests for non-trivial parsing, routing, validation, retrieval behavior, and guardrails.
- Cover expected behavior and important failure cases.
- Prefer lightweight test setup appropriate for a local-first codebase.
- If tests are not added yet, at minimum validate behavior with focused local checks and document any gaps.

## Documentation Rules

- Keep `README.md` aligned with the actual implementation status.
- Do not document files, workflows, providers, or interfaces that do not exist yet without clearly marking them as planned.
- When adding config, document required values, defaults, and privacy or cost implications.
- When adding operational features, include enough detail for another engineer to run and debug the system.

## What To Avoid

- generic SaaS boilerplate unrelated to the AI operating system
- placeholder docs that overstate the repo's maturity
- unnecessary dependencies or layered abstractions
- logging of private prompts, notes, or secrets
- hidden cloud-dependent defaults
- uncontrolled autonomous behavior
- frontend-heavy additions unless explicitly requested

## Agent Instruction Summary

If you are an AI agent working in this repository:

- Treat this repo as a local-first multi-agent operating system with production-minded constraints.
- Keep documentation honest about what is implemented versus planned.
- Prioritize privacy, grounded outputs, cost control, and operational clarity.
- Make small, defensible changes that improve correctness and maintainability.
- Prefer simple, inspectable orchestration patterns over elaborate agent architecture.
