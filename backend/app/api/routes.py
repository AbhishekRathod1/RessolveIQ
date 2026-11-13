from fastapi import APIRouter

from app.api.ai_routes import router as ai_router
from app.api.analytics_routes import router as analytics_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.suggestion_routes import router as suggestion_router
from app.api.ticket_routes import router as ticket_router

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(ticket_router, prefix="/tickets", tags=["tickets"])
router.include_router(ai_router, prefix="/ai", tags=["ai"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
router.include_router(suggestion_router, prefix="/suggestions", tags=["suggestions"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
