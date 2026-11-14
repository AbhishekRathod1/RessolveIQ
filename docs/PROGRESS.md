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

## Milestone 6: React support workspace

- Added a responsive React/Vite/TypeScript application with Tailwind styling, React Router, Lucide icons, and Recharts.
- Built dashboard, paginated/filterable ticket list, validated ticket form with explicit AI analysis/apply action, ticket detail/review/escalation, knowledge search, and analytics pages.
- Connected pages to existing FastAPI endpoints through a centralized fetch client; backend URL is configurable with `VITE_API_BASE_URL`.
- Added API connection status, loading/empty/error states, responsive layouts, and demo/synthetic-data labels. Metrics and charts use live backend responses.
- Split route bundles to keep the initial production bundle under the build warning threshold.
- Verification: `npm run lint` passes, `npm run build` succeeds, and the Vite dev server returns HTTP 200. Browser smoke testing verified ticket creation, AI preview, persisted knowledge suggestion/review, analytics, and knowledge search.

## Milestone 7: Frontend/backend integration verification

- Exercised ticket creation, classifier preview, knowledge retrieval, persisted suggestions, edited/accepted/rejected reviews, escalation, valid status transitions, audit history, and live analytics through the browser against FastAPI.
- Verified list search, combined status/category/priority filters, and pagination with 12 records in a temporary isolated SQLite database.
- Confirmed API validation returns 422, missing-ticket UI handles 404, and the configured local frontend origin passes the CORS preflight.
- Added success feedback for ticket mutations, explicit refresh-failure messaging, and a retry action for ticket classification.
- Verification: all 76 backend tests pass, frontend lint and production build pass, and the manual browser integration flows are recorded in [docs/INTEGRATION_REPORT.md](./INTEGRATION_REPORT.md).

## Milestone 8: Final quality review and stabilization

- Re-ran the complete backend suite (76 passed), frontend lint, and production build.
- Reproduced the deterministic synthetic-data model evaluation and verified real artifact inference remains consistent after reload.
- Audited SQLAlchemy relationships/transaction scopes, status transitions, audit history, analytics denominators, validation, missing-model/KB behavior, and generic unexpected-error responses.
- Scanned tracked and workspace source for common credential patterns; checked fictional seed contacts and article source references. No upload endpoint exists.
- Removed an absolute local model-artifact path from the missing-model API response and added a regression assertion; updated missing-KB coverage to use a nonexistent path.
- Verified empty/loading/error UI behavior, offline retry, navigation, actual ticket creation/classification, and live analytics in the browser. Recorded a small warm local benchmark and its limitations.
- Full outcomes, production gaps, evaluation protocol, and remaining blockers are documented in [docs/QUALITY_REPORT.md](./QUALITY_REPORT.md).

## Milestone 9: Public portfolio documentation

- Rewrote the root README with the problem/use case, implemented features, architecture, stack, Windows PowerShell setup and run instructions, environment configuration, seed-data steps, AI approach and measured synthetic evaluation, limitations, and license status.
- Added architecture, API reference, demo walkthrough, and interview Q&A documentation with Mermaid diagrams where useful.
- Captured a genuine dashboard screenshot from the local application using five fictional seeded tickets; no screenshot or benchmark results were fabricated.
- Updated `.gitignore` to ignore `.env.*` while retaining the checked-in `.env.example` templates. Verified the preview database and environment files are ignored.
- Confirmed documented training/seeding scripts and environment-template paths exist; verified API and Vite startup for the screenshot and checked all local Markdown links.
- Verification: all 76 backend tests pass with one existing Starlette/httpx deprecation warning; frontend lint and production build pass; `git diff --check` passes.

## Deferred

- Advanced workflow automation.
- Real-world model validation/calibration, production deployment, authentication, and operational hardening.

This project remains an early development milestone and is not production-ready.
