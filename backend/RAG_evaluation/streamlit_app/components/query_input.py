"""
Query Input Components for RAG Evaluation

This module contains Streamlit components for handling query and reference
input including CSV upload, dynamic forms, and template downloads.
"""

import streamlit as st
import pandas as pd
from typing import List, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.session_state import SessionStateManager
from utils.csv_handling import CSVProcessor
from constants import UI_MESSAGES


class QueryInputManager:
    """Manages query and reference input for the RAG evaluation application."""
    
    @staticmethod
    def render_csv_upload_section(enable_reference_metrics: bool) -> Tuple[List[str], Optional[List[str]], any]:
        """
        Render CSV upload section with template download.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
            
        Returns:
            Tuple of (uploaded_queries, uploaded_references_or_none, uploaded_file)
        """
        st.write("**Option 1: Use CSV file**")
        
        # Template download button
        template_csv, template_filename, help_text = CSVProcessor.get_template_for_mode(enable_reference_metrics)
        
        st.download_button(
            label="📥 Download CSV Template",
            data=template_csv,
            file_name=template_filename,
            mime="text/csv",
            help=help_text,
            use_container_width=False
        )
        
        # File upload widget
        uploaded_file = st.file_uploader(
            "Upload your filled CSV file",
            type=['csv'],
            help="CSV should have a 'prompt' column with one query per row"
        )
        
        # Process uploaded file
        uploaded_queries = []
        uploaded_references = None
        
        if uploaded_file is not None:
            try:
                # Validate file
                is_valid, error_msg = CSVProcessor.validate_uploaded_file(uploaded_file)
                if not is_valid:
                    st.error(f"File validation failed: {error_msg}")
                    return [], None
                
                # Parse CSV
                df = pd.read_csv(uploaded_file)
                uploaded_queries, uploaded_references, parse_error = CSVProcessor.parse_csv_queries(df)
                
                if parse_error:
                    st.error(f"Error parsing CSV: {parse_error}")
                    uploaded_queries = []
                    uploaded_references = None
                else:
                    # Show success message with details
                    QueryInputManager._show_csv_success_message(
                        uploaded_queries, uploaded_references, enable_reference_metrics
                    )
                    
                    # Log processing results
                    CSVProcessor.log_csv_processing(
                        uploaded_queries, uploaded_references, enable_reference_metrics
                    )
                    
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")
                uploaded_queries = []
                uploaded_references = None
        
        return uploaded_queries, uploaded_references, uploaded_file
    
    @staticmethod
    def _show_csv_success_message(queries: List[str], references: Optional[List[str]], 
                                enable_reference_metrics: bool) -> None:
        """Show appropriate success message for CSV upload."""
        if references and any(ref.strip() for ref in references):
            ref_count = len([ref for ref in references if ref.strip()])
            st.success(UI_MESSAGES['csv_success_with_refs'].format(
                query_count=len(queries), ref_count=ref_count
            ))
            
            if enable_reference_metrics:
                st.success(UI_MESSAGES['full_mode_enabled'])
            else:
                st.warning(UI_MESSAGES['basic_mode_with_refs'])
        else:
            st.success(UI_MESSAGES['csv_success_no_refs'].format(query_count=len(queries)))
            if enable_reference_metrics:
                st.warning(UI_MESSAGES['full_mode_no_refs'])
    
    @staticmethod
    def handle_csv_population(uploaded_queries: List[str], uploaded_references: Optional[List[str]], 
                            uploaded_file, enable_reference_metrics: bool) -> None:
        """
        Handle population of dynamic fields from CSV upload.
        
        Args:
            uploaded_queries: Parsed queries from CSV
            uploaded_references: Parsed references from CSV
            uploaded_file: Streamlit uploaded file object
            enable_reference_metrics: Whether reference metrics are enabled
        """
        if uploaded_file is not None:
            # Check if this is a new file upload
            current_file_info = CSVProcessor.create_file_info_tuple(uploaded_file)
            
            if SessionStateManager.is_csv_change_detected(current_file_info):
                if uploaded_queries:  # Only populate if we successfully parsed queries
                    SessionStateManager.populate_from_csv(
                        uploaded_queries, uploaded_references, enable_reference_metrics
                    )
                    SessionStateManager.mark_csv_populated()
        else:
            # No file uploaded, reset tracking
            SessionStateManager.reset_csv_state()
    
    @staticmethod
    def render_manual_input_section(enable_reference_metrics: bool) -> None:
        """
        Render manual query input section with dynamic fields.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
        """
        st.write("**Option 2: Enter queries manually**")
        
        if enable_reference_metrics:
            QueryInputManager._render_full_mode_inputs()
        else:
            QueryInputManager._render_basic_mode_inputs()
    
    @staticmethod
    def _render_full_mode_inputs() -> None:
        """Render query and reference input pairs for full mode."""
        st.write("**Query and Reference Pairs**")
        st.caption("Each query should have a corresponding reference answer for full evaluation.")
        
        field_count = SessionStateManager.get_field_count()
        
        for i in range(field_count):
            field_id = st.session_state.field_ids[i]
            col1, col2, col3 = st.columns([5, 5, 1])
            
            with col1:
                query_key = f"query_{field_id}"
                st.session_state.dynamic_queries[i] = st.text_area(
                    f"Query {i+1}",
                    value=st.session_state.dynamic_queries[i],
                    height=100,
                    key=query_key,
                    help="Enter your question or prompt here"
                )
            
            with col2:
                ref_key = f"reference_{field_id}"
                st.session_state.dynamic_references[i] = st.text_area(
                    f"Reference Answer {i+1}",
                    value=st.session_state.dynamic_references[i],
                    height=100,
                    key=ref_key,
                    help="Enter the expected/correct answer for this query"
                )
            
            with col3:
                st.write("")
                st.write("")
                if field_count > 1:
                    if st.button("🗑️", key=f"remove_{field_id}", help="Remove this pair"):
                        if SessionStateManager.remove_field(i):
                            st.rerun()
        
        # Add new pair button
        if st.button("➕ Add Query/Reference Pair", key="add_pair"):
            SessionStateManager.add_field()
            st.rerun()
    
    @staticmethod
    def _render_basic_mode_inputs() -> None:
        """Render query-only inputs for basic mode."""
        st.write("**Queries**")
        st.caption("Enter your questions or prompts for evaluation.")
        
        field_count = SessionStateManager.get_field_count()
        
        for i in range(field_count):
            field_id = st.session_state.field_ids[i]
            col1, col2 = st.columns([9, 1])
            
            with col1:
                query_key = f"query_basic_{field_id}"
                st.session_state.dynamic_queries[i] = st.text_area(
                    f"Query {i+1}",
                    value=st.session_state.dynamic_queries[i],
                    height=80,
                    key=query_key,
                    help="Enter your question or prompt here"
                )
            
            with col2:
                st.write("")
                st.write("")
                if field_count > 1:
                    if st.button("🗑️", key=f"remove_basic_{field_id}", help="Remove this query"):
                        if SessionStateManager.remove_field(i):
                            st.rerun()
        
        # Add new query button
        if st.button("➕ Add Query", key="add_query"):
            SessionStateManager.add_field()
            st.rerun()
    
    @staticmethod
    def collect_and_validate_queries(enable_reference_metrics: bool) -> Tuple[List[str], Optional[List[str]]]:
        """
        Collect queries and references from dynamic fields and validate.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
            
        Returns:
            Tuple of (queries, reference_answers_or_none)
        """
        queries, reference_answers = SessionStateManager.get_queries_and_references(enable_reference_metrics)
        
        # Show summary
        if queries:
            QueryInputManager._show_query_summary(queries, reference_answers, enable_reference_metrics)
        else:
            st.warning(UI_MESSAGES['no_queries_entered'])
        
        # Update session state
        SessionStateManager.update_current_state(queries, reference_answers)
        
        return queries, reference_answers
    
    @staticmethod
    def _show_query_summary(queries: List[str], reference_answers: Optional[List[str]], 
                          enable_reference_metrics: bool) -> None:
        """Show summary of prepared queries and references."""
        if enable_reference_metrics and reference_answers:
            ref_count = len([ref for ref in reference_answers if ref])
            st.success(UI_MESSAGES['queries_prepared_with_refs'].format(
                query_count=len(queries), ref_count=ref_count
            ))
            
            if ref_count < len(queries):
                missing_count = len(queries) - ref_count
                st.warning(UI_MESSAGES['queries_missing_refs'].format(missing_count=missing_count))
        else:
            st.success(UI_MESSAGES['queries_prepared_basic'].format(query_count=len(queries)))
    
    @staticmethod
    def initialize_default_queries_if_needed() -> None:
        """Initialize default queries if dynamic fields are empty."""
        SessionStateManager.initialize_all_state()
        
        # Initialize with default queries if no CSV uploaded and fields are empty
        if (not st.session_state.dynamic_queries or 
            st.session_state.dynamic_queries == [""]):
            SessionStateManager.populate_from_csv(
                SessionStateManager._get_default_queries(), 
                None, 
                False
            )
    
    @staticmethod
    def _get_default_queries() -> List[str]:
        """Get default test queries from constants."""
        from constants import DEFAULT_TEST_QUERIES
        return DEFAULT_TEST_QUERIES[:]