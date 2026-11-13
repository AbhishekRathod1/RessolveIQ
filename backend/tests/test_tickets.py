from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

TicketPayload = dict[str, Any]


@pytest.fixture
def create_ticket(client: TestClient) -> Callable[..., dict[str, Any]]:
    def create(**overrides: Any) -> dict[str, Any]:
        payload: TicketPayload = {
            "title": "Laptop cannot connect to office Wi-Fi",
            "description": "A fictional test requester cannot connect after a restart.",
            "category": "network",
            "priority": "high",
            "requester_name": "Alex Example",
            "requester_email": "alex@example.com",
        }
        payload.update(overrides)
        response = client.post("/api/tickets", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create


def test_create_ticket_uses_server_values_and_records_creation(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    ticket = create_ticket()

    assert ticket["id"] > 0
    assert ticket["ticket_number"].startswith("RIQ-")
    assert ticket["status"] == "open"
    assert ticket["assigned_team"] == "IT Support"
    assert ticket["created_at"]
    assert ticket["updated_at"]
    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    assert len(history) == 1
    assert history[0]["event_type"] == "created"
    assert history[0]["actor"] == "demo-user"


@pytest.mark.parametrize(
    "payload",
    [
        {"description": "Missing required fields"},
        {"title": "   "},
        {"title": "t" * 201},
        {"description": "d" * 10_001},
        {"requester_email": "not-an-email"},
        {"status": "resolved"},
        {"actor": "pretend-admin"},
        {"id": 99},
        {"ticket_number": "CLIENT-1"},
    ],
)
def test_create_ticket_rejects_invalid_input(
    client: TestClient, payload: TicketPayload
) -> None:
    response = client.post("/api/tickets", json=payload)
    assert response.status_code == 422


def test_list_tickets_supports_pagination_and_search(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    first = create_ticket(title="Printer setup request")
    create_ticket(title="VPN access request", category="access", priority="medium")
    create_ticket(title="Network disconnect report")

    page = client.get("/api/tickets", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 3
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert len(page["items"]) == 1

    result = client.get("/api/tickets", params={"search": first["ticket_number"]}).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == first["id"]
    assert client.get(
        "/api/tickets", params={"search": "Printer setup"}
    ).json()["total"] == 1
    assert client.get(
        "/api/tickets", params={"search": "fictional test requester"}
    ).json()["total"] == 3


def test_list_tickets_filters_by_status_category_and_priority(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    network = create_ticket(category="network", priority="high")
    create_ticket(category="access", priority="medium")
    client.patch(
        f"/api/tickets/{network['id']}/status",
        json={"status": "in_progress"},
    )

    result = client.get(
        "/api/tickets",
        params={"status": "in_progress", "category": "network", "priority": "high"},
    ).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == network["id"]


def test_status_update_records_event_and_resolution_timestamp(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    ticket = create_ticket()
    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["resolved_at"] is None

    resolved = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    status_events = [event for event in history if event["event_type"] == "status_changed"]
    assert [(event["previous_value"], event["new_value"]) for event in status_events] == [
        ("open", "in_progress"),
        ("in_progress", "resolved"),
    ]
    assert all(event["actor"] == "demo-user" for event in history)


def test_invalid_status_transition_is_rejected_without_audit_event(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    ticket = create_ticket()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "resolved"},
    )
    assert response.status_code == 409
    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    assert len(history) == 1


def test_ticket_field_update_is_audited(
    client: TestClient, create_ticket: Callable[..., dict[str, Any]]
) -> None:
    ticket = create_ticket()
    response = client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"title": "Updated fictional request"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated fictional request"

    history = client.get(f"/api/tickets/{ticket['id']}/history").json()
    assert history[-1]["event_type"] == "title_changed"
    assert history[-1]["previous_value"] == ticket["title"]
    assert history[-1]["new_value"] == "Updated fictional request"
    assert history[-1]["actor"] == "demo-user"


def test_missing_ticket_returns_404(client: TestClient) -> None:
    assert client.get("/api/tickets/999999").status_code == 404
    assert client.patch(
        "/api/tickets/999999/status", json={"status": "in_progress"}
    ).status_code == 404
    assert client.get("/api/tickets/999999/history").status_code == 404
