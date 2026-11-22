# Decision records

Short records of the decisions that shaped Splitwise-lite. Each one has the context,
the decision, the alternatives we considered, and the consequences.

---

## ADR 1: Two services, split by reason to change

**Context.** The brief requires exactly two services, each with its own database,
talking over HTTP. The product has two kinds of logic: recording what people spent
(groups, members, expenses) and working out who owes whom (balances, settle-up,
payments).

**Decision.**
- **expenses-service** is the system of record: groups, members, expenses and their
  shares. It exposes `GET /groups/{id}/ledger` (paid minus owed per member).
- **settlements-service** owns the money logic: it reads the ledger over HTTP, applies
  recorded payments, and computes balances and the settle-up transfers.
- Inside each service the code is layered: `api/` (HTTP) → `domain/` (business rules,
  no database or HTTP imports) → `db/` (persistence). The settle-up algorithm is a pure
  function in `domain/`, which makes it easy to unit-test.

**Alternatives.**
- *Split by entity* (e.g. a groups service and an expenses service): every request
  would need both services, so one being down would break almost everything.
- *Hexagonal or modular structure inside each service*: more structure than a small
  MVP needs; layered is enough and easy for everyone to follow.

**Consequences.**
- The two parts change for different reasons, so each person can work on one service
  without blocking the other.
- Partial failure is contained: if settlements is down, expenses CRUD still works and
  the UI shows that balances are unavailable. If expenses is down, settlements stops
  waiting after 2 seconds and returns 503 with a clear message instead of hanging.
- The ledger response format is a contract between the services, so changing it
  needs both owners to agree.

---

## ADR 2: One serverless Azure SQL database per service, money as integer cents

**Context.** The brief requires one serverless Azure SQL database per service with
auto-pause, versioned migrations applied on startup, and SQL Server locally.

**Decision.**
- Each service owns one database (`expenses` and `settlements`). No foreign keys
  cross databases: payments store `group_id` and member ids as plain integers.
- The schema is defined by Alembic migrations, run with `alembic upgrade head` when
  each container starts. Locally, `docker compose` runs SQL Server.
- All money is stored and passed as integer cents. Equal splits give leftover cents
  to the members with the lowest ids, so shares always add up to the total.
- Only `expense_shares` cascades on delete, because SQL Server rejects a schema with
  more than one cascade path to the same table.

**Alternatives.**
- *One shared database*: simpler joins, but breaks the brief's "own database per
  service" rule and couples the services.
- *Decimal or float amounts*: floats cannot represent values like 0.10 exactly, so
  totals drift. Decimals work, but integer cents are simpler and exact.

**Consequences.**
- Data integrity across services is logical only: settlements trusts the ids it gets
  from expenses-service.
- Auto-pause keeps cost near zero, but the first request after idle waits for the
  database to resume (see the SLO notes in `docs/monitoring/queries.md`).
- Every schema change needs a new migration file, which keeps local, CI and Azure in
  the same state.

---

## ADR 3: Hosting on an Azure for Students subscription, UI as a Storage static website

**Context.** We deploy on an Azure for Students subscription. It only allows five
regions (Spain Central, Norway East, Germany West Central, Italy North, Poland
Central). Static Web Apps is not offered in any of them, and the Azure SQL free offer
is not available in Spain Central.

**Decision.**
- Everything runs in one resource group in Germany West Central, defined in
  `infra/main.bicep` and deployed by the CD pipeline.
- The UI is served as a Storage account static website instead of a Static Web App.
- Both Container Apps run on the Consumption plan with 0 to 1 replicas, and both
  databases use the free serverless offer with auto-pause.
- The pipeline signs in to Azure with OIDC (no stored Azure password).

**Alternatives.**
- *Static Web Apps in another region*: not allowed by the subscription.
- *Serve the UI from one of the Container Apps*: would mix the UI with a backend
  service and break the two-service architecture.

**Consequences.**
- This differs from the brief (§4), which asks for a Static Web App in the professor's
  shared resource group with the group service principal. The UI is still static files
  calling both services from the browser, so the architecture is the same; only the
  hosting resource differs. To be confirmed with the professor.
- Running outside Spain adds some network latency, which is small compared with cold
  starts.

---

## ADR 4: Monitoring with JSON request logs, Log Analytics and a Workbook

**Context.** The brief requires request logs visible in Azure, a dashboard with request
count, error rate and response time, one SLO with the query that measures it, and low
log volume (INFO level, no request bodies). It also says to use the Log Analytics
workspace of the Container Apps environment and no other Azure services.

**Decision.**
- Both services use the same middleware: one JSON line per request to stdout with
  `service`, `method`, `path` (the route template, e.g. `/groups/{group_id}/settle-up`,
  not the raw path), `status` and `duration_ms`. INFO level, no bodies.
- The Container Apps environment sends stdout to the `sdd-splitwise-logs` workspace,
  where the lines land in `ContainerAppConsoleLogs_CL`.
- The KQL queries are in `docs/monitoring/queries.md`. They exclude `/health`, so the
  pipeline's health checks do not skew the numbers.
- The dashboard is an Azure Workbook with four tiles (request count, error rate,
  p50/p95 latency, SLO). It is defined in `infra/workbook.json` and deployed by Bicep,
  so it is not created by hand.
- **SLO:** 99% of `GET /groups/{group_id}/settle-up` requests return a non-5xx status
  in under 1000 ms, over 7 days. Settle-up is the core feature and depends on both
  services, so it is the best single signal that the product works.

**Alternatives.**
- *Application Insights SDK*: richer traces, but adds another Azure service and a
  dependency in both services; the brief asks for the environment's workspace.
- *Prometheus and Grafana*: would need a third container, which is out of scope.
- *A dashboard built by hand in the portal*: quick, but breaks "nothing changed
  manually" and would be lost if the resource group were recreated.

**Consequences.**
- Logging the route template keeps queries simple: every settle-up call groups
  under one path, whatever the group id.
- Cold starts count against the SLO. With scale to zero and SQL auto-pause, the first
  request after idle takes about 30 seconds. With little traffic, a few cold starts can
  push the SLO below 99%. We accept this to keep cost near zero; keeping one replica
  always on would fix it but goes against the brief's scale-to-zero rule.
- New log lines take a few minutes to appear in Log Analytics.

---

## ADR 5: CI on every change, CD on merge to main with OIDC

**Context.** The brief requires lint, format check, tests with a 70% coverage gate and
an image build on every pull request and push, and on merge to main: images in GHCR
tagged with the commit SHA, a deploy of both services and the UI only if CI passed,
migrations applied, and a `/health` check that fails the run if it does not return 200.

**Decision.**
- **CI** (`ci.yml`) runs on every pull request and push, once per service: `ruff
  check`, `ruff format --check`, `pytest` with `--cov-fail-under=70`, `pip-audit` and
  `docker build`. A final `CI passed` job is the single check that branch protection
  requires before merging.
- **CD** (`cd.yml`) starts only when CI succeeds on a push to main, and runs one
  deploy at a time:
  1. Build both images and push them to GHCR, tagged with the commit SHA.
  2. Sign in to Azure with OIDC: GitHub's token is trusted by a federated credential
     on a deploy identity with Contributor on the resource group. No Azure password
     is stored.
  3. Deploy `infra/main.bicep` with the new image tags. Each container runs its
     Alembic migrations on startup.
  4. Poll `/health` on both services for up to 5 minutes; fail the run if either never
     returns 200.
  5. Write `config.js` with the service URLs and upload the UI; check it is served.
- Secrets (SQL admin password, API key) live only in the GitHub `production`
  environment and in Container App secrets.

**Alternatives.**
- *`az containerapp update` with only the new image*: faster, but the infrastructure
  would drift from the code. Deploying the whole Bicep file every time keeps Azure
  matching the repository.
- *A stored service principal secret*: works, but a long-lived secret can leak. OIDC
  tokens are short-lived and tied to this repository's `production` environment.
- *Tagging images `latest`*: simpler, but you cannot tell which commit is running or
  roll back to an exact version.

**Consequences.**
- Every merge to main goes live within a few minutes, so main must always be
  deployable.
- The 5-minute health window is long because of cold starts and SQL resume; a
  genuinely broken deploy takes up to 5 minutes to fail.
- Migrations run on startup, so a schema change must stay compatible with the code
  still running until the new revision is up.
- The demo API key is written into `config.js`, so it is visible in the browser by
  design; it only guards against casual use, not real attackers.
