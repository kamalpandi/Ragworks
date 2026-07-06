## ADDED Requirements

### Requirement: Local LLM request queuing
When the LLM provider is `llamacpp` (local mode), concurrent `complete()` calls SHALL be serialized through an async queue with a single worker. Requests SHALL be processed in FIFO order.

#### Scenario: Two concurrent LLM requests queued
- **WHEN** Request A and Request B call the local llama.cpp LLM simultaneously
- **THEN** Request A is processed first, and Request B begins only after Request A completes

#### Scenario: Queue timeout
- **WHEN** a request has been in the queue longer than `LLM_QUEUE_TIMEOUT_SECONDS`
- **THEN** the system returns HTTP 503 with `{"error": "LLM request timed out in queue", "queue_position": <n>}`

#### Scenario: No queuing for cloud providers
- **WHEN** the LLM provider is `openai` or `ollama`
- **THEN** requests are processed concurrently without queuing

### Requirement: Queue health metrics
The LLM queue SHALL expose Prometheus metrics for queue depth, wait time, and timeout count, gated by `OBSERVABILITY_ENABLED`.

#### Scenario: Queue depth metric
- **WHEN** 3 requests are waiting in the LLM queue
- **THEN** the `rag_llm_queue_depth` gauge reads 3

### Requirement: Configurable queue timeout
The queue timeout SHALL be configurable via `LLM_QUEUE_TIMEOUT_SECONDS` environment variable, defaulting to 120 seconds.

#### Scenario: Custom timeout
- **WHEN** `LLM_QUEUE_TIMEOUT_SECONDS=60`
- **THEN** requests time out after 60 seconds in the queue

### Requirement: Error isolation
A failed LLM invocation for one request SHALL NOT affect other queued requests. Subsequent requests SHALL still be processed.

#### Scenario: One request fails, next succeeds
- **WHEN** Request A fails with a model error
- **THEN** the error is returned to Request A, and Request B is processed normally
