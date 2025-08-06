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

# Import our chat utility and performance monitoring
from chat_util import RagChatUtil
from performance_monitor import get_monitor

# Default test questions
DEFAULT_TEST_QUERIES = [
    "What is the living income benchmark?",
    "How is the living income benchmark calculated?",
    "What factors influence the living income benchmark?",
    "How does the living income benchmark differ from minimum wage?",
    "What is the purpose of establishing a living income benchmark?"
]

def detect_csv_format(df: pd.DataFrame) -> Tuple[bool, bool, Optional[str]]:
    """Detect CSV format and validate structure.
    
    Args:
        df: Pandas DataFrame from CSV
        
    Returns:
        Tuple of (has_prompts, has_references, error_message)
    """
    # Check for required prompt column
    prompt_columns = ['prompt', 'query', 'question']
    prompt_col = None
    for col in prompt_columns:
        if col in df.columns:
            prompt_col = col
            break
    
    if not prompt_col:
        return False, False, f"CSV must contain one of these columns: {', '.join(prompt_columns)}"
    
    # Check for reference answer columns
    reference_columns = ['reference_answer', 'reference', 'ground_truth', 'answer']
    reference_col = None
    for col in reference_columns:
        if col in df.columns:
            reference_col = col
            break
    
    has_references = reference_col is not None
    
    # Validate data
    if df.empty:
        return False, False, "CSV file is empty"
    
    # Check if prompt column has data
    non_empty_prompts = df[prompt_col].dropna().str.strip().astype(bool).sum()
    if non_empty_prompts == 0:
        return False, False, f"No valid prompts found in '{prompt_col}' column"
    
    # If we have references, check if they have data
    if has_references:
        non_empty_refs = df[reference_col].dropna().str.strip().astype(bool).sum()
        if non_empty_refs == 0:
            has_references = False  # References column exists but is empty
    
    return True, has_references, None

def parse_csv_queries(df: pd.DataFrame) -> Tuple[List[str], Optional[List[str]], Optional[str]]:
    """Parse queries and optional reference answers from CSV DataFrame.
    
    Args:
        df: Pandas DataFrame from CSV
        
    Returns:
        Tuple of (queries, reference_answers, error_message)
    """
    has_prompts, has_references, error_msg = detect_csv_format(df)
    if error_msg:
        return [], None, error_msg
    
    # Find prompt column
    prompt_columns = ['prompt', 'query', 'question']
    prompt_col = None
    for col in prompt_columns:
        if col in df.columns:
            prompt_col = col
            break
    
    # Extract queries
    queries = df[prompt_col].dropna().str.strip().tolist()
    queries = [q for q in queries if q]  # Remove empty strings
    
    reference_answers = None
    if has_references:
        # Find reference column
        reference_columns = ['reference_answer', 'reference', 'ground_truth', 'answer']
        reference_col = None
        for col in reference_columns:
            if col in df.columns:
                reference_col = col
                break
        
        if reference_col:
            reference_answers = df[reference_col].fillna('').str.strip().tolist()
            # Ensure reference_answers matches queries length
            if len(reference_answers) != len(df):
                # Pad or truncate to match DataFrame length, then filter to match queries
                reference_answers = reference_answers[:len(df)]
            
            # Filter reference answers to match non-empty queries
            filtered_refs = []
            for i, query in enumerate(df[prompt_col]):
                if pd.notna(query) and str(query).strip():
                    ref_idx = min(i, len(reference_answers) - 1)
                    filtered_refs.append(reference_answers[ref_idx] if ref_idx >= 0 else '')
            reference_answers = filtered_refs
    
    logger.info(f"Parsed {len(queries)} queries" + 
                (f" with {len([r for r in reference_answers if r])} reference answers" if reference_answers else " (no references)"))
    
    return queries, reference_answers, None

def validate_queries_and_references(queries: List[str], reference_answers: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """Validate queries and reference answers.
    
    Args:
        queries: List of query strings
        reference_answers: Optional list of reference answers
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not queries:
        return False, "No queries provided"
    
    if len(queries) == 0:
        return False, "Query list is empty"
    
    # Check for empty queries
    empty_queries = [i for i, q in enumerate(queries) if not q or not q.strip()]
    if empty_queries:
        return False, f"Empty queries found at positions: {empty_queries}"
    
    # Validate reference answers if provided
    if reference_answers is not None:
        if len(reference_answers) != len(queries):
            return False, f"Mismatch: {len(queries)} queries but {len(reference_answers)} reference answers"
        
        # Check for reference quality (warn but don't fail)
        empty_refs = [i for i, ref in enumerate(reference_answers) if not ref or not ref.strip()]
        if empty_refs:
            logger.warning(f"Empty reference answers found at positions: {empty_refs} - these queries will use reference-free metrics only")
    
    return True, None

def setup_ragas(enable_reference_metrics: bool = False) -> Tuple[bool, List, List[str], Optional[str]]:
    """Set up RAGAS for evaluation and determine available metrics.
    
    Args:
        enable_reference_metrics: If True, include metrics that require reference answers
    
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
            from ragas.metrics import ContextRelevance
            metrics.append(ContextRelevance)
            metric_names.append("context_relevancy")
        except ImportError:
            logger.info("ContextRelevance metric not available")

        # Add reference-based metrics if enabled
        if enable_reference_metrics:
            logger.info("Adding reference-based metrics...")
            
            try:
                from ragas.metrics import AnswerSimilarity
                metrics.append(AnswerSimilarity)
                metric_names.append("answer_similarity")
                logger.info("Added AnswerSimilarity metric")
            except ImportError:
                try:
                    from ragas.metrics import SemanticSimilarity
                    metrics.append(SemanticSimilarity)
                    metric_names.append("answer_similarity")  # Keep same name for UI consistency
                    logger.info("Added SemanticSimilarity metric as fallback for answer_similarity")
                except ImportError:
                    logger.info("Neither AnswerSimilarity nor SemanticSimilarity metric available")
            
            try:
                from ragas.metrics import AnswerCorrectness
                metrics.append(AnswerCorrectness)
                metric_names.append("answer_correctness")
                logger.info("Added AnswerCorrectness metric")
            except ImportError:
                logger.info("AnswerCorrectness metric not available")
            
            try:
                from ragas.metrics import ContextPrecision
                metrics.append(ContextPrecision)
                metric_names.append("context_precision")
                logger.info("Added ContextPrecision metric (standard version)")
            except ImportError:
                logger.info("ContextPrecision metric not available")
            
            try:
                from ragas.metrics import ContextRecall
                metrics.append(ContextRecall)
                metric_names.append("context_recall")
                logger.info("Added ContextRecall metric")
            except ImportError:
                logger.info("ContextRecall metric not available")

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
    reference_answers: Optional[List[str]] = None,
    progress_callback=None,
    use_batch_processing: bool = True,
    batch_size: int = 5,
    max_concurrent: int = 3
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate RAG responses for a list of queries
    
    Args:
        queries: List of query strings
        kb_name: Name of the knowledge base to use
        rag_api_url: URL of the RAG API
        username: Username for API authentication
        password: Password for API authentication
        reference_answers: Optional list of reference answers (must match queries length if provided)
        progress_callback: Optional callback function for progress updates
        use_batch_processing: Enable batch processing for better performance
        batch_size: Number of queries to process in each batch
        max_concurrent: Maximum concurrent requests per batch
        
    Returns:
        Tuple of (list of response dictionaries, logs)
    """
    monitor = get_monitor()
    
    with monitor.measure_operation("rag_responses_generation", 
                                 query_count=len(queries), 
                                 kb_name=kb_name,
                                 use_batch_processing=use_batch_processing,
                                 batch_size=batch_size):
        # Create chat utility
        chat_util = RagChatUtil(
            base_url=rag_api_url,
            username=username,
            password=password
        )

        # Enable instrumentation
        chat_util.enable_instrumentation()

        if use_batch_processing and len(queries) > 1:
            logger.info(f"Using batch processing: {len(queries)} queries, batch_size={batch_size}, max_concurrent={max_concurrent}")
            
            # Use batch processing for better performance
            with monitor.measure_operation("rag_batch_processing", 
                                         query_count=len(queries)):
                raw_results = await chat_util.generate_rag_responses_batch(
                    queries, kb_name, batch_size=batch_size, max_concurrent=max_concurrent
                )
        else:
            logger.info(f"Using sequential processing: {len(queries)} queries")
            
            # Fall back to sequential processing
            raw_results = []
            for i, query in enumerate(queries):
                logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")

                with monitor.measure_operation("rag_api_single_query", 
                                             query_index=i+1, 
                                             query_preview=query[:50]):
                    rag_result = await chat_util.generate_rag_response(query, kb_name)
                
                raw_results.append(rag_result)

        # Process results and add reference answers
        results = []
        all_logs = chat_util.get_logs()
        
        for i, rag_result in enumerate(raw_results):
            query = queries[i] if i < len(queries) else ""
            
            # Get reference answer for this query
            reference_answer = ""
            if reference_answers and i < len(reference_answers):
                reference_answer = reference_answers[i] or ""

            # Format response
            if "error" not in rag_result:
                contexts = [item["page_content"] for item in rag_result.get("contexts", [])]
                results.append({
                    "query": query,
                    "ground_truths": [reference_answer] if reference_answer else [""],
                    "reference_answer": reference_answer,  # Store for easier access
                    "answer": rag_result["response"],
                    "contexts": contexts,
                    "response_time": rag_result.get("response_time", 0),
                    "kb_id": rag_result.get("kb_id"),
                    "chat_id": rag_result.get("chat_id"),
                })
            else:
                # Store error result
                results.append({
                    "query": query,
                    "answer": rag_result.get("response", ""),  # For RAGAS compatibility
                    "contexts": [],
                    "ground_truths": [reference_answer] if reference_answer else [""],
                    "reference_answer": reference_answer,
                    "error": rag_result.get("error", "Unknown error"),
                    "response_time": rag_result.get("response_time", 0)
                })
                monitor.increment_counter("failed_operations")

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
        
        # Add 'reference' column for reference-based metrics from reference_answer or ground_truths
        if 'reference_answer' in eval_df.columns:
            eval_df['reference'] = eval_df['reference_answer']
            logger.info("Added 'reference' column from 'reference_answer'")
        elif 'ground_truths' in eval_df.columns:
            # Extract first ground truth as reference
            eval_df['reference'] = eval_df['ground_truths'].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x if x else ""
            )
            logger.info("Added 'reference' column from first ground truth")
        
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
        if 'reference' in eval_df.columns:
            non_empty_refs = eval_df['reference'].apply(lambda x: bool(str(x).strip())).sum()
            logger.info(f"Reference column analysis: {non_empty_refs}/{len(eval_df)} rows have non-empty references")
        
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
    monitor = get_monitor()
    
    with monitor.measure_operation("ragas_eval_faithfulness", dataset_size=len(eval_dataset)):
        try:
            from ragas.metrics import Faithfulness
            from ragas import evaluate
            
            logger.info("Initializing faithfulness metric...")
            faithfulness_metric = Faithfulness(llm=eval_llm)
            logger.info("Successfully initialized faithfulness metric")
            
            logger.info("Running faithfulness evaluation...")
            monitor.increment_counter("openai_api_calls")  # This will make multiple API calls
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
        
        # Debug: Check what attributes are available
        logger.info(f"RAGAS result type: {type(result).__name__}")
        logger.info(f"RAGAS result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        
        # Try different possible attribute names for context precision
        possible_attrs = ['context_precision_without_reference', 'context_precision', 'contextprecision', 'llm_context_precision_without_reference']
        precision_scores = None
        
        for attr in possible_attrs:
            if hasattr(result, attr):
                precision_scores = getattr(result, attr)
                logger.info(f"Found context precision result under attribute: {attr}")
                break
        
        if precision_scores is not None:
            logger.info(f"Context precision evaluation completed: {type(precision_scores).__name__}")
            return precision_scores.tolist() if hasattr(precision_scores, 'tolist') else precision_scores, None
        else:
            # Try to get from scores like other metrics
            if hasattr(result, 'scores') and result.scores:
                logger.info(f"RAGAS scores: {result.scores}")
                # Find the correct key for context precision
                precision_key = None
                for score_dict in result.scores:
                    for key in score_dict:
                        if 'precision' in key.lower() and 'context' in key.lower():
                            precision_key = key
                            logger.info(f"Found context precision in scores under key: {key}")
                            break
                    if precision_key:
                        break
                
                if precision_key:
                    # Extract scores from all queries
                    precision_scores = [score_dict.get(precision_key) for score_dict in result.scores if precision_key in score_dict]
                    return precision_scores, None
            
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
        from ragas.metrics import ContextRelevance
        from ragas import evaluate
        
        logger.info("Initializing context relevancy metric...")
        context_relevancy_metric = ContextRelevance(llm=eval_llm)
        logger.info("Successfully initialized context relevancy metric")
        
        logger.info("Running context relevancy evaluation...")
        result = evaluate(
            dataset=eval_dataset,
            metrics=[context_relevancy_metric]
        )
        
        # Debug: Check what attributes are available
        logger.info(f"RAGAS result type: {type(result).__name__}")
        logger.info(f"RAGAS result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        
        # Try different possible attribute names for context relevancy
        possible_attrs = ['context_relevancy', 'context_relevance', 'contextrelevancy', 'contextrelevance']
        relevancy_scores = None
        
        for attr in possible_attrs:
            if hasattr(result, attr):
                relevancy_scores = getattr(result, attr)
                logger.info(f"Found context relevancy result under attribute: {attr}")
                break
        
        if relevancy_scores is not None:
            logger.info(f"Context relevancy evaluation completed: {type(relevancy_scores).__name__}")
            return relevancy_scores.tolist() if hasattr(relevancy_scores, 'tolist') else relevancy_scores, None
        else:
            # Try to get from scores like other metrics
            if hasattr(result, 'scores') and result.scores:
                logger.info(f"RAGAS scores: {result.scores}")
                # Find the correct key for context relevancy
                relevancy_key = None
                for score_dict in result.scores:
                    for key in score_dict:
                        if 'context_relevance' in key.lower() or 'relevancy' in key.lower():
                            relevancy_key = key
                            logger.info(f"Found context relevancy in scores under key: {key}")
                            break
                    if relevancy_key:
                        break
                
                if relevancy_key:
                    # Extract scores from all queries
                    relevancy_scores = [score_dict.get(relevancy_key) for score_dict in result.scores if relevancy_key in score_dict]
                    return relevancy_scores, None
            
            logger.warning("No context_relevancy result found in evaluation output")
            return None, "No context_relevancy result found"
            
    except Exception as e:
        error_msg = f"Context relevancy evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return None, error_msg

def evaluate_metrics_batch(eval_dataset, eval_llm, target_metrics: List[str], 
                          has_contexts: bool, has_references: bool) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Evaluate multiple RAGAS metrics in batches for better performance.
    
    Args:
        eval_dataset: EvaluationDataset instance
        eval_llm: LLM instance for evaluation
        target_metrics: List of metrics to evaluate
        has_contexts: Whether dataset has retrieved contexts
        has_references: Whether dataset has reference answers
        
    Returns:
        Tuple of (results_dict, successful_metrics, errors)
    """
    monitor = get_monitor()
    results = {}
    successful_metrics = []
    errors = []
    
    # Filter out metrics that can't be evaluated due to missing data
    available_metrics = []
    
    for metric in target_metrics:
        # Check data requirements for each metric
        if metric in ['faithfulness', 'answer_relevancy']:
            # These only need question + answer (always available)
            available_metrics.append(metric)
        elif metric in ['context_precision_without_reference', 'context_relevancy']:
            # These need contexts (always available in RAG)
            if has_contexts:
                available_metrics.append(metric)
            else:
                errors.append(f"{metric}: No contexts available")
        elif metric in ['answer_similarity', 'answer_correctness']:
            # These need reference answers
            if has_references:
                available_metrics.append(metric)
            else:
                errors.append(f"{metric}: No reference answers available")
        elif metric in ['context_precision', 'context_recall']:
            # These need both contexts and references
            if has_contexts and has_references:
                available_metrics.append(metric)
            else:
                missing = []
                if not has_contexts:
                    missing.append("contexts")
                if not has_references:
                    missing.append("references")
                errors.append(f"{metric}: Missing {', '.join(missing)}")
    
    # Single unified batch evaluation for all available metrics
    if available_metrics:
        with monitor.measure_operation("batch_eval_unified_metrics",
                                     metrics=available_metrics,
                                     metric_count=len(available_metrics)):
            logger.info(f"Unified batch evaluation: {len(available_metrics)} metrics - {available_metrics}")
            batch_results, batch_errors = _evaluate_unified_metrics_batch(eval_dataset, eval_llm, available_metrics)
            results.update(batch_results)
            successful_metrics.extend(batch_results.keys())
            errors.extend(batch_errors)
    else:
        logger.warning("No metrics available for evaluation due to missing data requirements")
    
    return results, successful_metrics, errors

def _evaluate_unified_metrics_batch(eval_dataset, eval_llm, metrics: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """Unified batch evaluation for all RAGAS metrics in a single call."""
    try:
        from ragas.metrics import (
            Faithfulness, AnswerRelevancy, 
            LLMContextPrecisionWithoutReference, ContextRelevance,
            AnswerSimilarity, AnswerCorrectness,
            ContextPrecision, ContextRecall
        )
        from ragas import evaluate
        
        # Build metric instances for all requested metrics
        metric_instances = []
        metric_name_mapping = {}
        
        for metric in metrics:
            if metric == 'faithfulness':
                metric_instances.append(Faithfulness())
                metric_name_mapping['faithfulness'] = 'faithfulness'
            elif metric == 'answer_relevancy':
                metric_instances.append(AnswerRelevancy())
                metric_name_mapping['answer_relevancy'] = 'answer_relevancy'
            elif metric == 'context_precision_without_reference':
                metric_instances.append(LLMContextPrecisionWithoutReference())
                metric_name_mapping['context_precision_without_reference'] = 'llm_context_precision_without_reference'
            elif metric == 'context_relevancy':
                metric_instances.append(ContextRelevance())
                metric_name_mapping['context_relevancy'] = 'nv_context_relevance'
            elif metric == 'answer_similarity':
                metric_instances.append(AnswerSimilarity())
                metric_name_mapping['answer_similarity'] = 'semantic_similarity'
            elif metric == 'answer_correctness':
                metric_instances.append(AnswerCorrectness())
                metric_name_mapping['answer_correctness'] = 'answer_correctness'
            elif metric == 'context_precision':
                metric_instances.append(ContextPrecision())
                metric_name_mapping['context_precision'] = 'context_precision'
            elif metric == 'context_recall':
                metric_instances.append(ContextRecall())
                metric_name_mapping['context_recall'] = 'context_recall'
        
        if not metric_instances:
            return {}, []
        
        logger.info(f"Unified batch evaluating {len(metric_instances)} metrics: {metrics}")
        monitor = get_monitor()
        monitor.increment_counter("openai_api_calls", len(metric_instances))
        
        # Single unified RAGAS evaluation call
        result = evaluate(dataset=eval_dataset, metrics=metric_instances)
        
        # Extract results for all metrics
        results = {}
        errors = []
        
        for metric_name in metrics:
            ragas_key = metric_name_mapping.get(metric_name, metric_name)
            
            if hasattr(result, 'scores') and isinstance(result.scores, list) and len(result.scores) > 0:
                # Extract scores from list of dicts
                scores = [score_dict.get(ragas_key) for score_dict in result.scores if ragas_key in score_dict]
                if scores and all(score is not None for score in scores):
                    results[metric_name] = scores
                    logger.info(f"Successfully extracted {len(scores)} scores for {metric_name} (ragas key: {ragas_key})")
                else:
                    errors.append(f"{metric_name}: No valid scores found for {ragas_key}")
                    logger.warning(f"No valid scores for {metric_name} (ragas key: {ragas_key})")
            elif hasattr(result, ragas_key):
                metric_result = getattr(result, ragas_key)
                results[metric_name] = metric_result.tolist() if hasattr(metric_result, 'tolist') else metric_result
                logger.info(f"Successfully extracted attribute result for {metric_name}")
            else:
                errors.append(f"{metric_name}: No result found for {ragas_key}")
                logger.warning(f"No result found for {metric_name} (ragas key: {ragas_key})")
        
        logger.info(f"Unified batch evaluation completed: {len(results)} successful, {len(errors)} errors")
        return results, errors
        
    except Exception as e:
        error_msg = f"Unified batch metrics evaluation error: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {}, [error_msg]

def evaluate_metrics_individual(eval_dataset, eval_llm, target_metrics: List[str],
                               has_contexts: bool, has_references: bool) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Evaluate metrics individually (original approach for fallback)."""
    results = {}
    successful_metrics = []
    errors = []
    
    # Evaluate faithfulness (doesn't require contexts) - only if in target metrics
    if 'faithfulness' in target_metrics:
        logger.info("Evaluating faithfulness metric...")
        faithfulness_result, error_msg = evaluate_faithfulness(eval_dataset, eval_llm)
        if error_msg:
            errors.append(f"faithfulness: {error_msg}")
        else:
            results["faithfulness"] = faithfulness_result
            successful_metrics.append("faithfulness")
    
    # Evaluate answer relevancy (doesn't require contexts) - only if in target metrics
    if 'answer_relevancy' in target_metrics:
        logger.info("Evaluating answer relevancy metric...")
        relevancy_result, error_msg = evaluate_answer_relevancy(eval_dataset, eval_llm)
        if error_msg:
            errors.append(f"answer_relevancy: {error_msg}")
        else:
            results["answer_relevancy"] = relevancy_result
            successful_metrics.append("answer_relevancy")
    
    # Add other individual metric evaluations as needed...
    
    return results, successful_metrics, errors

def run_ragas_evaluation(
    evaluation_data: List[Dict[str, Any]], 
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None,
    enable_reference_metrics: bool = False,
    metrics_mode: str = "full",
    use_batch_evaluation: bool = True
) -> Dict[str, Any]:
    """Run RAGAS evaluation on the given data
    
    Args:
        evaluation_data: List of dictionaries with query, answer, contexts, ground_truths
        openai_model: OpenAI model to use for evaluation
        openai_api_key: OpenAI API key (will use env var if None)
        enable_reference_metrics: If True, enable metrics that require reference answers
        metrics_mode: Metrics evaluation mode - 'basic', 'full', or 'reference-only'
        use_batch_evaluation: Use batch evaluation for better performance
        
    Returns:
        Dictionary with evaluation results or error
    """
    monitor = get_monitor()
    
    logger.info(f"Starting RAGAS evaluation with enable_reference_metrics={enable_reference_metrics}, metrics_mode={metrics_mode}, use_batch_evaluation={use_batch_evaluation}...")
    
    # Define metrics for each mode
    BASIC_METRICS = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
    REFERENCE_METRICS = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']
    
    # Determine which metrics to evaluate based on mode
    if metrics_mode == 'basic':
        target_metrics = BASIC_METRICS
        logger.info(f"Basic mode: evaluating {len(target_metrics)} metrics")
    elif metrics_mode == 'reference-only':
        target_metrics = REFERENCE_METRICS
        logger.info(f"Reference-only mode: evaluating {len(target_metrics)} metrics")
    else:  # metrics_mode == 'full'
        target_metrics = BASIC_METRICS + (REFERENCE_METRICS if enable_reference_metrics else [])
        logger.info(f"Full mode: evaluating {len(target_metrics)} metrics (reference metrics: {enable_reference_metrics})")
    
    logger.info(f"Target metrics: {target_metrics}")
    
    # Check for OpenAI API key
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."}
    
    # Setup RAGAS
    logger.info("Setting up RAGAS metrics...")
    ragas_available, metric_classes, metric_names, error_message = setup_ragas(enable_reference_metrics)
    logger.info(f"DEBUG: setup_ragas returned - available: {ragas_available}, metric_names: {metric_names}")
    if not ragas_available:
        return {"error": error_message}
    
    logger.info(f"Available metrics: {', '.join(metric_names)}")
    
    try:
        # Prepare evaluation data
        eval_df, has_contexts, error_msg = prepare_evaluation_data(evaluation_data)
        if error_msg:
            return {"error": error_msg}
        
        # Check for reference answers availability
        has_references = False
        if 'ground_truths' in eval_df.columns:
            # Check if we have meaningful reference answers (not just empty strings)
            non_empty_refs = eval_df['ground_truths'].apply(
                lambda x: any(ref.strip() for ref in x) if isinstance(x, list) and x else False
            )
            has_references = non_empty_refs.any()
            ref_count = non_empty_refs.sum()
            logger.info(f"Reference analysis: {ref_count}/{len(eval_df)} rows have reference answers")
            
            if enable_reference_metrics and not has_references:
                logger.warning("Reference metrics requested but no reference answers found - some metrics will be skipped")
        else:
            logger.warning("No 'ground_truths' column found")
        
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
        
        # Choose evaluation strategy
        if use_batch_evaluation:
            # Use batch evaluation for better performance
            results, successful_metrics, errors = evaluate_metrics_batch(
                eval_dataset, eval_llm, target_metrics, has_contexts, has_references
            )
        else:
            # Use individual metric evaluations (original approach)
            results, successful_metrics, errors = evaluate_metrics_individual(
                eval_dataset, eval_llm, target_metrics, has_contexts, has_references
            )
        
        # Log evaluation results
        logger.info(f"RAGAS evaluation completed: {len(successful_metrics)} successful metrics, {len(errors)} errors")
        if successful_metrics:
            logger.info(f"Successful metrics: {', '.join(successful_metrics)}")
        if errors:
            logger.warning(f"Metric errors: {'; '.join(errors)}")
        # Return successful evaluation results
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
    openai_model: str = "gpt-4o-mini",
    openai_api_key: Optional[str] = None,
    rag_api_url: str = "http://localhost:8000",
    username: str = "admin@example.com",
    password: str = "password",
    reference_answers: Optional[List[str]] = None,
    metrics_mode: str = "full",
    progress_callback=None,
    ragas_status_callback=None,
    use_batch_processing: bool = True,
    batch_size: int = 5,
    max_concurrent: int = 3
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
        reference_answers: Optional list of reference answers for enhanced metrics
        metrics_mode: Metrics evaluation mode - 'basic', 'full', or 'reference-only'
        progress_callback: Optional callback for query progress updates
        ragas_status_callback: Optional callback for RAGAS status updates
        
    Returns:
        Dictionary with evaluation results
    """
    # Validate inputs
    is_valid, error_msg = validate_queries_and_references(queries, reference_answers)
    if not is_valid:
        return {"error": error_msg}
    
    # Determine metrics evaluation mode
    if metrics_mode == 'reference-only':
        # Reference-only mode requires reference answers
        if not reference_answers or not any(ref.strip() for ref in reference_answers):
            return {"error": "reference-only mode requires reference answers"}
        enable_reference_metrics = True
        logger.info("DEBUG: Reference-only mode - will evaluate only reference-based metrics")
    elif metrics_mode == 'basic':
        # Basic mode never uses reference metrics
        enable_reference_metrics = False
        logger.info("DEBUG: Basic mode - will evaluate only basic metrics (no reference required)")
    else:  # metrics_mode == 'full'
        # Full mode uses reference metrics if available
        enable_reference_metrics = reference_answers is not None and any(ref.strip() for ref in reference_answers)
        logger.info(f"DEBUG: Full mode - reference metrics enabled: {enable_reference_metrics}")
    
    logger.info(f"DEBUG: Metrics mode: {metrics_mode}, enable_reference_metrics: {enable_reference_metrics}")
    if reference_answers:
        logger.info(f"DEBUG: Reference answers count: {len(reference_answers)}, non-empty: {sum(1 for ref in reference_answers if ref.strip())}")
    
    # Initialize performance monitoring for Streamlit path
    from performance_monitor import reset_monitor
    reset_monitor()
    monitor = get_monitor()
    monitor.start_monitoring()
    
    # Generate RAG responses
    rag_results, logs = await generate_rag_responses(
        queries=queries,
        kb_name=kb_name,
        rag_api_url=rag_api_url,
        username=username,
        password=password,
        reference_answers=reference_answers,
        progress_callback=progress_callback,
        use_batch_processing=use_batch_processing,
        batch_size=batch_size,
        max_concurrent=max_concurrent
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
        logger.info(f"DEBUG: Calling run_ragas_evaluation with enable_reference_metrics={enable_reference_metrics}, metrics_mode={metrics_mode}")
        ragas_results = run_ragas_evaluation(
            evaluation_data=rag_results,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            enable_reference_metrics=enable_reference_metrics,
            metrics_mode=metrics_mode
        )
        logger.info(f"DEBUG: RAGAS evaluation completed, results keys: {list(ragas_results.keys()) if isinstance(ragas_results, dict) else 'Not a dict'}")
        
        if "success" in ragas_results and ragas_results["success"]:
            # Add metrics to individual results for backwards compatibility
            metrics_data = ragas_results.get("metrics", {})
            metric_names = ragas_results.get("metric_names", [])
            logger.info(f"DEBUG: RAGAS success - metrics_data keys: {list(metrics_data.keys())}")
            logger.info(f"DEBUG: RAGAS metric_names: {metric_names}")
            logger.info(f"DEBUG: Reference metrics in results: {[m for m in metric_names if m in ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']]}")
            
            # Check for incomplete metric evaluation (common RAGAS issue)
            expected_results = len(rag_results)
            for metric, values in metrics_data.items():
                if len(values) != expected_results:
                    logger.warning(f"RAGAS metric '{metric}' only has {len(values)} values for {expected_results} queries")
            
            for i, result in enumerate(rag_results):
                logger.info(f"DEBUG: Processing result {i+1} - existing keys: {list(result.keys())}")
                for metric in metric_names:
                    if metric in metrics_data and i < len(metrics_data[metric]):
                        result[metric] = metrics_data[metric][i]
                        logger.info(f"DEBUG: Added metric '{metric}' = {metrics_data[metric][i]} to result {i+1}")
                    else:
                        # For missing metrics, assign None to indicate failed evaluation
                        result[metric] = None
                        logger.warning(f"DEBUG: RAGAS failed to evaluate '{metric}' for query {i+1} - setting to None")
                logger.info(f"DEBUG: Result {i+1} final keys: {list(result.keys())}")

    # Stop performance monitoring
    monitor.stop_monitoring()
    
    # Get performance summary from monitor
    try:
        performance_report = monitor.generate_report(len(queries))
        performance_summary = {
            "total_duration": performance_report.total_duration,
            "avg_query_time": performance_report.avg_query_time,
            "peak_memory_mb": performance_report.peak_memory_mb,
            "openai_api_calls": performance_report.openai_api_calls,
            "rag_api_time": performance_report.rag_api_total_time,
            "ragas_eval_time": performance_report.ragas_eval_total_time
        }
    except Exception as e:
        logger.warning(f"Could not generate performance summary: {e}")
        performance_summary = {}
    
    # Return combined results
    return {
        "kb_name": kb_name,
        "queries": queries,
        "rag_results": rag_results,
        "avg_response_time": avg_response_time,
        "ragas_results": ragas_results,
        "logs": logs,
        "performance_summary": performance_summary
    }

def run_headless_evaluation(
    kb_name: str, 
    queries: Optional[List[str]] = None,
    reference_answers: Optional[List[str]] = None,
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None,
    rag_api_url: str = "http://localhost:8000",
    username: str = "admin@example.com",
    password: str = "password",
    metrics_mode: str = "full",
    progress_callback=None,
    ragas_status_callback=None
) -> Dict[str, Any]:
    """Run a headless evaluation on the specified knowledge base
    
    Args:
        kb_name: Name of the knowledge base to evaluate
        queries: List of queries to evaluate (or None to use defaults)
        reference_answers: Optional list of reference answers for enhanced metrics
        openai_model: OpenAI model to use for evaluation
        openai_api_key: OpenAI API key
        rag_api_url: URL of the RAG API
        username: Username for authentication
        password: Password for authentication
        metrics_mode: Metrics evaluation mode - 'basic', 'full', or 'reference-only'
        progress_callback: Optional callback for query progress updates
        ragas_status_callback: Optional callback for RAGAS status updates
        
    Returns:
        Dictionary with evaluation results
    """
    # Initialize performance monitoring
    from performance_monitor import reset_monitor
    reset_monitor()  # Clear any previous monitoring data
    monitor = get_monitor()
    monitor.start_monitoring()
    
    try:
        # Use default queries if none provided
        if queries is None:
            queries = DEFAULT_TEST_QUERIES
        
        with monitor.measure_operation("full_headless_evaluation",
                                     query_count=len(queries),
                                     metrics_mode=metrics_mode,
                                     kb_name=kb_name):
            # Run evaluation asynchronously
            result = asyncio.run(evaluate_queries(
                queries=queries,
                kb_name=kb_name,
                openai_model=openai_model,
                openai_api_key=openai_api_key,
                rag_api_url=rag_api_url,
                username=username,
                password=password,
                reference_answers=reference_answers,
                metrics_mode=metrics_mode,
                progress_callback=progress_callback,
                ragas_status_callback=ragas_status_callback
            ))
            
            return result
            
    except Exception as e:
        logger.error(f"Error in headless evaluation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "kb_name": kb_name,
            "queries": queries,
            "error": f"Error in headless evaluation: {str(e)}"
        }
    finally:
        # Stop monitoring and log performance summary
        monitor.stop_monitoring()
        monitor.log_summary(len(queries) if queries else 0)