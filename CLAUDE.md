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

Open the operator console at `http://127.0.0.1:8000/`.

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
| API entry point | `apps/api/main.py` |
| Chief of Staff routing | `packages/shared/orchestration/chief_of_staff.py` |
| Director OS graph | `packages/shared/graphs/director_os.py` |
| Brand OS graph | `packages/shared/graphs/brand_os.py` |
| Claude provider | `packages/shared/providers/claude.py` |
| Ollama provider | `packages/shared/providers/ollama.py` |
| Provider interface | `packages/shared/providers/base.py` |
| Provider factory | `_build_provider()` in `packages/shared/graphs/director_os.py` |
| Retrieval | `packages/shared/retrieval/local_files.py` |
| Validation | `packages/shared/validation/weekly_update.py` |
| Director OS schemas | `packages/shared/schemas/director_os.py` |
| Brand OS schemas | `packages/shared/schemas/brand_os.py` |
| Orchestrator schema | `packages/shared/schemas/orchestrator.py` |
| Eval cases (Director OS) | `evaluations/director_os/weekly_update_cases.json` |
| Eval cases (Brand OS) | `evaluations/brand_os/content_draft_cases.json` |
| Sample project data | `data/local_only/projects/` |
| Sample brand data | `data/local_only/brand/` |
| LangSmith observability | `packages/shared/observability/langsmith.py` |

## Architecture invariants

- Domain providers implement domain-specific interfaces defined in `packages/shared/providers/`. The Director OS `WeeklyUpdateProvider` in `base.py` is the reference pattern. Each domain defines its own provider interface — do not add provider-specific logic outside of the provider files.
- Provider selection is handled by `_build_provider()` in the Director OS graph. Switching providers is a single field change on the request  -  no workflow logic should branch on provider identity.
- The API layer (`apps/api/main.py`) stays thin. Workflow logic lives in `director_os/` and `brand_os/` so it can be tested without FastAPI.
- Deterministic fallback must always be available. Any model-assisted path must have a fallback when `fallback_to_deterministic=True`.
- Evidence grounding is non-negotiable. Every output item must cite a source and line number that appears in the retrieved evidence. Do not relax this in the validator or provider.

## Adding a new workflow

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

## CI

GitHub Actions runs on every PR to `main`:
- `ruff` lint
- `pytest` with coverage
- `python scripts/run_director_os_evals.py` (local evals, no API key)
- `python scripts/run_brand_os_evals.py` (local evals, no API key)

LangSmith-backed evals are on-demand only and not run in CI.
