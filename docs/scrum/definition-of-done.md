# Definition of Done

An item is done only when all of these hold:

1. Merged to `main` through a pull request approved by another team member.
2. CI is green: lint, format check, tests, coverage ≥ 70% on core logic, image build.
3. Deployed to Azure by the pipeline, and `/health` returns 200 after the deploy.
4. The story's acceptance criteria are checked on the live URL.
5. New logic has tests; new tables have a migration.
6. No secrets in code or images; configuration only through environment variables.
7. Docs updated if the API, data model or setup changed.
