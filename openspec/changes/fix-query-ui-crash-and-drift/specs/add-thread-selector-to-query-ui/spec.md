## ADDED Requirements

### Requirement: Thread selector in query UI
The query page SHALL include a dropdown that lists existing conversation threads for the current tenant and allows the user to select a thread for the query. A "New Thread" action SHALL create a new thread ID.

#### Scenario: User selects an existing thread
- **WHEN** a user selects an existing thread from the dropdown and submits a query
- **THEN** the query is associated with the selected thread ID

#### Scenario: User creates a new thread
- **WHEN** a user triggers the "New Thread" action
- **THEN** a new UUID thread ID is generated and used for the next query

#### Scenario: No threads exist for tenant
- **WHEN** the query page loads and no threads exist for the tenant
- **THEN** the thread dropdown is rendered with no pre-existing options and the default state is "New Thread"
