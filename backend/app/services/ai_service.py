from typing import Literal

from fastapi import HTTPException, status
from sklearn.pipeline import Pipeline

from app.ai.classifier import load_classifier
from app.schemas.ai import TicketAnalysisRequest, TicketAnalysisResponse, TicketCategory

CATEGORY_TEAMS: dict[TicketCategory, str] = {
    TicketCategory.HARDWARE: "Desktop Support",
    TicketCategory.SOFTWARE: "Application Support",
    TicketCategory.NETWORK: "Network Support",
    TicketCategory.ACCOUNT_ACCESS: "Identity & Access Support",
    TicketCategory.SECURITY: "Security Operations",
    TicketCategory.OTHER: "IT Support",
}

CRITICAL_CUES = (
    "ransomware",
    "confirmed breach",
    "active compromise",
    "organization-wide outage",
    "company-wide outage",
    "production outage",
    "all users cannot access",
    "all users are unable",
    "service unavailable for everyone",
)
HIGH_CUES = (
    "multiple users",
    "department affected",
    "blocked from working",
    "cannot work",
    "complete outage",
    "data loss",
    "security incident",
    "urgent",
    "time-sensitive",
    "business critical",
)
LOW_CUES = (
    "minor",
    "cosmetic",
    "intermittent",
    "non-urgent",
    "how do i",
    "how to",
    "question",
    "when convenient",
    "workaround available",
)
MANUAL_REVIEW_THRESHOLD = 0.55
RecommendedPriority = Literal["low", "medium", "high", "critical"]


def recommend_priority(
    title: str, description: str, business_impact: str | None
) -> tuple[RecommendedPriority, str]:
    text = " ".join((title, description, business_impact or "")).casefold()
    for cue in CRITICAL_CUES:
        if cue in text:
            return "critical", f"matched critical-impact cue: '{cue}'"
    for cue in HIGH_CUES:
        if cue in text:
            return "high", f"matched high-impact cue: '{cue}'"
    for cue in LOW_CUES:
        if cue in text:
            return "low", f"matched low-impact cue: '{cue}'"
    return "medium", "no explicit critical, high, or low impact cue; defaulted to medium"

def analyze_ticket(data: TicketAnalysisRequest) -> TicketAnalysisResponse:
    try:
        model: Pipeline = load_classifier()
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Ticket classification model is unavailable. "
                "Run `python scripts/train_ticket_classifier.py` first."
            ),
        ) from error

    text = f"{data.title}\n{data.description}"
    predicted_category = str(model.predict([text])[0])
    class_labels = list(model.classes_)
    predicted_index = class_labels.index(predicted_category)
    confidence = float(model.predict_proba([text])[0][predicted_index])
    category = TicketCategory(predicted_category)
    priority, priority_reason = recommend_priority(
        data.title, data.description, data.business_impact
    )
    needs_manual_review = confidence < MANUAL_REVIEW_THRESHOLD

    explanation = (
        f"TF-IDF and logistic regression classified the title and description as "
        f"{category.value} (classifier confidence {confidence:.3f}). "
        f"Priority '{priority}' is a rules-based recommendation: {priority_reason}. "
        "Business impact is used only by the priority rules. This recommendation "
        "does not change any saved ticket fields."
    )
    if needs_manual_review:
        explanation += (
            " Confidence is below the 0.55 review threshold; "
            "manual review is recommended."
        )

    return TicketAnalysisResponse(
        predicted_category=category,
        category_confidence=confidence,
        recommended_team=CATEGORY_TEAMS[category],
        recommended_priority=priority,
        explanation=explanation,
        needs_manual_review=needs_manual_review,
    )
