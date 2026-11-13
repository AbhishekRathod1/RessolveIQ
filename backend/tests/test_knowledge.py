from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import knowledge_service
from app.services.knowledge_service import (
    MAX_CHUNK_CHARACTERS,
    chunk_content,
    load_documents,
)


@pytest.fixture(autouse=True)
def clear_knowledge_index() -> Generator[None, None, None]:
    knowledge_service.get_knowledge_index.cache_clear()
    yield
    knowledge_service.get_knowledge_index.cache_clear()


def test_knowledge_catalog_lists_fictional_articles(client: TestClient) -> None:
    response = client.get("/api/knowledge")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 20
    assert len(body["items"]) == 20
    assert all(
        item["document_id"]
        and item["title"]
        and item["category"]
        and item["revision_date"]
        and item["source_reference"]
        for item in body["items"]
    )


def test_relevant_retrieval_returns_vpn_sources_and_raw_scores(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/knowledge/search",
        json={"query": "Approved VPN profile authentication rejected connection", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "reliable_match"
    assert body["matches"]
    assert body["matches"][0]["document_id"] in {
        "KB-NETWORK-003",
        "KB-NETWORK-004",
    }
    assert body["matches"][0]["source_reference"].startswith(
        "ResolveIQ fictional support handbook"
    )
    assert 0 < body["matches"][0]["similarity_score"] <= 1
    assert body["matches"][0]["score_type"] == "raw_cosine_similarity"


def test_unrelated_query_has_explicit_no_reliable_match(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/knowledge/search",
        json={"query": "What is the best recipe for a lemon tart by the ocean?"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "no_reliable_match"
    assert response.json()["matches"] == []


def test_search_results_are_repeatable(client: TestClient) -> None:
    payload = {
        "query": "A printer queue is stuck and jobs remain pending",
        "top_k": 4,
    }

    first = client.post("/api/knowledge/search", json=payload).json()
    second = client.post("/api/knowledge/search", json=payload).json()

    assert first == second


def test_resolution_suggestion_is_extractive_and_cites_sources(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ai/suggest-resolution",
        json={
            "title": "Fictional office printer shows a paper feed error",
            "description": "A demo printer repeatedly jams during an approved print job.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_state"] == "suggested"
    assert body["issue_summary"].startswith("Fictional office printer")
    assert body["recommended_steps"]
    assert body["supporting_sources"]
    assert body["manual_review_required"] is True
    assert "human" in body["manual_review_reason"].lower()
    assert "not probabilities" in body["confidence_warning"]
    assert all(
        step["document_id"] and step["source_reference"]
        for step in body["recommended_steps"]
    )
    assert all(
        source["document_id"]
        and source["source_reference"]
        and source["retrieval_score"] > 0
        and source["score_type"] == "raw_cosine_similarity"
        for source in body["supporting_sources"]
    )


def test_privileged_suggestion_requires_authorized_human_review(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ai/suggest-resolution",
        json={
            "title": "Fictional password reset request",
            "description": "The requester cannot complete the sample account recovery flow.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["manual_review_required"] is True
    assert "authorized staff" in body["manual_review_reason"]
    assert body["recommended_steps"]


def test_unrelated_suggestion_uses_safe_insufficient_evidence_fallback(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ai/suggest-resolution",
        json={
            "title": "Fictional seaside pastry question",
            "description": "How long should a lemon tart bake for a weekend picnic?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_state"] == "insufficient_evidence"
    assert body["recommended_steps"] == []
    assert body["supporting_sources"] == []
    assert "No troubleshooting instructions were generated" in body["confidence_warning"]
    assert body["manual_review_required"] is True


def test_missing_documents_return_empty_catalog_and_insufficient_evidence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    empty_directory = tmp_path / "empty-kb"
    empty_directory.mkdir()
    monkeypatch.setattr(knowledge_service, "KNOWLEDGE_BASE_DIR", empty_directory)
    knowledge_service.get_knowledge_index.cache_clear()

    catalog = client.get("/api/knowledge")
    search = client.post(
        "/api/knowledge/search", json={"query": "VPN connection failure"}
    )
    suggestion = client.post(
        "/api/ai/suggest-resolution",
        json={"title": "VPN problem", "description": "Connection failure."},
    )

    assert catalog.json() == {"items": [], "total": 0}
    assert search.json()["state"] == "no_documents"
    assert search.json()["matches"] == []
    assert suggestion.json()["evidence_state"] == "insufficient_evidence"
    assert suggestion.json()["recommended_steps"] == []
    assert suggestion.json()["supporting_sources"] == []


def test_loader_supports_markdown_and_text_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "article.md"
    markdown.write_text(
        "---\n"
        "document_id: TEST-MD-001\n"
        "title: Fictional Markdown article\n"
        "category: Network\n"
        "revision_date: 2026-10-01\n"
        "source_reference: Fictional source / MD-001\n"
        "---\n"
        "# Article\n\n"
        "1. Check the managed network status.\n"
        "2. Do not share password=\"Super Secret Value\" or contact demo@example.com.\n",
        encoding="utf-8",
    )
    text = tmp_path / "article.txt"
    text.write_text(
        "Document ID: TEST-TXT-001\n"
        "Title: Fictional text article\n"
        "Category: Software\n"
        "Revision Date: 2026-10-02\n"
        "Source Reference: Fictional source / TXT-001\n"
        "Content:\n"
        "1. Use the approved application catalog.\n",
        encoding="utf-8",
    )

    documents = load_documents(tmp_path)

    assert [document.document_id for document in documents] == [
        "TEST-MD-001",
        "TEST-TXT-001",
    ]
    assert "Super Secret Value" not in documents[0].content
    assert "demo@example.com" not in documents[0].content
    assert "[REDACTED]" in documents[0].content
    assert documents[1].content.startswith("1. Use")


def test_long_document_chunking_is_deterministic_and_bounded() -> None:
    content = "\n\n".join(
        f"Section {number}. " + ("Fictional troubleshooting detail. " * 80)
        for number in range(5)
    )

    first = chunk_content(content)
    second = chunk_content(content)

    assert first == second
    assert len(first) > 1
    assert all(len(chunk) <= MAX_CHUNK_CHARACTERS for chunk in first)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": "VPN", "top_k": 0},
        {"query": "VPN", "unexpected": True},
    ],
)
def test_search_validates_request(client: TestClient, payload: dict[str, Any]) -> None:
    assert client.post("/api/knowledge/search", json=payload).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": " ", "description": "Network issue"},
        {"title": "VPN issue"},
        {"title": "VPN", "description": "Issue", "top_k": 6},
        {"title": "VPN", "description": "Issue", "actor": "pretend-admin"},
    ],
)
def test_suggestion_validates_request(
    client: TestClient, payload: dict[str, Any]
) -> None:
    assert client.post("/api/ai/suggest-resolution", json=payload).status_code == 422
