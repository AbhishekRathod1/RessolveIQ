from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
DescriptionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)
]
CategoryText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
TeamText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
RequesterNameText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ShortText
    description: DescriptionText
    category: CategoryText
    priority: TicketPriority
    assigned_team: TeamText = "IT Support"
    requester_name: RequesterNameText
    requester_email: EmailStr = Field(max_length=254)


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ShortText | None = None
    description: DescriptionText | None = None
    category: CategoryText | None = None
    priority: TicketPriority | None = None
    assigned_team: TeamText | None = None
    requester_name: RequesterNameText | None = None
    requester_email: EmailStr | None = Field(default=None, max_length=254)

    @model_validator(mode="after")
    def validate_changes(self) -> "TicketUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Ticket fields cannot be null")
        return self


class TicketStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    title: str
    description: str
    category: str
    priority: TicketPriority
    assigned_team: str
    status: TicketStatus
    requester_name: str
    requester_email: EmailStr
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    event_type: str
    previous_value: str | None
    new_value: str | None
    actor: str
    timestamp: datetime


class TicketListResponse(BaseModel):
    items: list[TicketRead]
    total: int
    limit: int
    offset: int


TicketSearch = Annotated[str, Field(min_length=1, max_length=200)]
