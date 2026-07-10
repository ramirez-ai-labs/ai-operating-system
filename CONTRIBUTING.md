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

Open the console at `http://127.0.0.1:8000/`.

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
Interview OS, One-on-One OS) — plus a Director OS multi-agent set and a ChromaDB pass per
domain, nine eval steps in total. The build must be green before merge.

## Architecture rules

These are invariants  -  do not work around them:

1. **All providers implement `WeeklyUpdateProvider`** from `packages/shared/providers/base.py`. Provider-specific logic stays in the provider file.
2. **Provider selection via `_build_provider()`** in the Director OS graph. No workflow logic should branch on provider identity.
3. **API layer stays thin.** Workflow logic lives in the graph / workflow modules so it can be tested without FastAPI.
4. **Deterministic fallback always available.** Any model-assisted path must work when `fallback_to_deterministic=True`.
5. **Evidence grounding is required.** Every output item must cite `source` and `line_number` from retrieved evidence.

## Adding a new workflow domain

Follow the steps in `CLAUDE.md` under "Adding a new workflow." In short:

1. Schema → `packages/shared/schemas/<domain>.py`
2. Graph → `packages/shared/graphs/<domain>.py`
3. Workflow entry point → `<domain>/workflows/<entry>.py`
4. Route → `apps/api/main.py`
5. Routing → `packages/shared/orchestration/chief_of_staff.py`
6. Sample data → `data/local_only/<domain>/`
7. Eval cases → `evaluations/<domain>/`
8. Tests → `tests/test_<domain>_graph.py`
9. MCP tool → `apps/mcp/server.py`
10. Register packages → `pyproject.toml` + `pip install -e .`

Use `.github/ISSUE_TEMPLATE/workflow.md` to propose new domains before building.

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check .`)
- [ ] Local evals pass (`scripts/run_director_os_evals.py`)
- [ ] New workflow? All 10 steps above are complete
- [ ] Evidence grounding verified (every output item has `source` + `line_number`)
- [ ] No API keys committed

## Questions?

Open an issue using the appropriate template in `.github/ISSUE_TEMPLATE/`.
