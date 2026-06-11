# AI-OS Sprint Tracker

Tactical execution checklist for the current build cycle. Phases and long-term roadmap are in [plan.md](plan.md).

---

## Sprint 1 — Wire Claude in

**Objective:** Validate the Claude provider end-to-end with a live eval run and lock in the layered model config.

**Maps to:** plan.md Phase 5b

| Step | Status | Notes |
|---|---|---|
| `packages/shared/providers/claude.py` | ✅ Done | Implements `WeeklyUpdateProvider` via Anthropic SDK tool use |
| `ANTHROPIC_API_KEY` in `.env.example` | ✅ Done | Documented alongside `OLLAMA_*` and `LANGSMITH_*` vars |
| `anthropic` in `pyproject.toml` | ✅ Done | `anthropic>=0.40.0` is a core dependency |
| `--provider claude` flag on eval runner | ✅ Done | `scripts/run_director_os_evals.py --provider claude` |
| Run live eval and commit results | ❌ Pending | Requires `ANTHROPIC_API_KEY`; commit output as `evaluations/director_os/results_claude.json` |
| `config/models.yaml` | ❌ Pending | Directory and file don't exist yet; README target structure references it |

**Commit target:** `feat: add Claude provider with live eval results`

---

## Sprint 2 — MCP Server

**Objective:** Expose Director OS and Brand OS workflows as MCP tools so any MCP-compatible host (Claude Desktop, Claude Code, enterprise integrations) can invoke them.

**Maps to:** plan.md Phase 5c

| Step | Status | Notes |
|---|---|---|
| `packages/shared/mcp/filesystem_server.py` | ❌ Pending | MCP server using the `mcp` Python SDK |
| `packages/shared/mcp/orchestrator_integration.py` | ❌ Pending | Wires MCP tool calls into the orchestrator |
| `mcp` SDK added to `pyproject.toml` | ❌ Pending | |
| Wire `orchestrator_integration` into `/orchestrate` endpoint | ❌ Pending | `trace.mcp_tool_calls` should appear in response |
| `tests/test_claude_mcp.py` | ❌ Pending | Stub tests for tool registration, schema correctness, round-trip invocation |
| `claude_desktop_config.json` example | ❌ Pending | One-step wiring to Claude Desktop |
| All MCP stub tests passing | ❌ Pending | Must pass in CI without a live Claude connection |

**Commit target:** `feat: add filesystem MCP server with orchestrator integration`

---

## Sprint 3 — Docs and Framing

**Objective:** Ship the deployment guide, updated README, and a v1.0 release tag that frames AI-OS as an enterprise-ready MCP-first AI system.

**Maps to:** plan.md Phase 7 (hardening) and Phase 5c (MCP docs)

| Step | Status | Notes |
|---|---|---|
| `docs/DEPLOYMENT.md` | ❌ Pending | Enterprise deployment guide |
| Update `README.md` with MCP section and v1.0 framing | ❌ Pending | Drop in `README_new.md` content |
| GitHub topics: `anthropic`, `claude`, `mcp`, `langgraph`, `ai-agents`, `enterprise-ai` | ❌ Pending | GitHub UI task |
| Archive or unpin `openai-foundations` from org page | ❌ Pending | GitHub UI task |
| Cut `v1.0` release tag with description | ❌ Pending | `git tag v1.0 && git push origin v1.0` |

**Commit target:** `docs: enterprise deployment guide and updated README`

---

## Coordination notes

- Sprint 2 files (`filesystem_server.py`, `orchestrator_integration.py`, `test_claude_mcp.py`, `claude_desktop_config.json`) are ready to drop in from the working zip — the repo structure and provider/graph patterns are fully compatible.
- Sprint 3 README update should land after Sprint 2 is merged so the MCP section reflects real, working code.
- `config/models.yaml` (Sprint 1 remainder) should be created before Sprint 2 ships since it's referenced in the README target structure.
