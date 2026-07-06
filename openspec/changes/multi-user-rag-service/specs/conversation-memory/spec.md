## ADDED Requirements

### Requirement: Conversation thread creation
When a query includes a `thread_id` that does not exist, the system SHALL create a new thread scoped to the requesting tenant. A new `thread_id` (UUID) SHALL be generated and returned in the response.

#### Scenario: First query with new thread_id
- **WHEN** Tenant A queries with `thread_id: "new-thread-abc"`
- **THEN** a new conversation thread is created with `tenant_id = 'tenant_a'` and `thread_id = 'new-thread-abc'`

#### Scenario: Query without thread_id
- **WHEN** a query is made without a `thread_id`
- **THEN** the system generates a new `thread_id` and returns it in the response

### Requirement: Conversation history injection
When a `thread_id` is provided and has prior messages, the system SHALL include the last N messages (up to `CONVERSATION_HISTORY_LENGTH`, default 10) as chat history in the LLM prompt, between the system prompt and the retrieved context.

#### Scenario: Follow-up question with history
- **WHEN** Tenant A queries a thread that has 3 prior Q&A pairs
- **THEN** those 3 pairs are formatted as `User: ...\nAssistant: ...` and injected before the current question and retrieved context

#### Scenario: Thread exceeds history length
- **WHEN** a thread has 20 prior messages and `CONVERSATION_HISTORY_LENGTH` is 10
- **THEN** only the most recent 10 messages are included

### Requirement: Tenant-scoped conversation isolation
Conversation threads SHALL be scoped to a tenant. Tenant A SHALL NOT be able to read or continue Tenant B's threads.

#### Scenario: Cross-tenant thread access denied
- **WHEN** Tenant A queries with a `thread_id` that belongs to Tenant B
- **THEN** the system treats it as a new thread for Tenant A (or returns an error) — Tenant B's messages are never exposed

### Requirement: Message storage
Each user query and its corresponding assistant response SHALL be stored as a row in the `conversations` table with columns: `id`, `tenant_id`, `thread_id`, `role`, `content`, `created_at`.

#### Scenario: Q&A pair stored
- **WHEN** a query completes successfully with an answer
- **THEN** both the user message (`role = 'user'`) and assistant response (`role = 'assistant'`) are persisted to the `conversations` table

### Requirement: Conversation retrieval API
The system SHALL provide `GET /api/v1/conversations/{thread_id}` to retrieve the full message history for a thread, scoped to the requesting tenant.

#### Scenario: Retrieve thread history
- **WHEN** Tenant A requests `GET /api/v1/conversations/new-thread-abc`
- **THEN** all messages in that thread for Tenant A are returned in chronological order
