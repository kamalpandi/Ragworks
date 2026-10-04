# evaluation-api Specification

## Purpose
Expose evaluation runs, progress, and results as JSON only, removing HTML fragments and request-header content negotiation from the evaluation API.

## Requirements

### Requirement: Evaluation endpoints are JSON only
All evaluation endpoints under `/api/v1/eval/*` SHALL return JSON. The evaluation API SHALL NOT render HTML fragments and SHALL NOT change response format based on the `HX-Request` header.

#### Scenario: HX-Request still receives JSON
- **WHEN** a client requests `POST /api/v1/eval/run` with `HX-Request: true`
- **THEN** the response body is JSON

#### Scenario: No HTML result card
- **WHEN** an evaluation completes and its result is requested
- **THEN** the response is a JSON result object and no HTML fragment or result-card endpoint is produced

### Requirement: Evaluation progress as JSON
The evaluation progress endpoint SHALL return a JSON object describing run status. While running it SHALL include progress counts; when complete it SHALL include the result; when failed it SHALL include an error.

#### Scenario: Running progress
- **WHEN** an authenticated client requests `GET /api/v1/eval/progress/{run_id}` for an in-progress run
- **THEN** the response is JSON containing `status = "running"` and current/total progress

#### Scenario: Completed run
- **WHEN** an authenticated client requests progress for a completed run
- **THEN** the response is JSON containing `status = "done"` and the evaluation result

#### Scenario: Failed run
- **WHEN** an authenticated client requests progress for a failed run
- **THEN** the response is JSON containing `status = "error"` and an error message

#### Scenario: Unknown run
- **WHEN** an authenticated client requests progress for an unknown `run_id`
- **THEN** the backend responds with HTTP 404 and a JSON error body
