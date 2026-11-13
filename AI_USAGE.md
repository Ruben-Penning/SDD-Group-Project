# AI usage

One row per significant AI-assisted piece of work.

| Date | Member | Tool | What it helped with | How we checked it |
| --- | --- | --- | --- | --- |
| 2026-11-07 | Ruben (Geulo) | Claude | Project scaffold: service skeletons, request logging, API key check, Dockerfiles, docker-compose, CI workflow, UI shell | Ran ruff, pytest (100% coverage) and a local uvicorn start; reviewed in PR |
| 2026-11-10 | Fer (f3renp) | Claude | Help UI group page with sample data | Ran it locally with both services up and checked the page |
| 2026-11-10 | Athul (athulgokuldas22) | Claude | Backlog issue wording, sprint-0.md and README team/roles tables | Checked against the assignment brief and team plan; reviewed in PR |
| 2026-11-10 | Hadi (hadimoumeni) | Claude | expenses schema: models, Alembic migration 0001 (groups, members, expenses, expense_shares), migration tests, alembic CLI path fix | Ran ruff, pytest (17 passed, 100% coverage), alembic upgrade/downgrade on SQLite, and docker compose against SQL Server (migration applied, /health 200, cascade and check constraints verified); reviewed in PR |
| 2026-11-10 | Amit | Claude | settlements payments model, Alembic migration 0001, migration tests, alembic CLI path fix | Ran ruff, pytest (12 passed, 100% coverage), alembic upgrade/downgrade and app.migrate on SQLite; reviewed in PR |
| 2026-11-10 | Fer (f3renp) | Claude | Help UI group page with sample data | Ran it locally with both services up and checked the page |
| 2026-11-11 | Amit | Claude | settlements payments CRUD (record, list, undo), payment validation rules, API and domain tests | Ran ruff, pytest (28 passed, 100% coverage) and a migrate + POST/GET/DELETE round trip on SQLite; reviewed in PR |
| 2026-11-12 | Hadi (hadimoumeni) | Claude | expenses groups and members endpoints (GET/POST /groups, GET /groups/{id}, GET/POST /groups/{id}/members), duplicate-name check, tests | Ran ruff, pytest (35 passed, 98% coverage); checked the response shapes against the UI draft in #30; reviewed in PR |
| 2026-11-12 | Fer (f3renp) | Claude | UI groups and members: group list, create group and add member forms, API error messages | Tested in a browser against a stand-in API; draft until the expenses endpoints are merged |
