from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.ticket import (
    TicketCreate,
    TicketEventRead,
    TicketListResponse,
    TicketPriority,
    TicketRead,
    TicketSearch,
    TicketStatus,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.schemas.workflow import (
    EscalationRequest,
    SuggestionCreateRequest,
    TicketSuggestionRead,
)
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    get_ticket_history,
    list_tickets,
    update_ticket,
    update_ticket_status,
)
from app.services.ticket_workflow_service import (
    create_ticket_suggestion,
    escalate_ticket,
    list_ticket_suggestions,
)

router = APIRouter()
DatabaseDependency: TypeAlias = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket_endpoint(
    data: TicketCreate, database: DatabaseDependency
) -> TicketRead:
    return create_ticket(database, data)


@router.get("", response_model=TicketListResponse)
def list_tickets_endpoint(
    database: DatabaseDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    priority: TicketPriority | None = None,
    search: TicketSearch | None = None,
) -> TicketListResponse:
    items, total = list_tickets(
        database,
        limit=limit,
        offset=offset,
        ticket_status=ticket_status,
        category=category,
        priority=priority,
        search=search,
    )
    return TicketListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket_endpoint(ticket_id: int, database: DatabaseDependency) -> TicketRead:
    return get_ticket(database, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket_endpoint(
    ticket_id: int,
    data: TicketUpdate,
    database: DatabaseDependency,
) -> TicketRead:
    return update_ticket(database, ticket_id, data)


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_ticket_status_endpoint(
    ticket_id: int,
    data: TicketStatusUpdate,
    database: DatabaseDependency,
) -> TicketRead:
    return update_ticket_status(database, ticket_id, data.status)


@router.post(
    "/{ticket_id}/suggestions",
    response_model=TicketSuggestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_suggestion_endpoint(
    ticket_id: int,
    request: SuggestionCreateRequest,
    database: DatabaseDependency,
) -> TicketSuggestionRead:
    return create_ticket_suggestion(database, ticket_id, request.top_k)


@router.get(
    "/{ticket_id}/suggestions",
    response_model=list[TicketSuggestionRead],
)
def list_ticket_suggestions_endpoint(
    ticket_id: int,
    database: DatabaseDependency,
) -> list[TicketSuggestionRead]:
    return list_ticket_suggestions(database, ticket_id)


@router.post("/{ticket_id}/escalate", response_model=TicketRead)
def escalate_ticket_endpoint(
    ticket_id: int,
    request: EscalationRequest,
    database: DatabaseDependency,
) -> TicketRead:
    return escalate_ticket(database, ticket_id, request)


@router.get("/{ticket_id}/history", response_model=list[TicketEventRead])
def get_ticket_history_endpoint(
    ticket_id: int,
    database: DatabaseDependency,
) -> list[TicketEventRead]:
    return get_ticket_history(database, ticket_id)
