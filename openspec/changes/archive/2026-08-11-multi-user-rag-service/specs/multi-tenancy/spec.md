## ADDED Requirements

### Requirement: Tenant-scoped vector storage
All vector data SHALL be stored with a `tenant_id` column that scopes every row to a specific tenant. Queries without a valid `tenant_id` filter MUST return empty results.

#### Scenario: Tenant A queries only their data
- **WHEN** Tenant A queries `annual_report.pdf`
- **THEN** the system retrieves only vectors where `tenant_id = 'tenant_a'` AND `source = 'annual_report.pdf'`

#### Scenario: Cross-tenant isolation
- **WHEN** Tenant A ingests `shared_report.pdf` and Tenant B queries `shared_report.pdf`
- **THEN** Tenant B retrieves zero results because no vectors exist with `tenant_id = 'tenant_b'` for that source

#### Scenario: Query without tenant context
- **WHEN** a request reaches the vector search layer without a `tenant_id` in the request state
- **THEN** the system SHALL raise an error or return empty results

### Requirement: Tenant-scoped ingestion
All ingestion operations SHALL associate created chunks with the requesting tenant's ID. Ingested metadata MUST include the `tenant_id`.

#### Scenario: Tenant ingests a PDF
- **WHEN** Tenant A uploads `contract.pdf`
- **THEN** all generated chunks have `tenant_id = 'tenant_a'` in their metadata and database row

#### Scenario: Ingestion without tenant context
- **WHEN** ingestion is triggered without a tenant context
- **THEN** the system SHALL reject the operation with an authentication error

### Requirement: Tenant-scoped source listing
The `get_distinct_sources` API SHALL return only source names belonging to the requesting tenant.

#### Scenario: List files for specific tenant
- **WHEN** Tenant A calls `GET /api/v1/ingest/files`
- **THEN** only filenames associated with `tenant_id = 'tenant_a'` are returned

### Requirement: Default tenant migration
Existing data in vector tables SHALL be assigned to a default tenant (`"default"`) during migration to preserve backward compatibility.

#### Scenario: Existing data after migration
- **WHEN** the migration adds the `tenant_id` column
- **THEN** all pre-existing rows have `tenant_id = 'default'`
