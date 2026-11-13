from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketEvent, utc_now
from app.schemas.ticket import (
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)

DEMO_ACTOR = "demo-user"

ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED},
    TicketStatus.IN_PROGRESS: {
        TicketStatus.OPEN,
        TicketStatus.PENDING_REVIEW,
        TicketStatus.RESOLVED,
        TicketStatus.ESCALATED,
    },
    TicketStatus.PENDING_REVIEW: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.ESCALATED,
    },
    TicketStatus.ESCALATED: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING_REVIEW,
        TicketStatus.RESOLVED,
    },
    TicketStatus.RESOLVED: set(),
}


def _ticket_or_404(database: Session, ticket_id: int) -> Ticket:
    ticket = database.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket


def create_ticket(database: Session, data: TicketCreate) -> Ticket:
    with database.begin():
        ticket = Ticket(
            ticket_number=f"RIQ-{uuid4().hex.upper()}",
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority.value,
            assigned_team=data.assigned_team,
            status=TicketStatus.OPEN.value,
            requester_name=data.requester_name,
            requester_email=str(data.requester_email),
        )
        ticket.events.append(
            TicketEvent(
                event_type="created",
                previous_value=None,
                new_value=TicketStatus.OPEN.value,
                actor=DEMO_ACTOR,
            )
        )
        database.add(ticket)
        database.flush()
    return ticket


def get_ticket(database: Session, ticket_id: int) -> Ticket:
    return _ticket_or_404(database, ticket_id)


def list_tickets(
    database: Session,
    *,
    limit: int,
    offset: int,
    ticket_status: TicketStatus | None = None,
    category: str | None = None,
    priority: TicketPriority | None = None,
    search: str | None = None,
) -> tuple[list[Ticket], int]:
    filters = []
    if ticket_status is not None:
        filters.append(Ticket.status == ticket_status.value)
    if category is not None:
        filters.append(Ticket.category == category)
    if priority is not None:
        filters.append(Ticket.priority == priority.value)
    if search is not None:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Ticket.ticket_number.ilike(pattern),
                Ticket.title.ilike(pattern),
                Ticket.description.ilike(pattern),
            )
        )

    total = database.scalar(select(func.count()).select_from(Ticket).where(*filters))
    tickets = database.scalars(
        select(Ticket)
        .where(*filters)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(tickets), total or 0


def update_ticket(
    database: Session, ticket_id: int, data: TicketUpdate
) -> Ticket:
    with database.begin():
        ticket = _ticket_or_404(database, ticket_id)
        changed = False
        changes = data.model_dump(exclude_unset=True)
        for field, new_value in changes.items():
            if isinstance(new_value, TicketPriority):
                new_value = new_value.value
            new_value = str(new_value)
            old_value = getattr(ticket, field)
            if old_value == new_value:
                continue
            changed = True
            setattr(ticket, field, new_value)
            ticket.events.append(
                TicketEvent(
                    event_type=f"{field}_changed",
                    previous_value=str(old_value),
                    new_value=new_value,
                    actor=DEMO_ACTOR,
                )
            )
        if changed:
            ticket.updated_at = utc_now()
        database.flush()
    return ticket


def update_ticket_status(
    database: Session, ticket_id: int, new_status: TicketStatus
) -> Ticket:
    with database.begin():
        ticket = _ticket_or_404(database, ticket_id)
        current_status = TicketStatus(ticket.status)
        if new_status == current_status:
            return ticket
        if new_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot transition ticket from '{current_status.value}' "
                    f"to '{new_status.value}'"
                ),
            )

        ticket.status = new_status.value
        ticket.updated_at = utc_now()
        if new_status is TicketStatus.RESOLVED:
            ticket.resolved_at = ticket.updated_at
        ticket.events.append(
            TicketEvent(
                event_type="status_changed",
                previous_value=current_status.value,
                new_value=new_status.value,
                actor=DEMO_ACTOR,
            )
        )
        database.flush()
    return ticket


def get_ticket_history(database: Session, ticket_id: int) -> list[TicketEvent]:
    _ticket_or_404(database, ticket_id)
    return list(
        database.scalars(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.timestamp, TicketEvent.id)
        ).all()
    )
