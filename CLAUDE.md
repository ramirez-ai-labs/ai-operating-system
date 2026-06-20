# CLAUDE.md  -  AI Operating System

Project-level guidance for Claude Code sessions. These instructions apply to every session in this repo.

## Branch and commit rules

- Never commit directly to `main`. Always create a branch first.
- Branch naming: `feat/`, `fix/`, `docs/`, `test/` prefixes.
- PRs only  -  no force pushes to main.

## How to run the project

Start the API server:
```bash
uvicorn apps.api.main:app --reload --env-file .env
```

Open the legacy operator console at `http://127.0.0.1:8000/`.

Start the Next.js frontend (requires the API server running first):
```bash
cd apps/web && npm install && npm run dev
```

Open the Next.js frontend at `http://localhost:3000/`.

Run tests:
```bash
pytest
```

Run Director OS evals (local, no API key required):
```bash
python scripts/run_director_os_evals.py
```

Run Director OS evals against the Claude provider (requires `ANTHROPIC_API_KEY`):
```bash
python scripts/run_director_os_evals.py --provider claude
```

Run Brand OS evals:
```bash
python scripts/run_brand_os_evals.py
```

## Environment setup

Copy `.env.example` to `.env` and fill in keys. The system runs fully without any API keys  -  both `ANTHROPIC_API_KEY` and `LANGSMITH_API_KEY` are opt-in.

## Key file locations

| What | Where |
|---|---|
| Next.js frontend | `apps/web/src/app/page.tsx` |
| API entry point | `apps/api/main.py` |
| Chief of Staff routing | `packages/shared/orchestration/chief_of_staff.py` |
| Director OS graph | `packages/shared/graphs/director_os.py` |
| Brand OS graph | `packages/shared/graphs/brand_os.py` |
| Interview OS graph | `packages/shared/graphs/interview_os.py` |
| One-on-One OS graph | `packages/shared/graphs/one_on_one_os.py` |
| Claude provider (Director OS) | `packages/shared/providers/claude.py` |
| Ollama provider (Director OS) | `packages/shared/providers/ollama.py` |
| Provider interface | `packages/shared/providers/base.py` |
| Provider factory | `_build_provider()` in each domain graph |
| Retrieval | `packages/shared/retrieval/local_files.py` |
| Validation (Director OS) | `packages/shared/validation/weekly_update.py` |
| Validation (Brand OS) | `packages/shared/validation/brand_os.py` |
| Validation (Interview OS) | `packages/shared/validation/interview_os.py` |
| Validation (One-on-One OS) | `packages/shared/validation/one_on_one_os.py` |
| Director OS schemas | `packages/shared/schemas/director_os.py` |
| Brand OS schemas | `packages/shared/schemas/brand_os.py` |
| Interview OS schemas | `packages/shared/schemas/interview_os.py` |
| One-on-One OS schemas | `packages/shared/schemas/one_on_one_os.py` |
| Orchestrator schema | `packages/shared/schemas/orchestrator.py` |
| Eval cases (Director OS) | `evaluations/director_os/weekly_update_cases.json` |
| Eval cases (Brand OS) | `evaluations/brand_os/content_draft_cases.json` |
| Sample project data | `data/local_only/projects/` |
| Sample brand data | `data/local_only/brand/` |
| LangSmith observability | `packages/shared/observability/langsmith.py` |

## Architecture invariants

- Domain providers implement domain-specific interfaces defined in `packages/shared/providers/`. The Director OS `WeeklyUpdateProvider` in `base.py` is the reference pattern. Each domain defines its own provider interface — do not add provider-specific logic outside of the provider files.
- Provider selection is handled by `_build_provider()` in each domain graph. Switching providers is a single field change on the request  -  no workflow logic should branch on provider identity.
- **Director OS supports both Claude and Ollama** for model synthesis (`provider='ollama'` or `provider='claude'`). **Brand OS, Interview OS, and One-on-One OS are Claude-only** (`provider='claude'`, requires `ANTHROPIC_API_KEY`). Passing a non-Claude provider to these three domains raises a `ValueError` that is caught by the graph's `build_response` node and falls back to deterministic synthesis when `fallback_to_deterministic=True` (the default). The system is therefore fully runnable without any API keys — set `use_model=False` (the default) or rely on the fallback.
- The API layer (`apps/api/main.py`) stays thin. Workflow logic lives in the domain graph files so it can be tested without FastAPI.
- Deterministic fallback must always be available. Any model-assisted path must have a fallback when `fallback_to_deterministic=True`.
- Evidence grounding is non-negotiable. Every output item must cite a source and line number that appears in the retrieved evidence. Do not relax this in the validator or provider.
- All domain response schemas must inherit from `BaseResponse` in `packages/shared/schemas/base.py`. This enforces `evidence: list[EvidenceItem]` and `provider_usage: dict[str, int]` at the Pydantic level and requires a `section_counts` property (`NotImplementedError` at runtime if missing).

## Adding a new domain — checklist

Use Interview OS as the canonical reference implementation.

**Files to create (5):**

| File | Template |
| --- | --- |
| `packages/shared/schemas/<domain>.py` | `InterviewBriefRequest(BaseModel)`, `InterviewBriefResponse(BaseResponse)` |
| `packages/shared/graphs/<domain>.py` | `packages/shared/graphs/interview_os.py` |
| `packages/shared/validation/<domain>.py` | `packages/shared/validation/interview_os.py` |
| `packages/shared/evaluations/<domain>.py` | `packages/shared/evaluations/interview_os.py` |
| `evaluations/<domain>/<cases>.json` | `evaluations/interview_os/interview_cases.json` |

**Files to modify (5):**

| File | Change |
| --- | --- |
| `packages/shared/schemas/orchestrator.py` | Add response type to `OrchestratorResponse.result` union |
| `packages/shared/orchestration/chief_of_staff.py` | Add workflow constant, routing keyword, and `_build_trace` branch |
| `apps/api/main.py` | Register new route |
| `CLAUDE.md` | Update key file locations table |
| `.github/workflows/ci.yml` | Add eval runner step |

**Invariants to satisfy:**

- Response schema inherits `BaseResponse` — `evidence`, `provider_usage`, `section_counts` are mandatory.
- `_build_provider()` in the graph raises `ValueError` for non-Claude providers (Brand/Interview/OneOnOne pattern).
- `validate_response` node + `route_after_validation` conditional wired in the graph.
- Deterministic fallback always available (`fallback_to_deterministic=True`).
- All grounded items cite `source` + `line_number` from the retrieved evidence.
- Eval cases cover: deterministic path, model path, fallback path, empty-sections rejection.
- `run_evals.py` auto-discovers the new domain — no script changes needed.

## Adding a new workflow (within an existing domain)

1. Add request/response schemas to `packages/shared/schemas/`
2. Build the LangGraph state graph in `packages/shared/graphs/`
3. Add the workflow entry point in the domain directory (e.g., `director_os/workflows/`)
4. Register the route in `apps/api/main.py`
5. Add routing logic to `packages/shared/orchestration/chief_of_staff.py`
6. Add eval cases to `evaluations/<domain>/`
7. Add tests in `tests/`

## What's in progress

See `sprints.md` for the active sprint checklist.
See `plan.md` for the full phased roadmap (Phases 1–7).

## Running evals

Use the unified dispatcher for new work:

```bash
python scripts/run_evals.py                              # all domains, local
python scripts/run_evals.py --domain director_os        # one domain
python scripts/run_evals.py --domain director_os --backend claude
python scripts/run_evals.py --domain all --backend chroma --ci
```

The dispatcher auto-discovers domains from `packages/shared/evaluations/` — adding a new domain requires only the evaluations module, not a new script.

The legacy per-domain scripts (`scripts/run_director_os_evals.py` etc.) remain for CI backwards-compatibility.

## CI

GitHub Actions runs on every PR to `main`:
- `ruff` lint
- `pytest` with coverage
- `python scripts/run_director_os_evals.py` (local evals, no API key)
- `python scripts/run_brand_os_evals.py` (local evals, no API key)
- `python scripts/run_interview_os_evals.py` (local evals, no API key)
- `python scripts/run_one_on_one_os_evals.py` (local evals, no API key)
- Chroma evals (all 4 domains, skip gracefully in CI if index absent)

LangSmith-backed evals are on-demand only and not run in CI.
