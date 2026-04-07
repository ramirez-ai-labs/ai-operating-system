# Contributing

This repository uses a branch-and-PR workflow.

## Workflow

1. Create a branch from `main`
2. Make the smallest coherent change set you can
3. Run local verification before opening a PR
4. Open a pull request back to `main`
5. Wait for CI and review before merging

## Local Checks

Set up a local environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows, activate the environment with:

```bash
.venv\Scripts\activate
```

For Python changes, run:

```bash
python -m ruff check .
python -m pytest -q
python scripts/run_director_os_evals.py
python scripts/run_brand_os_evals.py
```

Use the LangSmith-backed eval path only when you explicitly want remote experiment tracking:

```bash
python scripts/run_director_os_evals.py --langsmith
```

## REST Smoke Tests

Start the API locally first:

```bash
uvicorn apps.api.main:app --reload
```

Smoke-check the current endpoints with:

```bash
curl -X GET http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/director-os/weekly-update -H "Content-Type: application/json" -d '{"data_path":"data/local_only/projects","focus":"leadership update","max_documents":5}'
curl -X POST http://127.0.0.1:8000/brand-os/content-draft -H "Content-Type: application/json" -d '{"data_path":"data/local_only/brand","focus":"podcast discussion theme","max_documents":5}'
curl -X POST http://127.0.0.1:8000/orchestrate -H "Content-Type: application/json" -d '{"prompt":"Turn this work into a podcast and LinkedIn content draft","data_path":"data/local_only/brand","max_documents":5}'
```

Inspect these response fields:

- `/health`: `status`
- `/director-os/weekly-update`: `summary`, `wins`, `next_steps`, `evidence`
- `/brand-os/content-draft`: `insight_summary`, `post_outline`, `podcast_angles`, `repo_improvements`
- `/orchestrate`: `selected_workflow`, `rationale`, `trace.section_counts`, `result`

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
