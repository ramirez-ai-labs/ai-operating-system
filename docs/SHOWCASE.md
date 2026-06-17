# AI-OS Showcase

## What this is

AI Operating System (AI-OS) is a production-grade multi-agent system I built to
solve a real problem I face as a Director of Developer & Platform Experience:
technical leaders operate across fragmented systems - Jira, Confluence, 1:1 notes,
roadmap docs, candidate pipelines - and spend significant time synthesizing that
information into structured output for stakeholders.

AI-OS automates that synthesis. It reads local markdown notes, retrieves the most
relevant evidence, and produces grounded output where every item cites the exact
source file and line number it came from. No hallucination, no black-box summaries -
every output item is traceable back to the data.

Four workflow domains, each solving a specific synthesis problem a technical leader
faces weekly:

| Domain | What it does |
|---|---|
| **Director OS** | Synthesizes project notes into wins, risks, and next steps for a weekly leadership update |
| **Brand OS** | Turns technical work into LinkedIn post outlines, podcast angles, and repo improvement notes |
| **Interview OS** | Builds a candidate brief with key questions, talking points, and red flags from local hiring notes |
| **One-on-One OS** | Prepares a 1:1 meeting brief with action items, talking points, blockers, and kudos |

---

## Why I built it

I run a developer platform organization at a large financial services firm. Every week
I synthesize status across 8+ active workstreams, prepare for 6-10 direct report 1:1s,
and produce content that represents the team externally. The existing tools - Jira,
Confluence, meeting notes - don't talk to each other.

I built AI-OS as both a working tool and a portfolio artifact that demonstrates
how I think about production AI systems:

- **Evidence grounding as an invariant** - enterprise AI outputs must be auditable.
  Every item cites source + line number. This is enforced at the schema level, not post-hoc.
- **Deterministic fallback as a safety net** - model synthesis is opt-in. The system
  always has a working deterministic path, so it never fails silently.
- **Evaluation as a first-class concern** - 28 eval cases across all 4 domains,
  three retrieval paths (keyword / ChromaDB semantic / LangSmith cloud), all committed
  and gated in CI.
- **Observability by default** - LangSmith traces every graph node automatically
  when configured. Zero code changes to switch tracing on or off.

---

## How I use it - domain walkthroughs

### Director OS - weekly leadership update

I keep markdown files under `data/local_only/projects/` with running notes from
1:1s, syncs, and async updates. Before my Monday leadership review I run:

```bash
curl -X POST http://127.0.0.1:8000/director-os/weekly-update \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/projects",
    "week_label": "week_15"
  }'
```

Response (truncated):

```json
{
  "summary": "Weekly update synthesized from local project evidence...",
  "wins": [
    {
      "text": "Win: the new developer onboarding checklist cut average time-to-first-commit from 4 days to 11 hours for the last 3 new hires.",
      "source": "1on1_marcus_devex_lead.md",
      "line_number": 10
    }
  ],
  "risks": [
    {
      "text": "Risk: the vendor auth middleware EOL is causing anxiety among the developer community...",
      "source": "1on1_marcus_devex_lead.md",
      "line_number": 14
    }
  ],
  "next_steps": [...],
  "evidence": [...]
}
```

Every item is grounded. The source file and line number are the citation.

---

### Brand OS - content from technical work

I keep notes on work I want to write about under `data/local_only/brand/`. Brand OS
turns those notes into structured content starting points:

```bash
curl -X POST http://127.0.0.1:8000/brand-os/content-draft \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/brand",
    "focus": "developer onboarding"
  }'
```

Returns `post_outline`, `podcast_angles`, and `repo_improvements` - each item
grounded to a specific note.

---

### Interview OS - candidate brief before a screen

Before a candidate screen I drop notes into `data/local_only/interviews/` and run:

```bash
curl -X POST http://127.0.0.1:8000/interview-os/brief \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/interviews",
    "candidate_name": "Alex Rivera",
    "role": "Senior Platform Engineer",
    "focus": "distributed systems experience"
  }'
```

Returns `key_questions`, `talking_points`, and `red_flags` - grounded to my notes,
not generated from thin air.

---

### One-on-One OS - 1:1 meeting prep

I keep running notes on each direct report. Before a 1:1 I run:

```bash
curl -X POST http://127.0.0.1:8000/one-on-one/brief \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "data/local_only/1on1s",
    "direct_report": "Marcus",
    "focus": "platform migration blockers"
  }'
```

Returns `action_items`, `talking_points`, `blockers`, and `kudos` - drawn from
the notes I have been collecting, not invented.

---

## Technical depth - what this demonstrates

### LangGraph state machines with conditional routing

All 4 domains run as compiled LangGraph `StateGraph` instances. Each graph has
a conditional edge after `build_response` that retries with the deterministic path
if model synthesis fails and `fallback_to_deterministic=True`. Director OS has
an additional `validate_response` node that enforces evidence grounding before
the response reaches the API layer.

```
Director OS graph:
retrieve_evidence -> build_draft -> assemble_response -> validate_response
                                                              |
                                              route_after_validation -> END
                                                              | (fallback)
                                                       build_draft (retry)
```

### Claude tool use for schema-enforced grounding

The Claude provider passes a tool schema with required `source` and `line_number`
fields. Claude cannot return a wins/risks/next-steps item without citing both.
Hallucinated citations fail at parse time - the validator catches them before they
reach the response.

This is distinct from prompt-level instructions like "always cite your sources."
The schema enforces it structurally.

### LangSmith observability - node-level traces

Every graph node carries `@traceable`. Setting `LANGSMITH_TRACING=true` and
`LANGSMITH_API_KEY` in `.env` is all that is required - every `graph.invoke()`
across all 4 domains emits a full execution trace to the `ai-os` project at
smith.langsmith.com, with inputs, outputs, and latency at each node.

![LangSmith trace - Director OS graph with retrieve_evidence, build_draft, assemble_response, validate_response nodes](../LanndSmithOutput.png)

### Three-path evaluation harness

Each domain has eval cases covering three retrieval paths:

| Path | Retriever | Requires |
|---|---|---|
| Local (keyword) | `local_files.py` - BM25-style keyword match | Nothing - runs in CI |
| Chroma (semantic) | `chroma.py` - ChromaDB + `nomic-embed-text` embeddings | Local Ollama |
| LangSmith (cloud) | `run_*_evals.py --langsmith` | `LANGSMITH_API_KEY` |

All 28 eval cases pass across all 4 domains on the local and chroma paths.
Results are committed as `results_chroma.json` per domain - the CI gate fails
if any case regresses.

### Pydantic as the single source of truth

The same Pydantic `BaseModel` definitions drive:
- FastAPI request validation and 422 error responses
- LangGraph `TypedDict` state shape
- Eval case deserialization from JSON on disk
- LangSmith dataset sync via `model_dump()`

One schema change propagates through the full stack with no manual wiring.

### Multi-agent pipeline for audience-aware formatting

When `target_audience` is set on `/orchestrate`, a `ResearcherAgent -> WriterAgent`
pipeline runs after the domain workflow. The researcher uses Claude tool use to
produce structured findings (`ResearchSynthesis`); the writer takes only that
struct - not raw evidence - and formats it for the audience. This bounds
hallucination risk: the writer can only rephrase what the researcher extracted.

---

## Eval results

| Domain | Local | Chroma |
|---|---|---|
| Director OS | 7/7 | 7/7 |
| Brand OS | 7/7 | 7/7 |
| Interview OS | 4/4 | 4/4 |
| One-on-One OS | 4/4 | 4/4 |
| **Total** | **22/22** | **22/22** |

---

## Technology stack - how each tool is used

### Python 3.11+

| | |
|---|---|
| **Used for** | Primary implementation language across all layers |
| **Key features used** | `TypedDict` for LangGraph state, `Literal` types for provider constraints, `from __future__ import annotations` for forward refs, `contextlib.contextmanager` for tracing lifecycle |
| **Where** | Everything under `packages/`, `apps/`, `scripts/` |

### FastAPI

| | |
|---|---|
| **Used for** | HTTP API layer - request parsing, response serialization, route registration |
| **Key features used** | Pydantic model integration for automatic request validation and 422 errors, `response_model` for typed responses, `HTMLResponse` for the operator console, `HTTPException` for structured error envelopes |
| **Where** | `apps/api/main.py` |
| **Why thin** | All workflow logic lives in domain packages so it can be tested without starting FastAPI. The API layer is intentionally under 125 lines. |

### Pydantic v2

| | |
|---|---|
| **Used for** | Request/response contracts, eval case serialization, evidence grounding enforcement |
| **Key features used** | `BaseModel` for all domain schemas, `Field()` with `ge`/`le` for range validation, `Literal` for provider enum constraints, `model_validate()` for JSON-to-typed-object deserialization, `model_dump()` for serialization to LangSmith and evaluators, `default_factory` for mutable defaults |
| **Where** | `packages/shared/schemas/` - all 5 schema files; `packages/shared/evaluations/` - all 4 eval modules |
| **Architectural role** | The same schema models are shared by FastAPI (HTTP), LangGraph (state), the eval harness (case loading), and LangSmith (dataset sync). One definition drives the full stack. |

### LangGraph

| | |
|---|---|
| **Used for** | Stateful workflow orchestration for all 4 domain graphs |
| **Key features used** | `StateGraph` with `TypedDict` state, `add_node` / `add_edge` / `add_conditional_edges`, `compile()` for a reusable compiled graph, `START` / `END` sentinels, conditional routing for deterministic fallback |
| **Where** | `packages/shared/graphs/director_os.py`, `brand_os.py`, `interview_os.py`, `one_on_one_os.py` |
| **Pattern** | Each domain graph has two nodes: `retrieve_evidence` and `build_response`. Director OS adds `build_draft`, `assemble_response`, `validate_response`. A conditional edge after `build_response` retries with the deterministic path if model synthesis fails and `fallback_to_deterministic=True`. |

### LangSmith

| | |
|---|---|
| **Used for** | Node-level execution tracing and cloud-backed evaluation runs |
| **Key features used** | `@traceable` decorator on every graph entry point and internal node, `tracing_context()` wrapping each `graph.invoke()`, `Client.create_dataset()` / `create_examples()` for eval dataset sync, `evaluate()` for cloud-backed eval runs |
| **Where** | `packages/shared/observability/langsmith.py` - tracing helpers; `packages/shared/evaluations/` - `sync_langsmith_*_dataset()` and `run_langsmith_*_evaluations()` in all 4 eval modules |
| **Opt-in design** | Tracing is a silent no-op when `LANGSMITH_TRACING != "true"` or `LANGSMITH_API_KEY` is absent. No code paths branch on whether tracing is enabled. |
| **Traces land in** | `ai-os` project at smith.langsmith.com (configurable via `LANGSMITH_PROJECT`) |

### Anthropic SDK (Claude)

| | |
|---|---|
| **Used for** | Structured synthesis in all 4 domains, multi-agent pipeline, MCP tool loop |
| **Key features used** | Tool use (`tools` + `tool_choice`) for schema-enforced structured output, `cache_control: {"type": "ephemeral"}` for prompt caching, streaming-compatible message construction |
| **Models used** | `claude-haiku-4-5-20251001` (default - cost-effective for structured extraction), Sonnet/Opus on demand |
| **Where** | `packages/shared/providers/claude.py` (Director OS), `packages/shared/providers/brand_os.py`, `interview_os.py`, `one_on_one_os.py`; `packages/shared/agents/researcher.py`, `writer.py`; `packages/shared/mcp/orchestrator_integration.py` |
| **Why tool use** | The evidence grounding invariant - every output item must cite `source` + `line_number` - is enforced at the schema level via tool definitions. Hallucinated citations fail at parse time, not post-hoc. |

### Ollama

| | |
|---|---|
| **Used for** | Local LLM inference - Chief of Staff routing classification and Director OS synthesis |
| **Key features used** | `/api/chat` HTTP endpoint (no SDK - raw `urllib.request` for zero external dependencies), `llama3.2` as the default routing and synthesis model |
| **Where** | `packages/shared/orchestration/chief_of_staff.py` (routing), `packages/shared/providers/ollama.py` (Director OS synthesis) |
| **Scope** | Ollama synthesis is Director OS only. Brand OS, Interview OS, and One-on-One OS require `provider="claude"`. |
| **Fallback** | Chief of Staff falls back to keyword routing automatically when Ollama is unreachable - no operator action required. |

### ChromaDB

| | |
|---|---|
| **Used for** | Semantic vector retrieval - embedding-based document search as an alternative to keyword matching |
| **Key features used** | `PersistentClient` for on-disk index, `collection.query()` with `n_results`, metadata filtering by `data_root` to scope retrieval per domain, `nomic-embed-text` via Ollama for embeddings |
| **Where** | `packages/shared/retrieval/chroma.py`, `packages/shared/retrieval/backend.py` (retrieval backend selector) |
| **Ingest** | `scripts/ingest_chroma.py` - builds the index from markdown files under `data/local_only/` |
| **Eval results** | All 4 domains have committed `results_chroma.json` (28/28 pass rate) |
| **vs keyword retrieval** | Keyword retrieval is the default (no Ollama required). ChromaDB activates when the index exists - the backend selector chooses automatically. |

### MCP (Model Context Protocol)

| | |
|---|---|
| **Used for** | Two distinct integration patterns |
| **Pattern 1 - In-process tool loop** | Claude calls `list_files`, `read_file`, `search_content` autonomously during synthesis. The orchestrator executes each tool call, appends the result to the message history, and continues until Claude produces a final response. Activated via `use_mcp=True` on `/orchestrate`. |
| **Pattern 2 - Standalone MCP server** | `apps/mcp/server.py` exports all 4 domain entry points as MCP tools (`director_os.weekly_update`, `brand_os.content_draft`, `interview_os.brief`, `one_on_one_os.brief`) for use with Claude Desktop or Claude Code. |
| **Where** | `packages/shared/mcp/filesystem_server.py` (tool definitions), `packages/shared/mcp/orchestrator_integration.py` (loop runner), `apps/mcp/server.py` (standalone server) |

### GitHub Actions

| | |
|---|---|
| **Used for** | CI gate on every PR to `main` |
| **Pipeline steps** | `ruff` lint -> `pytest` with coverage -> 4 deterministic eval runners -> 4 chroma eval runners (skipped if index absent) -> multiagent eval runner |
| **Where** | `.github/workflows/ci.yml` |
| **Design principle** | All CI steps run without API keys. LangSmith and Claude evals are on-demand only - never blocking CI. |

### ruff + pytest

| | |
|---|---|
| **ruff** | Linting and import sorting - `pyproject.toml` (config), `.github/workflows/ci.yml` (CI step) |
| **pytest** | 224 passing tests, 6 skipped (Claude/Ollama tests skipped without API keys). Claude-dependent tests use environment checks so the full suite passes in CI without any API keys. |
| **Where** | `tests/` |
