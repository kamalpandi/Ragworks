## 1. Fix get_distinct_sources Cursor Bug

- [x] 1.1 Add `row_factory=dict_row` to the cursor creation in `app/components/vector_dbs/pgvector_db.py:98` (`get_distinct_sources` method)
- [x] 1.2 Add `row_factory=dict_row` to the cursor creation in `app/services/conversation_service.py:60` (`list_threads` function — same bug)
- [ ] 1.3 Verify `/query` page loads without 500 error

## 2. Make file_name Optional in Query UI

- [x] 2.1 Change `file_name: str = Form(...)` to `file_name: str = Form(None)` in `app/ui/query.py:36`
- [x] 2.2 Remove the `if not file_name.strip()` guard in `app/ui/query.py:59-60` (pass empty string through as None for file_filter)
- [x] 2.3 Update label text in `app/templates/pages/query.html:55` from "Target Document (Required)" to "Target Document (Optional)"
- [x] 2.4 Remove the `required` attribute from the `<input>` in `app/templates/pages/query.html:64`
- [x] 2.5 Update help text in `app/templates/pages/query.html:71` from "Queries are strictly isolated to this file." to "Leave empty to search across all documents in your knowledge base."

## 3. Add Thread Selector to Query UI

- [x] 3.1 Import `conversation_service` in `app/ui/query.py` and fetch thread list in the `query_page` handler, passing `threads` to the template context
- [x] 3.2 Add a thread selector dropdown (`<select name="thread_selector">`) to `app/templates/pages/query.html` listing existing threads with a "New Thread" default option
- [x] 3.3 Add a hidden `thread_id` field auto-populated from the selector (or a UUID if "New Thread" is selected) to the chat form
- [x] 3.4 Update the `ui_chat` handler in `app/ui/query.py` to use the dedicated `thread_id` form field instead of parsing it from `prompt_name`
- [ ] 3.5 Verify thread selection and "New Thread" creation work end-to-end on the query page

## 4. Linting & Verification

- [x] 4.1 Run `ruff check . && ruff format .` to verify no lint errors
- [ ] 4.2 Start the app and verify `/query` loads, file_name is optional, and thread selector functions
