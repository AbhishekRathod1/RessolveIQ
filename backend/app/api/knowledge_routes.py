from fastapi import APIRouter

from app.schemas.knowledge import (
    KnowledgeCatalogResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import list_knowledge, search_knowledge

router = APIRouter()


@router.get("", response_model=KnowledgeCatalogResponse)
def list_knowledge_endpoint() -> KnowledgeCatalogResponse:
    return list_knowledge()


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge_endpoint(
    request: KnowledgeSearchRequest,
) -> KnowledgeSearchResponse:
    return search_knowledge(request.query, request.top_k)
