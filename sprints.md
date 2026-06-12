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
| Add unit tests for `packages/shared/providers/claude.py` | Done | local |
| Add unit tests for `packages/shared/providers/ollama.py` | Done | local |
| Add tests for `packages/shared/providers/claude_provider.py` fallback and tool-use paths | Done | local |
| Add tests for `packages/shared/mcp/orchestrator_integration.py` | Done | local |
| Add tests for remaining `packages/shared/mcp/filesystem_server.py` edge cases | Pending | — |
| Measure and track coverage trend in CI | Pending | — |

---

## Sprint 4 — Docs and Framing

**Objective:** Ship the deployment guide, updated README, and a v1.0 release tag that frames AI-OS as an enterprise-ready MCP-first AI system.

**Maps to:** plan.md Phase 7 (hardening) and Phase 5c (MCP docs)

**Status: Partially complete — deployment guide shipped; README and release tag remain**

| Step | Status | PR |
|---|---|---|
| `docs/DEPLOYMENT.md` | Done | main |
| Update `README.md` with MCP section and v1.0 framing | Pending | — |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Pending | — |
| Archive or unpin `openai-foundations` from org page | Pending | — |
| Cut `v1.0` release tag with description | Pending | — |

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

## Sprint 6 — Tiered Architecture + MCP Default + Prompt Caching

**Objective:** Move Ollama to the routing layer, make Claude Haiku the default synthesis provider, wire the MCP agentic loop into the default Director OS path, and add prompt caching. Two Claude-native wins in one sprint.

**Maps to:** plan.md Phase 5e and Phase 5f

**Status:** Planned — not yet started

| Step | Status | PR |
|---|---|---|
| Replace keyword routing in `chief_of_staff.py` with Ollama classification call | Pending | — |
| Change `OrchestratorRequest` default `provider` from `"ollama"` to `"claude"` | Pending | — |
| Update operator console default to `provider=claude` | Pending | — |
| Demote Ollama synthesis to explicit fallback (absent API key or explicit opt-in) | Pending | — |
| Wire `orchestrator_integration.py` into default Director OS path when API key present | Pending | — |
| Add `cache_control` to evidence block in `packages/shared/providers/claude.py` | Pending | — |
| Add `cache_read_tokens` and `cache_creation_tokens` to `WorkflowTrace` | Pending | — |
| Operator console renders "Cache hit: X tokens saved" when cache is hit | Pending | — |
| Surface routing model in `WorkflowTrace` alongside synthesis model | Pending | — |
| Tests for Ollama routing path and Claude caching fields | Pending | — |

---

## Sprint 7 — Multi-Agent Researcher → Writer

**Objective:** Add a two-agent workflow demonstrating Claude-to-Claude orchestration. Researcher retrieves and synthesizes evidence via filesystem tools; writer formats the synthesis for a target audience. Required agentic pattern for the Anthropic FE showcase.

**Maps to:** plan.md Phase 5g

**Status:** Planned — not yet started

| Step | Status | PR |
|---|---|---|
| `packages/shared/agents/researcher.py` — Claude with filesystem MCP tools, returns structured synthesis | Pending | — |
| `packages/shared/agents/writer.py` — Claude formats researcher output for `linkedin_post`, `executive_brief`, or `team_update` | Pending | — |
| `target_audience` field on `OrchestratorRequest` — triggers researcher → writer pipeline | Pending | — |
| `agent_calls` list in `WorkflowTrace` — shows researcher and writer invocations with token counts | Pending | — |
| Operator console renders agent call chain when `agent_calls` is populated | Pending | — |
| Tests covering researcher → writer handoff contract | Pending | — |

---

## Sprint 8 — Realistic Demo Data + "Why Claude" Framing

**Objective:** Replace toy markdown files with a realistic enterprise scenario. Add a "Why Claude" README section that explains Claude-specific design decisions. Makes the demo land with a hiring manager or enterprise evaluator.

**Maps to:** plan.md Phase 5h

**Status:** Planned — not yet started

| Step | Status | PR |
|---|---|---|
| Replace `data/local_only/projects/` with realistic quarterly planning scenario (platform migration, cross-team dependencies, open risks) | Pending | — |
| Replace `data/local_only/brand/` with realistic brand scenario (conference talk, podcast pipeline, LinkedIn backlog) | Pending | — |
| Add "Why Claude" section to `README.md` | Pending | — |
| Update `README.md` architecture diagram to show tiered model layers | Pending | — |

---

## Sprint 9 — Hygiene (Sprint 3 remainder + Sprint 4 docs/tag)

**Objective:** Close out the two remaining Sprint 3 test gaps and complete the Sprint 4 docs and release framing. Runs in parallel with Sprint 7 and D.

**Maps to:** plan.md Phase 5 (test coverage), Phase 5c (MCP docs), Phase 7 (hardening)

**Status:** Planned — not yet started

| Step | Status | PR |
|---|---|---|
| Add tests for remaining `packages/shared/mcp/filesystem_server.py` edge cases | Pending | — |
| Measure and track coverage trend in CI | Pending | — |
| Update `README.md` with MCP section and v1.0 framing | Pending | — |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Pending | — |
| Archive or unpin `openai-foundations` from org page | Pending | — |
| Cut `v1.0` release tag with description | Pending | — |

---

## Coordination notes

- Sprint 1 is complete. Live Claude eval results committed in PR #56 — 3/3 cases, 100% signal and safety. All five JD requirements are now satisfied in the repo.
- Sprint 2 is complete. The standalone MCP server shipped in PR #50 with both workflow tools registered, tests passing, and Claude Desktop config included.
- Sprint 3 remaining items (filesystem edge cases, CI coverage) roll into Sprint 9.
- Sprint 4 remaining items (README MCP section, topics, tag) roll into Sprint 9.
- Sprint 5 is complete (PR #57). ChromaDB + Ollama embedding infrastructure is in place. Activate with `RETRIEVAL_BACKEND=chroma` after running the ingest script. Semantic search becomes demonstrably better than keyword matching after Sprint 8 replaces the toy sample data.
- Sprint 6 and Sprint 7 can be sequenced or parallelized after Sprint 5 ships.
- Sprint 8 and Sprint 9 have no hard dependencies and can run alongside any showcase sprint.
