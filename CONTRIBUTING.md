# Contributing

This repository uses a branch-and-PR workflow.

## Workflow

1. Create a branch from `main`
2. Make the smallest coherent change set you can
3. Run local verification before opening a PR
4. Open a pull request back to `main`
5. Wait for CI and review before merging

## Local Checks

For Python changes, run:

```bash
python -m ruff check .
python -m pytest -q
python scripts/run_director_os_evals.py
```

Use the LangSmith-backed eval path only when you explicitly want remote experiment tracking:

```bash
python scripts/run_director_os_evals.py --langsmith
```

## Change Expectations

- Keep `README.md`, `AGENTS.md`, and `plan.md` aligned with implementation status
- Add or update tests when behavior changes
- Do not commit secrets, tokens, or private data
- Keep local-first behavior as the default
- Prefer small, reviewable PRs over broad multi-purpose changes

## Pull Requests

PRs should include:

- a short summary of what changed
- a short explanation of why it changed
- validation notes
- any risk or operator-impact notes

The repo already includes a pull request template under `.github/PULL_REQUEST_TEMPLATE.md`.
