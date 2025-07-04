"""
RAGAS Setup Utility

This module provides a wrapper for the RAGAS setup functionality
to avoid circular imports and maintain clean separation.
"""

from typing import Tuple, List, Any, Optional


def setup_ragas(enable_reference_metrics: bool = False) -> Tuple[bool, List[Any], List[str], Optional[str]]:
    """
    Set up RAGAS metrics based on the evaluation mode.
    
    Args:
        enable_reference_metrics: Whether to include reference-based metrics
        
    Returns:
        Tuple of (ragas_available, metrics, metric_names, error_message)
    """
    # Import the original setup function from headless_evaluation
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from headless_evaluation import setup_ragas as original_setup_ragas
        return original_setup_ragas(enable_reference_metrics)
    except ImportError as e:
        error_message = f"Failed to import RAGAS setup: {str(e)}"
        return False, [], [], error_message
    except Exception as e:
        error_message = f"Error setting up RAGAS: {str(e)}"
        return False, [], [], error_message