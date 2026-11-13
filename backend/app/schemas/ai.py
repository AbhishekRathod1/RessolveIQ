from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class TicketCategory(str, Enum):
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network"
    ACCOUNT_ACCESS = "Account & Access"
    SECURITY = "Security"
    OTHER = "Other"


AnalysisTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
AnalysisDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)
]
BusinessImpact = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000)
]


class TicketAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: AnalysisTitle
    description: AnalysisDescription
    business_impact: BusinessImpact | None = None


class TicketAnalysisResponse(BaseModel):
    predicted_category: TicketCategory
    category_confidence: float = Field(ge=0, le=1)
    recommended_team: str
    recommended_priority: Literal["low", "medium", "high", "critical"]
    explanation: str
    needs_manual_review: bool
