"""
Benchmark suite for RAG evaluation performance testing.

This module provides standardized performance tests to measure baseline
performance and track improvements from optimizations.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from performance_monitor import PerformanceMonitor, get_monitor, reset_monitor
from headless_evaluation import run_headless_evaluation, parse_csv_queries
import pandas as pd

logger = logging.getLogger("rag_evaluation")

class BenchmarkSuite:
    """
    Performance benchmark suite for RAG evaluation system.
    
    Provides standardized tests to measure performance across different
    scenarios and track improvements from optimizations.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 username: str = "admin@example.com", 
                 password: str = "password",
                 kb_name: str = "Living Income Benchmark Knowledge Base"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.kb_name = kb_name
        self.results: List[Dict[str, Any]] = []
        
    def create_test_queries(self, count: int) -> List[str]:
        """Create a list of test queries for benchmarking."""
        base_queries = [
            "What is the living income benchmark?",
            "How is the living income benchmark calculated?", 
            "What factors influence the living income benchmark?",
            "How does the living income benchmark differ from minimum wage?",
            "What is the purpose of establishing a living income benchmark?",
            "Which countries use living income benchmarks?",
            "How often are living income benchmarks updated?",
            "What are the main components of a living income calculation?",
            "How do living costs affect the living income benchmark?",
            "What role do living income benchmarks play in poverty reduction?"
        ]
        
        # Repeat and extend as needed
        queries = []
        for i in range(count):
            base_query = base_queries[i % len(base_queries)]
            if i >= len(base_queries):
                # Add variation to avoid exact duplicates
                queries.append(f"{base_query} (variation {i // len(base_queries) + 1})")
            else:
                queries.append(base_query)
                
        return queries[:count]
        
    def create_test_csv(self, queries: List[str], include_references: bool = False) -> str:
        """Create a temporary CSV file with test queries."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            if include_references:
                f.write("prompt,reference_answer\n")
                for query in queries:
                    ref_answer = f"This is a reference answer for: {query}"
                    f.write(f'"{query}","{ref_answer}"\n')
            else:
                f.write("prompt\n")
                for query in queries:
                    f.write(f'"{query}"\n')
            return f.name
            
    async def run_benchmark_scenario(self, 
                                   scenario_name: str,
                                   query_count: int,
                                   metrics_mode: str = "basic",
                                   include_references: bool = False,
                                   iterations: int = 1) -> Dict[str, Any]:
        """
        Run a single benchmark scenario.
        
        Args:
            scenario_name: Name of the benchmark scenario
            query_count: Number of queries to process
            metrics_mode: Metrics mode (basic, full, reference-only)
            include_references: Whether to include reference answers
            iterations: Number of times to run the scenario
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"🏃 Running benchmark: {scenario_name}")
        logger.info(f"   Queries: {query_count}, Mode: {metrics_mode}, References: {include_references}")
        
        scenario_results = []
        
        for iteration in range(iterations):
            logger.info(f"   Iteration {iteration + 1}/{iterations}")
            
            # Reset monitor for this iteration
            reset_monitor()
            monitor = get_monitor()
            monitor.start_monitoring()
            
            try:
                # Create test data
                queries = self.create_test_queries(query_count)
                csv_path = self.create_test_csv(queries, include_references)
                
                try:
                    # Parse CSV queries and references
                    df = pd.read_csv(csv_path)
                    queries, reference_answers, error_msg = parse_csv_queries(df)
                    if error_msg:
                        raise ValueError(f"CSV parsing error: {error_msg}")
                    
                    # Run evaluation
                    with monitor.measure_operation("full_evaluation", 
                                                 scenario=scenario_name, 
                                                 iteration=iteration + 1):
                        result = run_headless_evaluation(
                            kb_name=self.kb_name,
                            queries=queries,
                            reference_answers=reference_answers,
                            openai_model="gpt-4o",
                            rag_api_url=self.base_url,
                            username=self.username,
                            password=self.password,
                            metrics_mode=metrics_mode
                        )
                        success = "error" not in result
                        
                    if not success:
                        logger.warning(f"   Iteration {iteration + 1} failed")
                        monitor.increment_counter("failed_iterations")
                        
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(csv_path)
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.error(f"   Iteration {iteration + 1} error: {str(e)}")
                monitor.increment_counter("failed_iterations")
                
            finally:
                monitor.stop_monitoring()
                
                # Generate report for this iteration
                report = monitor.generate_report(query_count)
                iteration_result = {
                    "iteration": iteration + 1,
                    "success": success if 'success' in locals() else False,
                    "performance": report.to_dict()
                }
                scenario_results.append(iteration_result)
                
        # Calculate aggregate results
        successful_iterations = [r for r in scenario_results if r["success"]]
        
        if successful_iterations:
            durations = [r["performance"]["total_duration"] for r in successful_iterations]
            avg_query_times = [r["performance"]["avg_query_time"] for r in successful_iterations]
            memory_peaks = [r["performance"]["peak_memory_mb"] for r in successful_iterations]
            
            aggregate_results = {
                "scenario_name": scenario_name,
                "query_count": query_count,
                "metrics_mode": metrics_mode,
                "include_references": include_references,
                "iterations": iterations,
                "successful_iterations": len(successful_iterations),
                "avg_total_duration": sum(durations) / len(durations),
                "min_total_duration": min(durations),
                "max_total_duration": max(durations),
                "avg_query_time": sum(avg_query_times) / len(avg_query_times),
                "avg_peak_memory": sum(memory_peaks) / len(memory_peaks),
                "detailed_results": scenario_results
            }
        else:
            aggregate_results = {
                "scenario_name": scenario_name,
                "query_count": query_count,
                "metrics_mode": metrics_mode,
                "include_references": include_references,
                "iterations": iterations,
                "successful_iterations": 0,
                "error": "All iterations failed",
                "detailed_results": scenario_results
            }
            
        self.results.append(aggregate_results)
        
        if successful_iterations:
            logger.info(f"✅ {scenario_name} completed successfully")
            logger.info(f"   Avg Duration: {aggregate_results['avg_total_duration']:.2f}s")
            logger.info(f"   Avg Query Time: {aggregate_results['avg_query_time']:.2f}s")
            logger.info(f"   Peak Memory: {aggregate_results['avg_peak_memory']:.1f} MB")
        else:
            logger.error(f"❌ {scenario_name} failed completely")
            
        return aggregate_results
        
    async def run_full_benchmark_suite(self, iterations: int = 1) -> Dict[str, Any]:
        """
        Run the complete benchmark suite with all scenarios.
        
        Args:
            iterations: Number of iterations per scenario
            
        Returns:
            Complete benchmark results
        """
        logger.info("🚀 Starting full benchmark suite")
        start_time = time.time()
        
        # Define benchmark scenarios
        scenarios = [
            # Basic scenarios (no references needed)
            {
                "name": "Small_Basic_NoRef",  
                "query_count": 2,
                "metrics_mode": "basic",
                "include_references": False
            },
            {
                "name": "Medium_Basic_NoRef",
                "query_count": 5, 
                "metrics_mode": "basic",
                "include_references": False
            },
            {
                "name": "Large_Basic_NoRef",
                "query_count": 10,
                "metrics_mode": "basic", 
                "include_references": False
            },
            
            # Reference-based scenarios  
            {
                "name": "Small_Full_WithRef",
                "query_count": 2,
                "metrics_mode": "full",
                "include_references": True
            },
            {
                "name": "Medium_RefOnly_WithRef", 
                "query_count": 5,
                "metrics_mode": "reference-only",
                "include_references": True
            }
        ]
        
        # Run each scenario
        for scenario in scenarios:
            try:
                await self.run_benchmark_scenario(
                    scenario_name=scenario["name"],
                    query_count=scenario["query_count"], 
                    metrics_mode=scenario["metrics_mode"],
                    include_references=scenario["include_references"],
                    iterations=iterations
                )
            except Exception as e:
                logger.error(f"❌ Scenario {scenario['name']} failed: {str(e)}")
                
        total_time = time.time() - start_time
        
        # Generate summary report
        summary = {
            "benchmark_suite_version": "1.0",
            "timestamp": time.time(),
            "total_benchmark_time": total_time,
            "total_scenarios": len(scenarios),
            "completed_scenarios": len(self.results),
            "configuration": {
                "base_url": self.base_url,
                "username": self.username,
                "kb_name": self.kb_name,
                "iterations_per_scenario": iterations
            },
            "scenarios": self.results
        }
        
        logger.info("🎯 Benchmark suite completed")
        logger.info(f"   Total Time: {total_time:.2f}s")
        logger.info(f"   Scenarios: {len(self.results)}/{len(scenarios)} completed")
        
        return summary
        
    def save_results(self, filepath: str):
        """Save benchmark results to JSON file."""
        if not self.results:
            logger.warning("No benchmark results to save")
            return
            
        summary = {
            "benchmark_results": self.results,
            "timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"💾 Benchmark results saved to: {filepath}")
        
    def print_summary(self):
        """Print a summary of benchmark results."""
        if not self.results:
            logger.warning("No benchmark results to summarize")
            return
            
        logger.info("=" * 60)
        logger.info("📊 BENCHMARK RESULTS SUMMARY")
        logger.info("=" * 60)
        
        for result in self.results:
            if result["successful_iterations"] > 0:
                logger.info(f"{result['scenario_name']}:")
                logger.info(f"  Queries: {result['query_count']}, Mode: {result['metrics_mode']}")
                logger.info(f"  Avg Duration: {result['avg_total_duration']:.2f}s")
                logger.info(f"  Avg Query Time: {result['avg_query_time']:.2f}s")
                logger.info(f"  Peak Memory: {result['avg_peak_memory']:.1f} MB")
                logger.info(f"  Success Rate: {result['successful_iterations']}/{result['iterations']}")
            else:
                logger.info(f"{result['scenario_name']}: ❌ FAILED")
            logger.info("")
            
        logger.info("=" * 60)

async def main():
    """Main function to run benchmarks from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Evaluation Performance Benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000", help="RAG API base URL")
    parser.add_argument("--username", default="admin@example.com", help="Username for authentication")
    parser.add_argument("--password", default="password", help="Password for authentication") 
    parser.add_argument("--kb-name", default="Living Income Benchmark Knowledge Base", help="Knowledge base name")
    parser.add_argument("--iterations", type=int, default=1, help="Iterations per scenario")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--scenario", help="Run single scenario only")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create benchmark suite
    suite = BenchmarkSuite(
        base_url=args.base_url,
        username=args.username, 
        password=args.password,
        kb_name=args.kb_name
    )
    
    if args.scenario:
        # Run single scenario
        logger.info(f"Running single scenario: {args.scenario}")
        # Implementation for single scenario would go here
    else:
        # Run full suite
        results = await suite.run_full_benchmark_suite(iterations=args.iterations)
        
    # Print summary
    suite.print_summary()
    
    # Save results if requested
    if args.output:
        suite.save_results(args.output)
        
if __name__ == "__main__":
    asyncio.run(main())