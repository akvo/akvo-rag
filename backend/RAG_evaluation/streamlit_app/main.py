"""
Main Entry Point for Modular RAG Evaluation Streamlit Application

This is the new modular entry point that replaces the monolithic app.py file.
Run this with: streamlit run streamlit_app/main.py
"""

import streamlit as st
import asyncio
import logging
import time
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
    evaluation_mode = ConfigurationManager.render_mode_selection()
    enable_reference_metrics = evaluation_mode in ['full', 'reference-only']
    
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
    evaluation_mode = st.session_state.get('evaluation_mode', 'full')
    csv_data = CSVProcessor.generate_results_csv(st.session_state.results, metrics_mode=evaluation_mode)
    
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
        return
    
    # Validate reference-only mode requirements
    evaluation_mode = st.session_state.get('evaluation_mode', 'full')
    if evaluation_mode == 'reference-only':
        if not reference_answers or not any(ref.strip() for ref in reference_answers if ref):
            st.error("❌ Reference-only mode requires reference answers. Please upload a CSV with reference answers or switch to a different evaluation mode.")
            return
    
    # Proceed with evaluation
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
        # Get evaluation mode from session state
        evaluation_mode = st.session_state.get('evaluation_mode', 'full')
        
        # Track total evaluation time
        eval_start_time = time.time()
        
        # Run evaluation with performance settings
        eval_results = await evaluate_queries(
            queries=queries,
            kb_name=config['kb_name'],
            openai_model=config['openai_model'],
            openai_api_key=config['openai_api_key'],
            rag_api_url=config['rag_api_url'],
            username=config['username'],
            password=config['password'],
            reference_answers=reference_answers,
            metrics_mode=evaluation_mode,
            progress_callback=update_progress,
            ragas_status_callback=update_ragas_status,
            use_batch_processing=config.get('use_batch_processing', True),
            batch_size=config.get('batch_size', 5),
            max_concurrent=config.get('max_concurrent', 3)
        )
        
        # Calculate total evaluation time
        total_eval_time = time.time() - eval_start_time
        
        # Store results and performance data
        rag_results = eval_results.get("rag_results", [])
        st.session_state.results = rag_results
        st.session_state.logs = eval_results.get("logs", [])
        
        # Store performance data for detailed display
        if "performance_summary" in eval_results:
            st.session_state.performance_data = eval_results["performance_summary"]
            logger.info(f"🐛 Stored performance data keys: {list(st.session_state.performance_data.keys())}")
        else:
            st.session_state.performance_data = {}
            logger.info("🐛 No performance_summary in eval_results")
        
        # Show detailed performance summary 
        if "performance_summary" in eval_results:
            perf = eval_results["performance_summary"]
            
            # Main performance summary
            st.success(f"⚡ **Performance**: {perf['total_duration']:.1f}s total "
                      f"({perf['avg_query_time']:.1f}s/query) • "
                      f"Peak memory: {perf['peak_memory_mb']:.0f}MB • "
                      f"API calls: {perf['openai_api_calls']}")
            
            # Detailed timing breakdown
            rag_time = perf.get('rag_api_time', 0)
            ragas_time = perf.get('ragas_eval_time', 0)
            
            if rag_time > 0 or ragas_time > 0:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "🔍 RAG API Time", 
                        f"{rag_time:.1f}s",
                        help="Time spent generating RAG responses from your knowledge base"
                    )
                
                with col2:
                    st.metric(
                        "📊 Metrics Evaluation Time", 
                        f"{ragas_time:.1f}s",
                        help="Time spent evaluating all metrics for all queries using RAGAS"
                    )
                
                with col3:
                    avg_metrics_time = ragas_time / len(queries) if queries and ragas_time > 0 else 0
                    st.metric(
                        "📈 Avg Metrics Time/Query", 
                        f"{avg_metrics_time:.1f}s",
                        help="Average time to evaluate all metrics for a single query"
                    )
        else:
            # Fallback to basic timing if no performance summary
            avg_time = total_eval_time / len(queries) if queries else 0
            st.success(f"⚡ **Evaluation Complete**: {total_eval_time:.1f}s total "
                      f"({avg_time:.1f}s/query) • "
                      f"{len(queries)} queries processed")
        
        # Update completion status
        progress_bar.progress(1.0)
        status_text.text(f"✅ Evaluation completed in {total_eval_time:.1f} seconds")
        
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