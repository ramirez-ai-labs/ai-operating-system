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

**Objective:** Expose Director OS and Brand OS workflows as MCP tools so any MCP-compatible host (Claude Desktop, Claude Code, enterprise integrations) can invoke them.

**Maps to:** plan.md Phase 5c

**Status: Not started**

| Step | Status | PR |
|---|---|---|
| `packages/shared/mcp/filesystem_server.py` | Pending | — |
| `packages/shared/mcp/orchestrator_integration.py` | Pending | — |
| `mcp` SDK added to `pyproject.toml` | Pending | — |
| Wire `orchestrator_integration` into `/orchestrate` endpoint | Pending | — |
| `tests/test_claude_mcp.py` | Pending | — |
| `claude_desktop_config.json` example | Pending | — |
| All MCP stub tests passing | Pending | — |

---

## Sprint 3 — Docs and Framing

**Objective:** Ship the deployment guide, updated README, and a v1.0 release tag that frames AI-OS as an enterprise-ready MCP-first AI system.

**Maps to:** plan.md Phase 7 (hardening) and Phase 5c (MCP docs)

**Status: Not started**

| Step | Status | PR |
|---|---|---|
| `docs/DEPLOYMENT.md` | Pending | — |
| Update `README.md` with MCP section and v1.0 framing | Pending | — |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | Pending | — |
| Archive or unpin `openai-foundations` from org page | Pending | — |
| Cut `v1.0` release tag with description | Pending | — |

---

## Coordination notes

- Sprint 2 files (`filesystem_server.py`, `orchestrator_integration.py`, `test_claude_mcp.py`, `claude_desktop_config.json`) are ready to drop in from the working zip — the repo structure and provider/graph patterns are fully compatible.
- Sprint 3 README update should land after Sprint 2 is merged so the MCP section reflects real, working code.
- `config/models.yaml` (Sprint 1 remainder) was created before Sprint 2 ships since it is referenced in the README target structure.
