# Sprint 1 (11–18 Nov 2026)

## Roles

| Role | Member |
| --- | --- |
| Product Owner | Fernando (@f3renp) |
| Scrum Master | Ruben (@Geulo) |

## Sprint Planning (11 Nov)

### Sprint Goal

The skeleton is deployed to Azure by the pipeline, and a user can create a group,
add members, and add, edit and delete equally split expenses on the live URL.

### Items selected

| Issue | Story | Owner |
| --- | --- | --- |
| #18 | Deploy both services and the UI through the pipeline | Ruben |
| #19 | Create a group and add members | Hadi, Fernando (UI) |
| #20 | Add an expense split equally | Hadi, Fernando (UI) |
| #21 | Edit and delete expenses | Hadi, Fernando (UI) |

Supporting work this sprint (not separate stories): payments CRUD and the ledger client
with a 2 s timeout (Amit), request logs confirmed in Log Analytics and first saved
queries (Athul).

## Sprint Review (18 Nov)

Sprint Goal met. The Product Owner (Fernando) checked all four stories on the live URL.
Tagged `v0.1` on main after #48.

### Done

- #18 Deploy both services and the UI through the pipeline: CD deploys on every merge to
  main (#42, #43)
- #19 Create a group and add members (#31, #30)
- #20 Add an expense split equally (#33, landed in #38; UI #41)
- #21 Edit and delete expenses (#47; UI #48)
- Ahead of plan: payments CRUD (#29), ledger endpoint and client (#39, #35), `settle_up()`
  with its unit tests (#37), balances (#40, #46), monitoring queries (#34), data model
  (#36)

### Not done

- Nothing from the Sprint 1 backlog.
- The post-deploy smoke test moved to Sprint 2.

## Retrospective

**Went well:** small PRs, fast reviews, and the product working end to end on the live URL.

**To improve:** the first deploy landed a day after the Fri 13 milestone; a stacked PR (#33)
was merged into a feature branch instead of main; `AI_USAGE.md` caused merge conflicts on
almost every PR.

### Agreements

- Every PR targets `main`: check it says "merge into main" before merging.
- Whoever approves a PR merges it straight away, then deletes the branch.
- Review within 24 h; the reviewer of the day takes all PRs opened that day.
- `AI_USAGE.md` conflicts are never real: keep both rows, in date order.
- No force pushes to `main`.
