from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.knowledge import ResolutionStep, SupportingSource


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class SuggestionDecision(str, Enum):
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class DemoReviewer(str, Enum):
    REVIEWER_1 = "demo-reviewer-1"
    REVIEWER_2 = "demo-reviewer-2"


class HumanSupportTeam(str, Enum):
    IT_SUPPORT = "IT Support"
    DESKTOP_SUPPORT = "Desktop Support"
    APPLICATION_SUPPORT = "Application Support"
    NETWORK_SUPPORT = "Network Support"
    IDENTITY_ACCESS_SUPPORT = "Identity & Access Support"
    SECURITY_OPERATIONS = "Security Operations"


EditedResolutionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)
]
EscalationReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000)
]


class SuggestionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(default=3, ge=1, le=5)


class SuggestionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SuggestionDecision
    reviewer: DemoReviewer
    edited_resolution: EditedResolutionText | None = None

    @model_validator(mode="after")
    def validate_decision_text(self) -> "SuggestionReviewRequest":
        if self.status is SuggestionDecision.EDITED and self.edited_resolution is None:
            raise ValueError("An edited resolution is required for an edited decision")
        if self.status is not SuggestionDecision.EDITED and self.edited_resolution is not None:
            raise ValueError("Edited resolution is only allowed with an edited decision")
        return self


class EscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: HumanSupportTeam
    reason: EscalationReason | None = None


class TicketSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    issue_summary: str
    suggested_resolution: str
    approved_resolution: str | None
    evidence_state: Literal["suggested", "insufficient_evidence"]
    recommended_steps: list[ResolutionStep]
    supporting_sources: list[SupportingSource]
    confidence_warning: str
    manual_review_required: bool
    manual_review_reason: str
    status: SuggestionStatus
    reviewer: DemoReviewer | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnalyticsSummary(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    tickets_by_category: dict[str, int]
    tickets_by_priority: dict[str, int]
    tickets_by_status: dict[str, int]
    average_resolution_time_seconds: float | None
    average_resolution_time_ticket_count: int
    ai_suggestion_acceptance_rate: float | None
    ai_suggestion_reviewed_count: int
    ai_suggestion_accepted_count: int
    ai_suggestion_edited_count: int
    ai_suggestion_rejected_count: int
