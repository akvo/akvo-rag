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

def create_evaluation_llm(openai_model: str, api_key: str) -> Tuple[Any, Optional[str]]:
    """Create LLM for RAGAS evaluation.
    
    Args:
        openai_model: OpenAI model name
        api_key: OpenAI API key
        
    Returns:
        Tuple of (llm_instance, error_message)
    """
    try:
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper
        
        # Create the base LangChain LLM
        base_llm = ChatOpenAI(model=openai_model, api_key=api_key)
        
        # Wrap it for RAGAS compatibility
        eval_llm = LangchainLLMWrapper(base_llm)
        
        logger.info(f"Created and wrapped LLM: {openai_model}")
        return eval_llm, None
    except Exception as e:
        error_msg = f"Error creating LLM: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

def prepare_evaluation_data(evaluation_data: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, bool, Optional[str]]:
    """Prepare and validate evaluation data.
    
    Args:
        evaluation_data: List of evaluation dictionaries
        
    Returns:
        Tuple of (dataframe, has_contexts, error_message)
    """
    try:
        # Convert data to DataFrame
        eval_df = pd.DataFrame(evaluation_data)
        logger.info(f"Created DataFrame with {len(eval_df)} rows")
        
        # Rename columns to match expected format
        column_mapping = {
            'query': 'user_input',
            'answer': 'response', 
            'contexts': 'retrieved_contexts'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in eval_df.columns:
                eval_df = eval_df.rename(columns={old_col: new_col})
                logger.info(f"Renamed column '{old_col}' to '{new_col}'")
        
        # Check if we have any data to evaluate
        if eval_df.empty:
            return None, False, "No evaluation data available"
        
        # Check for contexts
        has_contexts = False
        if 'retrieved_contexts' in eval_df.columns:
            context_counts = eval_df['retrieved_contexts'].apply(lambda x: len(x) if x else 0)
            has_contexts = (context_counts > 0).any()
            total_contexts = context_counts.sum()
            rows_with_contexts = (context_counts > 0).sum()
            
            logger.info(f"Context analysis: {rows_with_contexts}/{len(eval_df)} rows have contexts, total contexts: {total_contexts}")
            
            if not has_contexts:
                logger.warning("No retrieved contexts found in any rows - context-based metrics will be skipped")
        else:
            logger.warning("No 'retrieved_contexts' column found")
        
        # Debug info
        logger.info(f"DataFrame columns: {eval_df.columns.tolist()}")
        if len(eval_df) > 0:
            sample_row = eval_df.iloc[0].to_dict()
            # Truncate long values for logging
            for key, value in sample_row.items():
                if isinstance(value, str) and len(value) > 100:
                    sample_row[key] = value[:100] + "..."
            logger.info(f"Sample row: {sample_row}")
        
        return eval_df, has_contexts, None
        
    except Exception as e:
        error_msg = f"Error preparing evaluation data: {str(e)}"
        logger.error(error_msg)
        return None, False, error_msg

def evaluate_faithfulness(eval_dataset, eval_llm) -> Tuple[Optional[Any], Optional[str]]:
    """Evaluate faithfulness metric.
    
    Args:
        eval_dataset: EvaluationDataset instance
        eval_llm: LLM instance for evaluation
        
    Returns:
        Tuple of (metric_result, error_message)
    """
    try:
        from ragas.metrics import Faithfulness
        from ragas import evaluate
        
        logger.info("Initializing faithfulness metric...")
        faithfulness_metric = Faithfulness(llm=eval_llm)
        logger.info("Successfully initialized faithfulness metric")
        
        logger.info("Running faithfulness evaluation...")
        result = evaluate(
            dataset=eval_dataset,
            metrics=[faithfulness_metric]
        )
        
        # Debug: log what we actually got back
        logger.info(f"RAGAS result type: {type(result).__name__}")
        logger.info(f"RAGAS result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        logger.info(f"RAGAS scores: {result.scores if hasattr(result, 'scores') else 'No scores attr'}")
        
        # Try accessing through scores attribute first (correct for RAGAS 0.2.x)
        if hasattr(result, 'scores') and isinstance(result.scores, list) and len(result.scores) > 0:
            # Extract faithfulness scores from list of dicts
            faithfulness_scores = [score_dict.get('faithfulness') for score_dict in result.scores if 'faithfulness' in score_dict]
            if faithfulness_scores:
                logger.info(f"Faithfulness evaluation completed via scores: {len(faithfulness_scores)} scores")
                return faithfulness_scores, None
        elif hasattr(result, 'faithfulness'):
            faithfulness_scores = result.faithfulness
            logger.info(f"Faithfulness evaluation completed: {type(faithfulness_scores).__name__}")
            return faithfulness_scores.tolist() if hasattr(faithfulness_scores, 'tolist') else faithfulness_scores, None
        else:
            logger.warning("No faithfulness result found in evaluation output")
            # Try to log what's actually in the result
            if hasattr(result, '__dict__'):
                logger.info(f"Result dict keys: {list(result.__dict__.keys())}")
            if hasattr(result, 'scores') and hasattr(result.scores, '__dict__'):
                logger.info(f"Scores dict keys: {list(result.scores.__dict__.keys())}")
            return None, "No faithfulness result found"
            
    except Exception as e:
        error_msg = f"Faithfulness evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return None, error_msg

def evaluate_answer_relevancy(eval_dataset, eval_llm) -> Tuple[Optional[Any], Optional[str]]:
    """Evaluate answer relevancy metric.
    
    Args:
        eval_dataset: EvaluationDataset instance
        eval_llm: LLM instance for evaluation
        
    Returns:
        Tuple of (metric_result, error_message)
    """
    try:
        from ragas.metrics import AnswerRelevancy
        from ragas import evaluate
        
        logger.info("Initializing answer relevancy metric...")
        answer_relevancy_metric = AnswerRelevancy(llm=eval_llm)
        logger.info("Successfully initialized answer relevancy metric")
        
        logger.info("Running answer relevancy evaluation...")
        result = evaluate(
            dataset=eval_dataset,
            metrics=[answer_relevancy_metric]
        )
        
        # Debug: log what we actually got back
        logger.info(f"RAGAS result type: {type(result).__name__}")
        logger.info(f"RAGAS result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        logger.info(f"RAGAS scores: {result.scores if hasattr(result, 'scores') else 'No scores attr'}")
        
        # Try accessing through scores attribute first (correct for RAGAS 0.2.x)
        if hasattr(result, 'scores') and isinstance(result.scores, list) and len(result.scores) > 0:
            # Extract answer_relevancy scores from list of dicts
            relevancy_scores = [score_dict.get('answer_relevancy') for score_dict in result.scores if 'answer_relevancy' in score_dict]
            if relevancy_scores:
                logger.info(f"Answer relevancy evaluation completed via scores: {len(relevancy_scores)} scores")
                return relevancy_scores, None
        elif hasattr(result, 'answer_relevancy'):
            relevancy_scores = result.answer_relevancy
            logger.info(f"Answer relevancy evaluation completed: {type(relevancy_scores).__name__}")
            return relevancy_scores.tolist() if hasattr(relevancy_scores, 'tolist') else relevancy_scores, None
        else:
            logger.warning("No answer_relevancy result found in evaluation output")
            # Try to log what's actually in the result
            if hasattr(result, '__dict__'):
                logger.info(f"Result dict keys: {list(result.__dict__.keys())}")
            if hasattr(result, 'scores') and hasattr(result.scores, '__dict__'):
                logger.info(f"Scores dict keys: {list(result.scores.__dict__.keys())}")
            return None, "No answer_relevancy result found"
            
    except Exception as e:
        error_msg = f"Answer relevancy evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return None, error_msg

def evaluate_context_precision(eval_dataset, eval_llm) -> Tuple[Optional[Any], Optional[str]]:
    """Evaluate context precision metric (without reference).
    
    Args:
        eval_dataset: EvaluationDataset instance
        eval_llm: LLM instance for evaluation
        
    Returns:
        Tuple of (metric_result, error_message)
    """
    try:
        from ragas.metrics import LLMContextPrecisionWithoutReference
        from ragas import evaluate
        
        logger.info("Initializing context precision metric...")
        context_precision_metric = LLMContextPrecisionWithoutReference(llm=eval_llm)
        logger.info("Successfully initialized context precision metric")
        
        logger.info("Running context precision evaluation...")
        result = evaluate(
            dataset=eval_dataset,
            metrics=[context_precision_metric]
        )
        
        if hasattr(result, 'context_precision_without_reference'):
            precision_scores = result.context_precision_without_reference
            logger.info(f"Context precision evaluation completed: {type(precision_scores).__name__}")
            return precision_scores.tolist() if hasattr(precision_scores, 'tolist') else precision_scores, None
        else:
            logger.warning("No context_precision_without_reference result found in evaluation output")
            return None, "No context_precision_without_reference result found"
            
    except Exception as e:
        error_msg = f"Context precision evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return None, error_msg

def evaluate_context_relevancy(eval_dataset, eval_llm) -> Tuple[Optional[Any], Optional[str]]:
    """Evaluate context relevancy metric.
    
    Args:
        eval_dataset: EvaluationDataset instance
        eval_llm: LLM instance for evaluation
        
    Returns:
        Tuple of (metric_result, error_message)
    """
    try:
        from ragas.metrics import ContextRelevancy
        from ragas import evaluate
        
        logger.info("Initializing context relevancy metric...")
        context_relevancy_metric = ContextRelevancy(llm=eval_llm)
        logger.info("Successfully initialized context relevancy metric")
        
        logger.info("Running context relevancy evaluation...")
        result = evaluate(
            dataset=eval_dataset,
            metrics=[context_relevancy_metric]
        )
        
        if hasattr(result, 'context_relevancy'):
            relevancy_scores = result.context_relevancy
            logger.info(f"Context relevancy evaluation completed: {type(relevancy_scores).__name__}")
            return relevancy_scores.tolist() if hasattr(relevancy_scores, 'tolist') else relevancy_scores, None
        else:
            logger.warning("No context_relevancy result found in evaluation output")
            return None, "No context_relevancy result found"
            
    except Exception as e:
        error_msg = f"Context relevancy evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return None, error_msg

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
    logger.info("Starting RAGAS evaluation...")
    
    # Check for OpenAI API key
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."}
    
    # Setup RAGAS
    logger.info("Setting up RAGAS metrics...")
    ragas_available, metric_classes, metric_names, error_message = setup_ragas()
    if not ragas_available:
        return {"error": error_message}
    
    logger.info(f"Available metrics: {', '.join(metric_names)}")
    
    try:
        # Prepare evaluation data
        eval_df, has_contexts, error_msg = prepare_evaluation_data(evaluation_data)
        if error_msg:
            return {"error": error_msg}
        
        # Create LLM for evaluation
        eval_llm, error_msg = create_evaluation_llm(openai_model, api_key)
        if error_msg:
            return {"error": error_msg}
        
        # Convert to EvaluationDataset
        try:
            from ragas import EvaluationDataset
            eval_dataset = EvaluationDataset.from_pandas(eval_df)
            logger.info(f"Created EvaluationDataset with {len(eval_dataset)} samples")
        except Exception as e:
            error_msg = f"Error creating EvaluationDataset: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Run individual metric evaluations
        results = {}
        successful_metrics = []
        errors = []
        
        # Evaluate faithfulness (doesn't require contexts)
        logger.info("Evaluating faithfulness metric...")
        faithfulness_result, error_msg = evaluate_faithfulness(eval_dataset, eval_llm)
        if error_msg:
            errors.append(f"faithfulness: {error_msg}")
        else:
            results["faithfulness"] = faithfulness_result
            successful_metrics.append("faithfulness")
        
        # Evaluate answer relevancy (doesn't require contexts)
        logger.info("Evaluating answer relevancy metric...")
        relevancy_result, error_msg = evaluate_answer_relevancy(eval_dataset, eval_llm)
        if error_msg:
            errors.append(f"answer_relevancy: {error_msg}")
        else:
            results["answer_relevancy"] = relevancy_result
            successful_metrics.append("answer_relevancy")
        
        # Evaluate context-based metrics only if contexts are available
        if has_contexts:
            logger.info("Evaluating context precision metric...")
            precision_result, error_msg = evaluate_context_precision(eval_dataset, eval_llm)
            if error_msg:
                errors.append(f"context_precision_without_reference: {error_msg}")
            else:
                results["context_precision_without_reference"] = precision_result
                successful_metrics.append("context_precision_without_reference")
            
            logger.info("Evaluating context relevancy metric...")
            context_relevancy_result, error_msg = evaluate_context_relevancy(eval_dataset, eval_llm)
            if error_msg:
                errors.append(f"context_relevancy: {error_msg}")
            else:
                results["context_relevancy"] = context_relevancy_result
                successful_metrics.append("context_relevancy")
        else:
            logger.info("Skipping context-based metrics - no contexts available")
            errors.append("context_precision_without_reference: No contexts available")
            errors.append("context_relevancy: No contexts available")
        
        # Check if any metrics succeeded
        if not successful_metrics:
            error_details = "; ".join(errors) if errors else "Unknown reasons"
            return {"error": f"No metrics could be evaluated. Details: {error_details}"}
        
        logger.info(f"Successfully evaluated {len(successful_metrics)} metrics: {', '.join(successful_metrics)}")
        if errors:
            logger.warning(f"Failed to evaluate some metrics: {'; '.join(errors)}")
        
        logger.info("RAGAS evaluation completed successfully")
        return {
            "success": True,
            "metrics": results,
            "metric_names": successful_metrics,
            "has_contexts": has_contexts,
            "total_samples": len(eval_dataset),
            "errors": errors
        }
        
    except Exception as e:
        error_msg = f"Error in run_ragas_evaluation: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {"error": error_msg}

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