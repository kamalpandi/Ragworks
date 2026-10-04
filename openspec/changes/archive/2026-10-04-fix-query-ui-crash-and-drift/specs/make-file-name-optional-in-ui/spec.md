## ADDED Requirements

### Requirement: file_name is optional in query UI form
The query page HTML form SHALL NOT require the `file_name` field. The input SHALL be rendered without the `required` attribute, and the associated label and help text SHALL indicate the field is optional.

#### Scenario: User submits query without file_name
- **WHEN** a user submits the chat form with an empty `file_name` field
- **THEN** the form submission succeeds and the query handler receives `file_name=None`

#### Scenario: User submits query with file_name
- **WHEN** a user submits the chat form with a specific file name in the `file_name` field
- **THEN** the form submission succeeds and the query handler receives the specified file name

### Requirement: query UI handler accepts optional file_name
The `ui_chat` handler in `app/ui/query.py` SHALL accept `file_name` as an optional parameter with a default of `None` and SHALL NOT reject requests with empty or missing `file_name` values.

#### Scenario: Handler receives empty file_name
- **WHEN** the `ui_chat` handler receives an empty `file_name` string
- **THEN** the handler passes `None` as the `file_filter` to `engine.answer_question()`

#### Scenario: Handler receives valid file_name
- **WHEN** the `ui_chat` handler receives a non-empty `file_name` string
- **THEN** the handler passes the file name as the `file_filter` to `engine.answer_question()`
