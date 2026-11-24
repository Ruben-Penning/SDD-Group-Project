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

## Sprint Review (24 Nov)

Sprint Goal met: the MVP is complete on the live URL and tagged `v0.2`. Written at the end
of the sprint, before the `submission` tag; the live demo is at the class Sprint Review
(25–26 Nov).

### Done

- #23 Settle up with the fewest transfers (#44; UI #46)
- #24 Record a payment (#29; UI #52)
- #25 Clear message when a service is down: the UI gives up after 5 s and shows
  "unavailable" for the affected panel only; settlements returns 503 after 2 s if expenses
  is down
- #26 Monitoring dashboard and SLO: queries (#34), Workbook deployed by Bicep (#51),
  decision records for monitoring and CI/CD (#53)
- Supporting: amount limit of 1,000,000.00 (#49), success messages in the UI (#54),
  final README with the architecture diagram (#55), tags `v0.1` and `v0.2`

### Not done

- Post-deploy smoke test against the live URL in CD
- Blue-green deploys with Container Apps revisions (we still run in single-revision mode)
- Stretch stories #27 (unequal splits) and #28 (other currencies)

## Retrospective

**Went well:** the MVP was complete two days before the deadline; the dashboard and the
SLO are part of the infrastructure, not built by hand.

**To improve:** not everyone had Azure access, so the partial-failure test depended on one
person; the smoke test and blue-green slipped because the first deploy came late.

### Agreements

- Give every member Azure access on day one.
- Get the pipeline and a first deploy working before any feature work.

## Next sprint

If we had another sprint: the smoke test and blue-green deploys in CD, the two stretch
stories (#27, #28), and moving to the professor's resource group if he confirms it.
