"""
Centralized Session State Management for RAG Evaluation

This module provides a centralized way to initialize and manage
Streamlit session state for the RAG evaluation application.
"""

import streamlit as st
from typing import List, Optional, Any, Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from constants import DEFAULT_TEST_QUERIES


class SessionStateManager:
    """Manages Streamlit session state for the RAG evaluation application."""
    
    @staticmethod
    def initialize_all_state() -> None:
        """Initialize all session state variables with default values."""
        
        # Core evaluation state
        if "logs" not in st.session_state:
            st.session_state.logs = []
        if "results" not in st.session_state:
            st.session_state.results = []
        if "evaluation_running" not in st.session_state:
            st.session_state.evaluation_running = False
            
        # Configuration state
        if "selected_kb" not in st.session_state:
            st.session_state.selected_kb = ""
            
        # RAGAS state
        if "ragas_metrics" not in st.session_state:
            st.session_state.ragas_metrics = []
        if "ragas_available" not in st.session_state:
            st.session_state.ragas_available = False
        if "ragas_import_error" not in st.session_state:
            st.session_state.ragas_import_error = None
        if "ragas_metric_names" not in st.session_state:
            st.session_state.ragas_metric_names = []
            
        # Evaluation mode state
        if "enable_reference_metrics" not in st.session_state:
            st.session_state.enable_reference_metrics = False
        if "last_ragas_mode" not in st.session_state:
            st.session_state.last_ragas_mode = False
            
        # Dynamic input fields state
        SessionStateManager._initialize_dynamic_fields()
        
        # CSV handling state
        if "last_uploaded_file" not in st.session_state:
            st.session_state.last_uploaded_file = None
        if "csv_populated" not in st.session_state:
            st.session_state.csv_populated = False
            
        # Current query state
        if "current_queries" not in st.session_state:
            st.session_state.current_queries = []
        if "current_references" not in st.session_state:
            st.session_state.current_references = None
    
    @staticmethod
    def _initialize_dynamic_fields() -> None:
        """Initialize dynamic field management state."""
        if "dynamic_queries" not in st.session_state:
            st.session_state.dynamic_queries = DEFAULT_TEST_QUERIES[:]
        if "dynamic_references" not in st.session_state:
            st.session_state.dynamic_references = ["" for _ in DEFAULT_TEST_QUERIES]
        if "next_field_id" not in st.session_state:
            st.session_state.next_field_id = len(DEFAULT_TEST_QUERIES)
        if "field_ids" not in st.session_state:
            st.session_state.field_ids = list(range(len(DEFAULT_TEST_QUERIES)))
    
    @staticmethod
    def reset_evaluation_state() -> None:
        """Reset evaluation-related state for a fresh start."""
        st.session_state.logs = []
        st.session_state.results = []
        st.session_state.evaluation_running = False
        st.session_state.current_queries = []
        st.session_state.current_references = None
    
    @staticmethod
    def get_field_count() -> int:
        """Get the current number of dynamic fields."""
        return len(st.session_state.dynamic_queries)
    
    @staticmethod
    def add_field() -> None:
        """Add a new query/reference field pair."""
        st.session_state.dynamic_queries.append("")
        st.session_state.dynamic_references.append("")
        st.session_state.field_ids.append(st.session_state.next_field_id)
        st.session_state.next_field_id += 1
    
    @staticmethod
    def remove_field(index: int) -> bool:
        """
        Remove a field pair at the given index.
        
        Args:
            index: Index of the field to remove
            
        Returns:
            bool: True if field was removed, False if minimum count reached
        """
        if len(st.session_state.dynamic_queries) > 1:
            st.session_state.dynamic_queries.pop(index)
            st.session_state.dynamic_references.pop(index)
            st.session_state.field_ids.pop(index)
            return True
        return False
    
    @staticmethod
    def populate_from_csv(queries_list: List[str], 
                         references_list: Optional[List[str]] = None,
                         enable_reference_metrics: bool = False) -> None:
        """
        Populate dynamic fields from CSV upload.
        
        Args:
            queries_list: List of query strings
            references_list: Optional list of reference answers
            enable_reference_metrics: Whether reference metrics are enabled
        """
        st.session_state.dynamic_queries = queries_list[:] if queries_list else [""]
        
        if references_list and enable_reference_metrics:
            # Ensure same length
            refs = references_list[:]
            while len(refs) < len(st.session_state.dynamic_queries):
                refs.append("")
            st.session_state.dynamic_references = refs
        else:
            st.session_state.dynamic_references = ["" for _ in st.session_state.dynamic_queries]
        
        # Reset field IDs for CSV data
        st.session_state.field_ids = list(range(len(st.session_state.dynamic_queries)))
        st.session_state.next_field_id = len(st.session_state.dynamic_queries)
    
    @staticmethod
    def get_queries_and_references(enable_reference_metrics: bool = False) -> tuple[List[str], Optional[List[str]]]:
        """
        Get current queries and references from session state.
        
        Args:
            enable_reference_metrics: Whether to include reference answers
            
        Returns:
            Tuple of (queries, reference_answers or None)
        """
        queries = [q.strip() for q in st.session_state.dynamic_queries if q.strip()]
        
        if enable_reference_metrics:
            reference_answers = [r.strip() for r in st.session_state.dynamic_references]
            # Ensure same length
            while len(reference_answers) < len(queries):
                reference_answers.append("")
            reference_answers = reference_answers[:len(queries)]
            return queries, reference_answers
        else:
            return queries, None
    
    @staticmethod
    def update_current_state(queries: List[str], references: Optional[List[str]] = None) -> None:
        """
        Update the current queries and references in session state.
        
        Args:
            queries: List of query strings
            references: Optional list of reference answers
        """
        st.session_state.current_queries = queries
        st.session_state.current_references = references
    
    @staticmethod
    def is_csv_change_detected(file_info: Optional[tuple]) -> bool:
        """
        Check if a new CSV file has been uploaded.
        
        Args:
            file_info: Tuple of (filename, size) or None
            
        Returns:
            bool: True if this is a new file upload
        """
        if file_info != st.session_state.last_uploaded_file:
            st.session_state.last_uploaded_file = file_info
            return True
        return False
    
    @staticmethod
    def mark_csv_populated() -> None:
        """Mark that CSV data has been populated into the fields."""
        st.session_state.csv_populated = True
    
    @staticmethod
    def reset_csv_state() -> None:
        """Reset CSV-related state when no file is uploaded."""
        st.session_state.last_uploaded_file = None
        st.session_state.csv_populated = False
    
    @staticmethod
    def update_ragas_state(available: bool, metrics: List[Any], 
                          metric_names: List[str], error_message: Optional[str] = None) -> None:
        """
        Update RAGAS-related session state.
        
        Args:
            available: Whether RAGAS is available
            metrics: List of RAGAS metric objects
            metric_names: List of metric names
            error_message: Optional error message if RAGAS failed to initialize
        """
        st.session_state.ragas_available = available
        st.session_state.ragas_metrics = metrics
        st.session_state.ragas_metric_names = metric_names if available else []
        st.session_state.ragas_import_error = error_message
    
    @staticmethod
    def should_reinitialize_ragas(enable_reference_metrics: bool) -> bool:
        """
        Check if RAGAS should be reinitialized due to mode change.
        
        Args:
            enable_reference_metrics: Current reference metrics setting
            
        Returns:
            bool: True if RAGAS should be reinitialized
        """
        return (not st.session_state.ragas_available or 
                st.session_state.get('last_ragas_mode') != enable_reference_metrics)
    
    @staticmethod
    def update_ragas_mode(enable_reference_metrics: bool) -> None:
        """Update the last RAGAS mode setting."""
        st.session_state.last_ragas_mode = enable_reference_metrics
        st.session_state.enable_reference_metrics = enable_reference_metrics
    
    @staticmethod
    def get_state_summary() -> Dict[str, Any]:
        """
        Get a summary of current session state for debugging.
        
        Returns:
            Dict containing key session state information
        """
        return {
            'query_count': len(st.session_state.get('dynamic_queries', [])),
            'results_count': len(st.session_state.get('results', [])),
            'evaluation_running': st.session_state.get('evaluation_running', False),
            'ragas_available': st.session_state.get('ragas_available', False),
            'enable_reference_metrics': st.session_state.get('enable_reference_metrics', False),
            'csv_populated': st.session_state.get('csv_populated', False)
        }