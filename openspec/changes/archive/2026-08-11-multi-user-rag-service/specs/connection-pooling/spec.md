## ADDED Requirements

### Requirement: Shared connection pool
The PGVector database component SHALL use a shared `AsyncConnectionPool` instead of creating a new connection per operation. The pool SHALL be created at application startup and closed at shutdown.

#### Scenario: Multiple concurrent searches reuse connections
- **WHEN** 10 concurrent query requests hit the vector search path
- **THEN** connections are acquired from and returned to the pool, with no more than `POOL_MAX_SIZE` connections opened

#### Scenario: Pool created at startup
- **WHEN** the FastAPI application starts
- **THEN** the connection pool is initialized with `POOL_MIN_SIZE` connections

#### Scenario: Pool closed at shutdown
- **WHEN** the FastAPI application shuts down
- **THEN** all pool connections are gracefully closed

### Requirement: Configurable pool sizing
Pool parameters SHALL be configurable via environment variables: `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_TIMEOUT`.

#### Scenario: Custom pool size
- **WHEN** `DB_POOL_MAX_SIZE=20` is set
- **THEN** the pool allows up to 20 concurrent connections

### Requirement: Backward compatible with sync init
The synchronous `_init_db` method (table creation, extension setup) SHALL continue to work, using a separate sync connection outside the pool.

#### Scenario: Table creation on startup
- **WHEN** PGVectorDB initializes and the vector table does not exist
- **THEN** a sync connection creates the table and HNSW index, then disconnects
