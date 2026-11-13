from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketSuggestion
from app.schemas.ticket import TicketPriority, TicketStatus
from app.schemas.workflow import AnalyticsSummary, SuggestionStatus


def _count_tickets(database: Session, ticket_status: TicketStatus | None = None) -> int:
    statement = select(func.count()).select_from(Ticket)
    if ticket_status is not None:
        statement = statement.where(Ticket.status == ticket_status.value)
    return int(database.scalar(statement) or 0)


def get_analytics_summary(database: Session) -> AnalyticsSummary:
    total_tickets = _count_tickets(database)
    open_tickets = _count_tickets(database, TicketStatus.OPEN)
    resolved_tickets = _count_tickets(database, TicketStatus.RESOLVED)

    tickets_by_category = {
        str(category): int(count)
        for category, count in database.execute(
            select(Ticket.category, func.count())
            .group_by(Ticket.category)
            .order_by(Ticket.category)
        )
    }

    tickets_by_priority = {priority.value: 0 for priority in TicketPriority}
    for priority, count in database.execute(
        select(Ticket.priority, func.count())
        .group_by(Ticket.priority)
        .order_by(Ticket.priority)
    ):
        tickets_by_priority[str(priority)] = int(count)

    tickets_by_status = {ticket_status.value: 0 for ticket_status in TicketStatus}
    for ticket_status, count in database.execute(
        select(Ticket.status, func.count())
        .group_by(Ticket.status)
        .order_by(Ticket.status)
    ):
        tickets_by_status[str(ticket_status)] = int(count)

    resolution_rows = database.execute(
        select(Ticket.created_at, Ticket.resolved_at).where(
            Ticket.status == TicketStatus.RESOLVED.value,
            Ticket.resolved_at.is_not(None),
        )
    )
    resolution_durations = [
        (resolved_at - created_at).total_seconds()
        for created_at, resolved_at in resolution_rows
        if created_at is not None
        and resolved_at is not None
        and resolved_at >= created_at
    ]
    average_resolution_time = (
        sum(resolution_durations) / len(resolution_durations)
        if resolution_durations
        else None
    )

    suggestion_counts = {
        suggestion_status.value: 0 for suggestion_status in SuggestionStatus
    }
    for suggestion_status, count in database.execute(
        select(TicketSuggestion.status, func.count())
        .group_by(TicketSuggestion.status)
        .order_by(TicketSuggestion.status)
    ):
        suggestion_counts[str(suggestion_status)] = int(count)
    accepted_count = suggestion_counts[SuggestionStatus.ACCEPTED.value]
    edited_count = suggestion_counts[SuggestionStatus.EDITED.value]
    rejected_count = suggestion_counts[SuggestionStatus.REJECTED.value]
    reviewed_count = accepted_count + edited_count + rejected_count
    acceptance_rate = (
        (accepted_count + edited_count) / reviewed_count if reviewed_count else None
    )

    return AnalyticsSummary(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets,
        tickets_by_category=tickets_by_category,
        tickets_by_priority=tickets_by_priority,
        tickets_by_status=tickets_by_status,
        average_resolution_time_seconds=average_resolution_time,
        average_resolution_time_ticket_count=len(resolution_durations),
        ai_suggestion_acceptance_rate=acceptance_rate,
        ai_suggestion_reviewed_count=reviewed_count,
        ai_suggestion_accepted_count=accepted_count,
        ai_suggestion_edited_count=edited_count,
        ai_suggestion_rejected_count=rejected_count,
    )
