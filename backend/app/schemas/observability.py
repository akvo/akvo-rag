from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContainerHealth(BaseModel):
    service_name: str
    container_name: str
    status: str = Field(description="healthy, degraded, unhealthy, or unknown")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds")
    port_mapping: str = Field(default="", description="Container port mapping")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional telemetry info")


class DetailedSystemHealth(BaseModel):
    overall_status: str = Field(description="healthy, degraded, or unhealthy")
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    services: List[ContainerHealth]


class GateCheck(BaseModel):
    metric: str
    score: float
    target: str
    passed: bool
    info_only: Optional[bool] = False


class EvaluationMetricAverages(BaseModel):
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_similarity: Optional[float] = None
    answer_correctness: Optional[float] = None
    context_precision_without_reference: Optional[float] = None
    context_relevancy: Optional[float] = None


class EvaluationReportSummary(BaseModel):
    report_id: str
    timestamp: str
    kb_name: Optional[str] = "Kenya Drylands"
    dataset: Optional[str] = None
    total_queries: int = 0
    avg_latency_seconds: float = 0.0
    overall_passed: bool = True
    metric_averages: EvaluationMetricAverages = Field(default_factory=EvaluationMetricAverages)
    gate_checks: List[GateCheck] = Field(default_factory=list)


class QueryEvaluationResult(BaseModel):
    query: str
    answer: Optional[str] = None
    reference_answer: Optional[str] = None
    contexts: List[str] = Field(default_factory=list)
    response_time: Optional[float] = None
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_similarity: Optional[float] = None
    answer_correctness: Optional[float] = None


class EvaluationReportDetail(EvaluationReportSummary):
    results: List[QueryEvaluationResult] = Field(default_factory=list)
