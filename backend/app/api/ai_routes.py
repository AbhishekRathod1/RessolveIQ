from fastapi import APIRouter

from app.schemas.ai import TicketAnalysisRequest, TicketAnalysisResponse
from app.schemas.knowledge import (
    ResolutionSuggestionRequest,
    ResolutionSuggestionResponse,
)
from app.services.ai_service import analyze_ticket
from app.services.knowledge_service import suggest_resolution

router = APIRouter()


@router.post("/analyze-ticket", response_model=TicketAnalysisResponse)
def analyze_ticket_endpoint(data: TicketAnalysisRequest) -> TicketAnalysisResponse:
    return analyze_ticket(data)


@router.post("/suggest-resolution", response_model=ResolutionSuggestionResponse)
def suggest_resolution_endpoint(
    request: ResolutionSuggestionRequest,
) -> ResolutionSuggestionResponse:
    return suggest_resolution(request)
