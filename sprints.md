# AI-OS Sprint Tracker

Tactical execution checklist for the current build cycle. Phases and long-term roadmap are in [plan.md](plan.md).

---

## Sprint 1 — Wire Claude in

**Objective:** Validate the Claude provider end-to-end with a live eval run and lock in the layered model config.

**Maps to:** plan.md Phase 5b

**Status: Complete — all items merged or pending final PR merge**

| Step | Status | PR |
|---|---|---|
| `packages/shared/providers/claude.py` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `ANTHROPIC_API_KEY` in `.env.example` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `anthropic` in `pyproject.toml` | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `--provider claude` flag on eval runner | Done | [#39](https://github.com/ramirez-ai-labs/ai-operating-system/pull/39) |
| `config/models.yaml` | Done | [#42](https://github.com/ramirez-ai-labs/ai-operating-system/pull/42) |
| `evaluations/director_os/results_claude.json` | Open PR | [#44](https://github.com/ramirez-ai-labs/ai-operating-system/pull/44) |

---

## Sprint 2 — MCP Server

**Objective:** Complete the standalone MCP server path so Director OS and Brand OS workflows can be invoked as tools from MCP-compatible hosts.

**Maps to:** plan.md Phase 5c

**Status: Partially implemented — filesystem tool loop is present; standalone workflow server remains**

| Step | Status | PR |
|---|---|---|
| `packages/shared/mcp/filesystem_server.py` | Done | local |
| `packages/shared/mcp/orchestrator_integration.py` | Done | local |
| Wire `orchestrator_integration` into `/orchestrate` endpoint | Done | local |
| Provider selection through Chief of Staff routing | Done | local |
| `tests/test_claude_mcp.py` | Done | local |
| `apps/mcp/server.py` standalone workflow MCP server | Done | local |
| Expose `director_os_weekly_update` as MCP tool | Done | local |
| Expose `brand_os_content_draft` as MCP tool | Done | local |
| `mcp` SDK added to `pyproject.toml` | Done | local |
| `claude_desktop_config.json` example | Done | local |
| Standalone MCP server tests passing | Done | local |

---

## Sprint 3 — Test Coverage Hardening

**Objective:** Raise automated coverage on the provider and MCP integration paths that are still under-tested, so the repo has stronger confidence in its real execution paths.

**Maps to:** plan.md Phase 5 and Phase 5b

**Status: Planned — current suite is 85% overall, with notable gaps in provider and MCP paths**

| Step | Status | PR |
|---|---|---|
| Add unit tests for `packages/shared/providers/claude.py` | Pending | — |
| Add unit tests for `packages/shared/providers/ollama.py` | Pending | — |
| Add tests for `packages/shared/providers/claude_provider.py` fallback and tool-use paths | Pending | — |
| Add tests for `packages/shared/mcp/orchestrator_integration.py` | Pending | — |
| Add tests for remaining `packages/shared/mcp/filesystem_server.py` edge cases | Pending | — |
| Measure and track coverage trend in CI | Pending | — |

---

## Sprint 4 — Docs and Framing

**Objective:** Ship the deployment guide, updated README, and a v1.0 release tag that frames AI-OS as an enterprise-ready MCP-first AI system.

**Maps to:** plan.md Phase 7 (hardening) and Phase 5c (MCP docs)

**Status: Partially started — deployment guide exists; release framing remains**

| Step | Status | PR |
|---|---|---|
| `docs/DEPLOYMENT.md` | Done | local |
| Update `README.md` with MCP section and v1.0 framing | Pending | — |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Pending | — |
| Archive or unpin `openai-foundations` from org page | Pending | — |
| Cut `v1.0` release tag with description | Pending | — |

---

## Coordination notes

- Sprint 2 should now focus on the actual MCP server contract, not the already-implemented in-process Claude filesystem tool loop.
- Sprint 3 README update should land after the standalone MCP server exists so the MCP section reflects real, working code.
- `config/models.yaml` (Sprint 1 remainder) was created before Sprint 2 ships since it is referenced in the README target structure.
