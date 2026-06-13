---
name: New workflow domain proposal
about: Propose a new OS workflow domain (e.g. Recruiting OS, Finance OS)
labels: new-domain
---

## Domain name

<!-- e.g. "Recruiting OS" or "Finance OS" -->

## What problem does this domain solve?

<!-- What does a user do today that this workflow would make faster or better? -->

## What local data does it consume?

<!-- What kind of markdown files or notes would live under data/local_only/<domain>/? -->

## What does the response look like?

<!-- Sketch the response sections. e.g. key_questions, talking_points, red_flags for Interview OS. -->

## How does it route?

<!-- What keywords or phrases should the Chief of Staff use to route to this domain? -->

## Definition of done

- [ ] Schema added to `packages/shared/schemas/<domain>.py`
- [ ] LangGraph state graph added to `packages/shared/graphs/<domain>.py`
- [ ] Workflow entry point added to `<domain>/workflows/`
- [ ] Route registered in `apps/api/main.py`
- [ ] Routing added to `chief_of_staff.py`
- [ ] Sample data added to `data/local_only/<domain>/`
- [ ] Eval cases added to `evaluations/<domain>/`
- [ ] Tests added to `tests/test_<domain>_graph.py`
- [ ] MCP tool registered in `apps/mcp/server.py`
- [ ] Operator console updated
