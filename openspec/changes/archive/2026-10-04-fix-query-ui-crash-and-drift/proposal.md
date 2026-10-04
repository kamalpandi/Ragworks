## Why

The `/query` page crashes with a 500 error because `PGVectorDB.get_distinct_sources()` treats tuple rows as dicts after a missing `row_factory=dict_row` regression from the multi-user-rag-service refactor. Additionally, the query UI template and handler were never updated to match the post-multi-tenant backend contract: `file_name` is still required when it should be optional (tenant-based isolation), and no thread selector exists despite conversation threading being implemented.

## What Changes

- Fix `get_distinct_sources()` to use `row_factory=dict_row` on its cursor so the `/query` page can render
- Make `file_name` optional in the query UI form and handler, matching the backend's tenant-based query isolation
- Update the query UI template label, placeholder, and help text to reflect that `file_name` is now optional
- Add a conversation thread selector to the query UI so users can create, switch, and view threads

## Capabilities

### New Capabilities
- `fix-get-distinct-sources-cursor`: Fix the `row_factory=dict_row` regression in `PGVectorDB.get_distinct_sources()` that causes a 500 error on `/query`
- `make-file-name-optional-in-ui`: Update the query UI template and handler so `file_name` is optional, reflecting tenant-based query isolation
- `add-thread-selector-to-query-ui`: Add conversation thread creation and selection to the query page, completing the conversation memory feature

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- Affected code: `app/components/vector_dbs/pgvector_db.py`, `app/ui/query.py`, `app/templates/pages/query.html`
- No API changes, no new dependencies
- No breaking changes — existing API behavior is preserved; the UI becomes more permissive (optional file_name, optional thread)
