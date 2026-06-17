# AI-OS Technology Stack

How each tool in the stack is used, where it lives in the codebase, and what specific capability it provides.

---

## Python 3.11+

| | |
|---|---|
| **Used for** | Primary implementation language across all layers |
| **Key features used** | `TypedDict` for LangGraph state, `Literal` types for provider constraints, `from __future__ import annotations` for forward refs, `contextlib.contextmanager` for tracing lifecycle |
| **Where** | Everything under `packages/`, `apps/`, `scripts/` |

---

## FastAPI

| | |
|---|---|
| **Used for** | HTTP API layer — request parsing, response serialization, route registration |
| **Key features used** | Pydantic model integration for automatic request validation and 422 errors, `response_model` for typed responses, `HTMLResponse` for the operator console, `HTTPException` for structured error envelopes |
| **Where** | `apps/api/main.py` |
| **Why thin** | All workflow logic lives in domain packages so it can be tested without starting FastAPI. The API layer is intentionally ≤125 lines. |

---

## Pydantic v2

| | |
|---|---|
| **Used for** | Request/response contracts, eval case serialization, evidence grounding enforcement |
| **Key features used** | `BaseModel` for all domain schemas, `Field()` with `ge`/`le` for range validation, `Literal` for provider enum constraints, `model_validate()` for JSON-to-typed-object deserialization, `model_dump()` for serialization to LangSmith and evaluators, `default_factory` for mutable defaults |
| **Where** | `packages/shared/schemas/` — all 5 schema files; `packages/shared/evaluations/` — all 4 eval modules |
| **Architectural role** | The same schema models are shared by FastAPI (HTTP), LangGraph (state), the eval harness (case loading), and LangSmith (dataset sync). One definition drives the full stack. |

---

## LangGraph

| | |
|---|---|
| **Used for** | Stateful workflow orchestration for all 4 domain graphs |
| **Key features used** | `StateGraph` with `TypedDict` state, `add_node` / `add_edge` / `add_conditional_edges`, `compile()` for a reusable compiled graph, `START` / `END` sentinels, conditional routing for deterministic fallback |
| **Where** | `packages/shared/graphs/director_os.py`, `brand_os.py`, `interview_os.py`, `one_on_one_os.py` |
| **Pattern** | Each domain graph has two nodes: `retrieve_evidence` and `build_response`. Director OS adds `build_draft`, `assemble_response`, `validate_response`. A conditional edge after `build_response` retries with the deterministic path if model synthesis fails and `fallback_to_deterministic=True`. |

```
StateGraph nodes per domain:

Director OS:   retrieve_evidence → build_draft → assemble_response → validate_response ⟲
Brand OS:      retrieve_evidence → build_response ⟲
Interview OS:  retrieve_evidence → build_response ⟲
One-on-One OS: retrieve_evidence → build_response ⟲

⟲ = conditional fallback edge back to build_response on synthesis failure
```

---

## LangSmith

| | |
|---|---|
| **Used for** | Node-level execution tracing and cloud-backed evaluation runs |
| **Key features used** | `@traceable` decorator on every graph entry point and internal node, `tracing_context()` wrapping each `graph.invoke()`, `Client.create_dataset()` / `create_examples()` for eval dataset sync, `evaluate()` for cloud-backed eval runs |
| **Where** | `packages/shared/observability/langsmith.py` — tracing helpers; `packages/shared/evaluations/` — `sync_langsmith_*_dataset()` and `run_langsmith_*_evaluations()` in all 4 eval modules |
| **Opt-in design** | Tracing is a silent no-op when `LANGSMITH_TRACING != "true"` or `LANGSMITH_API_KEY` is absent. No code paths branch on whether tracing is enabled. |
| **Traces land in** | `ai-os` project at smith.langsmith.com (configurable via `LANGSMITH_PROJECT`) |

---

## Anthropic SDK (Claude)

| | |
|---|---|
| **Used for** | Structured synthesis in all 4 domains, multi-agent pipeline, MCP tool loop |
| **Key features used** | Tool use (`tools` + `tool_choice`) for schema-enforced structured output, `cache_control: {"type": "ephemeral"}` for prompt caching, streaming-compatible message construction |
| **Models used** | `claude-haiku-4-5-20251001` (default — cost-effective for structured extraction), Sonnet/Opus on demand |
| **Where** | `packages/shared/providers/claude.py` (Director OS), `packages/shared/providers/brand_os.py`, `interview_os.py`, `one_on_one_os.py`; `packages/shared/agents/researcher.py`, `writer.py`; `packages/shared/mcp/orchestrator_integration.py` |
| **Why tool use** | The evidence grounding invariant — every output item must cite `source` + `line_number` — is enforced at the schema level via tool definitions. Hallucinated citations fail at parse time, not post-hoc. |

---

## Ollama

| | |
|---|---|
| **Used for** | Local LLM inference — Chief of Staff routing classification and Director OS synthesis |
| **Key features used** | `/api/chat` HTTP endpoint (no SDK — raw `urllib.request` for zero external dependencies), `llama3.2` as the default routing and synthesis model |
| **Where** | `packages/shared/orchestration/chief_of_staff.py` (routing), `packages/shared/providers/ollama.py` (Director OS synthesis) |
| **Scope** | Ollama synthesis is Director OS only. Brand OS, Interview OS, and One-on-One OS require `provider="claude"`. |
| **Fallback** | Chief of Staff falls back to keyword routing automatically when Ollama is unreachable — no operator action required. |

---

## ChromaDB

| | |
|---|---|
| **Used for** | Semantic vector retrieval — embedding-based document search as an alternative to keyword matching |
| **Key features used** | `PersistentClient` for on-disk index, `collection.query()` with `n_results`, metadata filtering by `data_root` to scope retrieval per domain, `nomic-embed-text` via Ollama for embeddings |
| **Where** | `packages/shared/retrieval/chroma.py`, `packages/shared/retrieval/backend.py` (retrieval backend selector) |
| **Ingest** | `scripts/ingest_chroma.py` — builds the index from markdown files under `data/local_only/` |
| **Eval results** | All 4 domains have committed `results_chroma.json` (28/28 pass rate) |
| **vs keyword retrieval** | Keyword retrieval is the default (no Ollama required). ChromaDB activates when the index exists — the backend selector chooses automatically. |

---

## MCP (Model Context Protocol)

| | |
|---|---|
| **Used for** | Two distinct integration patterns |
| **Pattern 1 — In-process tool loop** | Claude calls `list_files`, `read_file`, `search_content` autonomously during synthesis. The orchestrator executes each tool call, appends the result to the message history, and continues until Claude produces a final response. Activated via `use_mcp=True` on `/orchestrate`. |
| **Pattern 2 — Standalone MCP server** | `apps/mcp/server.py` exports all 4 domain entry points as MCP tools (`director_os.weekly_update`, `brand_os.content_draft`, `interview_os.brief`, `one_on_one_os.brief`) for use with Claude Desktop or Claude Code. |
| **Where** | `packages/shared/mcp/filesystem_server.py` (tool definitions), `packages/shared/mcp/orchestrator_integration.py` (loop runner), `apps/mcp/server.py` (standalone server) |

---

## GitHub Actions

| | |
|---|---|
| **Used for** | CI gate on every PR to `main` |
| **Pipeline steps** | `ruff` lint → `pytest` with coverage → 4 deterministic eval runners → 4 chroma eval runners (skipped if index absent) → multiagent eval runner |
| **Where** | `.github/workflows/ci.yml` |
| **Design principle** | All CI steps run without API keys. LangSmith and Claude evals are on-demand only — never blocking CI. |

---

## ruff

| | |
|---|---|
| **Used for** | Linting and import sorting |
| **Where** | `pyproject.toml` (config), `.github/workflows/ci.yml` (CI step) |

---

## pytest

| | |
|---|---|
| **Used for** | Unit and integration tests across all 4 domains |
| **Test count** | 224 passing, 6 skipped (Claude/Ollama tests skipped without API keys) |
| **Where** | `tests/` |
| **Pattern** | Claude-dependent tests use `pytest.importorskip` or environment checks so the full suite passes in CI without any API keys. |
