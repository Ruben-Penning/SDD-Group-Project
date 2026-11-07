# Instructions for AI coding assistants

Splitwise-lite: a university group project (IE, Software Development and DevOps).
Read README.md first. These constraints come from the grading rubric; follow them exactly.

## Architecture (fixed, do not change)

- Exactly two FastAPI services (Python 3.12), each in its own container with its own database.
  Do not add a third service, a message broker or another database.
  - `services/expenses`: groups, members, expenses, expense_shares.
    Exposes `GET /groups/{id}/ledger` (net paid minus owed per member).
  - `services/settlements`: payments; computes balances and settle-up.
    Calls expenses' `/ledger` over HTTP with a 2 s timeout; on failure returns
    503 with a clear message, never a stack trace or a hung request.
- Static UI in `ui/` (plain HTML + JS, no build step). It calls both services from the
  browser. Every fetch goes through `api()` in `ui/app.js` (5 s timeout) and shows a
  clear message when a service is unavailable.
- Each service is layered:
  - `app/api`: routes only, thin.
  - `app/domain`: pure business logic, no database or HTTP imports. Most tests go here.
  - `app/db`: SQLAlchemy models and sessions.

## Conventions

- Money is integer cents (`amount_cents`), never floats.
- Schema changes only through Alembic migrations in `migrations/versions/`
  (`alembic revision -m "..."`). They run on startup and must work on SQL Server
  (Azure SQL) and SQLite (tests). A service never reads the other service's database.
- Config only from environment variables via `app/config.py`:
  `DATABASE_URL`, `API_KEY`, `CORS_ORIGIN`, `EXPENSES_URL`. Never hardcode or commit
  secrets, keys or connection strings.
- Add routers to `app/api/__init__.py`; they get the API key check automatically.
  Do not change `/health`, the request-logging middleware or CORS.
- Tests: pytest in `tests/`, using SQLite or no database, never Azure.
  Coverage must stay at or above 70%.
- Code must pass `ruff check .` and `ruff format --check .` (run from the service folder).
- Pin every new dependency to an exact version in `requirements.txt`
  (test-only tools go in `requirements-dev.txt`).
- Dockerfiles: no `COPY . .`, non-root user, no secrets in the image.

## Workflow

- Small changes on a feature branch (`feat/...`, `fix/...`), one pull request per user story.
- Never push to `main`. Every change needs a PR approved by another team member and green CI.
- Before pushing, run lint, the format check and the tests for every service you touched.
- Follow `docs/scrum/definition-of-done.md`.
- If AI helped significantly, add a row to `AI_USAGE.md`.
