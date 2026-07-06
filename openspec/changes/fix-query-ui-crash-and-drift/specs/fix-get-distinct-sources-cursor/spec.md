## ADDED Requirements

### Requirement: get_distinct_sources returns dict rows
The `PGVectorDB.get_distinct_sources()` method SHALL create its cursor with `row_factory=dict_row` so that `fetchall()` returns a list of dictionaries with string keys, matching the behavior of the `search()` method.

#### Scenario: get_distinct_sources returns valid source names
- **WHEN** `get_distinct_sources()` is called with a valid `tenant_id`
- **THEN** the method returns a `List[str]` of distinct source names without raising `AttributeError`

#### Scenario: get_distinct_sources handles empty results
- **WHEN** `get_distinct_sources()` is called and no documents exist for the tenant
- **THEN** the method returns an empty list `[]` without error
