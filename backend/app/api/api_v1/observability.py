from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.schemas.observability import (
    DetailedSystemHealth,
    EvaluationReportDetail,
    EvaluationReportSummary,
)
from app.services.observability_service import ObservabilityService

router = APIRouter()


@router.get("/health/detailed", response_model=DetailedSystemHealth)
async def get_detailed_system_health(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve real-time telemetry and health diagnostics for all 7 core containers:
    PostgreSQL, Redis, ChromaDB, MinIO, Query Worker, Ingestion Worker, and Backend API.
    """
    service = ObservabilityService(db=db)
    return await service.get_system_health()


@router.get("/evaluations/reports", response_model=List[EvaluationReportSummary])
def get_evaluation_reports(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve past Ragas golden-set evaluation reports and benchmark summaries.
    """
    service = ObservabilityService()
    return service.get_evaluation_reports(limit=limit)


@router.get("/evaluations/latest", response_model=EvaluationReportSummary)
def get_latest_evaluation(
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve the most recent Ragas golden evaluation report.
    """
    service = ObservabilityService()
    return service.get_latest_evaluation()


@router.get("/evaluations/reports/{report_id}", response_model=EvaluationReportDetail)
def get_evaluation_report_detail(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve detailed query results, ground truths, and metrics for a specific evaluation run.
    """
    service = ObservabilityService()
    report = service.get_evaluation_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return report
