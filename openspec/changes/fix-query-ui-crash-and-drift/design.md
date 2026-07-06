## Context

The `multi-user-rag-service` change refactored `PGVectorDB.get_distinct_sources()` to add a `tenant_id` filter (task 2.4), but the cursor was created without `row_factory=dict_row`. In psycopg 3, the default row factory returns tuples, so `row.get("source")` fails with `AttributeError`. The `search()` method (line 118) has `row_factory=dict_row` but `get_distinct_sources()` (line 98) does not.

Separately, tasks 10.2 and 10.3 from `multi-user-rag-service` specified making `file_name` optional in the UI and adding a thread selector. The backend `ChatRequest` model was updated (`file_name: Optional[str] = None`), and the conversation service was implemented, but the UI template and handler were never updated.

## Goals / Non-Goals

**Goals:**
- Fix the 500 crash on `/query` by restoring `row_factory=dict_row` in `get_distinct_sources()`
- Make `file_name` optional in the query UI form and handler
- Update query UI labels and help text to reflect tenant-based isolation
- Add a thread selector to the query UI for conversation thread management

**Non-Goals:**
- Changing the search/query pipeline or RAG engine behavior
- Modifying the auth or middleware stack
- Adding new API endpoints or changing the API contract
- Adding full thread management UI (rename, delete) — just create and select

## Decisions

### Decision 1: Fix cursor with `row_factory=dict_row` (not convert tuples manually)

**Chosen**: Add `row_factory=dict_row` to the cursor on line 98 of `get_distinct_sources()`.
**Alternative**: Iterate tuples with `row[0]` index access.
**Rationale**: Consistent with `search()` method (line 118) and `get_sync_connection()` in `pool.py` (line 49). Dict access is more readable and resilient to column order changes. This is the pattern already used everywhere else in the codebase.

### Decision 2: Make `file_name` optional via `Form(None)` + remove client-side validation

**Chosen**: Change the handler parameter to `file_name: str = Form(None)` and remove the `if not file_name.strip()` guard. On the template side, remove the `required` attribute and update labels.
**Alternative**: Keep it required in UI but default to `None` at the API level.
**Rationale**: The backend already supports `file_name=None` (tenant-based isolation). The UI should match. Users may want to search across all documents in their tenant, which is the new default behavior.

### Decision 3: Thread selector as a simple dropdown + "New Thread" button

**Chosen**: Add a `<select>` dropdown listing existing threads for the tenant, plus a "New Thread" button that generates a UUID. Pass the selected thread_id in the form submission. The query handler already extracts `thread_id` from `thread:<id>` format in the `prompt_name` field (line 71-73 of query.py) — we'll add a dedicated `thread_id` hidden field instead.
**Alternative**: Full thread management page separate from query.
**Rationale**: The handler already supports thread_id via the form. We just need to expose it in the UI. A simple dropdown keeps the change minimal and self-contained within the query page. The existing `prompt_name` hack for threads can be preserved or replaced with a cleaner approach — but since it's backward-compatible, we'll add a proper `thread_id` hidden field and keep the existing `prompt_name` fallback.

## Risks / Trade-offs

- **[Low] Thread list query on every page load**: The query page will make an additional API call to list threads. This is a lightweight query against the `conversations` table. If it becomes a performance concern, it can be cached or lazy-loaded via HTMX later.
- **[Low] `file_name` optional may confuse users**: Users accustomed to mandatory file filtering might not realize they're searching all documents. Mitigation: clear label "Target Document (Optional)" and help text "Leave empty to search across all documents in your knowledge base."
