# Contributing to AI Operating System

## Getting started

```bash
git clone <repo>
cd ai-operating-system
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in any optional keys
```

Start the API server:

```bash
uvicorn apps.api.main:app --reload --env-file .env
```

Open the legacy console at `http://127.0.0.1:8000/`, or start the Next.js frontend:

```bash
cd apps/web && npm install && npm run dev   # http://localhost:3000
```

## Branch and commit rules

- Never commit directly to `main`  -  branch first.
- Branch naming: `feat/`, `fix/`, `docs/`, `test/` prefixes.
- One PR per logical unit of work. Squash-merge preferred.
- Keep commit messages short (one line, imperative mood).

## Running tests and linting

```bash
pytest                                # full test suite
pytest tests/test_director_os*.py -v # one domain
ruff check .                          # lint
python scripts/run_evals.py           # all 4 domains, local (no API key)
python scripts/run_evals.py --domain director_os
```

CI runs `ruff`, `pytest`, and local eval steps for all four domains (Director OS, Brand OS,
Interview OS, One-on-One OS) — plus a Director OS multi-agent set, the planner
routing/planning set, and a ChromaDB pass per domain (skipped when no index is present),
ten eval steps in total. A separate job type-checks and builds the Next.js frontend
(`npm run type-check && npm run build` in `apps/web`). The build must be green before merge.

## Architecture rules

These are invariants  -  do not work around them:

1. **Each domain defines its own provider interface** in `packages/shared/providers/`; Director OS's `WeeklyUpdateProvider` in `base.py` is the reference pattern. Provider-specific logic stays in the provider file.
2. **Provider selection via `_build_provider()`** in each domain graph. No workflow logic should branch on provider identity.
3. **API layer stays thin.** Workflow logic lives in the graph / workflow modules so it can be tested without FastAPI.
4. **Deterministic fallback always available.** Any model-assisted path must work when `fallback_to_deterministic=True`.
5. **Evidence grounding is required.** Every output item must cite `source` and `line_number` from retrieved evidence.

## Adding a new workflow domain

Follow the checklist in `CLAUDE.md` under "Adding a new domain." Interview OS is the reference implementation. In short:

1. Schema → `packages/shared/schemas/<domain>.py` (response inherits `BaseResponse`)
2. Graph → `packages/shared/graphs/<domain>.py`
3. Validation → `packages/shared/validation/<domain>.py`
4. Evals module → `packages/shared/evaluations/<domain>.py`
5. Eval cases → `evaluations/<domain>/<name>_cases.json`
6. Workflow entry point → `<domain>/workflows/<entry>.py`
7. Domain spec → `packages/shared/domains/<domain>.py`, added to `_REGISTERED` in `packages/shared/domains/__init__.py`
8. Response union → `packages/shared/schemas/orchestrator.py`
9. CI eval step → `.github/workflows/ci.yml`
10. Register packages → `pyproject.toml` + `pip install -e .`, then regenerate the tool snapshot with `python -m packages.shared.domains --write`

The registry drives the router, API route, and MCP tool, so `chief_of_staff.py`, `apps/api/main.py`, and `apps/mcp/server.py` need no changes. `tests/test_domain_registry.py` fails if any step is missing.

Use `.github/ISSUE_TEMPLATE/workflow.md` to propose new domains before building.

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check .`)
- [ ] Local evals pass (`scripts/run_director_os_evals.py`)
- [ ] New domain? All 10 steps above are complete and `tests/test_domain_registry.py` passes
- [ ] Evidence grounding verified (every output item has `source` + `line_number`)
- [ ] Changed a request or response schema? `apps/web/src/lib/types.ts` updated and `npm run type-check` passes
- [ ] No API keys committed

## Questions?

Open an issue using the appropriate template in `.github/ISSUE_TEMPLATE/`.
