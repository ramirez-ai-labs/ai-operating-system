# AI-OS Showcase

## What this is

AI Operating System (AI-OS) is a production-grade multi-agent system I built to
solve a real problem I face as a Director of Developer & Platform Experience:
technical leaders operate across fragmented systems — Jira, Confluence, 1:1 notes,
roadmap docs, candidate pipelines — and spend significant time synthesizing that
information into structured output for stakeholders.

AI-OS automates that synthesis. It reads local markdown notes, retrieves the most
relevant evidence, and produces grounded output where every item cites the exact
source file and line number it came from. No hallucination, no black-box summaries —
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
and produce content that represents the team externally. The existing tools — Jira,
Confluence, meeting notes — don't talk to each other.

I built AI-OS as both a working tool and a portfolio artifact that demonstrates
how I think about production AI systems:

- **Evidence grounding as an invariant** — enterprise AI outputs must be auditable.
  Every item cites source + line number. This is enforced at the schema level, not post-hoc.
- **Deterministic fallback as a safety net** — model synthesis is opt-in. The system
  always has a working deterministic path, so it never fails silently.
- **Evaluation as a first-class concern** — 28 eval cases across all 4 domains,
  three retrieval paths (keyword / ChromaDB semantic / LangSmith cloud), all committed
  and gated in CI.
- **Observability by default** — LangSmith traces every graph node automatically
  when configured. Zero code changes to switch tracing on or off.

---

## How I use it — domain walkthroughs

### Director OS — weekly leadership update

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

Every item is grounded. The source file and line number are the citation — the
same standard a lawyer would apply to evidence.

---

### Brand OS — content from technical work

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

Returns `post_outline`, `podcast_angles`, and `repo_improvements` — each item
grounded to a specific note.

---

### Interview OS — candidate brief before a screen

Before a candidate screen I drop notes (JD highlights, resume observations, past
feedback) into `data/local_only/interviews/` and run:

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

Returns `key_questions`, `talking_points`, and `red_flags` — grounded to my notes,
not generated from thin air.

---

### One-on-One OS — 1:1 meeting prep

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

Returns `action_items`, `talking_points`, `blockers`, and `kudos` — drawn from
the notes I've been collecting, not invented.

---

## Technical depth — what this demonstrates

### LangGraph state machines with conditional routing

All 4 domains run as compiled LangGraph `StateGraph` instances. Each graph has
a conditional edge after `build_response` that retries with the deterministic path
if model synthesis fails and `fallback_to_deterministic=True`. Director OS has
an additional `validate_response` node that enforces evidence grounding before
the response reaches the API layer.

```
Director OS graph:
retrieve_evidence → build_draft → assemble_response → validate_response
                                                              ↓
                                              route_after_validation → END
                                                              ↓ (fallback)
                                                       build_draft (retry)
```

### Claude tool use for schema-enforced grounding

The Claude provider passes a tool schema with required `source` and `line_number`
fields. Claude cannot return a wins/risks/next-steps item without citing both.
Hallucinated citations fail at parse time — the validator catches them before they
reach the response.

This is distinct from prompt-level instructions like "always cite your sources."
The schema enforces it structurally.

### LangSmith observability — node-level traces

Every graph node carries `@traceable`. Setting `LANGSMITH_TRACING=true` and
`LANGSMITH_API_KEY` in `.env` is all that's required — every `graph.invoke()`
across all 4 domains emits a full execution trace to the `ai-os` project at
smith.langsmith.com, with inputs, outputs, and latency at each node.

![LangSmith trace — Director OS graph with retrieve_evidence, build_draft, assemble_response, validate_response nodes](../LanndSmithOutput.png)

### Three-path evaluation harness

Each domain has eval cases covering three retrieval paths:

| Path | Retriever | Requires |
|---|---|---|
| Local (keyword) | `local_files.py` — BM25-style keyword match | Nothing — runs in CI |
| Chroma (semantic) | `chroma.py` — ChromaDB + `nomic-embed-text` embeddings | Local Ollama |
| LangSmith (cloud) | `run_*_evals.py --langsmith` | `LANGSMITH_API_KEY` |

All 28 eval cases pass across all 4 domains on the local and chroma paths.
Results are committed as `results_chroma.json` per domain — the CI gate fails
if any case regresses.

### Pydantic as the single source of truth

The same Pydantic `BaseModel` definitions drive:
- FastAPI request validation and 422 error responses
- LangGraph `TypedDict` state shape
- Eval case deserialization from JSON on disk
- LangSmith dataset sync via `model_dump()`

One schema change propagates through the full stack with no manual wiring.

### Multi-agent pipeline for audience-aware formatting

When `target_audience` is set on `/orchestrate`, a `ResearcherAgent → WriterAgent`
pipeline runs after the domain workflow. The researcher uses Claude tool use to
produce structured findings (`ResearchSynthesis`); the writer takes only that
struct — not raw evidence — and formats it for the audience. This bounds
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

## Stack

Python 3.11 · FastAPI · Pydantic v2 · LangGraph · LangSmith · Anthropic SDK ·
Ollama · ChromaDB · MCP · GitHub Actions

Full per-tool breakdown: [docs/TECH_STACK.md](TECH_STACK.md)
