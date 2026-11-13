# ResolveIQ

ResolveIQ is an AI-powered enterprise IT support and workflow automation platform. This repository is an early development milestone and is not production-ready.

## Backend quick start

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
python scripts\train_ticket_classifier.py
python -m uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is available at <http://127.0.0.1:8000/api/health>. Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

The classifier artifact is generated locally by the training command and is excluded from Git. The analyzer returns `503` until the model has been trained. Training is not performed by API requests.

## Ticket API

- `POST /api/tickets` creates a ticket with server-generated ID, ticket number, timestamps, and initial `open` status.
- `GET /api/tickets` supports `limit`, `offset`, `status`, `category`, `priority`, and `search` query parameters.
- `GET /api/tickets/{id}` retrieves a ticket.
- `PATCH /api/tickets/{id}` updates ticket details.
- `PATCH /api/tickets/{id}/status` changes status using the allowed transitions.
- `GET /api/tickets/{id}/history` retrieves its audit events.

Ticket status transitions: `open` to `in_progress` or `escalated`; `in_progress` to `open`, `pending_review`, `resolved`, or `escalated`; `pending_review` to `in_progress`, `resolved`, or `escalated`; `escalated` to `in_progress`, `pending_review`, or `resolved`. `resolved` is terminal. Resolving a ticket sets `resolved_at`.

The MVP has no authentication. Ticket actions are recorded as `demo-user`; request-supplied actor fields are rejected, not treated as authenticated identity.

To insert the fictional sample tickets once, run this from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\seed_tickets.py
```

### Example requests

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/tickets `
  -H "Content-Type: application/json" `
  -d '{"title":"Fictional VPN access issue","description":"A demo user cannot connect to the sample VPN.","category":"network","priority":"medium","requester_name":"Alex Example","requester_email":"alex@example.com"}'

curl.exe "http://127.0.0.1:8000/api/tickets?status=open&category=network&limit=10&offset=0"
curl.exe -X PATCH http://127.0.0.1:8000/api/tickets/1/status `
  -H "Content-Type: application/json" -d '{"status":"in_progress"}'
```

## AI ticket analysis

`POST /api/ai/analyze-ticket` accepts a title, description, and optional `business_impact`. It returns a classifier category and confidence, a deterministic team mapping, a rules-based priority recommendation, an explanation, and a manual-review flag. It never writes to or overwrites a ticket; standard ticket CRUD remains unchanged.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/ai/analyze-ticket `
  -H "Content-Type: application/json" `
  -d '{"title":"Fictional office Wi-Fi disconnects","description":"A demo workstation loses the sample network connection.","business_impact":"Several users are blocked from working."}'
```

Recreate the deterministic fictional dataset with `python scripts\generate_ticket_dataset.py`. Train, evaluate, and persist the local model with `python scripts\train_ticket_classifier.py`. The protocol, synthetic-data-only metrics, confusion matrix, and limitations are documented in [docs/AI_CLASSIFICATION.md](./docs/AI_CLASSIFICATION.md); machine-readable metrics are in [docs/AI_CLASSIFICATION_EVALUATION.json](./docs/AI_CLASSIFICATION_EVALUATION.json).

## Knowledge-base retrieval and suggestions

The fictional Markdown knowledge base is in `data\knowledge_base`. `GET /api/knowledge` lists article metadata; `POST /api/knowledge/search` accepts `{"query":"VPN sign-in fails","top_k":5}` and returns chunks, document/source identifiers, raw cosine-similarity scores, and a `reliable_match`, `no_reliable_match`, or `no_documents` state. The minimum retrieval score is a heuristic threshold, not a probability.

`POST /api/ai/suggest-resolution` accepts a title and description, retrieves evidence, and extracts troubleshooting steps from cited articles. It does not call an LLM, execute commands, or modify tickets. Weak evidence returns `insufficient_evidence` with no steps. All suggestions require human review; account, access, and security topics also require authorized review before privileged actions. The local knowledge index is cached, so restart the backend after changing article files.

Retrieved text is treated as untrusted and common credential/token/email patterns are redacted before indexing or response. This is best-effort redaction, not a substitute for keeping sensitive information out of knowledge articles.

## Human review and escalation

- `POST /api/tickets/{id}/suggestions` creates and persists a pending, human-review-required suggestion; `GET /api/tickets/{id}/suggestions` lists saved suggestions.
- `POST /api/suggestions/{id}/review` accepts `accepted`, `edited`, or `rejected` and requires an explicit demo reviewer (`demo-reviewer-1` or `demo-reviewer-2`). An edited decision must include `edited_resolution`.
- A suggestion without reliable evidence cannot be accepted. Review decisions are final and recorded in ticket history. Acceptance or editing stores approved resolution text but never changes the ticket status or resolves it.
- `POST /api/tickets/{id}/escalate` assigns a human support team and transitions an eligible ticket to `escalated`; the team, status, reason, and fixed `demo-user` actor are recorded in history.
- Demo reviewer and user labels are attribution for this unauthenticated MVP, not authentication or authorization.

Example review:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/suggestions/1/review `
  -H "Content-Type: application/json" `
  -d '{"status":"edited","reviewer":"demo-reviewer-1","edited_resolution":"Ask the requester to verify the approved sample profile."}'
```

## Analytics

`GET /api/analytics/summary` computes ticket counts and groupings from SQLite. Average resolution time is the mean of `resolved_at - created_at` for resolved tickets with valid nonnegative durations; `average_resolution_time_ticket_count` is its denominator. Suggestion acceptance rate is `(accepted + edited) / (accepted + edited + rejected)`; pending suggestions are excluded, and `ai_suggestion_reviewed_count` is that denominator. An average or rate is `null` when its denominator is zero. These are operational sample metrics, not predictions.

## Run backend tests

```powershell
python -m pytest backend\tests
```
