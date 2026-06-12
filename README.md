# AI Operating System (AI-OS)

AI-OS is a production-grade multi-agent system that helps technical leaders
synthesize fragmented information — project status, team signals, brand work —
into structured, actionable output.

Built on **Claude** (Anthropic) with **LangGraph orchestration**, an
in-process filesystem tool loop, and a **standalone MCP server** for workflow
entry points.

---

## What this demonstrates

| Capability | Implementation |
|---|---|
| Production Claude integration | `packages/shared/providers/claude_provider.py` |
| In-process MCP tool loop | `packages/shared/mcp/filesystem_server.py` + `packages/shared/mcp/orchestrator_integration.py` |
| Standalone MCP server | `apps/mcp/server.py` |
| LLM evaluation framework | `scripts/run_director_os_evals_claude.py` + committed results |
| Operator trace / observability | `trace.mcp_tool_calls` in every `/orchestrate` response |
| Repeatable deployment pattern | `docs/DEPLOYMENT.md` — secrets, eval gate, rollback, MCP adapters |
| LangGraph state graphs | `packages/shared/graphs/director_os.py`, `brand_os.py` |
| LangSmith tracing | Optional — `LANGSMITH_API_KEY` + `--langsmith` flag |

The architecture is designed to be adapted. The provider layer, the
in-process filesystem tool loop, and the standalone MCP server are all
swappable — designed for the kind of customer environment customization that
enterprise AI work requires.

---

## Architecture

```
User prompt
    │
    ▼
Chief of Staff Orchestrator  ──── routes to ────▶  Director OS workflow
    │                                               Brand OS workflow
    │
    ├── ClaudeProvider (claude-haiku-4-5, default)
    │       └── Falls back to Ollama when ANTHROPIC_API_KEY absent
    │
    ├── FilesystemMCPServer
    │       ├── list_files(path, pattern)
    │       ├── read_file(path)
    │       └── search_content(path, query)
    │
    ├── Retrieval layer (local markdown, CSV, JSON)
    │
    └── Validator agent (evidence-based, low verbosity, no unsupported claims)
            │
            ▼
        Structured response + operator trace
```

---

## Quick start

Requirements: Python 3.11+

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Copy env and optionally add your Anthropic API key
cp .env.example .env

# Run the API
uvicorn apps.api.main:app --reload --env-file .env

# Run Director OS evals — local, no API key required
python scripts/run_director_os_evals.py

# Run tests (Claude tests skipped without API key)
pytest tests/ -v
```

---

## Working with Claude

The Claude provider is active when `ANTHROPIC_API_KEY` is set.
Falls back to the Ollama deterministic path when the key is absent —
no code changes required.

```bash
# Director OS — weekly update with Claude
curl -X POST http://127.0.0.1:8000/director-os/weekly-update \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/projects",
    "focus": "leadership update",
    "max_documents": 5
  }'
```

The response includes a `trace` object showing which MCP tools were called,
what data was retrieved, and token counts:

```json
{
  "result": "...",
  "trace": {
    "mcp_tool_calls": [
      {
        "tool": "read_file",
        "input": {"path": "projects/weekly-notes.md"},
        "success": true,
        "result_preview": "# Week of June 2026..."
      }
    ],
    "total_input_tokens": 842,
    "total_output_tokens": 312
  }
}
```

---

## MCP entry points

AI-OS currently supports two MCP-related paths:

1. The in-process filesystem tool loop used by the FastAPI `/orchestrate` flow.
2. The standalone MCP server in `apps/mcp/server.py`, which exports the real
   workflow entry points as MCP tools for Claude Desktop or Claude Code.

The filesystem loop exposes three tools Claude can invoke during synthesis:

| Tool | Description |
|---|---|
| `list_files(path, pattern)` | Discover available project notes and docs |
| `read_file(path)` | Retrieve full file contents for synthesis |
| `search_content(path, query)` | Find documents mentioning a specific topic or risk |

Claude calls these autonomously during the orchestration loop. The orchestrator
executes each tool call, appends the result to the message history, and
continues until Claude produces a final text response.

---

## Eval results

Eval results against Claude are committed to `evaluations/director_os/`.
Run the eval set and commit updated results before any production deployment:

```bash
python scripts/run_director_os_evals_claude.py
git add evaluations/director_os/results_claude.json
git commit -m "eval: update Director OS results against claude-haiku"
```

---

## Model provider strategy

AI-OS uses different models for different workloads — local inference for
routing and low-stakes tasks, Claude for structured synthesis, Sonnet/Opus
on demand for complex runs:

| Layer | Model | Workload |
|---|---|---|
| Local inference | Ollama (`llama3.2`) | Routing, classification, low-stakes summarization — free, on-device, no API key |
| Cloud synthesis | Claude Haiku 4.5 | Structured output via tool use, MCP orchestration — cost-effective |
| Premium synthesis | Claude Sonnet / Opus | Complex or high-stakes runs — on demand |

All providers implement the same interface. Switching is a single field
change in the request — no workflow logic changes required.

```bash
# Ollama — no API key required
curl -X POST http://127.0.0.1:8000/director-os/weekly-update \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/projects",
    "use_model": true,
    "provider": "ollama",
    "ollama_model": "llama3.2"
  }'

# Claude Haiku — structured synthesis
curl -X POST http://127.0.0.1:8000/director-os/weekly-update \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/projects",
    "use_model": true,
    "provider": "claude",
    "claude_model": "claude-haiku-4-5-20251001"
  }'
```

---

## Technology stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Pydantic |
| Workflow orchestration | LangGraph |
| Model provider (cloud) | Anthropic SDK — Claude Haiku / Sonnet / Opus |
| Model provider (local) | Ollama |
| In-process MCP loop | `packages/shared/mcp/filesystem_server.py` |
| Standalone MCP server | `apps/mcp/server.py` |
| Observability | LangSmith (optional) |
| Evaluation | Custom eval harness with committed results |
| CI/CD | GitHub Actions (lint, test, evals on every PR) |

---

## Why this exists

Technical leaders operate across fragmented systems: Jira, Confluence,
meeting notes, roadmap docs, 1:1 notes. AI-OS synthesizes these into
structured, evidence-grounded output — weekly updates, risk summaries,
content drafts — without defaulting to opaque or autonomous agent behavior.

It is designed to show how to embed AI into real enterprise workflows:
provider abstraction, MCP tool integration, evaluation frameworks,
operator observability, and deployment patterns that survive contact
with real InfoSec and compliance requirements.
