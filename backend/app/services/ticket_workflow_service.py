import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketEvent, TicketSuggestion, utc_now
from app.schemas.knowledge import ResolutionSuggestionRequest
from app.schemas.ticket import TicketStatus
from app.schemas.workflow import (
    EscalationRequest,
    SuggestionDecision,
    SuggestionReviewRequest,
)
from app.services.knowledge_service import suggest_resolution
from app.services.ticket_service import (
    ALLOWED_STATUS_TRANSITIONS,
    DEMO_ACTOR,
    get_ticket,
)

AI_DEMO_ACTOR = "demo-ai"


def create_ticket_suggestion(
    database: Session,
    ticket_id: int,
    top_k: int,
) -> TicketSuggestion:
    with database.begin():
        ticket = get_ticket(database, ticket_id)
        analysis = suggest_resolution(
            ResolutionSuggestionRequest(
                title=ticket.title,
                description=ticket.description,
                top_k=top_k,
            )
        )
        suggested_resolution = "\n".join(
            f"{number}. {step.text}"
            for number, step in enumerate(analysis.recommended_steps, start=1)
        )
        suggestion = TicketSuggestion(
            ticket_id=ticket.id,
            issue_summary=analysis.issue_summary,
            suggested_resolution=suggested_resolution,
            approved_resolution=None,
            evidence_state=analysis.evidence_state,
            recommended_steps=[
                step.model_dump(mode="json") for step in analysis.recommended_steps
            ],
            supporting_sources=[
                source.model_dump(mode="json")
                for source in analysis.supporting_sources
            ],
            confidence_warning=analysis.confidence_warning,
            manual_review_required=True,
            manual_review_reason=analysis.manual_review_reason,
            status="pending",
        )
        ticket.suggestions.append(suggestion)
        database.add(suggestion)
        database.flush()
        ticket.events.append(
            TicketEvent(
                event_type="suggestion_created",
                previous_value=None,
                new_value=json.dumps(
                    {
                        "suggestion_id": suggestion.id,
                        "status": suggestion.status,
                        "evidence_state": suggestion.evidence_state,
                    }
                ),
                actor=AI_DEMO_ACTOR,
            )
        )
        database.flush()
    return suggestion


def list_ticket_suggestions(
    database: Session, ticket_id: int
) -> list[TicketSuggestion]:
    get_ticket(database, ticket_id)
    return list(
        database.scalars(
            select(TicketSuggestion)
            .where(TicketSuggestion.ticket_id == ticket_id)
            .order_by(TicketSuggestion.created_at, TicketSuggestion.id)
        ).all()
    )


def review_ticket_suggestion(
    database: Session,
    suggestion_id: int,
    request: SuggestionReviewRequest,
) -> TicketSuggestion:
    with database.begin():
        suggestion = database.get(TicketSuggestion, suggestion_id)
        if suggestion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )
        if suggestion.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending suggestions can be reviewed",
            )
        if (
            request.status is SuggestionDecision.ACCEPTED
            and suggestion.evidence_state != "suggested"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Suggestions without reliable evidence cannot be accepted",
            )

        approved_resolution: str | None
        if request.status is SuggestionDecision.ACCEPTED:
            approved_resolution = suggestion.suggested_resolution
        elif request.status is SuggestionDecision.EDITED:
            approved_resolution = request.edited_resolution
        else:
            approved_resolution = None

        old_value = json.dumps(
            {
                "status": suggestion.status,
                "approved_resolution": suggestion.approved_resolution,
            }
        )
        suggestion.status = request.status.value
        suggestion.approved_resolution = approved_resolution
        suggestion.reviewer = request.reviewer.value
        reviewed_at = utc_now()
        suggestion.reviewed_at = reviewed_at
        suggestion.updated_at = reviewed_at
        new_value = json.dumps(
            {
                "status": suggestion.status,
                "approved_resolution": suggestion.approved_resolution,
                "reviewer": suggestion.reviewer,
            }
        )
        database.add(
            TicketEvent(
                ticket_id=suggestion.ticket_id,
                event_type=f"suggestion_{suggestion.status}",
                previous_value=old_value,
                new_value=new_value,
                actor=request.reviewer.value,
            )
        )
        database.flush()
    return suggestion


def escalate_ticket(
    database: Session,
    ticket_id: int,
    request: EscalationRequest,
) -> Ticket:
    with database.begin():
        ticket = get_ticket(database, ticket_id)
        current_status = TicketStatus(ticket.status)
        if TicketStatus.ESCALATED not in ALLOWED_STATUS_TRANSITIONS[current_status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ticket in '{current_status.value}' status cannot be escalated",
            )

        old_team = ticket.assigned_team
        new_team = request.team.value
        now = utc_now()
        ticket.assigned_team = new_team
        ticket.status = TicketStatus.ESCALATED.value
        ticket.updated_at = now
        if old_team != new_team:
            ticket.events.append(
                TicketEvent(
                    event_type="assigned_team_changed",
                    previous_value=old_team,
                    new_value=new_team,
                    actor=DEMO_ACTOR,
                )
            )
        ticket.events.append(
            TicketEvent(
                event_type="status_changed",
                previous_value=current_status.value,
                new_value=TicketStatus.ESCALATED.value,
                actor=DEMO_ACTOR,
            )
        )
        ticket.events.append(
            TicketEvent(
                event_type="ticket_escalated",
                previous_value=current_status.value,
                new_value=json.dumps(
                    {
                        "status": TicketStatus.ESCALATED.value,
                        "team": new_team,
                        "reason": request.reason,
                    }
                ),
                actor=DEMO_ACTOR,
            )
        )
        database.flush()
    return ticket
