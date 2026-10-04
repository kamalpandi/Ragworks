# UAT / Manual Verification Checklist

Manual verification rules for this repo. The purpose is to stop "everything
returns 200" sign-offs that pass only because the database is empty.

## Precondition: seed data before any fragment/page check

A `200` on an aggregation or list fragment is **not** evidence the path works.
`fetchall()` returning `[]` skips the row-processing loop entirely, so bugs that
only trigger on populated rows (wrong cursor row factory, bad column access,
empty-result divides) hide behind a green check.

Before exercising any page or fragment, seed at least:

- [ ] 1 document in the vector table
- [ ] 1 eval result
- [ ] **≥ 1 `usage_logs` row with `operation = 'query'`**
- [ ] **≥ 1 `usage_logs` row with `operation = 'ingest'`** (the ingest branch and
  `chunks_created` aggregate are separate code paths from the query branch)

Every row-processing branch is only verified when at least one row exists for it.

## Checklist

- [ ] Login / logout
- [ ] Every page renders
- [ ] Every GET fragment returns `200` **with seeded data present** (see precondition)
- [ ] Usage surfaces (`/ui/dashboard/stats`, `/api/v1/usage`, `/api/v1/dashboard`)
  return `200` and correct numbers — run this in three passes:
  - [ ] both `query` and `ingest` rows present
  - [ ] `query`-only (exercises the query branch, `tokens` aggregate)
  - [ ] `ingest`-only (exercises the ingest branch, `chunks` aggregate)
- [ ] Eval polling, prompts CRUD, logs filter/pagination
- [ ] Ingest file / url / custom
- [ ] Postman: every `/api/v1/*` endpoint returns JSON (never HTML)
- [ ] DevTools: browser never calls `/api/v1/*` directly and never exposes the API key

## Why this exists

The UI/backend split shipped a `500` on `GET /ui/dashboard/stats` because the
manual checklist (`separate-ui-from-backend/tasks.md:57`) checked every fragment
against an empty `usage_logs` table. The aggregation ran no rows and returned an
empty panel with `200`. See change `fix-usage-row-factory`.
