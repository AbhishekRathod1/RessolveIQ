# ResolveIQ Interview Q&A

## Why this project?

IT support is a concrete workflow where data validation, state management, search, ML, human judgment, and auditability meet. ResolveIQ demonstrates an end-to-end version of that workflow: tickets are persisted, AI recommendations are advisory, source evidence is visible, decisions are audited, and metrics come from actual database queries. The data and evaluation are synthetic, so the project demonstrates engineering choices rather than proven operational value.

## Why FastAPI?

FastAPI provides typed request/response contracts using Pydantic, automatic OpenAPI documentation, dependency injection for database sessions, and a small service-oriented API surface. This fits an MVP where clear validation and interactive API docs matter. For deployment, I would add authentication, request limits, consistent observability, and lifecycle management rather than treating the framework defaults as a complete production platform.

## Why SQLAlchemy?

SQLAlchemy gives the application explicit Ticket, TicketEvent, and TicketSuggestion models, relationships, and transaction boundaries. It allows service logic to group a state mutation and its audit event atomically, while the SQLite backend keeps local setup simple. I would add schema migrations and evaluate a managed relational database before production.

## Why React?

The workflow has multiple connected views—ticket list/detail, review controls, knowledge search, and analytics—so reusable components and stateful navigation are useful. React with TypeScript gives the client typed API shapes and lets each screen refresh from the backend after mutations. The UI remains a client of the API rather than a second source of business data.

## Why TF-IDF and Logistic Regression?

They are fast, interpretable baseline tools for short text classification, run locally without paid services, and integrate cleanly into one scikit-learn Pipeline. The model is deterministic under the fixed training procedure and exposes class probabilities for an advisory confidence signal. Those probabilities are not calibrated. The small synthetic dataset has templated labels, so the perfect held-out result is not representative; a real service would need consented representative data, baseline comparisons, subgroup evaluation, calibration, and monitored retraining.

## How is retrieval different from generation?

Retrieval ranks existing document chunks against a query and returns the original content with document/source attribution. Generation creates new text and can introduce unsupported claims. ResolveIQ's default resolution path is extractive: it selects numbered instructions from retrieved articles and attaches their source references. It does not call an LLM. A low-evidence result has no steps, and similarity scores are not presented as probabilities.

## What happens if the AI is wrong?

The classifier only returns a recommendation; it does not overwrite ticket category/priority fields. Low classifier confidence recommends manual review. Resolution suggestions require a reviewer, show their supporting sources and warnings, and cannot automatically resolve tickets. Humans can edit or reject suggestions, and decisions are audited. This reduces automation risk but does not guarantee correctness; a human must verify guidance before acting.

## What makes this system end-to-end?

The product demonstrates a complete request path: a user submits a ticket in React, FastAPI validates and stores it in SQLite, classification and knowledge endpoints return advisory results, the suggestion workflow persists a human decision, escalation changes team/status with audit events, and dashboard/analytics pages query the resulting database state. The browser has been manually exercised against the real endpoints. This is not a production deployment or an automated E2E test suite.

## How would it scale?

First measure actual traffic and database contention rather than assume scale. I would add indexes based on query plans, pagination limits, and a migration-managed relational database. Then separate CPU-heavy model inference/document indexing into versioned workers if needed, cache immutable model/index artifacts, and move document search to a managed search/vector service only when corpus size and relevance requirements justify it. Add observability, backpressure, retries, and load tests before horizontal scaling.

## How would a company deploy it securely?

Use an identity provider with server-validated authentication and role-based authorization; never treat the demo reviewer string as identity. Place the service behind TLS and a managed ingress, restrict CORS to approved origins, store secrets in a managed secret store, and use an encrypted managed database with backups and migrations. Add rate limits, request-size limits, monitoring, alerting, audit-log access controls, retention policies, and privacy review. Keep model artifacts and knowledge documents trusted and versioned, validate uploaded documents if ingestion is added, and require human approval for privileged account/security actions.

## What were the important design tradeoffs?

- **Local SQLite and no paid service** made the MVP reproducible quickly, at the cost of production concurrency, migration, and operational concerns.
- **Synthetic labeled data** enabled deterministic model training and testing, but sharply limits any performance conclusion.
- **TF-IDF and Logistic Regression** are cheap and explainable baselines, not semantic language models.
- **Extractive retrieval** keeps suggestions tied to source text and avoids default LLM hallucination, but cannot paraphrase or reconcile conflicting articles.
- **Explicit human review** adds friction but prevents suggestion acceptance from implicitly changing ticket status.
- **Fixed demo actors** make audit flows testable, but are not an authentication scheme.
- **Simple priority rules** are transparent and testable, but use keyword cues rather than full impact/context understanding.
- **Static knowledge files** simplify deployment; they are unsuitable as an uncontrolled user-upload mechanism.

## Other technical facts worth mentioning

- Ticket IDs, numbers, and timestamps are server-controlled.
- Ticket state transitions are explicit and resolved is terminal.
- Ticket and suggestion changes use SQLAlchemy transaction scopes with audit records.
- Analytics define denominators: pending suggestions are excluded from acceptance rate; averages/rates are null when no valid denominator exists.
- No production-readiness claim is made. The limitations and measured test results are documented in [QUALITY_REPORT.md](QUALITY_REPORT.md).
