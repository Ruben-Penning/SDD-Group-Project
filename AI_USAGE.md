# AI usage

One row per significant AI-assisted piece of work.

| Date | Member | Tool | What it helped with | How we checked it |
| --- | --- | --- | --- | --- |
| 2026-11-07 | Ruben (Geulo) | Claude | Project scaffold: service skeletons, request logging, API key check, Dockerfiles, docker-compose, CI workflow, UI shell | Ran ruff, pytest (100% coverage) and a local uvicorn start; reviewed in PR |
| 2026-11-10 | Amit | Claude | settlements payments model, Alembic migration 0001, migration tests, alembic CLI path fix | Ran ruff, pytest (12 passed, 100% coverage), alembic upgrade/downgrade and app.migrate on SQLite; reviewed in PR |
| 2026-11-10 | Fer (f3renp) | Claude | Help UI group page with sample data | Ran it locally with both services up and checked the page |
| 2026-11-11 | Amit | Claude | settlements payments CRUD (record, list, undo), payment validation rules, API and domain tests | Ran ruff, pytest (28 passed, 100% coverage) and a migrate + POST/GET/DELETE round trip on SQLite; reviewed in PR |
