## 1. Critical Bug Fixes

- [x] 1.1 Fix LLM queue never started: make `_get_queue()` async, call `await queue.start()` after creating `LLMRequestQueue` in `app/components/llms/llamacpp_llm.py`
- [x] 1.2 Fix migration SQL crash: import `Literal` from `psycopg.sql`, change `Identifier(self.table_name)` to `Literal(self.table_name)` for the `WHERE table_name = ...` comparison in `app/components/vector_dbs/pgvector_db.py:46`
- [x] 1.3 Fix streaming broken: revert `LlamaCppProvider.stream()` local path to use `asyncio.Lock` instead of `LLMRequestQueue`, restore chunk-by-chunk yielding in `app/components/llms/llamacpp_llm.py`

## 2. High-Severity Fixes

- [x] 2.1 Add `thread_id: Optional[str] = None` field to `QueryResponse` model in `app/models/api_response.py`
- [x] 2.2 Remove dead `_hash_key()` + `compare_digest` code in `validate_api_key()` in `app/services/api_key_manager.py:48-50`
- [x] 2.3 Fix `deactivate_api_key()`: change SQL to `UPDATE ... RETURNING id` and check for returned row in `app/services/api_key_manager.py:58-62`

## 3. Medium-Severity Fixes

- [x] 3.1 Add `@app.get("/health")` route returning `{"status": "healthy"}` in `main.py`
- [x] 3.2 Fix rate limit path matching: replace broad `"/query" in path` with explicit endpoint checks in `app/middleware/rate_limit.py:67-73`
- [x] 3.3 Remove auto thread_id generation in `RAGEngine.answer_question()`: only create thread_id when one is provided by caller, skip conversation storage otherwise in `app/services/rag_engine.py:69-86,188-194`
- [x] 3.4 Fix admin key logic: when both `X-Admin-Key` and `X-API-Key` are present, let API key determine `tenant_id` while still setting `is_admin = True` in `app/middleware/auth.py:26-31`
- [x] 3.5 Remove misleading `request: Request = None` defaults — change to `request: Request` in `app/api/v1/endpoints/ingest.py`, `app/ui/ingest.py`
- [x] 3.6 Wrap `run_migrations()` in `await asyncio.to_thread(run_migrations)` in `main.py` lifespan

## 4. Linting & Verification

- [x] 4.1 Run `ruff check . && ruff format .` to verify no lint errors
- [x] 4.2 Verify `main.py` starts without migration SQL errors
