# Splitwise-lite

Group project for the Software Development and DevOps course (BCSAI, IE University).
A web app where a group logs shared expenses and sees the fewest transfers needed to settle up.

**Live URL:** _added after the first deploy_

## Architecture

Two FastAPI services, each in its own container with its own database. A static UI calls both from the browser.

| Part | Folder | Owns | Local port |
| --- | --- | --- | --- |
| expenses-service | `services/expenses` | groups, members, expenses, shares | 8001 |
| settlements-service | `services/settlements` | payments, balances, settle-up | 8002 |
| UI | `ui` | static HTML + JS | 8080 |

settlements-service reads each group's ledger from expenses-service over HTTP.
Each service is layered: `app/api` (HTTP) → `app/domain` (business rules) → `app/db` (persistence).

_Architecture diagram: added with the Azure setup._

## Run locally

Requires Docker.

```bash
docker compose up --build
```

- expenses: http://localhost:8001/health and http://localhost:8001/docs
- settlements: http://localhost:8002/health and http://localhost:8002/docs
- UI: in a second terminal, `python3 -m http.server 8080 -d ui`, then open http://localhost:8080

Migrations run automatically when each service starts.

## Run the tests

```bash
cd services/expenses   # or services/settlements
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest   # fails under 70% coverage
```

## Configuration

Every service reads its config from environment variables only. See `.env.example`.

| Variable | Used by | Meaning |
| --- | --- | --- |
| `SERVICE_NAME` | both | `expenses` or `settlements` |
| `DATABASE_URL` | both | SQLAlchemy URL (`mssql+pyodbc://…`) |
| `API_KEY` | both | demo key, sent as `X-API-Key`; empty disables the check |
| `CORS_ORIGIN` | both | the UI's origin |
| `EXPENSES_URL` | settlements | base URL of expenses-service |

## Adding a migration

```bash
cd services/expenses
alembic revision -m "create groups table"   # then edit the file in migrations/versions/
```

## Workflow

- Branch from `main`, open a pull request, get one approval. No direct pushes to `main`.
- CI must be green. Follow the [Definition of Done](docs/scrum/definition-of-done.md).
- Add a row to [AI_USAGE.md](AI_USAGE.md) for significant AI-assisted work.

## Azure setup

_Added with the infrastructure (Bicep) and CD pipeline._

## Team

| Name | GitHub | Area |
| --- | --- | --- |
| Ruben | [@Geulo](https://github.com/Geulo) | Infrastructure and pipeline |
| | | |
| | | |
| | | |
| | | |
