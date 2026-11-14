# ResolveIQ Demo Guide

This guide walks through the local app using fictional support records and a local classifier. Allow approximately 5–10 minutes for the walkthrough.

## Before the demo

Follow the [README setup](../README.md#setup-on-windows-powershell), including classifier training. In another terminal, optionally seed the five fictional tickets. Start the backend and frontend as described in the README.

Open:

- UI: <http://localhost:5173>
- API health: <http://127.0.0.1:8000/api/health>
- Interactive API docs: <http://127.0.0.1:8000/docs>

Seeding is idempotent. Do not enter real names, email addresses, passwords, customer content, or company secrets into this demo.

## Presenter flow

### 1. Show the real database-backed dashboard

Point out total/open/resolved/escalated counts, ticket distributions, recent tickets, and suggestion-review metrics. The demo does not ship mock metric values; the cards query the local SQLite database. With a fresh, unseeded database, zero counts and `N/A` metrics are expected.

### 2. Create and classify a fictional request

Navigate to **New ticket** and enter sample content such as:

- Title: `Fictional VPN profile connection failure`
- Description: `A demo workstation cannot connect to the approved sample VPN profile.`
- Requester: `Alex Example`, `alex@example.com`
- Business impact: `One fictional user is blocked from a training resource.`

Select **Analyze with AI**. Explain that category comes from a local TF-IDF/Logistic Regression classifier, confidence is the model's predicted-class probability (not calibrated), routing is deterministic, and priority uses explicit text rules. The result is only a preview. The user can keep or change the ticket's category and priority before saving.

Submit the ticket. Its detail view shows the persisted ID/number, initial status, current assignment, history event, and another non-binding triage view.

### 3. Find cited troubleshooting guidance

Choose **Generate suggestion**. Review the extracted steps, supporting document IDs/source references, and raw retrieval scores. Explain that cosine scores are not probabilities, retrieved text is untrusted, and no commands are automatically run. Every suggestion requires human verification. An unrelated issue should return insufficient evidence instead of invented steps.

### 4. Demonstrate human control

Use the suggestion controls to accept, edit, or reject a pending suggestion. An edited decision requires resolution text. Show that the decision appears in ticket history and that the ticket remains open; a review decision does not resolve a ticket.

Use the escalation panel to select a human support team. The ticket transitions to escalated, the team assignment changes, and the event is audited. If appropriate, move the ticket to another allowed state using the status controls.

### 5. Show analytics and knowledge search

Open Analytics and point out that metrics update from persisted records and show `N/A` when the denominator is zero. In Knowledge Base, search `VPN profile connection failure` and inspect ranked chunks, revision dates, document identifiers, and source references.

## API-only alternatives

Use Swagger UI at `/docs` to invoke ticket, AI, knowledge, suggestion, review, escalation, and analytics endpoints. Request and response details are summarized in [API_REFERENCE.md](API_REFERENCE.md).

## Demo caveats

- Demo users/reviewers are fixed fictional labels, not authenticated identities.
- All seed tickets and knowledge articles are fictional.
- Evaluation results are synthetic-data results and must not be presented as real-world accuracy.
- The application is a portfolio MVP, not a secure production service.
