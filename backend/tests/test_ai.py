from collections.abc import Generator
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from app.ai import classifier
from app.ai.training import (
    DATASET_PATH,
    NEAR_DUPLICATE_THRESHOLD,
    RANDOM_SEED,
    SPLIT_COUNT,
    _verify_split,
    train_and_evaluate,
)
from app.schemas.ai import TicketCategory
from app.services import ai_service
from app.services.ai_service import CATEGORY_TEAMS, recommend_priority
from scripts.generate_ticket_dataset import generate_rows, write_dataset


@pytest.fixture(scope="session")
def trained_model_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("ai-model")
    model_path = directory / "ticket_classifier.joblib"
    train_and_evaluate(
        model_path=model_path,
        report_path=directory / "evaluation.json",
    )
    return model_path


@pytest.fixture(autouse=True)
def use_test_model(
    trained_model_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setattr(classifier, "MODEL_PATH", trained_model_path)
    classifier.load_classifier.cache_clear()
    yield
    classifier.load_classifier.cache_clear()


def test_model_loading_reads_and_caches_pipeline() -> None:
    model = classifier.load_classifier()

    assert isinstance(model, Pipeline)
    assert list(model.named_steps) == ["tfidf", "classifier"]
    assert classifier.load_classifier() is model
    assert classifier.load_classifier.cache_info().misses == 1


def test_fictional_dataset_generation_is_reproducible(tmp_path: Path) -> None:
    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"

    assert generate_rows() == generate_rows()
    write_dataset(first_path)
    write_dataset(second_path)
    assert first_path.read_bytes() == second_path.read_bytes()


def test_grouped_split_has_no_exact_or_near_duplicate_leakage() -> None:
    dataset = pd.read_csv(DATASET_PATH, keep_default_na=False)
    texts = (dataset["title"] + "\n" + dataset["description"]).tolist()
    splitter = StratifiedGroupKFold(
        n_splits=SPLIT_COUNT,
        shuffle=True,
        random_state=RANDOM_SEED,
    )
    train_indices, test_indices = next(
        splitter.split(texts, dataset["category"], dataset["scenario_group"])
    )

    similarity = _verify_split(dataset, train_indices, test_indices)
    assert similarity < NEAR_DUPLICATE_THRESHOLD


def test_valid_prediction_uses_classifier_confidence(client: TestClient) -> None:
    request = {
        "title": "Laptop keyboard has unresponsive keys",
        "description": "A fictional physical equipment issue affects a sample workstation.",
        "business_impact": "One demo employee is blocked from working.",
    }
    response = client.post("/api/ai/analyze-ticket", json=request)

    assert response.status_code == 200
    result = response.json()
    assert result["predicted_category"] == "Hardware"
    assert 0.0 <= result["category_confidence"] <= 1.0
    model = classifier.load_classifier()
    text = f"{request['title']}\n{request['description']}"
    predicted_index = list(model.classes_).index(result["predicted_category"])
    expected_confidence = model.predict_proba([text])[0][predicted_index]
    assert result["category_confidence"] == pytest.approx(expected_confidence)
    assert result["recommended_team"] == "Desktop Support"
    assert result["recommended_priority"] == "high"
    assert "rules-based" in result["explanation"]


def test_classifier_predicts_every_dataset_category(client: TestClient) -> None:
    dataset = pd.read_csv(DATASET_PATH, keep_default_na=False)
    examples = dataset.groupby("category", sort=False).first()

    for category, row in examples.iterrows():
        response = client.post(
            "/api/ai/analyze-ticket",
            json={"title": row["title"], "description": row["description"]},
        )
        assert response.status_code == 200
        assert response.json()["predicted_category"] == category


def test_analysis_does_not_change_saved_human_ticket_fields(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/tickets",
        json={
            "title": "Fictional network support request",
            "description": "A demo user cannot connect to the sample network.",
            "category": "network",
            "priority": "high",
            "requester_name": "Alex Example",
            "requester_email": "alex@example.com",
        },
    ).json()

    response = client.post(
        "/api/ai/analyze-ticket",
        json={
            "title": created["title"],
            "description": created["description"],
            "business_impact": "One sample user is blocked from working.",
        },
    )
    saved = client.get(f"/api/tickets/{created['id']}").json()

    assert response.status_code == 200
    assert saved["category"] == "network"
    assert saved["priority"] == "high"


@pytest.mark.parametrize(
    ("category", "team"),
    [
        ("Hardware", "Desktop Support"),
        ("Software", "Application Support"),
        ("Network", "Network Support"),
        ("Account & Access", "Identity & Access Support"),
        ("Security", "Security Operations"),
        ("Other", "IT Support"),
    ],
)
def test_category_to_team_mapping(category: str, team: str) -> None:
    assert CATEGORY_TEAMS[TicketCategory(category)] == team


@pytest.mark.parametrize(
    ("title", "description", "impact", "expected"),
    [
        ("Minor display preference", "Cosmetic setting request", None, "low"),
        ("Cannot work", "One user cannot work", None, "high"),
        ("Service issue", "Normal request", "Company-wide production outage", "critical"),
        ("General question", "How to open the demo page", None, "low"),
        ("Routine request", "No impact details provided", None, "medium"),
    ],
)
def test_priority_rules(
    title: str, description: str, impact: str | None, expected: str
) -> None:
    priority, _ = recommend_priority(title, description, impact)
    assert priority == expected


class LowConfidenceClassifier:
    classes_ = np.array([category.value for category in TicketCategory])

    def predict(self, _: list[str]) -> np.ndarray:
        return np.array(["Other"])

    def predict_proba(self, _: list[str]) -> np.ndarray:
        return np.array([[0.10, 0.10, 0.10, 0.10, 0.10, 0.50]])


def test_low_confidence_prediction_requires_manual_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_service, "load_classifier", LowConfidenceClassifier)
    response = client.post(
        "/api/ai/analyze-ticket",
        json={"title": "Unclear request", "description": "A vague fictional issue."},
    )

    assert response.status_code == 200
    assert response.json()["category_confidence"] == 0.5
    assert response.json()["needs_manual_review"] is True
    assert "manual review" in response.json()["explanation"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "", "description": "Fictional details"},
        {"title": "Fictional issue"},
        {"title": 42, "description": "Fictional details"},
        {"title": "Title", "description": "   "},
        {"title": "Title", "description": "Details", "business_impact": " "},
        {"title": "Title", "description": "Details", "actor": "pretend-admin"},
    ],
)
def test_analysis_rejects_empty_or_malformed_input(
    client: TestClient, payload: dict[str, Any]
) -> None:
    response = client.post("/api/ai/analyze-ticket", json=payload)
    assert response.status_code == 422


def test_missing_model_returns_actionable_service_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(classifier, "MODEL_PATH", tmp_path / "missing.joblib")
    classifier.load_classifier.cache_clear()

    response = client.post(
        "/api/ai/analyze-ticket",
        json={"title": "Fictional issue", "description": "Sample details."},
    )

    assert response.status_code == 503
    assert "train_ticket_classifier.py" in response.json()["detail"]
