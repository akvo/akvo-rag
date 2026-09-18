import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.services.observability_service import ObservabilityService
from app.schemas.observability import DetailedSystemHealth, EvaluationReportSummary, EvaluationReportDetail


@pytest.fixture
def override_deps():
    mock_user = {"id": 1, "email": "admin@example.com", "is_superuser": True}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_user, mock_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_observability_service_probes():
    mock_db = MagicMock()
    service = ObservabilityService(db=mock_db)

    # Test PostgreSQL probe
    pg_health = await service.check_postgres()
    assert pg_health.service_name == "PostgreSQL Database"
    assert pg_health.status == "healthy"

    # Test Backend probe
    backend_health = await service.check_backend()
    assert backend_health.service_name == "Backend Core API"
    assert backend_health.status == "healthy"

    # Test System Health aggregation
    health = await service.get_system_health()
    assert isinstance(health, DetailedSystemHealth)
    assert len(health.services) == 7
    assert health.overall_status in ["healthy", "degraded", "unhealthy"]


def test_observability_service_evaluation_reports():
    service = ObservabilityService()
    reports = service.get_evaluation_reports(limit=5)
    assert isinstance(reports, list)
    assert len(reports) > 0

    first = reports[0]
    assert isinstance(first, EvaluationReportSummary)
    assert first.total_queries >= 0
    assert first.metric_averages.faithfulness is not None or first.metric_averages.context_precision is not None

    latest = service.get_latest_evaluation()
    assert isinstance(latest, EvaluationReportSummary)
    assert latest.report_id == first.report_id

    detail = service.get_evaluation_report_by_id(first.report_id)
    assert isinstance(detail, EvaluationReportDetail)
    assert detail.report_id == first.report_id


def test_detailed_system_health_endpoint(override_deps):
    client = TestClient(app)
    response = client.get("/api/v1/system/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "overall_status" in data
    assert "services" in data
    assert len(data["services"]) == 7


def test_evaluations_reports_endpoints(override_deps):
    client = TestClient(app)

    # Test listing reports
    response = client.get("/api/v1/system/evaluations/reports?limit=5")
    assert response.status_code == 200
    reports = response.json()
    assert isinstance(reports, list)
    assert len(reports) > 0

    first_id = reports[0]["report_id"]

    # Test latest report
    latest_resp = client.get("/api/v1/system/evaluations/latest")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["report_id"] == first_id

    # Test report detail
    detail_resp = client.get(f"/api/v1/system/evaluations/reports/{first_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["report_id"] == first_id
    assert "results" in detail_data


def test_evaluation_report_path_traversal_defense(override_deps):
    client = TestClient(app)
    # 1. Test via endpoint
    response = client.get("/api/v1/system/evaluations/reports/..passwd")
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data

    # 2. Test service directly with raw traversal
    service = ObservabilityService()
    report = service.get_evaluation_report_by_id("../../etc/passwd")
    assert report is not None
    assert report.report_id is not None
