# Sprint 2 (19–24 Nov 2026)

## Roles

| Role | Member |
| --- | --- |
| Product Owner | Amit (@amayer2024) |
| Scrum Master | Hadi (@hadimoumeni) |

## Sprint Planning (18 Nov)

### Sprint Goal

The MVP is complete on the live URL: a user can see balances, record a payment and
settle up with the fewest transfers, every partial failure shows a clear message, and
the team can show the monitoring dashboard and SLO. Tagged `v0.2` by Sun 22 Nov.

### Items selected

| Issue | Story | Owner | Status at planning |
| --- | --- | --- | --- |
| #23 | Settle up with the fewest transfers | Amit (backend), Fernando (UI) | Backend (#37, #44) and panel (#46) merged; check the acceptance criteria on the live URL |
| #24 | Record a payment | Amit (backend), UI owner to confirm | Backend merged (#29); UI not started |
| #25 | Clear message when a service is down | Fernando (UI), Amit (live test) | UI messages in place; test on Azure by stopping one Container App |
| #26 | Monitoring dashboard and SLO | Athul | Queries merged (#34); Workbook in progress |

Supporting work (not separate stories):

- Expenses validation hardening (Hadi): reject amounts above 1,000,000.00 (#49)
- Post-deploy smoke test and blue-green revisions in CD (Ruben)
- Decision records for monitoring and the pipeline (Athul)

### Milestones

| When | What |
| --- | --- |
| Sun 22 Nov | MVP complete, tag `v0.2` |
| Mon 23 Nov, 20:00 | Code freeze, bug bash on the live URL |
| Tue 24 Nov, 20:00 (deadline 23:59) | Tag `submission` on `main`; this file with Review and Retro; contribution statements on Blackboard |

### Working agreements

- Every PR targets `main` (check it says "merge into main"); delete the branch after merging.
- Whoever approves a PR merges it straight away.
- Review within 24 h; reviewer of the day takes all PRs opened that day.
- `AI_USAGE.md` conflicts are never real: keep both rows, in date order.
- No force pushes to `main`.

## Sprint Review

_Added at the Sprint 2 Review._

### Done

### Not done

## Retrospective

_Added at the Sprint 2 Retrospective._

### Agreements
