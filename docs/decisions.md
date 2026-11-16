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
