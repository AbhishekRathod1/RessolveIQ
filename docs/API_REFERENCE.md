# ResolveIQ API Reference

The API is rooted at `/api`. Run the backend and use the generated [Swagger UI](http://127.0.0.1:8000/docs) or [OpenAPI document](http://127.0.0.1:8000/openapi.json) for interactive schemas.

All request/response bodies are JSON. Unknown input fields are rejected by the request schemas. Common responses:

- `422 Unprocessable Entity` — invalid JSON shape, field, or value.
- `404 Not Found` — a referenced ticket or suggestion does not exist.
- `409 Conflict` — a validly formed request conflicts with the current workflow state.
- `503 Service Unavailable` — classifier model artifact is missing.
- Unexpected server failures return generic `500` responses when debug mode is disabled.

This MVP has no authentication. Fixed actor labels and accepted demo reviewer values are attribution only, not verified identities.

## Health

### `GET /api/health`

Returns `{"status":"ok"}` when the API process is responsive. It is not a complete database/model readiness check.

## Tickets

### `POST /api/tickets`

Creates a ticket with server-generated `id`, `ticket_number`, timestamps, `open` status, and a creation audit event. Returns `201`.

Required fields:

| Field | Constraints |
| --- | --- |
| `title` | non-empty, max 200 |
| `description` | non-empty, max 10,000 |
| `category` | non-empty, max 50 |
| `priority` | `low`, `medium`, `high`, or `urgent` |
| `requester_name` | non-empty, max 120 |
| `requester_email` | valid email, max 254 |

Optional: `assigned_team` (non-empty, max 100; defaults to `IT Support`). Client-supplied IDs, ticket numbers, status/timestamps, and actor fields are not accepted.

```json
{
  "title": "Fictional VPN access issue",
  "description": "A demo workstation cannot connect to the sample VPN.",
  "category": "network",
  "priority": "medium",
  "requester_name": "Alex Example",
  "requester_email": "alex@example.com"
}
```

### `GET /api/tickets`

Returns `{"items":[...],"total":n,"limit":n,"offset":n}`. Query parameters:

| Parameter | Default | Constraints |
| --- | ---: | --- |
| `limit` | 20 | 1–100 |
| `offset` | 0 | >= 0 |
| `status` | — | Ticket status enum |
| `category` | — | 1–50 characters |
| `priority` | — | Ticket priority enum |
| `search` | — | 1–200 characters; searches ticket number, title, and description |

### `GET /api/tickets/{ticket_id}`

Returns a ticket or `404`.

### `PATCH /api/tickets/{ticket_id}`

Updates one or more ticket detail fields (`title`, `description`, `category`, `priority`, `assigned_team`, `requester_name`, `requester_email`). Must provide at least one valid non-null field. Each changed field is audited. Status is changed through the dedicated endpoint.

Example:

```json
{"title":"Updated fictional VPN issue","priority":"high"}
```

### `PATCH /api/tickets/{ticket_id}/status`

Body: `{"status":"in_progress"}`. Allowed transitions:

| Current | Allowed next states |
| --- | --- |
| `open` | `in_progress`, `escalated` |
| `in_progress` | `open`, `pending_review`, `resolved`, `escalated` |
| `pending_review` | `in_progress`, `resolved`, `escalated` |
| `escalated` | `in_progress`, `pending_review`, `resolved` |
| `resolved` | none |

Invalid transitions return `409`. Resolving a ticket sets server-controlled `resolved_at`; no AI endpoint performs this transition.

### `GET /api/tickets/{ticket_id}/history`

Returns the ordered audit events for the ticket. An event includes `id`, `ticket_id`, `event_type`, `previous_value`, `new_value`, `actor`, and `timestamp`.

## AI analysis

### `POST /api/ai/analyze-ticket`

Input: required `title` (1–200) and `description` (1–10,000), optional `business_impact` (1–1,000).

Returns `predicted_category`, `category_confidence`, `recommended_team`, `recommended_priority`, `explanation`, and `needs_manual_review`. Categories are Hardware, Software, Network, Account & Access, Security, Other. Priority is a separate deterministic rule recommendation (`low`, `medium`, `high`, `critical`); it is not trained. The endpoint does not update tickets.

### `POST /api/ai/suggest-resolution`

Input: required title/description and optional `top_k` (1–5, default 3). Returns `evidence_state`, `issue_summary`, source-attributed `recommended_steps`, `supporting_sources` with raw cosine scores, a warning, and a human-review requirement. `insufficient_evidence` means the step list is empty. This endpoint does not persist or execute a suggestion.

## Knowledge base

### `GET /api/knowledge`

Returns `{"items":[...],"total":n}`. Document metadata includes document ID, title, category, revision date, and source reference.

### `POST /api/knowledge/search`

Input: `query` (1–1,000 characters), optional `top_k` (1–10, default 5). Response state is `reliable_match`, `no_reliable_match`, or `no_documents`; matches contain chunk/document IDs, content, source reference, revision, raw similarity score, and score type. Similarities are not probabilities.

```json
{"query":"VPN profile authentication connection fails","top_k":5}
```

## Persisted suggestions and human review

### `POST /api/tickets/{ticket_id}/suggestions`

Creates a pending ticket-linked suggestion using retrieved knowledge (`top_k` 1–5, default 3), and records a `demo-ai` event. Returns `201`. Weak/no evidence can still create an `insufficient_evidence` suggestion, but it contains no troubleshooting steps and cannot be accepted.

### `GET /api/tickets/{ticket_id}/suggestions`

Lists persisted suggestions for the ticket.

### `POST /api/suggestions/{suggestion_id}/review`

Input requires:

- `status`: `accepted`, `edited`, or `rejected`.
- `reviewer`: `demo-reviewer-1` or `demo-reviewer-2` (not authentication).
- `edited_resolution`: required only for `edited`; non-empty, max 10,000.

Only pending suggestions can be reviewed. Review decisions are final and audited. Accepted/edited text is stored as approved resolution text, but does not close or otherwise change the ticket.

### `POST /api/tickets/{ticket_id}/escalate`

Input requires a `team` from `IT Support`, `Desktop Support`, `Application Support`, `Network Support`, `Identity & Access Support`, or `Security Operations`; optional `reason` is max 1,000 characters. Eligible tickets move to `escalated`, are assigned to that team, and receive audit events. Invalid workflow transitions return `409`.

## Analytics

### `GET /api/analytics/summary`

Returns database-backed ticket totals and groupings, average resolution seconds and denominator, plus suggestion reviewed/accepted/edited/rejected counts and acceptance rate.

- Average resolution time is calculated over resolved tickets with non-null and nonnegative `resolved_at - created_at` values; the response includes `average_resolution_time_ticket_count`.
- Acceptance rate is `(accepted + edited) / (accepted + edited + rejected)`; pending suggestions are excluded and `ai_suggestion_reviewed_count` is the denominator.
- An average or rate is `null` when the denominator is zero.

## Responses

Ticket responses include `id`, `ticket_number`, `title`, `description`, `category`, `priority`, `assigned_team`, `status`, requester details, `created_at`, `updated_at`, and nullable `resolved_at`. Timestamps are ISO-8601 strings. See OpenAPI for the full nested suggestion and analytics shapes.
