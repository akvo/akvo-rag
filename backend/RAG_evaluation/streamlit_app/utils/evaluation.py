"""
Evaluation Orchestration Utilities for RAG Evaluation

This module provides utilities for orchestrating the evaluation process,
including progress tracking and result handling.
"""

import logging
from typing import List, Optional, Dict, Any, Callable

logger = logging.getLogger("rag_evaluation")


class EvaluationOrchestrator:
    """Orchestrates the evaluation process with progress tracking and error handling."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the evaluation orchestrator.
        
        Args:
            config: Configuration dictionary containing API settings
        """
        self.config = config
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set the progress update callback function."""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable):
        """Set the status update callback function."""
        self.status_callback = callback
    
    def update_progress(self, i: int, total: int, query: str, result: Dict[str, Any]):
        """Update progress during evaluation."""
        if self.progress_callback:
            self.progress_callback(i, total, query, result)
        
        # Log progress
        logger.info(f"Query {i+1}/{total} completed: {query[:100]}...")
        if 'error' in result:
            logger.error(f"Query {i+1} error: {result['error']}")
        else:
            response_len = len(result.get('response', ''))
            context_count = len(result.get('contexts', []))
            logger.info(f"Query {i+1} success: response_length={response_len}, contexts={context_count}")
    
    def update_status(self, message: str):
        """Update status message during evaluation."""
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"Status: {message}")
    
    def validate_configuration(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            bool: True if configuration is valid
        """
        required_fields = ['rag_api_url', 'username', 'password', 'kb_name']
        
        for field in required_fields:
            if not self.config.get(field):
                logger.error(f"Missing required configuration: {field}")
                return False
        
        return True
    
    def log_evaluation_start(self, queries: List[str], reference_answers: Optional[List[str]]):
        """Log evaluation start parameters."""
        logger.info("=== EVALUATION STARTING ===")
        logger.info(f"RAG API URL: {self.config.get('rag_api_url')}")
        logger.info(f"Username: {self.config.get('username')}")
        logger.info(f"Knowledge Base: {self.config.get('kb_name')}")
        logger.info(f"Number of queries: {len(queries)}")
        logger.info(f"OpenAI Model: {self.config.get('openai_model')}")
        logger.info(f"OpenAI API Key set: {'Yes' if self.config.get('openai_api_key') else 'No'}")
        logger.info(f"Reference answers provided: {reference_answers is not None}")
        if reference_answers:
            logger.info(f"Reference answers count: {len(reference_answers)}")
    
    def log_evaluation_complete(self, results: List[Dict[str, Any]]):
        """Log evaluation completion."""
        logger.info("=== EVALUATION COMPLETED ===")
        logger.info(f"Total results: {len(results)}")
        
        # Log summary statistics
        successful_queries = len([r for r in results if 'error' not in r])
        failed_queries = len(results) - successful_queries
        
        logger.info(f"Successful queries: {successful_queries}")
        logger.info(f"Failed queries: {failed_queries}")
        
        if results:
            # Log average response time if available
            response_times = [r.get('response_time', 0) for r in results if 'response_time' in r]
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                logger.info(f"Average response time: {avg_time:.2f} seconds")


def create_progress_tracker():
    """Create a simple progress tracking function for use with the orchestrator."""
    def progress_tracker(i: int, total: int, query: str, result: Dict[str, Any]):
        """Simple progress tracking function."""
        progress_percent = ((i + 1) / total) * 100
        status = "SUCCESS" if 'error' not in result else "ERROR"
        logger.info(f"Progress: {progress_percent:.1f}% - Query {i+1}/{total} - {status}")
    
    return progress_tracker


def create_status_tracker():
    """Create a simple status tracking function."""
    def status_tracker(message: str):
        """Simple status tracking function."""
        logger.info(f"Status Update: {message}")
    
    return status_tracker