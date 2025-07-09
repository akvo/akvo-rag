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
    progress_callback=None
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
                "response_time": end_time - start_time,
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

def run_ragas_evaluation(
    evaluation_data: List[Dict[str, Any]], 
    openai_model: str = "gpt-4o",
    openai_api_key: Optional[str] = None,
    enable_reference_metrics: bool = False
) -> Dict[str, Any]:
    """Run RAGAS evaluation on the given data
    
    Args:
        evaluation_data: List of dictionaries with query, answer, contexts, ground_truths
        openai_model: OpenAI model to use for evaluation
        openai_api_key: OpenAI API key (will use env var if None)
        enable_reference_metrics: If True, enable metrics that require reference answers
        
    Returns:
        Dictionary with evaluation results or error
    """
    logger.info(f"Starting RAGAS evaluation with enable_reference_metrics={enable_reference_metrics}...")
    
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
        
        # Evaluate reference-based metrics if enabled and references are available
        logger.info(f"DEBUG: Reference metrics check - enable_reference_metrics: {enable_reference_metrics}, has_references: {has_references}")
        if enable_reference_metrics and has_references:
            logger.info("DEBUG: Starting evaluation of reference-based metrics...")
            
            # Answer Similarity - try multiple import approaches for RAGAS v0.2.15
            answer_sim_success = False
            try:
                # First try standard AnswerSimilarity
                try:
                    from ragas.metrics import AnswerSimilarity
                    answer_sim_metric = AnswerSimilarity()
                    metric_name = "AnswerSimilarity"
                    logger.info("DEBUG: Using AnswerSimilarity metric")
                except ImportError:
                    # Fallback to SemanticSimilarity if AnswerSimilarity doesn't exist
                    from ragas.metrics import SemanticSimilarity
                    answer_sim_metric = SemanticSimilarity()
                    metric_name = "SemanticSimilarity"
                    logger.info("DEBUG: Using SemanticSimilarity metric as fallback")
                
                from ragas import evaluate
                logger.info(f"DEBUG: Evaluating {metric_name} metric...")
                logger.info(f"DEBUG: Created {metric_name} metric, evaluating on dataset with {len(eval_dataset)} samples")
                
                # Check if dataset has required columns before evaluation
                dataset_df = eval_dataset.to_pandas()
                logger.info(f"DEBUG: Dataset columns before answer similarity evaluation: {list(dataset_df.columns)}")
                logger.info(f"DEBUG: Dataset has 'reference' column: {'reference' in dataset_df.columns}")
                if 'reference' in dataset_df.columns:
                    non_empty_refs = dataset_df['reference'].apply(lambda x: bool(str(x).strip())).sum()
                    logger.info(f"DEBUG: Non-empty references in dataset: {non_empty_refs}/{len(dataset_df)}")
                    logger.info(f"DEBUG: Sample reference value: {dataset_df['reference'].iloc[0] if len(dataset_df) > 0 else 'None'}")
                
                answer_sim_result = evaluate(eval_dataset, metrics=[answer_sim_metric], llm=eval_llm)
                logger.info(f"DEBUG: {metric_name} result type: {type(answer_sim_result)}")
                
                # Extract from pandas DataFrame
                df_result = answer_sim_result.to_pandas()
                logger.info(f"DEBUG: {metric_name} result columns: {list(df_result.columns)}")
                logger.info(f"DEBUG: {metric_name} result shape: {df_result.shape}")
                logger.info(f"DEBUG: {metric_name} result sample: {df_result.head().to_dict()}")
                
                # Try multiple possible column names based on metric type
                if metric_name == "SemanticSimilarity":
                    possible_columns = ['semantic_similarity', 'answer_similarity', 'similarity']
                else:
                    possible_columns = ['answer_similarity', 'semantic_similarity', 'similarity']
                
                found_column = None
                for col in possible_columns:
                    if col in df_result.columns:
                        found_column = col
                        break
                
                if found_column:
                    sim_values = df_result[found_column].tolist()
                    results["answer_similarity"] = sim_values
                    successful_metrics.append("answer_similarity")
                    answer_sim_success = True
                    logger.info(f"DEBUG: {metric_name} evaluation completed with values from column '{found_column}': {sim_values}")
                else:
                    # Try to find similar column names
                    sim_columns = [col for col in df_result.columns if 'similarity' in col.lower()]
                    logger.error(f"DEBUG: No similarity columns found in {metric_name} result. Available similarity columns: {sim_columns}")
                    logger.error(f"DEBUG: All available columns: {list(df_result.columns)}")
                    errors.append(f"answer_similarity: No similarity column found. Available: {list(df_result.columns)}")
                    
            except Exception as e:
                error_msg = f"answer_similarity: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Answer similarity evaluation error: {str(e)}")
                logger.error(f"DEBUG: Full error traceback for answer similarity:")
                import traceback
                logger.error(traceback.format_exc())
            
            # Answer Correctness - using correct RAGAS v0.2.15 API
            try:
                from ragas.metrics import AnswerCorrectness
                from ragas import evaluate
                logger.info("DEBUG: Evaluating answer correctness metric...")
                answer_corr_metric = AnswerCorrectness()  # No llm parameter needed
                answer_corr_result = evaluate(eval_dataset, metrics=[answer_corr_metric], llm=eval_llm)
                
                # Extract from pandas DataFrame
                df_result = answer_corr_result.to_pandas()
                logger.info(f"DEBUG: Answer correctness result columns: {list(df_result.columns)}")
                logger.info(f"DEBUG: Answer correctness result shape: {df_result.shape}")
                
                if 'answer_correctness' in df_result.columns:
                    corr_values = df_result['answer_correctness'].tolist()
                    results["answer_correctness"] = corr_values
                    successful_metrics.append("answer_correctness")
                    logger.info(f"DEBUG: Answer correctness evaluation completed with values: {corr_values}")
                else:
                    # Try to find similar column names
                    corr_columns = [col for col in df_result.columns if 'correctness' in col.lower()]
                    logger.error(f"DEBUG: answer_correctness column not found. Available correctness columns: {corr_columns}")
                    logger.error(f"DEBUG: All available columns: {list(df_result.columns)}")
                    errors.append(f"answer_correctness: Column not found. Available: {list(df_result.columns)}")
            except Exception as e:
                error_msg = f"answer_correctness: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Answer correctness evaluation error: {str(e)}")
            
            # Context Precision (with reference) - using correct RAGAS v0.2.15 API
            if has_contexts:
                try:
                    from ragas.metrics import ContextPrecision
                    from ragas import evaluate
                    logger.info("DEBUG: Evaluating context precision metric (with reference)...")
                    context_prec_metric = ContextPrecision()  # No llm parameter needed
                    context_prec_result = evaluate(eval_dataset, metrics=[context_prec_metric], llm=eval_llm)
                    
                    # Extract from pandas DataFrame
                    df_result = context_prec_result.to_pandas()
                    logger.info(f"DEBUG: Context precision result columns: {list(df_result.columns)}")
                    logger.info(f"DEBUG: Context precision result shape: {df_result.shape}")
                    
                    if 'context_precision' in df_result.columns:
                        prec_values = df_result['context_precision'].tolist()
                        results["context_precision"] = prec_values
                        successful_metrics.append("context_precision")
                        logger.info(f"DEBUG: Context precision evaluation completed with values: {prec_values}")
                    else:
                        # Try to find similar column names
                        prec_columns = [col for col in df_result.columns if 'precision' in col.lower()]
                        logger.error(f"DEBUG: context_precision column not found. Available precision columns: {prec_columns}")
                        logger.error(f"DEBUG: All available columns: {list(df_result.columns)}")
                        errors.append(f"context_precision: Column not found. Available: {list(df_result.columns)}")
                except Exception as e:
                    error_msg = f"context_precision: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Context precision evaluation error: {str(e)}")
                
                # Context Recall - using correct RAGAS v0.2.15 API
                try:
                    from ragas.metrics import ContextRecall
                    from ragas import evaluate
                    logger.info("DEBUG: Evaluating context recall metric...")
                    context_recall_metric = ContextRecall()  # No llm parameter needed
                    context_recall_result = evaluate(eval_dataset, metrics=[context_recall_metric], llm=eval_llm)
                    
                    # Extract from pandas DataFrame
                    df_result = context_recall_result.to_pandas()
                    logger.info(f"DEBUG: Context recall result columns: {list(df_result.columns)}")
                    logger.info(f"DEBUG: Context recall result shape: {df_result.shape}")
                    
                    if 'context_recall' in df_result.columns:
                        recall_values = df_result['context_recall'].tolist()
                        results["context_recall"] = recall_values
                        successful_metrics.append("context_recall")
                        logger.info(f"DEBUG: Context recall evaluation completed with values: {recall_values}")
                    else:
                        # Try to find similar column names
                        recall_columns = [col for col in df_result.columns if 'recall' in col.lower()]
                        logger.error(f"DEBUG: context_recall column not found. Available recall columns: {recall_columns}")
                        logger.error(f"DEBUG: All available columns: {list(df_result.columns)}")
                        errors.append(f"context_recall: Column not found. Available: {list(df_result.columns)}")
                except Exception as e:
                    error_msg = f"context_recall: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Context recall evaluation error: {str(e)}")
            else:
                logger.info("Skipping context-based reference metrics - no contexts available")
                errors.append("context_precision: No contexts available")
                errors.append("context_recall: No contexts available")
        elif enable_reference_metrics:
            logger.info("Reference metrics requested but no reference answers available")
            errors.append("answer_similarity: No reference answers available")
            errors.append("answer_correctness: No reference answers available")
            errors.append("context_precision: No reference answers available")
            errors.append("context_recall: No reference answers available")
        
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
    reference_answers: Optional[List[str]] = None,
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
        reference_answers: Optional list of reference answers for enhanced metrics
        progress_callback: Optional callback for query progress updates
        ragas_status_callback: Optional callback for RAGAS status updates
        
    Returns:
        Dictionary with evaluation results
    """
    # Validate inputs
    is_valid, error_msg = validate_queries_and_references(queries, reference_answers)
    if not is_valid:
        return {"error": error_msg}
    
    # Determine if we should enable reference metrics
    enable_reference_metrics = reference_answers is not None and any(ref.strip() for ref in reference_answers)
    logger.info(f"DEBUG: Reference metrics decision - reference_answers: {reference_answers is not None}, enable_reference_metrics: {enable_reference_metrics}")
    if reference_answers:
        logger.info(f"DEBUG: Reference answers count: {len(reference_answers)}, non-empty: {sum(1 for ref in reference_answers if ref.strip())}")
    
    # Generate RAG responses
    rag_results, logs = await generate_rag_responses(
        queries=queries,
        kb_name=kb_name,
        rag_api_url=rag_api_url,
        username=username,
        password=password,
        reference_answers=reference_answers,
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
        logger.info(f"DEBUG: Calling run_ragas_evaluation with enable_reference_metrics={enable_reference_metrics}")
        ragas_results = run_ragas_evaluation(
            evaluation_data=rag_results,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            enable_reference_metrics=enable_reference_metrics
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
    reference_answers: Optional[List[str]] = None,
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
        reference_answers: Optional list of reference answers for enhanced metrics
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
            reference_answers=reference_answers,
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