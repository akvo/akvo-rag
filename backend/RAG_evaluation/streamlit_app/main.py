"""
Main Entry Point for Modular RAG Evaluation Streamlit Application

This is the new modular entry point that replaces the monolithic app.py file.
Run this with: streamlit run streamlit_app/main.py
"""

import streamlit as st
import asyncio
import logging
from typing import List, Optional

# Import our modular components
import sys
import os
sys.path.append(os.path.dirname(__file__))
from components.configuration import ConfigurationManager, initialize_ragas_if_needed
from components.metrics_explanation import MetricsExplanationManager
from components.query_input import QueryInputManager
from utils.session_state import SessionStateManager
from utils.csv_handling import CSVProcessor
from constants import UI_MESSAGES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_evaluation")

# Configure Streamlit page
st.set_page_config(
    page_title="RAG Evaluation Dashboard", 
    page_icon="📊", 
    layout="wide"
)

def main():
    """Main application function."""
    
    # Page title and description
    st.title("RAG Evaluation Dashboard")
    st.markdown("Evaluate your RAG system responses using comprehensive RAGAS metrics including faithfulness, relevancy, and context precision.")
    
    # Initialize session state
    SessionStateManager.initialize_all_state()
    
    # Render main metrics explanation
    MetricsExplanationManager.render_main_explanation()
    
    # Render sidebar configuration
    config = ConfigurationManager.render_sidebar_config()
    
    # Render RAGAS status
    ConfigurationManager.render_ragas_status()
    
    # Main content area
    st.subheader("Test Queries")
    
    # Evaluation mode selection
    enable_reference_metrics = ConfigurationManager.render_mode_selection()
    
    # Initialize RAGAS if needed
    initialize_ragas_if_needed(enable_reference_metrics)
    
    # CSV upload section
    uploaded_queries, uploaded_references, uploaded_file = QueryInputManager.render_csv_upload_section(enable_reference_metrics)
    
    # Handle CSV population
    QueryInputManager.handle_csv_population(
        uploaded_queries, uploaded_references, uploaded_file, enable_reference_metrics
    )
    
    # Initialize default queries if needed
    QueryInputManager.initialize_default_queries_if_needed()
    
    # Manual input section
    QueryInputManager.render_manual_input_section(enable_reference_metrics)
    
    # Collect and validate queries
    queries, reference_answers = QueryInputManager.collect_and_validate_queries(enable_reference_metrics)
    
    # Evaluation controls
    render_evaluation_controls(config, queries, reference_answers)
    
    # Display results if available
    if st.session_state.results:
        render_results_section()

def render_evaluation_controls(config, queries, reference_answers):
    """Render evaluation control buttons."""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        run_button = st.button("Run Evaluation", disabled=st.session_state.evaluation_running)
    
    with col2:
        if st.session_state.results and not st.session_state.evaluation_running:
            render_download_button()
        else:
            help_text = ("Evaluation in progress..." if st.session_state.evaluation_running 
                        else "Run evaluation first to download results")
            st.button("📥 Download Results (CSV)", disabled=True, help=help_text)
    
    # Handle evaluation execution
    if run_button:
        handle_evaluation_execution(config, queries, reference_answers)

def render_download_button():
    """Render the download results button."""
    enable_ref_metrics = st.session_state.get('enable_reference_metrics', False)
    csv_data = CSVProcessor.generate_results_csv(st.session_state.results, enable_ref_metrics)
    
    if csv_data:
        filename = CSVProcessor.get_results_filename()
        st.download_button(
            label="📥 Download Results (CSV)",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help="Download evaluation results as CSV file"
        )
    else:
        st.button("📥 Download Results (CSV)", disabled=True, help="CSV generation failed")

def handle_evaluation_execution(config, queries, reference_answers):
    """Handle evaluation execution with proper validation."""
    logger.info("=== RUN EVALUATION BUTTON CLICKED ===")
    ConfigurationManager.log_configuration(config, logger)
    logger.info(f"Number of queries: {len(queries)}")
    
    # Validate configuration
    is_valid, missing_fields = ConfigurationManager.validate_configuration(config)
    
    if not is_valid:
        error_msg = UI_MESSAGES['missing_fields'].format(fields=', '.join(missing_fields))
        logger.error(error_msg)
        st.error(error_msg)
    else:
        try:
            # Set up environment
            ConfigurationManager.setup_openai_environment(config['openai_api_key'])
            
            # Run evaluation
            asyncio.run(run_evaluation_async(config, queries, reference_answers))
        except Exception as e:
            logger.error(f"Error in evaluation execution: {str(e)}")
            st.error(f"Evaluation failed: {str(e)}")
        finally:
            st.session_state.evaluation_running = False
            st.rerun()

async def run_evaluation_async(config, queries, reference_answers):
    """Run the actual evaluation asynchronously."""
    # Import here to avoid circular imports
    import sys
    import os
    # Get the parent directory of streamlit_app (which is RAG_evaluation)
    rag_eval_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(rag_eval_dir)
    from headless_evaluation import evaluate_queries
    
    st.session_state.evaluation_running = True
    SessionStateManager.reset_evaluation_state()
    
    # Set up progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(UI_MESSAGES['evaluation_starting'])
    
    def update_progress(i, total, query, result):
        progress_bar.progress((i + 1) / total)
        status_text.text(f"Processing query {i+1}/{total}: {query[:50]}...")
        
        # Update results in session state
        if len(st.session_state.results) <= i:
            st.session_state.results.append(result)
        else:
            st.session_state.results[i] = result
    
    def update_ragas_status(message):
        status_text.text(message)
        logger.info(f"RAGAS Status: {message}")
    
    try:
        # Run evaluation
        eval_results = await evaluate_queries(
            queries=queries,
            kb_name=config['kb_name'],
            openai_model=config['openai_model'],
            openai_api_key=config['openai_api_key'],
            rag_api_url=config['rag_api_url'],
            username=config['username'],
            password=config['password'],
            reference_answers=reference_answers,
            progress_callback=update_progress,
            ragas_status_callback=update_ragas_status
        )
        
        # Store results
        rag_results = eval_results.get("rag_results", [])
        st.session_state.results = rag_results
        st.session_state.logs = eval_results.get("logs", [])
        
        # Update completion status
        progress_bar.progress(1.0)
        status_text.text(UI_MESSAGES['evaluation_complete'])
        
    except Exception as e:
        logger.error(f"Error in evaluation: {str(e)}")
        status_text.text(f"Error: {str(e)}")
        raise

def render_results_section():
    """Render the results display section."""
    # Import here to avoid circular dependency issues during development
    try:
        from components.results_display import ResultsDisplayManager
        ResultsDisplayManager.render_all_results()
    except ImportError as e:
        # Fallback to basic results display
        logger.error(f"Failed to import ResultsDisplayManager: {e}")
        st.subheader("Evaluation Results")
        st.write(f"Found {len(st.session_state.results)} results")
        
        # Basic results table
        if st.session_state.results:
            import pandas as pd
            results_df = pd.DataFrame(st.session_state.results)
            st.dataframe(results_df, use_container_width=True)

if __name__ == "__main__":
    main()