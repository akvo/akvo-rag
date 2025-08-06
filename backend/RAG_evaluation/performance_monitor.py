"""
Performance monitoring utilities for RAG evaluation system.

This module provides tools to measure and track performance of various
operations during RAG evaluation to identify bottlenecks and measure
optimization improvements.
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional, ContextManager
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger("rag_evaluation")

@dataclass
class PerformanceMetric:
    """Represents a single performance measurement."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_start: Optional[float] = None
    memory_end: Optional[float] = None
    memory_delta: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time
        if self.memory_end and self.memory_start:
            self.memory_delta = self.memory_end - self.memory_start

@dataclass
class EvaluationPerformanceReport:
    """Complete performance report for an evaluation run."""
    total_queries: int
    total_duration: float
    avg_query_time: float
    rag_api_total_time: float
    ragas_eval_total_time: float
    peak_memory_mb: float
    openai_api_calls: int
    failed_operations: int
    metrics_breakdown: Dict[str, float]
    operation_timings: List[PerformanceMetric]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "total_queries": self.total_queries,
            "total_duration": self.total_duration,
            "avg_query_time": self.avg_query_time,
            "rag_api_total_time": self.rag_api_total_time,
            "ragas_eval_total_time": self.ragas_eval_total_time,
            "peak_memory_mb": self.peak_memory_mb,
            "openai_api_calls": self.openai_api_calls,
            "failed_operations": self.failed_operations,
            "metrics_breakdown": self.metrics_breakdown,
            "operation_count": len(self.operation_timings),
            "slowest_operations": sorted(
                [{"operation": op.operation, "duration": op.duration, "metadata": op.metadata} 
                 for op in self.operation_timings if op.duration], 
                key=lambda x: x["duration"], reverse=True
            )[:10]
        }

class PerformanceMonitor:
    """
    Performance monitoring system for RAG evaluation.
    
    Tracks timing, memory usage, and operation counts during evaluation
    to help identify bottlenecks and measure optimization improvements.
    """
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.active_operations: Dict[str, PerformanceMetric] = {}
        self.counters: Dict[str, int] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.peak_memory: float = 0
        self.memory_monitor_active = False
        self.memory_monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self):
        """Start the overall monitoring session."""
        self.start_time = time.time()
        self.peak_memory = self._get_memory_usage()
        self._start_memory_monitoring()
        logger.debug("Performance monitoring started")
        
    def stop_monitoring(self):
        """Stop the overall monitoring session."""
        self.end_time = time.time()
        self._stop_memory_monitoring()
        logger.debug("Performance monitoring stopped")
        
    def _start_memory_monitoring(self):
        """Start background thread to monitor peak memory usage."""
        if self.memory_monitor_active:
            return
            
        self.memory_monitor_active = True
        self.memory_monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self.memory_monitor_thread.start()
        
    def _stop_memory_monitoring(self):
        """Stop background memory monitoring."""
        self.memory_monitor_active = False
        if self.memory_monitor_thread and self.memory_monitor_thread.is_alive():
            self.memory_monitor_thread.join(timeout=1.0)
            
    def _monitor_memory(self):
        """Background thread function to track peak memory usage."""
        while self.memory_monitor_active:
            current_memory = self._get_memory_usage()
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
            time.sleep(0.5)  # Check every 500ms
            
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
            
    @contextmanager
    def measure_operation(self, operation: str, **metadata) -> ContextManager[PerformanceMetric]:
        """
        Context manager to measure the duration and memory usage of an operation.
        
        Args:
            operation: Name of the operation being measured
            **metadata: Additional metadata to store with the measurement
            
        Yields:
            PerformanceMetric object that will be populated with timing data
        """
        metric = PerformanceMetric(
            operation=operation,
            start_time=time.time(),
            memory_start=self._get_memory_usage(),
            metadata=metadata
        )
        
        # Store as active operation
        op_key = f"{operation}_{id(metric)}"
        self.active_operations[op_key] = metric
        
        try:
            yield metric
        finally:
            # Complete the measurement
            metric.end_time = time.time()
            metric.memory_end = self._get_memory_usage()
            metric.duration = metric.end_time - metric.start_time
            if metric.memory_end and metric.memory_start:
                metric.memory_delta = metric.memory_end - metric.memory_start
            
            # Remove from active and add to completed metrics
            self.active_operations.pop(op_key, None)
            self.metrics.append(metric)
            
            # Log slow operations
            if metric.duration and metric.duration > 10.0:  # Log operations > 10 seconds
                logger.info(f"Slow operation: {operation} took {metric.duration:.2f}s")
                
    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a named counter."""
        self.counters[counter_name] = self.counters.get(counter_name, 0) + amount
        
    def get_operation_stats(self, operation_pattern: str) -> Dict[str, Any]:
        """
        Get statistics for operations matching a pattern.
        
        Args:
            operation_pattern: String pattern to match operation names
            
        Returns:
            Dictionary with timing statistics
        """
        matching_ops = [m for m in self.metrics if operation_pattern in m.operation and m.duration]
        
        if not matching_ops:
            return {"count": 0, "total_time": 0, "avg_time": 0, "min_time": 0, "max_time": 0}
            
        durations = [op.duration for op in matching_ops]
        return {
            "count": len(matching_ops),
            "total_time": sum(durations),
            "avg_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations)
        }
        
    def generate_report(self, total_queries: int = 0) -> EvaluationPerformanceReport:
        """
        Generate a comprehensive performance report.
        
        Args:
            total_queries: Total number of queries processed
            
        Returns:
            EvaluationPerformanceReport with all performance data
        """
        if not self.start_time or not self.end_time:
            raise ValueError("Monitoring session not properly started/stopped")
            
        total_duration = self.end_time - self.start_time
        
        # Calculate timing breakdowns
        # Get all RAG-related operations (rag_api_single_query, rag_batch_processing, etc.)
        rag_operations = [m for m in self.metrics if any(term in m.operation for term in ["rag_api", "rag_batch", "rag_responses"]) and m.duration]
        rag_total_time = sum(op.duration for op in rag_operations)
        rag_api_stats = {"total_time": rag_total_time, "count": len(rag_operations)}
        
        # Get all RAGAS-related operations (ragas_eval_*, batch_eval_*)
        ragas_operations = [m for m in self.metrics if any(term in m.operation for term in ["ragas_eval", "batch_eval"]) and m.duration]
        ragas_total_time = sum(op.duration for op in ragas_operations)
        ragas_eval_stats = {"total_time": ragas_total_time, "count": len(ragas_operations)}
        
        # Build metrics breakdown
        metrics_breakdown = {}
        for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_relevancy", 
                           "answer_similarity", "answer_correctness", "context_recall"]:
            stats = self.get_operation_stats(metric_name)
            if stats["count"] > 0:
                metrics_breakdown[metric_name] = stats["total_time"]
        
        report = EvaluationPerformanceReport(
            total_queries=total_queries,
            total_duration=total_duration,
            avg_query_time=total_duration / max(total_queries, 1),
            rag_api_total_time=rag_api_stats["total_time"],
            ragas_eval_total_time=ragas_eval_stats["total_time"],
            peak_memory_mb=self.peak_memory,
            openai_api_calls=self.counters.get("openai_api_calls", 0),
            failed_operations=self.counters.get("failed_operations", 0),
            metrics_breakdown=metrics_breakdown,
            operation_timings=self.metrics.copy()
        )
        
        return report
        
    def log_summary(self, total_queries: int = 0):
        """Log a summary of performance metrics."""
        if not self.start_time or not self.end_time:
            logger.warning("Cannot log summary - monitoring not properly started/stopped")
            return
            
        report = self.generate_report(total_queries)
        
        logger.info(f"Performance: {report.total_duration:.1f}s total, {report.avg_query_time:.1f}s/query, "
                   f"RAG: {report.rag_api_total_time:.1f}s, RAGAS: {report.ragas_eval_total_time:.1f}s, "
                   f"Memory: {report.peak_memory_mb:.0f}MB")
        
    def save_report_to_file(self, filepath: str, total_queries: int = 0):
        """Save performance report to JSON file."""
        report = self.generate_report(total_queries)
        
        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_report": report.to_dict()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"Performance report saved to: {filepath}")

# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None

def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor

def reset_monitor():
    """Reset the global performance monitor."""
    global _global_monitor
    _global_monitor = PerformanceMonitor()