import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.ticket import Ticket
from app.schemas.ticket import TicketStatus


def create_ticket(
    client: TestClient,
    *,
    title: str = "Fictional office Wi-Fi cannot connect",
    description: str = "A demo workstation cannot connect to the sample network.",
    category: str = "network",
    priority: str = "medium",
) -> dict[str, Any]:
    response = client.post(
        "/api/tickets",
        json={
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "requester_name": "Alex Example",
            "requester_email": "alex@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_suggestion(client: TestClient, ticket_id: int) -> dict[str, Any]:
    response = client.post(
        f"/api/tickets/{ticket_id}/suggestions",
        json={"top_k": 3},
    )
    assert response.status_code == 201, response.text
    return response.json()


def review_suggestion(
    client: TestClient,
    suggestion_id: int,
    status: str,
    *,
    reviewer: str = "demo-reviewer-1",
    edited_resolution: str | None = None,
) -> Any:
    payload: dict[str, Any] = {"status": status, "reviewer": reviewer}
    if edited_resolution is not None:
        payload["edited_resolution"] = edited_resolution
    return client.post(
        f"/api/suggestions/{suggestion_id}/review",
        json=payload,
    )


def test_suggestion_is_persisted_pending_and_never_resolves_ticket(
    client: TestClient,
) -> None:
    ticket = create_ticket(client)
    suggestion = create_suggestion(client, ticket["id"])

    assert suggestion["status"] == "pending"
    assert suggestion["ticket_id"] == ticket["id"]
    assert suggestion["recommended_steps"]
    assert suggestion["supporting_sources"]
    assert suggestion["approved_resolution"] is None

    listed = client.get(f"/api/tickets/{ticket['id']}/suggestions")
    saved_ticket = client.get(f"/api/tickets/{ticket['id']}").json()
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [suggestion["id"]]
    assert saved_ticket["status"] == "open"
    assert saved_ticket["resolved_at"] is None

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    creation_event = next(event for event in history if event["event_type"] == "suggestion_created")
    assert json.loads(creation_event["new_value"]) == {
        "suggestion_id": suggestion["id"],
        "status": "pending",
        "evidence_state": "suggested",
    }
    assert creation_event["actor"] == "demo-ai"


def test_accepting_suggestion_is_audited_and_does_not_resolve_ticket(
    client: TestClient,
) -> None:
    ticket = create_ticket(client)
    suggestion = create_suggestion(client, ticket["id"])

    response = review_suggestion(client, suggestion["id"], "accepted")

    assert response.status_code == 200
    reviewed = response.json()
    assert reviewed["status"] == "accepted"
    assert reviewed["reviewer"] == "demo-reviewer-1"
    assert reviewed["approved_resolution"] == suggestion["suggested_resolution"]
    assert reviewed["reviewed_at"]
    saved_ticket = client.get(f"/api/tickets/{ticket['id']}").json()
    assert saved_ticket["status"] == "open"
    assert saved_ticket["resolved_at"] is None

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    audit = next(event for event in history if event["event_type"] == "suggestion_accepted")
    assert audit["actor"] == "demo-reviewer-1"
    assert json.loads(audit["previous_value"])["status"] == "pending"
    assert json.loads(audit["new_value"])["status"] == "accepted"
    assert json.loads(audit["new_value"])["approved_resolution"] == suggestion[
        "suggested_resolution"
    ]


def test_editing_suggestion_persists_human_resolution_and_audit(
    client: TestClient,
) -> None:
    ticket = create_ticket(client)
    suggestion = create_suggestion(client, ticket["id"])
    edited_text = "Ask the requester to verify the approved Wi-Fi profile, then contact network support."

    response = review_suggestion(
        client,
        suggestion["id"],
        "edited",
        reviewer="demo-reviewer-2",
        edited_resolution=edited_text,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "edited"
    assert response.json()["approved_resolution"] == edited_text
    assert response.json()["reviewer"] == "demo-reviewer-2"

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    audit = next(event for event in history if event["event_type"] == "suggestion_edited")
    assert audit["actor"] == "demo-reviewer-2"
    assert json.loads(audit["new_value"])["approved_resolution"] == edited_text


def test_rejection_is_audited_and_final(
    client: TestClient,
) -> None:
    ticket = create_ticket(client)
    suggestion = create_suggestion(client, ticket["id"])

    response = review_suggestion(
        client, suggestion["id"], "rejected", reviewer="demo-reviewer-2"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["approved_resolution"] is None
    history_before = client.get(f"/api/tickets/{ticket['id']}/history").json()
    rejection = next(event for event in history_before if event["event_type"] == "suggestion_rejected")
    assert rejection["actor"] == "demo-reviewer-2"
    assert json.loads(rejection["new_value"])["status"] == "rejected"

    repeated = review_suggestion(client, suggestion["id"], "accepted")
    assert repeated.status_code == 409
    history_after = client.get(f"/api/tickets/{ticket['id']}/history").json()
    assert len(history_after) == len(history_before)


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "pending", "reviewer": "demo-reviewer-1"},
        {"status": "edited", "reviewer": "demo-reviewer-1"},
        {
            "status": "accepted",
            "reviewer": "demo-reviewer-1",
            "edited_resolution": "Not an edit decision",
        },
        {"status": "accepted", "reviewer": "admin"},
        {"status": "accepted", "reviewer": "demo-reviewer-1", "actor": "admin"},
    ],
)
def test_review_rejects_invalid_decisions_and_non_demo_reviewers(
    client: TestClient, payload: dict[str, Any]
) -> None:
    ticket = create_ticket(client)
    suggestion = create_suggestion(client, ticket["id"])

    response = client.post(
        f"/api/suggestions/{suggestion['id']}/review",
        json=payload,
    )

    assert response.status_code == 422


def test_insufficient_evidence_suggestion_cannot_be_accepted(
    client: TestClient,
) -> None:
    ticket = create_ticket(
        client,
        title="Favorite picnic dessert",
        description="A fictional question about planning a seaside pastry menu.",
        category="other",
    )
    suggestion = create_suggestion(client, ticket["id"])

    assert suggestion["evidence_state"] == "insufficient_evidence"
    assert suggestion["suggested_resolution"] == ""
    response = review_suggestion(client, suggestion["id"], "accepted")

    assert response.status_code == 409
    saved_ticket = client.get(f"/api/tickets/{ticket['id']}").json()
    assert saved_ticket["status"] == "open"
    assert saved_ticket["resolved_at"] is None


def test_escalation_assigns_human_team_and_audits_changes(
    client: TestClient,
) -> None:
    ticket = create_ticket(client)
    response = client.post(
        f"/api/tickets/{ticket['id']}/escalate",
        json={
            "team": "Security Operations",
            "reason": "The requester reports a security incident for review.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "escalated"
    assert response.json()["assigned_team"] == "Security Operations"

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    event_types = {event["event_type"] for event in history}
    assert {"assigned_team_changed", "status_changed", "ticket_escalated"} <= event_types
    escalation_event = next(
        event for event in history if event["event_type"] == "ticket_escalated"
    )
    assert escalation_event["actor"] == "demo-user"
    assert json.loads(escalation_event["new_value"])["reason"].startswith(
        "The requester reports"
    )

    repeated = client.post(
        f"/api/tickets/{ticket['id']}/escalate",
        json={"team": "Network Support"},
    )
    assert repeated.status_code == 409


def test_resolved_ticket_cannot_be_escalated(client: TestClient) -> None:
    ticket = create_ticket(client)
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "in_progress"},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "resolved"},
    )

    response = client.post(
        f"/api/tickets/{ticket['id']}/escalate",
        json={"team": "Desktop Support"},
    )

    assert response.status_code == 409
    saved = client.get(f"/api/tickets/{ticket['id']}").json()
    assert saved["status"] == "resolved"


def test_escalation_rejects_invalid_team_or_actor(client: TestClient) -> None:
    ticket = create_ticket(client)
    response = client.post(
        f"/api/tickets/{ticket['id']}/escalate",
        json={"team": "AI Bot", "actor": "pretend-admin"},
    )
    assert response.status_code == 422
    assert client.get(f"/api/tickets/{ticket['id']}").json()["status"] == "open"


def test_analytics_uses_database_counts_and_documented_denominators(
    client: TestClient,
    test_session_factory: sessionmaker[Session],
) -> None:
    first = create_ticket(client, category="network", priority="high")
    second = create_ticket(client, category="software", priority="low")
    third = create_ticket(client, category="network", priority="medium")
    fourth = create_ticket(client, category="security", priority="urgent")

    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with test_session_factory.begin() as database:
        database.get(Ticket, first["id"]).created_at = base_time
        database.get(Ticket, second["id"]).created_at = base_time.replace(day=2)

    for ticket in (first, second):
        client.patch(
            f"/api/tickets/{ticket['id']}/status",
            json={"status": "in_progress"},
        )
        client.patch(
            f"/api/tickets/{ticket['id']}/status",
            json={"status": "resolved"},
        )
    client.patch(
        f"/api/tickets/{fourth['id']}/status",
        json={"status": "in_progress"},
    )

    for ticket, decision in (
        (first, "accepted"),
        (second, "edited"),
        (third, "rejected"),
        (fourth, None),
    ):
        suggestion = create_suggestion(client, ticket["id"])
        if decision == "edited":
            response = review_suggestion(
                client,
                suggestion["id"],
                decision,
                edited_resolution="Human-edited sample guidance.",
            )
            assert response.status_code == 200
        elif decision is not None:
            assert review_suggestion(
                client, suggestion["id"], decision
            ).status_code == 200

    with test_session_factory() as database:
        resolved_rows = database.execute(
            select(Ticket.created_at, Ticket.resolved_at).where(
                Ticket.status == TicketStatus.RESOLVED.value
            )
        ).all()
        expected_average = sum(
            (resolved_at - created_at).total_seconds()
            for created_at, resolved_at in resolved_rows
        ) / len(resolved_rows)

    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_tickets"] == 4
    assert summary["open_tickets"] == 1
    assert summary["resolved_tickets"] == 2
    assert summary["tickets_by_category"] == {
        "network": 2,
        "software": 1,
        "security": 1,
    }
    assert summary["tickets_by_priority"] == {
        "low": 1,
        "medium": 1,
        "high": 1,
        "urgent": 1,
    }
    assert summary["tickets_by_status"] == {
        "open": 1,
        "in_progress": 1,
        "pending_review": 0,
        "resolved": 2,
        "escalated": 0,
    }
    assert summary["average_resolution_time_ticket_count"] == 2
    assert summary["average_resolution_time_seconds"] == pytest.approx(
        expected_average
    )
    assert summary["ai_suggestion_reviewed_count"] == 3
    assert summary["ai_suggestion_accepted_count"] == 1
    assert summary["ai_suggestion_edited_count"] == 1
    assert summary["ai_suggestion_rejected_count"] == 1
    assert summary["ai_suggestion_acceptance_rate"] == pytest.approx(2 / 3)


def test_empty_analytics_returns_null_for_undefined_averages(
    client: TestClient,
) -> None:
    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_tickets"] == 0
    assert summary["average_resolution_time_seconds"] is None
    assert summary["average_resolution_time_ticket_count"] == 0
    assert summary["ai_suggestion_acceptance_rate"] is None
    assert summary["ai_suggestion_reviewed_count"] == 0
