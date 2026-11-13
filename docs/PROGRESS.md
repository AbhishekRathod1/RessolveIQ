# ResolveIQ Progress

## Milestone 1: Backend foundation

- Created the monorepo directory structure for the backend, data, scripts, and documentation.
- Added environment-based FastAPI settings, local frontend CORS configuration, and SQLite/SQLAlchemy setup.
- Added `GET /api/health` and a focused backend test.
- Added local setup instructions and repository ignore rules.

## Milestone 2: Ticket management API

- Added SQLAlchemy ticket and ticket-event models with relationships, constraints, and indexes.
- Implemented ticket create/read/list/update/status/history APIs with validation, pagination, filtering, search, atomic updates, and audit events.
- Status changes are explicitly validated; resolved tickets receive a server-controlled resolution timestamp.
- MVP actions are attributed to the fixed `demo-user` label; client actor fields are rejected.
- Added an isolated SQLite test fixture and endpoint tests.
- Added fictional sample tickets and an idempotent seed command.

## Milestone 3: AI-assisted classification and recommendations

- Added a deterministic fictional labeled dataset and reproducible generation script.
- Trained and persisted a TF-IDF/logistic-regression pipeline locally; model artifacts are ignored by Git and loaded once per process.
- Added group-stratified held-out evaluation with exact/near-duplicate leakage checks and a synthetic-data evaluation report.
- Added `POST /api/ai/analyze-ticket`, deterministic category-to-team routing, transparent rule-based priorities, and low-confidence manual review.
- Analysis is opt-in and does not update or overwrite ticket category/priority fields.
- Added tests for loading, predictions, categories, routing, priority rules, validation, review thresholds, and leakage checks.

## Milestone 4: Knowledge retrieval and reviewable suggestions

- Added 20 fictional Markdown troubleshooting articles with document IDs, categories, revision dates, and source references; the loader also supports TXT articles.
- Added deterministic paragraph/character chunking, a TF-IDF cosine index, stable top-k retrieval, source attribution, and explicit no-match/no-documents states.
- Added extractive resolution suggestions with supporting sources, raw similarity scores, quality warnings, and mandatory human review.
- Added best-effort secret redaction for common credentials/tokens and email addresses; retrieved text is never executed.
- Added a provider protocol for future LLM implementations; the default requires no LLM or paid API.
- Added tests for relevant/unrelated retrieval, missing and mixed-format documents, citations, repeatability, chunking, safe fallback, and validation.

## Milestone 5: Human-reviewed support workflow and analytics

- Persisted knowledge-based suggestions on tickets with evidence, recommended steps, source attribution, review status, reviewer, and approved resolution.
- Added accept, edit, and reject decisions restricted to explicit fictional demo reviewers. Decisions are audited, terminal, and do not resolve or otherwise change ticket status.
- Suggestions with insufficient evidence cannot be accepted; editable decisions require human-provided resolution text.
- Added ticket escalation to validated human support teams, with atomic team/status updates and ticket-history audit events.
- Added SQLite-backed ticket counts, category/priority/status groupings, mean resolution duration, and suggestion acceptance rate.
- Average resolution duration is calculated over resolved tickets with nonnegative `resolved_at - created_at` values; the response includes that denominator. Acceptance rate is `(accepted + edited) / (accepted + edited + rejected)`, excluding pending suggestions; it is null when no suggestion has been reviewed.
- Expanded isolated-database tests for persisted suggestions, human review decisions, insufficient evidence, escalation transitions, audit history, and analytics accuracy.
- Verification: all 76 backend tests pass. Pytest reports one existing Starlette/httpx TestClient deprecation warning.

## Deferred

- Frontend application and advanced workflow automation.
- Real-world model validation/calibration, production deployment, authentication, and operational hardening.

This project remains an early development milestone and is not production-ready.
