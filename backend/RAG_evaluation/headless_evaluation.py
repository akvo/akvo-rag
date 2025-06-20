"""
Core RAG Evaluation Logic

This module provides the core functionality for evaluating RAG systems,
independent of any user interface.
"""

import asyncio
import logging
import os
import time
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_evaluation")

# Import our chat utility
from chat_util import RagChatUtil

# Default test questions
DEFAULT_TEST_QUERIES = [
    "What is the living income benchmark?",
    "How is the living income benchmark calculated?",
    "What factors influence the living income benchmark?",
    "How does the living income benchmark differ from minimum wage?",
    "What is the purpose of establishing a living income benchmark?"
]

def setup_ragas() -> Tuple[bool, List, List[str], Optional[str]]:
    """Set up RAGAS for evaluation and determine available metrics.
    
    Returns:
        Tuple of (ragas_available, metrics, metric_names, error_message)
    """
    try:
        # Check if ragas is installed
        import importlib.util
        ragas_spec = importlib.util.find_spec("ragas")
        if ragas_spec is None:
            return False, [], [], "RAGAS package is not installed. Install with 'pip install ragas'"

        # Import RAGAS
        import ragas

        # Log RAGAS version
        ragas_version = ragas.__version__
        logger.info(f"RAGAS version: {ragas_version}")

        # Import metrics using new v0.2 API
        metrics = []
        metric_names = []

        # Import metrics that work without reference data
        try:
            from ragas.metrics import Faithfulness
            metrics.append(Faithfulness)
            metric_names.append("faithfulness")
        except ImportError:
            logger.info("Faithfulness metric not available")

        try:
            from ragas.metrics import AnswerRelevancy
            metrics.append(AnswerRelevancy)
            metric_names.append("answer_relevancy")
        except ImportError:
            logger.info("AnswerRelevancy metric not available")

        # Use LLMContextPrecisionWithoutReference instead of standard ContextPrecision
        try:
            from ragas.metrics import LLMContextPrecisionWithoutReference
            metrics.append(LLMContextPrecisionWithoutReference)
            metric_names.append("context_precision_without_reference")
        except ImportError:
            logger.info("LLMContextPrecisionWithoutReference metric not available")

        try:
            from ragas.metrics import ContextRelevancy
            metrics.append(ContextRelevancy)
            metric_names.append("context_relevancy")
        except ImportError:
            logger.info("ContextRelevancy metric not available")

        return True, metrics, metric_names, None
    except Exception as e:
        logger.error(f"Error setting up RAGAS: {str(e)}")
        return False, [], [], f"Error setting up RAGAS: {str(e)}"

async def generate_rag_responses(
    queries: List[str], 
    kb_name: str, 
    rag_api_url: str = "http://localhost:8000", 
    username: str = "admin@example.com", 
    password: str = "password",
    progress_callback=None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate RAG responses for a list of queries
    
    Args:
        queries: List of query strings
        kb_name: Name of the knowledge base to use
        rag_api_url: URL of the RAG API
        username: Username for API authentication
        password: Password for API authentication
        progress_callback: Optional callback function for progress updates
        
    Returns:
        Tuple of (list of response dictionaries, logs)
    """
    # Create chat utility
    chat_util = RagChatUtil(
        base_url=rag_api_url,
        username=username,
        password=password
    )

    # Enable instrumentation
    chat_util.enable_instrumentation()

    # Process each query
    results = []
    all_logs = []
    for i, query in enumerate(queries):
        logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")

        # Generate RAG response
        start_time = time.time()
        rag_result = await chat_util.generate_rag_response(query, kb_name)
        end_time = time.time()

        # Collect logs
        logs = chat_util.get_logs()
        all_logs.extend(logs)

        # Format response
        if "error" not in rag_result:
            contexts = [item["page_content"] for item in rag_result.get("contexts", [])]
            results.append({
                "query": query,
                "ground_truths": [""],  # No ground truth for now
                "answer": rag_result["response"],
                "response": rag_result["response"],  # For backwards compatibility
                "contexts": contexts,
                "response_time": end_time - start_time,
                "kb_id": rag_result.get("kb_id"),
                "chat_id": rag_result.get("chat_id"),
            })
        else:
            # Store error result
            results.append({
                "query": query,
                "response": rag_result.get("response", ""),
                "answer": rag_result.get("response", ""),  # For RAGAS compatibility
                "contexts": [],
                "ground_truths": [""],  # Still need this for RAGAS compatibility
                "error": rag_result.get("error", "Unknown error"),
                "response_time": end_time - start_time
            })

        # Update progress if callback is provided
        if progress_callback:
            progress_callback(i, len(queries), query, results[-1])

    return results, all_logs

def run_ragas_evaluation(
    evaluation_data: List[Dict[str, Any]], 
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Run RAGAS evaluation on the given data
    
    Args:
        evaluation_data: List of dictionaries with query, answer, contexts, ground_truths
        openai_model: OpenAI model to use for evaluation
        openai_api_key: OpenAI API key (will use env var if None)
        
    Returns:
        Dictionary with evaluation results or error
    """
    # Check for OpenAI API key
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."}
    
    # Setup RAGAS
    ragas_available, metric_classes, metric_names, error_message = setup_ragas()
    if not ragas_available:
        return {"error": error_message}
    
    logger.info(f"Using metrics: {', '.join(metric_names)}")
    
    try:
        # Convert data to DataFrame
        eval_df = pd.DataFrame(evaluation_data)
        
        # Rename columns to match expected format
        if 'query' in eval_df.columns:
            eval_df = eval_df.rename(columns={'query': 'user_input'})
        if 'answer' in eval_df.columns:
            eval_df = eval_df.rename(columns={'answer': 'response'})
        if 'contexts' in eval_df.columns:
            eval_df = eval_df.rename(columns={'contexts': 'retrieved_contexts'})
        
        # Check if we have any data to evaluate
        if eval_df.empty:
            return {"error": "No evaluation data available"}
            
        # Split data into entries with and without contexts
        has_contexts_df = eval_df[eval_df['retrieved_contexts'].apply(lambda x: len(x) > 0)] if 'retrieved_contexts' in eval_df.columns else pd.DataFrame()
        no_contexts_df = eval_df[eval_df['retrieved_contexts'].apply(lambda x: len(x) == 0)] if 'retrieved_contexts' in eval_df.columns else eval_df
        
        # Use metrics that don't require contexts if we have no retrieved contexts
        if has_contexts_df.empty and not no_contexts_df.empty:
            logger.info("No retrieved contexts found, using context-free metrics only")
        
        # Debug info
        logger.info(f"DataFrame columns: {eval_df.columns.tolist()}")
        logger.info(f"Sample row: {eval_df.iloc[0].to_dict()}")
        
        # Create LLM for evaluation
        try:
            from langchain_openai import ChatOpenAI
            eval_llm = ChatOpenAI(model=openai_model, api_key=api_key)
            logger.info(f"Created LLM: {openai_model}")
        except Exception as e:
            logger.error(f"Error creating LLM: {str(e)}")
            return {"error": f"Error creating LLM: {str(e)}"}
        
        # Import evaluate function and dataset
        try:
            from ragas import evaluate
            from ragas import EvaluationDataset
            
            # Determine which metrics to use based on available data
            available_metrics = []
            available_metric_names = []
            
            for i, metric_class in enumerate(metric_classes):
                metric_name = metric_names[i]
                
                # Skip context-based metrics if we have no contexts
                if has_contexts_df.empty and metric_name in ["context_precision_without_reference", "context_relevancy"]:
                    logger.info(f"Skipping {metric_name} - no retrieved contexts available")
                    continue
                    
                try:
                    metric_instance = metric_class(llm=eval_llm)
                    available_metrics.append(metric_instance)
                    available_metric_names.append(metric_name)
                except Exception as e:
                    logger.warning(f"Could not initialize {metric_class.__name__}: {e}")
            
            if not available_metrics:
                return {"error": "No metrics could be initialized"}
            
            logger.info(f"Using metrics: {', '.join(available_metric_names)}")
            
            # Convert to EvaluationDataset
            eval_dataset = EvaluationDataset.from_pandas(eval_df)
            logger.info(f"Created EvaluationDataset with {len(eval_dataset)} samples")
            
            # Run evaluation
            result = evaluate(
                dataset=eval_dataset,
                metrics=available_metrics
            )
            
            # Process results
            processed_results = {}
            for metric_name in available_metric_names:
                if hasattr(result, metric_name):
                    metric_result = getattr(result, metric_name)
                    processed_results[metric_name] = metric_result.tolist() if hasattr(metric_result, 'tolist') else metric_result
            
            return {
                "success": True,
                "metrics": processed_results,
                "metric_names": available_metric_names
            }
            
        except Exception as e:
            logger.error(f"RAGAS evaluation error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": f"RAGAS evaluation error: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Error in run_ragas_evaluation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"Error in run_ragas_evaluation: {str(e)}"}

async def evaluate_queries(
    queries: List[str],
    kb_name: str,
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None,
    rag_api_url: str = "http://localhost:8000",
    username: str = "admin@example.com",
    password: str = "password",
    progress_callback=None,
    ragas_status_callback=None
) -> Dict[str, Any]:
    """Evaluate a list of queries against a knowledge base
    
    Args:
        queries: List of query strings
        kb_name: Name of the knowledge base
        openai_model: OpenAI model for evaluation
        openai_api_key: OpenAI API key
        rag_api_url: URL of the RAG API
        username: Username for authentication
        password: Password for authentication
        progress_callback: Optional callback for query progress updates
        ragas_status_callback: Optional callback for RAGAS status updates
        
    Returns:
        Dictionary with evaluation results
    """
    # Generate RAG responses
    rag_results, logs = await generate_rag_responses(
        queries=queries,
        kb_name=kb_name,
        rag_api_url=rag_api_url,
        username=username,
        password=password,
        progress_callback=progress_callback
    )
    
    # Calculate response time stats
    response_times = [result.get("response_time", 0) for result in rag_results]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Run RAGAS evaluation if OpenAI API key is available
    ragas_results = {"error": "OpenAI API key not provided"}
    if ragas_status_callback:
        if openai_api_key or os.environ.get("OPENAI_API_KEY"):
            ragas_status_callback("Running RAGAS evaluation...")
        else:
            ragas_status_callback("Skipping RAGAS evaluation: OpenAI API key not provided")
            
    if openai_api_key or os.environ.get("OPENAI_API_KEY"):
        ragas_results = run_ragas_evaluation(
            evaluation_data=rag_results,
            openai_model=openai_model,
            openai_api_key=openai_api_key
        )
        
        if "success" in ragas_results and ragas_results["success"]:
            # Add metrics to individual results for backwards compatibility
            metrics_data = ragas_results.get("metrics", {})
            metric_names = ragas_results.get("metric_names", [])
            
            for i, result in enumerate(rag_results):
                for metric in metric_names:
                    if metric in metrics_data and i < len(metrics_data[metric]):
                        result[metric] = metrics_data[metric][i]
    
    # Return combined results
    return {
        "kb_name": kb_name,
        "queries": queries,
        "rag_results": rag_results,
        "avg_response_time": avg_response_time,
        "ragas_results": ragas_results,
        "logs": logs
    }

def run_headless_evaluation(
    kb_name: str, 
    queries: Optional[List[str]] = None,
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None,
    rag_api_url: str = "http://localhost:8000",
    username: str = "admin@example.com",
    password: str = "password",
    progress_callback=None,
    ragas_status_callback=None
) -> Dict[str, Any]:
    """Run a headless evaluation on the specified knowledge base
    
    Args:
        kb_name: Name of the knowledge base to evaluate
        queries: List of queries to evaluate (or None to use defaults)
        openai_model: OpenAI model to use for evaluation
        openai_api_key: OpenAI API key
        rag_api_url: URL of the RAG API
        username: Username for authentication
        password: Password for authentication
        progress_callback: Optional callback for query progress updates
        ragas_status_callback: Optional callback for RAGAS status updates
        
    Returns:
        Dictionary with evaluation results
    """
    # Use default queries if none provided
    if queries is None:
        queries = DEFAULT_TEST_QUERIES
    
    try:
        # Run evaluation asynchronously
        return asyncio.run(evaluate_queries(
            queries=queries,
            kb_name=kb_name,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            rag_api_url=rag_api_url,
            username=username,
            password=password,
            progress_callback=progress_callback,
            ragas_status_callback=ragas_status_callback
        ))
    except Exception as e:
        logger.error(f"Error in headless evaluation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "kb_name": kb_name,
            "queries": queries,
            "error": f"Error in headless evaluation: {str(e)}"
        }