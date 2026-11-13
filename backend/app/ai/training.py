import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from app.ai.classifier import (
    CATEGORY_LABELS,
    MODEL_PATH,
    RANDOM_SEED,
    build_pipeline,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "sample_tickets"
    / "fictional_classification_tickets.csv"
)
REPORT_PATH = REPOSITORY_ROOT / "docs" / "AI_CLASSIFICATION_EVALUATION.json"
NEAR_DUPLICATE_THRESHOLD = 0.88
SPLIT_COUNT = 4
SPLIT_PROTOCOL = (
    "First fold from StratifiedGroupKFold(n_splits=4, shuffle=True, "
    "random_state=20261113); all variants of each scenario_group stay "
    "in one split."
)


def _normalized_text(title: str, description: str) -> str:
    return re.sub(r"\W+", " ", f"{title} {description}".casefold()).strip()


def _verify_split(
    dataset: pd.DataFrame, train_indices: Any, test_indices: Any
) -> float:
    train_groups = set(dataset.iloc[train_indices]["scenario_group"])
    test_groups = set(dataset.iloc[test_indices]["scenario_group"])
    if train_groups & test_groups:
        raise ValueError("A scenario group occurs in both training and test data")

    train_texts = [
        _normalized_text(row.title, row.description)
        for row in dataset.iloc[train_indices].itertuples()
    ]
    test_texts = [
        _normalized_text(row.title, row.description)
        for row in dataset.iloc[test_indices].itertuples()
    ]
    if set(train_texts) & set(test_texts):
        raise ValueError("Exact duplicate text found across the train/test split")

    max_similarity = 0.0
    for train_text in train_texts:
        for test_text in test_texts:
            similarity = SequenceMatcher(None, train_text, test_text).ratio()
            max_similarity = max(max_similarity, similarity)
            if similarity >= NEAR_DUPLICATE_THRESHOLD:
                raise ValueError(
                    "Near-duplicate text found across the train/test split "
                    f"(similarity {similarity:.3f} >= {NEAR_DUPLICATE_THRESHOLD})"
                )
    return max_similarity


def train_and_evaluate(
    dataset_path: Path = DATASET_PATH,
    model_path: Path = MODEL_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    dataset = pd.read_csv(dataset_path, keep_default_na=False)
    required_columns = {"scenario_group", "title", "description", "category"}
    if not required_columns.issubset(dataset.columns):
        raise ValueError(f"Dataset must contain columns: {sorted(required_columns)}")
    text_columns = dataset[["title", "description"]]
    has_empty_text = (
        text_columns.apply(lambda column: column.str.strip().eq(""))
        .to_numpy()
        .any()
    )
    if dataset.empty or has_empty_text:
        raise ValueError("Dataset must contain non-empty ticket titles and descriptions")
    unexpected_labels = set(dataset["category"]) - set(CATEGORY_LABELS)
    missing_labels = set(CATEGORY_LABELS) - set(dataset["category"])
    if unexpected_labels or missing_labels:
        raise ValueError(
            f"Dataset labels mismatch; unexpected={sorted(unexpected_labels)}, "
            f"missing={sorted(missing_labels)}"
        )

    texts = (dataset["title"] + "\n" + dataset["description"]).tolist()
    labels = dataset["category"].tolist()
    groups = dataset["scenario_group"].tolist()
    splitter = StratifiedGroupKFold(
        n_splits=SPLIT_COUNT,
        shuffle=True,
        random_state=RANDOM_SEED,
    )
    train_indices, test_indices = next(splitter.split(texts, labels, groups))
    max_similarity = _verify_split(dataset, train_indices, test_indices)

    model = build_pipeline()
    model.fit(
        [texts[index] for index in train_indices],
        [labels[index] for index in train_indices],
    )
    test_labels = [labels[index] for index in test_indices]
    predictions = model.predict([texts[index] for index in test_indices])
    support = {
        category: int(sum(label == category for label in test_labels))
        for category in CATEGORY_LABELS
    }
    matrix = confusion_matrix(test_labels, predictions, labels=CATEGORY_LABELS)

    report: dict[str, Any] = {
        "evaluation_type": "synthetic-data performance",
        "random_seed": RANDOM_SEED,
        "dataset_path": (
            dataset_path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
            if dataset_path.resolve().is_relative_to(REPOSITORY_ROOT)
            else dataset_path.name
        ),
        "dataset_rows": int(len(dataset)),
        "split_protocol": SPLIT_PROTOCOL,
        "train_rows": int(len(train_indices)),
        "test_rows": int(len(test_indices)),
        "near_duplicate_check": {
            "method": "Normalized-character SequenceMatcher ratio",
            "threshold": NEAR_DUPLICATE_THRESHOLD,
            "maximum_cross_split_similarity": round(max_similarity, 4),
            "exact_duplicates": 0,
            "near_duplicates_over_threshold": 0,
        },
        "accuracy": float(accuracy_score(test_labels, predictions)),
        "macro_f1": float(
            f1_score(
                test_labels,
                predictions,
                labels=CATEGORY_LABELS,
                average="macro",
                zero_division=0,
            )
        ),
        "labels": list(CATEGORY_LABELS),
        "confusion_matrix": matrix.tolist(),
        "per_class_support": support,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
