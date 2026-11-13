from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.workflow import SuggestionReviewRequest, TicketSuggestionRead
from app.services.ticket_workflow_service import review_ticket_suggestion

router = APIRouter()
DatabaseDependency: TypeAlias = Annotated[Session, Depends(get_db)]


@router.post("/{suggestion_id}/review", response_model=TicketSuggestionRead)
def review_suggestion_endpoint(
    suggestion_id: int,
    request: SuggestionReviewRequest,
    database: DatabaseDependency,
) -> TicketSuggestionRead:
    return review_ticket_suggestion(database, suggestion_id, request)
