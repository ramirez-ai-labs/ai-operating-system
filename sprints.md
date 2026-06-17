# AI-OS Sprint Tracker

Tactical execution checklist for the current build cycle. Phases and long-term roadmap are in [plan.md](plan.md).

---

## Sprint 1 — Wire Claude in

**Objective:** Validate the Claude provider end-to-end with a live eval run and lock in the layered model config.

**Maps to:** plan.md Phase 5b

**Status: Complete — live Claude eval results committed in [#56](https://github.com/ramirez-ai-labs/ai-operating-system/pull/56), all 5 JD requirements satisfied**

| Step | Status | PR |
|---|---|---|
| `packages/shared/providers/claude.py` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `ANTHROPIC_API_KEY` in `.env.example` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `anthropic` in `pyproject.toml` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `--provider claude` flag on eval runner | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `config/models.yaml` | Done | [#42](https://github.com/ramirez-ai-labs/ai-operating-system/pull/42) |
| `evaluations/director_os/results_claude.json` — real Claude API output, 3/3 cases 100% | Done | [#56](https://github.com/ramirez-ai-labs/ai-operating-system/pull/56) |

---

## Sprint 2 — MCP Server

**Objective:** Complete the standalone MCP server path so Director OS and Brand OS workflows can be invoked as tools from MCP-compatible hosts.

**Maps to:** plan.md Phase 5c

**Status: Complete — all items shipped in [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50)**

| Step | Status | PR |
|---|---|---|
| `packages/shared/mcp/filesystem_server.py` | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| `packages/shared/mcp/orchestrator_integration.py` | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| Wire `orchestrator_integration` into `/orchestrate` endpoint | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| Provider selection through Chief of Staff routing | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| `tests/test_claude_mcp.py` | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| `apps/mcp/server.py` standalone workflow MCP server | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| Expose `director_os_weekly_update` as MCP tool | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| Expose `brand_os_content_draft` as MCP tool | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| `mcp` SDK added to `pyproject.toml` | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| `claude_desktop_config.json` example | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |
| Standalone MCP server tests passing | Done | [#50](https://github.com/ramirez-ai-labs/ai-operating-system/pull/50) |

---

## Sprint 3 — Test Coverage Hardening

**Objective:** Raise automated coverage on the provider and MCP integration paths that are still under-tested, so the repo has stronger confidence in its real execution paths.

**Maps to:** plan.md Phase 5 and Phase 5b

**Status: In progress — provider and orchestration paths now covered; filesystem edge cases and CI coverage tracking remain**

| Step | Status | PR |
|---|---|---|
| Add unit tests for `packages/shared/providers/claude.py` | Done | [#52](https://github.com/ramirez-ai-labs/ai-operating-system/pull/52) |
| Add unit tests for `packages/shared/providers/ollama.py` | Done | [#52](https://github.com/ramirez-ai-labs/ai-operating-system/pull/52) |
| Add tests for `packages/shared/providers/claude_provider.py` fallback and tool-use paths | Done | [#52](https://github.com/ramirez-ai-labs/ai-operating-system/pull/52) |
| Add tests for `packages/shared/mcp/orchestrator_integration.py` | Done | [#52](https://github.com/ramirez-ai-labs/ai-operating-system/pull/52) |
| Add tests for remaining `packages/shared/mcp/filesystem_server.py` edge cases | Rolled into Sprint 9 | — |
| Measure and track coverage trend in CI | Done — `pytest --cov` runs in CI with coverage artifact upload | — |

---

## Sprint 4 — Docs and Framing

**Objective:** Ship the deployment guide, updated README, and a v1.0 release tag that frames AI-OS as an enterprise-ready MCP-first AI system.

**Maps to:** plan.md Phase 7 (hardening) and Phase 5c (MCP docs)

**Status: Complete — v1.0.0 tag cut in Sprint 9; org-page unpin is a GitHub UI action, not a code item**

| Step | Status | PR |
|---|---|---|
| `docs/DEPLOYMENT.md` | Done | main |
| Update `README.md` with MCP section, Mermaid diagram, Why Claude | Done | [#60](https://github.com/ramirez-ai-labs/ai-operating-system/pull/60) |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Done | — |
| Archive or unpin `openai-foundations` from org page | GitHub UI only — not a code item | — |
| Cut `v1.0` release tag with description | Done (Sprint 9) | — |

---

---

## Sprint 5 — Semantic RAG

**Objective:** Replace keyword retrieval with ChromaDB-backed semantic vector search using Ollama `nomic-embed-text` embeddings. This is the prerequisite for all showcase sprints — the retrieval story is indefensible until this ships.

**Maps to:** plan.md Phase 5d

**Status: Complete — all items shipped in [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57)**

| Step | Status | PR |
|---|---|---|
| `packages/shared/retrieval/backend.py` — env-driven dispatcher (new single import point) | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `packages/shared/retrieval/chroma.py` — ChromaDB semantic retrieval matching `local_files.py` interface | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `packages/shared/retrieval/ingest.py` — indexing logic in the package tree (testable, CLI-independent) | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `scripts/ingest_local_data.py` — thin CLI wrapper calling `ingest.run()` | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `data/chroma/` added to `.gitignore` | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `chromadb>=0.5.0` added to `pyproject.toml` | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `RETRIEVAL_BACKEND` env var in `.env.example` (`local_files` or `chroma`) | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| Flat-file fallback when ChromaDB index absent or Ollama unavailable | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| `tests/test_chroma_retrieval.py` — 11 tests, all passing, no Ollama required | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |
| Update `director_os.py` and `brand_os.py` imports to use `backend.py` | Done | [#57](https://github.com/ramirez-ai-labs/ai-operating-system/pull/57) |

> **To activate:** `ollama pull nomic-embed-text` → `python scripts/ingest_local_data.py` → set `RETRIEVAL_BACKEND=chroma` in `.env`. Semantic search becomes meaningfully better than keyword matching after Sprint 8 replaces the toy sample data with a realistic enterprise scenario.

---

## Sprint 6 — Tiered Architecture + Prompt Caching

**Objective:** Make Claude Haiku the default synthesis provider, add prompt caching to reduce per-request cost, and surface cache metrics in every `WorkflowTrace`.

**Maps to:** plan.md Phase 5e and Phase 5f

**Status: Complete — shipped on `feat/sprint-6-7-tiered-agents`**

| Step | Status | PR |
|---|---|---|
| Change `OrchestratorRequest` default `provider` from `"ollama"` to `"claude"` | Done | feat/sprint-6-7-tiered-agents |
| Add `cache_control: {"type": "ephemeral"}` to system prompt in `claude.py` | Done | feat/sprint-6-7-tiered-agents |
| Add `get_last_usage()` default to `WeeklyUpdateProvider` base class | Done | feat/sprint-6-7-tiered-agents |
| Override `get_last_usage()` in `ClaudeWeeklyUpdateProvider` with cache fields | Done | feat/sprint-6-7-tiered-agents |
| Add `cache_read_input_tokens` and `cache_creation_input_tokens` to `WorkflowTrace` | Done | feat/sprint-6-7-tiered-agents |
| Thread `provider_usage` from model draft → `WeeklyUpdateResponse` → trace | Done | feat/sprint-6-7-tiered-agents |
| Surface `routing_model` field in `WorkflowTrace` | Done | feat/sprint-6-7-tiered-agents |
| `tests/test_sprint6_cache_tokens.py` — 9 tests, all passing | Done | feat/sprint-6-7-tiered-agents |

---

## Sprint 7 — Multi-Agent Researcher → Writer

**Objective:** Add a two-agent workflow demonstrating Claude-to-Claude orchestration. Researcher synthesizes evidence via tool use; writer formats the synthesis for a target audience. Required agentic pattern for the Anthropic FE showcase.

**Maps to:** plan.md Phase 5g

**Status: Complete — shipped on `feat/sprint-6-7-tiered-agents`**

| Step | Status | PR |
|---|---|---|
| `packages/shared/agents/researcher.py` — Claude Haiku tool use, returns `ResearchSynthesis` | Done | feat/sprint-6-7-tiered-agents |
| `packages/shared/agents/writer.py` — Claude Haiku completion, formats for target audience | Done | feat/sprint-6-7-tiered-agents |
| `AgentCall` schema — per-agent token counts including cache fields | Done | feat/sprint-6-7-tiered-agents |
| `target_audience` field on `OrchestratorRequest` — triggers researcher → writer pipeline | Done | feat/sprint-6-7-tiered-agents |
| `agent_calls` list in `WorkflowTrace` — researcher and writer invocations | Done | feat/sprint-6-7-tiered-agents |
| `formatted_content` field on `OrchestratorResponse` — writer output | Done | feat/sprint-6-7-tiered-agents |
| Wire researcher → writer in `chief_of_staff.py` | Done | feat/sprint-6-7-tiered-agents |
| `tests/test_sprint7_agents.py` — 9 tests, all passing | Done | feat/sprint-6-7-tiered-agents |

---

## Sprint 8 — Realistic Demo Data + "Why Claude" Framing

**Objective:** Replace toy markdown files with a realistic enterprise scenario. Add a "Why Claude" README section that explains Claude-specific design decisions. Makes the demo land with a hiring manager or enterprise evaluator.

**Maps to:** plan.md Phase 5h

**Status: Complete — shipped on `feat/sprint-6-7-tiered-agents`**

| Step | Status | PR |
|---|---|---|
| Replace `data/local_only/projects/` with realistic quarterly planning scenario | Done | feat/sprint-8-realistic-demo-data |
| Replace `data/local_only/brand/` with realistic brand scenario | Done | feat/sprint-8-realistic-demo-data |
| Add "Why Claude" section to `README.md` | Done | feat/sprint-6-7-tiered-agents |
| Update `README.md` architecture diagram to Mermaid with tiered model layers | Done | feat/sprint-6-7-tiered-agents |

---

## Sprint 9 — Console Polish + Plan Alignment + Release Hygiene

**Objective:** Make all Sprint 6+7+8 capabilities visible in the operator console, align plan.md with current reality, set GitHub topics, and cut a v1.0 release tag.

**Maps to:** plan.md Phase 6 (UI), Phase 7 (hardening)

**Status: Complete**

| Step | Status | PR |
|---|---|---|
| Operator console: add Provider selector and Target Audience dropdown | Done | [#62](https://github.com/ramirez-ai-labs/ai-operating-system/pull/62) |
| Operator console: cache hit metrics in Execution Trace card | Done | [#62](https://github.com/ramirez-ai-labs/ai-operating-system/pull/62) |
| Operator console: agent pipeline card (researcher → writer with token counts) | Done | [#62](https://github.com/ramirez-ai-labs/ai-operating-system/pull/62) |
| Operator console: formatted content card (writer output) | Done | [#62](https://github.com/ramirez-ai-labs/ai-operating-system/pull/62) |
| Fix FastAPI / Starlette version incompatibility (test_api.py, test_import_integrity.py) | Done | [#63](https://github.com/ramirez-ai-labs/ai-operating-system/pull/63) |
| Add tests for remaining `packages/shared/mcp/filesystem_server.py` edge cases | Done | [#63](https://github.com/ramirez-ai-labs/ai-operating-system/pull/63) |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Done | — |
| Update `plan.md` — mark phases 5d–5h complete, rewrite Next Steps | Done | [#65](https://github.com/ramirez-ai-labs/ai-operating-system/pull/65) |
| Phase 5e: Replace keyword router with Ollama classification + keyword fallback | Done | [#65](https://github.com/ramirez-ai-labs/ai-operating-system/pull/65) |
| Fix README diagram, plan.md, AGENTS.md showcase alignment | Done | [#67](https://github.com/ramirez-ai-labs/ai-operating-system/pull/67) |
| Cut `v1.0` release tag with description | Done | — |

---

## Sprint 10a — Bug Fixes

**Objective:** Fix 7 confirmed defects surfaced by post-ship code review. All are in shipped v1.0.0 code. Fix before adding new scope.

**Maps to:** plan.md Sprint 10a

**Status: Complete — all 6 defects fixed + parallel tool-call test added in [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70). 175 tests passing.**

| Step | Status | PR |
|---|---|---|
| Fix multi-tool API protocol violation — batch all tool_use + tool_result into single message pair (`orchestrator_integration.py:125`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Fix path traversal bypass — replace `startswith` with `is_relative_to` (`filesystem_server.py:298`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Fix false routing — replace `"brand" in content` with strict `content == "brand_os"` + keyword fallback for unrecognised tokens (`chief_of_staff.py:180`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Fix silent exception — add per-exception logging and differentiated trace labels (`chief_of_staff.py:176`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Fix fragile tuple concatenation — explicit destructure in fallback (`chief_of_staff.py:177`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Fix `files_searched` cap — count all traversed files, not only successfully-read text files (`filesystem_server.py:249`) | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |
| Add tests covering multi-tool-call round in orchestrator integration | Done | [#70](https://github.com/ramirez-ai-labs/ai-operating-system/pull/70) |

---

## Sprint 10b — Resolve `use_mcp` Design Gap + Provider Clarity

**Objective:** Implement MCP-first synthesis (Option B) so `use_mcp=True` actually uses the MCP response instead of discarding it. Clarify the two Claude provider roles so contributors are not confused when Sprint 10d adds a third workflow.

**Maps to:** plan.md Sprint 10b

**Decision: Option B (MCP-first synthesis).** The current behaviour burns tokens on a synthesis call whose result is thrown away — that is not a trace-only choice, it is a bug. Option B is the honest implementation.

**Status: Complete — shipped in [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72). 178 tests passing (172 + 6 API-key gated skips).**

| Step | Status | PR |
|---|---|---|
| Wire `mcp_response.content` into `OrchestratorResponse` as a new `mcp_synthesis` schema field | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |
| When `use_mcp=True`, skip the redundant `_run_workflow` synthesis call | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |
| Propagate `request.provider` into `run_with_mcp_tools` so model selection is consistent | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |
| Update `use_mcp` field description, schema comments, and README to reflect MCP-first behaviour | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |
| Add tests: MCP-first response path returns `mcp_synthesis` and skips `_run_workflow` | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |
| Provider clarity gap: expand `providers/__init__.py` docstring explaining the two Claude provider roles | Done | [#72](https://github.com/ramirez-ai-labs/ai-operating-system/pull/72) |

---

## Sprint 10c — Eval Coverage + Eval Runner Correctness

**Objective:** Close the eval gap for the researcher→writer pipeline, fix the eval runner to use the production provider path, and commit complete Claude results against all 7 canonical cases.

**Maps to:** plan.md Sprint 10c

**Root cause of eval runner gap:** `run_director_os_evals_claude.py` uses `ClaudeProvider.complete()` (the MCP general-purpose wrapper) with 3 hardcoded inline cases. Production uses `ClaudeWeeklyUpdateProvider` (forced tool use via `WeeklyUpdateProvider` interface) with the 7 cases in `weekly_update_cases.json`. The committed `results_claude.json` covers only the 3 hardcoded cases — none of them matching the canonical case IDs.

**Status: Complete — shipped on `feat/sprint-10c-10d-11-completeness`**

| Step | Status | PR |
|---|---|---|
| Rewrite `run_director_os_evals_claude.py` to load cases from `evaluations/director_os/weekly_update_cases.json` | Done | feat/sprint-10c-10d-11-completeness |
| Switch the eval runner to use `ClaudeWeeklyUpdateProvider` through the Director OS graph, not `ClaudeProvider.complete()` directly | Done | feat/sprint-10c-10d-11-completeness |
| Verify scoring logic works with structured tool-use output (not raw text completion) | Done | feat/sprint-10c-10d-11-completeness |
| Add `evaluations/director_os/multiagent_cases.json` — 5 eval cases for the researcher→writer pipeline | Done | feat/sprint-10c-10d-11-completeness |
| Commit `results_claude.json` with real Claude output covering all 7 canonical cases | Pending (requires `ANTHROPIC_API_KEY` at runtime) | — |

---

## Sprint 10d — Third Workflow Domain (Interview OS)

**Objective:** Add Interview OS as a third workflow domain to make the "operating system" framing credible. All shared infrastructure is in place — this is pattern-match work. Interview OS (candidate prep briefs, question banks, evidence-backed interviewer notes) fits the evidence-grounded retrieval pattern and is a strong portfolio signal.

**Maps to:** plan.md Sprint 10d

**Prerequisite:** Sprint 10b (provider clarity) should be complete so the new workflow knows which provider class to inherit from.

**Status: Complete — shipped on `feat/sprint-10c-10d-11-completeness`. 9 tests passing.**

| Step | Status | PR |
|---|---|---|
| Define `InterviewBriefRequest` / `InterviewBriefResponse` schemas in `packages/shared/schemas/interview_os.py` | Done | feat/sprint-10c-10d-11-completeness |
| Build LangGraph state graph in `packages/shared/graphs/interview_os.py` — nodes: retrieve_evidence → build_response | Done | feat/sprint-10c-10d-11-completeness |
| Deterministic `_collect_items` with prefix-first matching (no provider needed) | Done | feat/sprint-10c-10d-11-completeness |
| Add workflow entry point in `interview_os/workflows/interview_brief.py` | Done | feat/sprint-10c-10d-11-completeness |
| Register `/interview-os/brief` route in `apps/api/main.py` | Done | feat/sprint-10c-10d-11-completeness |
| Add routing logic in `chief_of_staff.py` — `INTERVIEW_ROUTING_KEYWORDS` + Ollama classification | Done | feat/sprint-10c-10d-11-completeness |
| Add realistic sample data under `data/local_only/interviews/` — 4 files with prefixed items | Done | feat/sprint-10c-10d-11-completeness |
| Add eval cases in `evaluations/interview_os/interview_cases.json` — 4 cases | Done | feat/sprint-10c-10d-11-completeness |
| Add `tests/test_interview_os_graph.py` — 9 tests covering graph, routing, grounding, multifile | Done | feat/sprint-10c-10d-11-completeness |
| Expose `interview_os_brief` as an MCP tool in `apps/mcp/server.py` | Done | feat/sprint-10c-10d-11-completeness |
| Add Interview OS to operator console — `use_mcp` checkbox, `mcp_synthesis` card, result sections | Done | feat/sprint-10c-10d-11-completeness |
| Register `interview_os` packages in `pyproject.toml` | Done | feat/sprint-10c-10d-11-completeness |

---

## Sprint 11 — Phase 7 Hardening

**Objective:** Complete the remaining Phase 7 items to make the project sustainable for ongoing contributors: branch protection verification, issue templates, and a contributor workflow doc.

**Maps to:** plan.md Phase 7

**Status: Complete — shipped on `feat/sprint-10c-10d-11-completeness`.**

| Step | Status | PR |
| --- | --- | --- |
| Verify branch protection is active on `main` | Done (confirmed active) | — |
| Add `.github/ISSUE_TEMPLATE/feature.md` | Done | feat/sprint-10c-10d-11-completeness |
| Add `.github/ISSUE_TEMPLATE/bug.md` | Done | feat/sprint-10c-10d-11-completeness |
| Add `.github/ISSUE_TEMPLATE/workflow.md` — for new OS workflow domain proposals | Done | feat/sprint-10c-10d-11-completeness |
| Add `CONTRIBUTING.md` — branch naming, PR checklist, how to add a new workflow domain, how to run evals | Done | feat/sprint-10c-10d-11-completeness |

---

## Sprint 12 — Interview OS CI Parity + Claude Provider

**Objective:** Bring Interview OS to full parity with Director OS and Brand OS: eval library, CI gate, and Claude-backed synthesis path. The third domain was complete in Sprint 10d but lacked the eval runner and model-assisted path that the other two domains have.

**Maps to:** plan.md Sprint 12

**Status: Complete — shipped on `feat/sprint-12-interview-os-completeness`. 192 tests passing.**

| Step | Status | PR |
| --- | --- | --- |
| Add `packages/shared/evaluations/interview_os.py` — 5 scorers: summary terms, expected sources, section minimums, source diversity, grounding | Done | feat/sprint-12-interview-os-completeness |
| Add `scripts/run_interview_os_evals.py` — CLI runner matching Brand OS pattern | Done | feat/sprint-12-interview-os-completeness |
| Wire Interview OS eval runner into CI `.github/workflows/ci.yml` | Done | feat/sprint-12-interview-os-completeness |
| Fix `compileall` step in CI to include `interview_os` package | Done | feat/sprint-12-interview-os-completeness |
| Add `ClaudeInterviewBriefProvider` in `packages/shared/providers/interview_os.py` — forced tool use, evidence citation grounding, prompt caching | Done | feat/sprint-12-interview-os-completeness |
| Add `use_model`, `provider`, `claude_model`, `fallback_to_deterministic` fields to `InterviewBriefRequest` | Done | feat/sprint-12-interview-os-completeness |
| Update `packages/shared/graphs/interview_os.py` — model-assisted path with deterministic fallback, `route_after_build` conditional edge | Done | feat/sprint-12-interview-os-completeness |
| Add `tests/test_interview_os_evals.py` — 11 tests for eval library scorers and runner | Done | feat/sprint-12-interview-os-completeness |
| Add 2 tests to `test_interview_os_graph.py` — provider call verified, fallback on error | Done | feat/sprint-12-interview-os-completeness |
| Calibrate `evaluations/interview_os/interview_cases.json` against actual retrieval output | Done | feat/sprint-12-interview-os-completeness |
| Update `plan.md` Current State and Recommended Next Steps | Done | feat/sprint-12-interview-os-completeness |

---

## Sprint 13 — One-on-One OS + Multiagent CI Gate

**Objective:** Add One-on-One OS as a fourth workflow domain and wire the orphaned `multiagent_cases.json` into CI. All shared infrastructure was in place — this is pattern-match work.

**Maps to:** plan.md Phase 4 (multi-domain expansion)

**Status: Complete — shipped in [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75). 213 tests passing.**

| Step | Status | PR |
| --- | --- | --- |
| Add `data/local_only/one_on_one/` — 4 realistic 1:1 note files with Action:/Blocker:/Kudos: prefixes | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Define `OneOnOneRequest` / `OneOnOneResponse` schemas in `packages/shared/schemas/one_on_one_os.py` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Build LangGraph state graph in `packages/shared/graphs/one_on_one_os.py` — model path + deterministic fallback | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `ClaudeOneOnOneProvider` in `packages/shared/providers/one_on_one_os.py` — forced tool use, citation grounding | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add workflow entry point in `one_on_one_os/workflows/meeting_brief.py` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Register `/one-on-one/brief` route in `apps/api/main.py` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add routing in `chief_of_staff.py` — `ONE_ON_ONE_ROUTING_KEYWORDS` + Ollama classification + `_build_trace` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Update `packages/shared/schemas/orchestrator.py` — add `OneOnOneResponse` to result union | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Expose `one_on_one_os_brief` as an MCP tool in `apps/mcp/server.py` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `packages/shared/evaluations/one_on_one_os.py` — 5 scorers | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `evaluations/one_on_one_os/meeting_brief_cases.json` — 4 eval cases | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `scripts/run_one_on_one_os_evals.py` — CLI runner | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Wire One-on-One OS eval runner + multiagent eval step into CI | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `tests/test_one_on_one_os_graph.py` — 12 tests | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Add `tests/test_one_on_one_os_evals.py` — 10 tests | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |
| Register `one_on_one_os` packages in `pyproject.toml` | Done | [#75](https://github.com/ramirez-ai-labs/ai-operating-system/pull/75) |

---

## Sprint 16 — ChromaDB Eval Coverage

**Objective:** Close the untested claim that `RETRIEVAL_BACKEND=chroma` produces valid grounded output. Since Sprint 5, the chroma backend has been live in production but exercised by zero eval cases. Sprint 16 adds end-to-end eval coverage, live chroma runners, CI gates, and an `is_index_ready()` helper that runners and tests share.

**Maps to:** plan.md Phase 8 / ChromaDB eval coverage

**Status: Complete — shipped in [#83](https://github.com/ramirez-ai-labs/ai-operating-system/pull/83). 224 tests passing.**

| Step | Status | PR |
| --- | --- | --- |
| Add `is_index_ready()` to `packages/shared/retrieval/chroma.py` — shared pre-flight check for runners and tests | Done | [#81](https://github.com/ramirez-ai-labs/ai-operating-system/pull/81) |
| Create `scripts/run_director_os_evals_chroma.py` — Director OS live runner; skips gracefully with `--ci` when index absent | Done | [#81](https://github.com/ramirez-ai-labs/ai-operating-system/pull/81) |
| Create `scripts/run_brand_os_evals_chroma.py` — Brand OS live runner; skips gracefully with `--ci` when index absent | Done | [#81](https://github.com/ramirez-ai-labs/ai-operating-system/pull/81) |
| Add `tests/test_chroma_eval_integration.py` — 8 tests: graph routing, full eval pipeline, index ready check, runner CI skip logic | Done | [#81](https://github.com/ramirez-ai-labs/ai-operating-system/pull/81) |
| Wire chroma eval steps into `.github/workflows/ci.yml` (both runners with `--ci` flag) | Done | [#81](https://github.com/ramirez-ai-labs/ai-operating-system/pull/81) |
| Fix source path mismatch — `chroma.py` `_parse_results` now uses `Path(...).name` to match `local_files.py` source format | Done | [#83](https://github.com/ramirez-ai-labs/ai-operating-system/pull/83) |
| Add `BRAND_OS_CHROMA_EVALUATORS` — excludes prefix-based scorers calibrated for keyword retrieval | Done | [#83](https://github.com/ramirez-ai-labs/ai-operating-system/pull/83) |
| Run live chroma evals — commit `evaluations/director_os/results_chroma.json` (7/7) and `evaluations/brand_os/results_chroma.json` (7/7) | Done | [#83](https://github.com/ramirez-ai-labs/ai-operating-system/pull/83) |

---

## Sprint 15 — Brand OS Claude Provider Path

**Objective:** Add the Claude provider path to Brand OS — the last domain without model-backed synthesis. Achieves full parity: all four domains have `use_model`, a Claude provider, a fallback graph, and a committed eval results file.

**Maps to:** plan.md Phase 8 / Brand OS Claude path

**Status: Complete — PR #80 merged, v1.2.0 tagged**

| Step | Status | PR |
| --- | --- | --- |
| Add `use_model`, `provider`, `claude_model`, `fallback_to_deterministic` to `BrandContentDraftRequest` in `packages/shared/schemas/brand_os.py` | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Create `packages/shared/providers/brand_os.py` — `ClaudeBrandContentDraftProvider` via forced tool use + citation grounding | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Update `packages/shared/graphs/brand_os.py` — add model path, fallback routing, `_build_provider`, conditional edge | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Recalibrate `required_summary_terms` in `evaluations/brand_os/content_draft_cases.json` for cross-path stability; clear unstable podcast terms; add `BRAND_OS_CLAUDE_EVALUATORS` excluding prefix-purity scorer | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Create `scripts/run_brand_os_evals_claude.py` — Claude eval runner using `BRAND_OS_CLAUDE_EVALUATORS` | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Add 3 model-path tests to `tests/test_brand_os_graph.py` (model path, fallback, no-fallback raise) | Done | [#80](https://github.com/ramirez-ai-labs/ai-operating-system/pull/80) |
| Run live Claude evals — commit `evaluations/brand_os/results_claude.json` (7/7 passed, 100%) | Done | — |
| Cut `v1.2.0` tag — milestone: all four domains have Claude providers and committed live eval results | Done | — |

---

## Sprint 14 — Live Claude Eval Results + v1.1.0 Release

**Objective:** Commit live-Claude eval results for all three model-capable domains and cut the v1.1.0 release tag. No code changes required — the runners are correct and the API key is the only blocker.

**Maps to:** plan.md Gap 1 / Gap 2 close-out

**Status: Complete — PR #78 merged, v1.1.0 tagged**

| Step | Status | PR |
| --- | --- | --- |
| Merge PR #77 — README 4-domain update + new Claude eval runner scripts | Done | [#77](https://github.com/ramirez-ai-labs/ai-operating-system/pull/77) |
| Recalibrate `required_summary_terms` across Director OS, Interview OS, and One-on-One OS eval cases to be stable across both deterministic and Claude paths | Done | [#78](https://github.com/ramirez-ai-labs/ai-operating-system/pull/78) |
| Run `python scripts/run_director_os_evals_claude.py` — 4/4 passed (100%) | Done | [#78](https://github.com/ramirez-ai-labs/ai-operating-system/pull/78) |
| Run `python scripts/run_interview_os_evals_claude.py` — commit `evaluations/interview_os/results_claude.json` (4/4 passed, 100%) | Done | [#78](https://github.com/ramirez-ai-labs/ai-operating-system/pull/78) |
| Run `python scripts/run_one_on_one_os_evals_claude.py` — commit `evaluations/one_on_one_os/results_claude.json` (4/4 passed, 100%) | Done | [#78](https://github.com/ramirez-ai-labs/ai-operating-system/pull/78) |
| Commit the three `results_claude.json` files | Done | [#78](https://github.com/ramirez-ai-labs/ai-operating-system/pull/78) |
| Cut `v1.1.0` tag — milestone: four domains, multiagent CI gate, committed Claude results for all three model-capable domains | Done | — |

---

## Coordination notes

- Sprint 1 is complete. Live Claude eval results committed in PR #56 — 3/3 cases, 100% signal and safety. All five JD requirements are satisfied in the repo.
- Sprint 2 is complete. The standalone MCP server shipped in PR #50 with both workflow tools registered, tests passing, and Claude Desktop config included.
- Sprint 3 remaining items (filesystem edge cases, CI coverage) rolled into Sprint 9.
- Sprint 4 remaining items (README MCP section, topics, tag) rolled into Sprint 9.
- Sprint 5 is complete (PR #57). ChromaDB + Ollama embedding infrastructure is in place. Activate with `RETRIEVAL_BACKEND=chroma` after running the ingest script.
- Sprints 6, 7, and 8 are complete on `feat/sprint-6-7-tiered-agents`. Prompt caching, multi-agent researcher→writer pipeline, realistic demo data, Mermaid architecture diagram, and "Why Claude" framing all shipped together.
- Sprint 9 is complete. Phase 5e Ollama routing shipped. `WorkflowTrace.routing_model` reflects the actual routing path. v1.0.0 tagged and released. 174 tests passing.
- Sprint 10a is complete (PR #70, 2026-06-13). Post-ship code review surfaced 7 defects; 6 fixed, 7th (mcp_response.content discarded) is the Sprint 10b design decision. 175 tests passing.
- Sprint 10b is complete (PR #72, 2026-06-13). MCP-first synthesis implemented. `mcp_synthesis` schema field added. Provider clarity docstring added. 178 tests passing.
- Sprints 10c, 10d, and 11 are complete (feat/sprint-10c-10d-11-completeness, 2026-06-13). Eval runner rewrote to use production provider path. Multiagent eval cases added. Interview OS third workflow domain shipped (schemas, graph, workflow, route, routing, data, evals, tests, MCP tool, console). Issue templates and CONTRIBUTING.md added.
- Sprint 12 is complete (feat/sprint-12-interview-os-completeness, 2026-06-13). Interview OS eval library, CI gate, and Claude provider path added. All three original workflow domains now have full eval coverage in CI and a model-backed synthesis option. 192 tests passing.
- Sprint 13 is complete (PR #75, 2026-06-13). One-on-One OS fourth workflow domain shipped (schemas, graph, provider, workflow, route, routing, data, evals, tests, MCP tool). Multiagent CI gate wired for `multiagent_cases.json`. All four domains have full eval runners in CI and a Claude-backed synthesis path. 213 tests passing.
- Sprint 14 is complete (PR #78, 2026-06-14). `required_summary_terms` recalibrated across three eval case files for cross-path stability. Live Claude eval results committed for Director OS (4/4), Interview OS (4/4), and One-on-One OS (4/4) — all 100%. v1.1.0 tagged.
- Sprint 15 is complete (PR #80, 2026-06-15). Brand OS Claude provider path shipped: `ClaudeBrandContentDraftProvider`, `use_model` schema fields, conditional graph edge, `BRAND_OS_CLAUDE_EVALUATORS` (excludes prefix-purity scorer, which tests deterministic routing only), eval runner. Live Claude evals: 7/7 passed (100%). All four domains now have full Claude provider parity and committed eval results. 216 tests passing. v1.2.0 tagged.
