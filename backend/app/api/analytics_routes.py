from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.workflow import AnalyticsSummary
from app.services.analytics_service import get_analytics_summary

router = APIRouter()
DatabaseDependency: TypeAlias = Annotated[Session, Depends(get_db)]


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary_endpoint(database: DatabaseDependency) -> AnalyticsSummary:
    return get_analytics_summary(database)
