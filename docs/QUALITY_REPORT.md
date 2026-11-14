# ResolveIQ Quality Report

## 1. Tests executed

- `.\.venv\Scripts\python.exe -m pytest backend\tests -q` — **76 passed** after the review fixes. One existing Starlette/httpx `TestClient` deprecation warning remains.
- `npm run lint` from `frontend\` — **passed**.
- `npm run build` from `frontend\` — **passed**, including TypeScript checks and Vite production bundling.
- `python scripts\train_ticket_classifier.py` — completed successfully and reproduced the documented held-out evaluation while generating the local, Git-ignored model artifact.
- Manual API and browser checks used an isolated `quality-check.db`, removed after the checks. The existing local application database was not used for these tests.

## 2. Actual results

### Backend and persistence

- Ticket and event/suggestion ORM relationships are bidirectional; ticket relationships use ORM delete-orphan cascades. Ticket creation, status changes, suggestion review, and escalation write their records and audit events inside SQLAlchemy `begin()` transaction scopes.
- Regression tests verified create/read/list behavior, server-owned timestamps and IDs, validation, filtering/pagination, invalid transitions, status and suggestion audit events, escalation audit events, and analytics values/denominators.
- A controlled unexpected service exception (simulating a database failure) returned HTTP 500 with the generic body `Internal Server Error`; the injected exception text was not returned to the client. Validation errors returned 422 and missing tickets returned 404.
- Analytics use SQLite queries. The tested acceptance rate is `(accepted + edited) / (accepted + edited + rejected)`; pending suggestions are excluded. Average resolution time uses resolved rows with valid nonnegative durations and is null when its denominator is zero.
- Seed files contain fictional names and `example.com` addresses. The model artifact and SQLite databases are ignored by Git and not tracked.

### AI and knowledge base

- The trained local scikit-learn Pipeline loaded from the actual artifact and returned the same category and confidence after clearing the cache and reloading the model.
- The analyzer loads and caches the model; tests verify missing-model behavior and that requests do not retrain it. Missing knowledge-directory behavior was tested: catalog/search remain usable, and suggestions return insufficient evidence with no steps.
- All 20 knowledge documents had unique IDs and non-empty source references containing the matching document suffix. Retrieved steps and ranked matches include document IDs and source references.
- Unrelated knowledge queries return `no_reliable_match` or `insufficient_evidence`; no steps are returned in the insufficient-evidence case. Accepted AI suggestions do not change ticket status or `resolved_at`.

### Frontend

- Browser checks against the actual API verified empty dashboard/ticket states, disabled empty knowledge search, required-field form validation, page navigation, ticket creation, actual classifier preview, and live analytics.
- Normal navigation/form/API flows produced no browser console errors or uncaught page errors.
- An intentionally aborted analytics request displayed the API error/retry state; removing the failure and retrying restored live metrics. The browser logged the expected network failure caused by the deliberate abort.
- Previous full integration verification of suggestion generation, editing/acceptance/rejection, escalation, history, filters, pagination, knowledge search, and status changes is recorded in [INTEGRATION_REPORT.md](./INTEGRATION_REPORT.md).

### Small local benchmark

On this Windows development environment, a warm in-process loop measured 100 calls per operation using `time.perf_counter`. Classifier timing included `predict` and `predict_proba` on one fixed fictional query; retrieval used the cached knowledge index and a fixed VPN query with `top_k=3`.

| Operation | Median | p95 |
| --- | ---: | ---: |
| Classifier inference | 2.307 ms | 3.782 ms |
| Knowledge search | 1.018 ms | 2.019 ms |

These are local warm-operation observations only. They exclude HTTP, concurrent load, process startup, cold indexing, database contention, and other machines; they are not latency guarantees, throughput measurements, or scalability evidence.

## 3. Bugs found and fixed

- The missing-model API response exposed the machine-specific absolute model-artifact path. It now returns an actionable, path-free 503 message. A regression assertion verifies the temporary path is not returned.
- The missing-knowledge test previously created an empty directory rather than checking a missing directory. It now verifies the actual missing-directory fallback.

## 4. AI evaluation protocol

The local evaluation uses 108 reproducibly generated fictional ticket records, six categories, and random seed `20261113`. It takes the first fold of `StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=20261113)`, producing 81 training rows and 27 held-out rows. All variants sharing a scenario group remain on one side. The trainer checks normalized exact duplicates and cross-split `SequenceMatcher` similarity; the recorded maximum is `0.7344`, below the `0.88` rejection threshold.

The measured held-out **synthetic-data performance** is accuracy **1.0000** and macro F1 **1.0000**. The report at [AI_CLASSIFICATION_EVALUATION.json](./AI_CLASSIFICATION_EVALUATION.json) includes the confusion matrix and per-class support. Category-specific templates strongly correlate with labels; this small generated dataset does not establish real-world performance. Class probabilities are not calibrated, and priority recommendations are substring rules rather than a trained model.

## 5. Known limitations

- There is no automated browser E2E suite; browser verification was manual.
- The existing TestClient dependency combination emits a deprecation warning.
- Model and knowledge search benchmarks are small, warm, and single-process; no load or concurrency behavior was measured.
- The model artifact is a trusted-local `joblib`/pickle artifact. Only load artifacts generated from this repository's trusted training script.
- Knowledge articles are static local Markdown/TXT files loaded from the repository data directory. There is no upload API. Adding any document ingestion feature will require strict size/type/path controls and continued treatment of text as untrusted.
- SQLite schema creation uses `create_all`; there is no migration or backup/restore workflow.

## 6. Security gaps before production

- **Authentication and RBAC:** absent. `demo-user`, `demo-ai`, and the allowlisted demo reviewer labels are attribution only; reviewer values are client supplied and are not authenticated identities.
- **Transport and data protection:** deploy behind TLS, define encryption-at-rest and backup controls, and establish retention/access policies for requester contact data before real data is used.
- **Abuse and operations:** no rate limiting, quotas, monitoring/alerting, security event retention controls, or production incident-response process.
- **Deployment configuration:** production must keep debug disabled and use an explicit trusted CORS-origin allowlist. The repository defaults allow local development origins.
- **AI supply chain and governance:** keep model artifacts trusted and versioned, validate on representative authorized data, assess calibration and bias, and retain human review. Synthetic metrics are not a production assurance.
- A focused pattern scan found no common provider-token or private-key material in source files; `.env` is absent and not tracked. A dedicated secret scanner such as Gitleaks was not installed, so this is not a comprehensive secret-history audit.

## 7. Remaining blockers

No blocking failure remains for the local demo MVP based on the checks above. **Production use is blocked** until authentication/RBAC, production database migrations and operations, TLS/data-protection controls, abuse monitoring, and representative AI validation are implemented and reviewed.
