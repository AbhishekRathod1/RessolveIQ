from functools import lru_cache
from pathlib import Path
from typing import Final

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.schemas.ai import TicketCategory

RANDOM_SEED: Final = 20261113
MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "ticket_category_pipeline.joblib"
CATEGORY_LABELS: Final[tuple[str, ...]] = tuple(
    category.value for category in TicketCategory
)


def build_pipeline(random_state: int = RANDOM_SEED) -> Pipeline:
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            (
                "classifier",
                LogisticRegression(max_iter=1_000, random_state=random_state),
            ),
        ]
    )


@lru_cache(maxsize=1)
def load_classifier() -> Pipeline:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Ticket classification model not found at {MODEL_PATH}. "
            "Run `python scripts/train_ticket_classifier.py` first."
        )

    model = joblib.load(MODEL_PATH)
    if not isinstance(model, Pipeline):
        raise TypeError("Ticket classification artifact is not a scikit-learn Pipeline")
    if not {"tfidf", "classifier"}.issubset(model.named_steps):
        raise ValueError("Ticket classification pipeline is missing required steps")
    if set(model.classes_) != set(CATEGORY_LABELS):
        raise ValueError("Ticket classification model has unexpected category labels")
    return model
