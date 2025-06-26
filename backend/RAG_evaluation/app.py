"""
Streamlit application for RAG evaluation.

This module provides a Streamlit-based UI for evaluating RAG responses
from the Akvo RAG system.
"""

import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from typing import List, Dict, Any, Optional
import json
import os
import logging
from datetime import datetime
import io

# Set up logging for the evaluation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_evaluation")

# Import our evaluation logic
from headless_evaluation import (
    DEFAULT_TEST_QUERIES,
    setup_ragas,
    evaluate_queries
)

# Set page title and initialize session state
st.set_page_config(page_title="RAG Evaluation Dashboard", page_icon="📊", layout="wide")
st.title("RAG Evaluation Dashboard")
st.markdown("Evaluate your RAG system responses using comprehensive RAGAS metrics including faithfulness, relevancy, and context precision.")

# Initialize session state
if "logs" not in st.session_state:
    st.session_state.logs = []
if "results" not in st.session_state:
    st.session_state.results = []
if "evaluation_running" not in st.session_state:
    st.session_state.evaluation_running = False
if "selected_kb" not in st.session_state:
    st.session_state.selected_kb = ""
if "ragas_metrics" not in st.session_state:
    st.session_state.ragas_metrics = []
if "ragas_available" not in st.session_state:
    st.session_state.ragas_available = False
if "ragas_import_error" not in st.session_state:
    st.session_state.ragas_import_error = None

# Dynamic input fields session state
if "dynamic_queries" not in st.session_state:
    st.session_state.dynamic_queries = [""]
if "dynamic_references" not in st.session_state:
    st.session_state.dynamic_references = [""]
if "field_counter" not in st.session_state:
    st.session_state.field_counter = 1
if "next_field_id" not in st.session_state:
    st.session_state.next_field_id = 0
if "field_ids" not in st.session_state:
    st.session_state.field_ids = [0]
if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None
if "csv_populated" not in st.session_state:
    st.session_state.csv_populated = False

# Configuration section
st.sidebar.header("Configuration")

# Connection settings
st.sidebar.subheader("Connection Settings")
rag_api_url = st.sidebar.text_input("RAG API URL", "http://localhost:8000").strip()
username = st.sidebar.text_input("Username", placeholder="Enter username").strip()
password = st.sidebar.text_input("Password", type="password", placeholder="Enter password")

# Knowledge base selection
st.sidebar.subheader("Knowledge Base")
kb_name = st.sidebar.text_input("Knowledge Base Name", placeholder="Enter your knowledge base name").strip()
st.session_state.selected_kb = kb_name

# RAGAS setup
def initialize_ragas(enable_reference_metrics=False):
    """Initialize RAGAS and check available metrics."""
    ragas_available, metrics, metric_names, error_message = setup_ragas(enable_reference_metrics)
    st.session_state.ragas_available = ragas_available
    st.session_state.ragas_metrics = metrics
    st.session_state.ragas_metric_names = metric_names if ragas_available else []
    st.session_state.ragas_import_error = error_message

# LLM for evaluation
st.sidebar.subheader("Evaluation LLM")
openai_api_key = st.sidebar.text_input("OpenAI API Key", os.environ.get("OPENAI_API_KEY", ""), type="password")
openai_model = st.sidebar.selectbox("Evaluation Model", ["gpt-4o", "gpt-4", "gpt-3.5-turbo-16k"], index=0)

# Check if RAGAS is available - reinitialize when mode changes
if (not st.session_state.ragas_available and not st.session_state.ragas_import_error) or \
   False:  # Disabled for now - will initialize after mode is determined
    with st.spinner("Setting up RAGAS..."):
        initialize_ragas(False)  # Initialize with basic metrics first
        st.session_state.last_reference_mode = False

# Display RAGAS status
if st.session_state.ragas_import_error:
    st.sidebar.error(st.session_state.ragas_import_error)
elif st.session_state.ragas_available:
    st.sidebar.success("✅ RAGAS evaluation ready")
    with st.sidebar.expander("Available Metrics", expanded=False):
        st.write("• **Faithfulness**: Response grounding in context")
        st.write("• **Answer Relevancy**: Response relevance to query")
        st.write("• **Context Relevancy**: Context relevance to query")
        st.write("• **Context Precision**: Context retrieval precision")

# Test queries
st.subheader("Test Queries")

# Mode selection
col1, col2 = st.columns([1, 3])
with col1:
    evaluation_mode = st.radio(
        "Evaluation Mode",
        ["Basic (4 metrics)", "Full (8 metrics)"],
        help="Basic: Uses 4 reference-free metrics. Full: Uses 8 metrics including reference-based ones."
    )

with col2:
    if evaluation_mode == "Full (8 metrics)":
        st.info("💡 Full mode requires reference answers for enhanced metrics like Answer Similarity and Answer Correctness.")
    else:
        st.info("ℹ️ Basic mode evaluates responses without requiring reference answers.")

enable_reference_metrics = evaluation_mode == "Full (8 metrics)"

# Store mode in session state
if "enable_reference_metrics" not in st.session_state:
    st.session_state.enable_reference_metrics = False
st.session_state.enable_reference_metrics = enable_reference_metrics

# Initialize or reinitialize RAGAS with the correct mode
if not st.session_state.ragas_available or st.session_state.get('last_ragas_mode') != enable_reference_metrics:
    with st.spinner("Setting up RAGAS metrics..."):
        initialize_ragas(enable_reference_metrics)
        st.session_state.last_ragas_mode = enable_reference_metrics

# CSV upload option with template download
st.write("**Option 1: Use CSV file**")

# Template CSV download button (above upload for better workflow)
def load_template(template_name: str) -> str:
    """Load template content from templates directory."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Template file not found: {template_path}")
        # Fallback to hardcoded content
        if template_name == "full_template.csv":
            return "prompt,reference_answer\nWhat is your first question?,This is the expected answer to the first question.\nWhat is your second question?,This is the expected answer to the second question.\nWhat is your third question?,This is the expected answer to the third question."
        else:
            return "prompt\nWhat is your first question?\nWhat is your second question?\nWhat is your third question?"

if enable_reference_metrics:
    template_csv = load_template("full_template.csv")
    template_filename = "query_template_with_references.csv"
    help_text = "Download a CSV template with reference answers for full evaluation mode"
else:
    template_csv = load_template("basic_template.csv")
    template_filename = "query_template_basic.csv"
    help_text = "Download a basic CSV template for queries only"

st.download_button(
    label="📥 Download CSV Template",
    data=template_csv,
    file_name=template_filename,
    mime="text/csv",
    help=help_text,
    use_container_width=False
)

# Upload widget below the template download
uploaded_file = st.file_uploader(
    "Upload your filled CSV file",
    type=['csv'],
    help="CSV should have a 'prompt' column with one query per row"
)

# Initialize queries from uploaded file or default
uploaded_queries = []
uploaded_references = None
if uploaded_file is not None:
    try:
        import pandas as pd
        from headless_evaluation import parse_csv_queries

        df = pd.read_csv(uploaded_file)
        uploaded_queries, uploaded_references, error_msg = parse_csv_queries(df)

        if error_msg:
            st.error(f"Error parsing CSV: {error_msg}")
            uploaded_queries = []
            uploaded_references = None
        else:
            # Show success message with details
            if uploaded_references and any(ref.strip() for ref in uploaded_references):
                ref_count = len([ref for ref in uploaded_references if ref.strip()])
                st.success(f"✅ Loaded {len(uploaded_queries)} queries with {ref_count} reference answers from CSV")

                if enable_reference_metrics:
                    st.success("🎯 Full evaluation mode enabled with reference answers!")
                else:
                    st.warning("⚠️ Reference answers found but Basic mode selected. Switch to Full mode to use reference-based metrics.")
            else:
                st.success(f"✅ Loaded {len(uploaded_queries)} queries from CSV (no reference answers)")
                if enable_reference_metrics:
                    st.warning("⚠️ Full mode selected but no reference answers found in CSV. Only basic metrics will be available.")

            # Show preview of uploaded content
            with st.expander("Preview uploaded content", expanded=False):
                for i, query in enumerate(uploaded_queries[:5], 1):
                    st.write(f"**Q{i}:** {query}")
                    if uploaded_references and i-1 < len(uploaded_references) and uploaded_references[i-1].strip():
                        st.write(f"**Ref:** {uploaded_references[i-1]}")
                    st.write("---")
                if len(uploaded_queries) > 5:
                    st.write(f"... and {len(uploaded_queries) - 5} more queries")

        # Note: Dynamic fields will be populated automatically via populate_from_csv()
        # No need for default text formatting since we're using individual input fields
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        default_queries_text = "\n".join(DEFAULT_TEST_QUERIES)
        default_references_text = ""
        uploaded_queries = []
        uploaded_references = None
else:
    # Initialize with default queries if no CSV uploaded
    if not st.session_state.dynamic_queries or st.session_state.dynamic_queries == [""]:
        st.session_state.dynamic_queries = DEFAULT_TEST_QUERIES[:]
        st.session_state.dynamic_references = ["" for _ in DEFAULT_TEST_QUERIES]
        st.session_state.field_counter = len(DEFAULT_TEST_QUERIES)
        st.session_state.field_ids = list(range(len(DEFAULT_TEST_QUERIES)))
        st.session_state.next_field_id = len(DEFAULT_TEST_QUERIES)

# Helper functions for dynamic fields
def populate_from_csv(queries_list, references_list=None):
    """Populate dynamic fields from CSV upload"""
    st.session_state.dynamic_queries = queries_list[:] if queries_list else [""]
    if references_list and enable_reference_metrics:
        # Ensure same length
        refs = references_list[:]
        while len(refs) < len(st.session_state.dynamic_queries):
            refs.append("")
        st.session_state.dynamic_references = refs
    else:
        st.session_state.dynamic_references = ["" for _ in st.session_state.dynamic_queries]
    st.session_state.field_counter = len(st.session_state.dynamic_queries)
    # Reset field IDs for CSV data
    st.session_state.field_ids = list(range(len(st.session_state.dynamic_queries)))
    st.session_state.next_field_id = len(st.session_state.dynamic_queries)

def add_field():
    """Add a new query/reference field pair"""
    st.session_state.dynamic_queries.append("")
    st.session_state.dynamic_references.append("")
    st.session_state.field_ids.append(st.session_state.next_field_id)
    st.session_state.next_field_id += 1
    st.session_state.field_counter += 1

def remove_field(index):
    """Remove a field pair at the given index"""
    if len(st.session_state.dynamic_queries) > 1:  # Keep at least one field
        st.session_state.dynamic_queries.pop(index)
        st.session_state.dynamic_references.pop(index)
        st.session_state.field_ids.pop(index)
        st.session_state.field_counter = len(st.session_state.dynamic_queries)

# Populate from CSV if uploaded (only once per new file)
if uploaded_file is not None:
    # Check if this is a new file upload
    current_file_info = (uploaded_file.name, uploaded_file.size) if uploaded_file else None
    if current_file_info != st.session_state.last_uploaded_file:
        st.session_state.last_uploaded_file = current_file_info
        if uploaded_queries:  # Only populate if we successfully parsed queries
            populate_from_csv(uploaded_queries, uploaded_references)
            st.session_state.csv_populated = True
else:
    # No file uploaded, reset tracking
    st.session_state.last_uploaded_file = None
    st.session_state.csv_populated = False

st.write("**Option 2: Enter queries manually**")

# Dynamic input fields
if enable_reference_metrics:
    # Full mode: Query + Reference pairs
    st.write("**Query and Reference Pairs**")
    st.caption("Each query should have a corresponding reference answer for full evaluation.")

    for i in range(len(st.session_state.dynamic_queries)):
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
            if len(st.session_state.dynamic_queries) > 1:
                if st.button("🗑️", key=f"remove_{field_id}", help="Remove this pair"):
                    remove_field(i)
                    st.rerun()

    # Add new pair button
    if st.button("➕ Add Query/Reference Pair", key="add_pair"):
        add_field()
        st.rerun()

else:
    # Basic mode: Queries only
    st.write("**Queries**")
    st.caption("Enter your questions or prompts for evaluation.")

    for i in range(len(st.session_state.dynamic_queries)):
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
            if len(st.session_state.dynamic_queries) > 1:
                if st.button("🗑️", key=f"remove_basic_{field_id}", help="Remove this query"):
                    remove_field(i)
                    st.rerun()

    # Add new query button
    if st.button("➕ Add Query", key="add_query"):
        add_field()
        st.rerun()

# Collect queries and references from dynamic fields
queries = [q.strip() for q in st.session_state.dynamic_queries if q.strip()]
if enable_reference_metrics:
    reference_answers = [r.strip() for r in st.session_state.dynamic_references]
    # Ensure same length
    while len(reference_answers) < len(queries):
        reference_answers.append("")
    reference_answers = reference_answers[:len(queries)]
else:
    reference_answers = None

# Show summary
if queries:
    if enable_reference_metrics and reference_answers:
        ref_count = len([ref for ref in reference_answers if ref])
        st.success(f"✅ {len(queries)} queries prepared with {ref_count} reference answers")
        if ref_count < len(queries):
            st.warning(f"⚠️ {len(queries) - ref_count} queries missing reference answers")
    else:
        st.success(f"✅ {len(queries)} queries prepared for basic evaluation")
else:
    st.warning("⚠️ No queries entered")

# Store in session state for evaluation
st.session_state.current_queries = queries
st.session_state.current_references = reference_answers

# Function to run evaluation
async def run_evaluation(queries: List[str], kb_name: str, reference_answers: Optional[List[str]] = None):
    """Run RAG evaluation on the given queries"""
    st.session_state.evaluation_running = True
    st.session_state.logs = []
    st.session_state.results = []

    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Starting evaluation...")

    # Add comprehensive logging
    logger.info(f"=== STREAMLIT EVALUATION STARTING ===")
    logger.info(f"RAG API URL: {rag_api_url}")
    logger.info(f"Username: {username}")
    logger.info(f"Knowledge Base: {kb_name}")
    logger.info(f"Number of queries: {len(queries)}")
    logger.info(f"OpenAI API Key set: {'Yes' if openai_api_key else 'No'}")

    # Progress callback to update the UI during evaluation
    def update_progress(i, total, query, result):
        # Update progress bar
        progress_bar.progress((i + 1) / total)
        # Update status text
        status_text.text(f"Processing query {i+1}/{total}: {query[:50]}...")
        # Log progress details
        logger.info(f"Query {i+1}/{total} completed: {query[:100]}...")
        if 'error' in result:
            logger.error(f"Query {i+1} error: {result['error']}")
        else:
            logger.info(f"Query {i+1} success: response_length={len(result.get('response', ''))}, contexts={len(result.get('contexts', []))}")
        # Update results in session state
        if len(st.session_state.results) <= i:
            st.session_state.results.append(result)
        else:
            st.session_state.results[i] = result

    # RAGAS status callback
    def update_ragas_status(message):
        status_text.text(message)
        logger.info(f"RAGAS Status: {message}")

    try:
        # Set OpenAI API key for evaluation if provided
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            logger.info("OpenAI API key set in environment")
        else:
            logger.warning("No OpenAI API key provided - RAGAS metrics may fail")

        # Log evaluation parameters
        logger.info(f"Starting evaluate_queries with parameters:")
        logger.info(f"  queries: {len(queries)} items")
        logger.info(f"  kb_name: '{kb_name}'")
        logger.info(f"  openai_model: {openai_model}")
        logger.info(f"  rag_api_url: {rag_api_url}")
        logger.info(f"  username: {username}")
        logger.info(f"  password: {'***' if password else 'None'}")

        # Run evaluation using our core evaluation logic
        logger.info("Calling evaluate_queries...")
        eval_results = await evaluate_queries(
            queries=queries,
            kb_name=kb_name,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            rag_api_url=rag_api_url,
            username=username,
            password=password,
            reference_answers=reference_answers,
            progress_callback=update_progress,
            ragas_status_callback=update_ragas_status
        )
        logger.info(f"evaluate_queries completed successfully")

        # Update the results for display
        # Update the results for display (metrics are now stored per-query)
        rag_results = eval_results.get("rag_results", [])
        logger.info(f"Received {len(rag_results)} RAG results")

        for i, result in enumerate(rag_results):
            # Debug: Log which metrics are present for each result
            basic_metrics = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
            reference_metrics = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']
            all_possible_metrics = basic_metrics + reference_metrics
            present_metrics = [metric for metric in all_possible_metrics if metric in result and result[metric] is not None]

            logger.info(f"Result {i+1}: query='{result.get('query', '')[:50]}...', "
                       f"response_len={len(result.get('response', ''))}, "
                       f"contexts={len(result.get('contexts', []))}, "
                       f"has_error={'error' in result}, "
                       f"metrics_present={present_metrics}")
            if 'error' in result:
                logger.error(f"Result {i+1} error: {result['error']}")

        st.session_state.results = rag_results

        # Store logs in session state
        logs = eval_results.get("logs", [])
        st.session_state.logs = logs
        logger.info(f"Stored {len(logs)} log entries")

        # Update progress bar to complete
        progress_bar.progress(1.0)
        status_text.text("Evaluation complete!")
        logger.info("=== STREAMLIT EVALUATION COMPLETED ===")

    except Exception as e:
        error_msg = f"Error running evaluation: {str(e)}"
        logger.error(error_msg)
        logger.error("Exception details:", exc_info=True)
        status_text.text(f"Error: {str(e)}")

    st.session_state.evaluation_running = False

# Function to convert results to CSV
def results_to_csv(results):
    """Convert evaluation results to CSV format"""
    logger.info(f"DEBUG CSV: results_to_csv called with {len(results) if results else 0} results")
    if not results:
        logger.warning("DEBUG CSV: No results provided, returning None")
        return None

    # Create a list to store CSV data
    csv_data = []
    # Include all possible metrics in CSV output
    basic_metrics = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
    reference_metrics = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']
    metric_names = basic_metrics + reference_metrics

    for i, result in enumerate(results):
        row = {
            "Query_ID": f"Q{i+1}",
            "Query": result.get('query', ''),
            "Response": result.get('answer', result.get('response', '')),
            "Reference_Answer": result.get('reference_answer', ''),
            "Response_Time_Seconds": result.get('response_time', 0),
            "Context_Count": len(result.get('contexts', [])),
            "Has_Error": 'Yes' if 'error' in result else 'No',
            "Error_Message": result.get('error', '')
        }

        # Add metric scores
        for metric in metric_names:
            if metric in result and result[metric] is not None:
                row[metric.replace('_', ' ').title().replace(' ', '_')] = f"{result[metric]:.4f}"
            else:
                row[metric.replace('_', ' ').title().replace(' ', '_')] = 'N/A'

        # Add contexts as a single text field
        if 'contexts' in result and result['contexts']:
            contexts_text = "\n\n--- CONTEXT SEPARATOR ---\n\n".join(result['contexts'])
            row['Retrieved_Contexts'] = contexts_text
        else:
            row['Retrieved_Contexts'] = ''

        csv_data.append(row)

    # Convert to DataFrame and then to CSV
    try:
        df = pd.DataFrame(csv_data)
        csv_result = df.to_csv(index=False)
        logger.info(f"DEBUG CSV: Successfully generated CSV with {len(df)} rows")
        return csv_result
    except Exception as e:
        logger.error(f"DEBUG CSV: Error generating CSV: {str(e)}")
        return None

# Controls section
col1, col2 = st.columns([1, 1])

# Run evaluation button
with col1:
    run_button = st.button("Run Evaluation", disabled=st.session_state.evaluation_running)

# Download results button
with col2:
    logger.info(f"DEBUG BUTTON: results={len(st.session_state.results) if st.session_state.results else 0}, running={st.session_state.evaluation_running}")
    if st.session_state.results and not st.session_state.evaluation_running:
        csv_data = results_to_csv(st.session_state.results)
        logger.info(f"DEBUG BUTTON: CSV data length={len(csv_data) if csv_data else 0}")
        if csv_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rag_evaluation_results_{timestamp}.csv"

            st.download_button(
                label="📥 Download Results (CSV)",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help="Download evaluation results as CSV file"
            )
        else:
            st.button("📥 Download Results (CSV)", disabled=True, help="CSV generation failed")
    else:
        help_text = "Evaluation in progress..." if st.session_state.evaluation_running else "Run evaluation first to download results"
        st.button("📥 Download Results (CSV)", disabled=True, help=help_text)

# Log current configuration when about to run
if run_button:
    logger.info(f"=== RUN EVALUATION BUTTON CLICKED ===")
    logger.info(f"Current settings:")
    logger.info(f"  RAG API URL: '{rag_api_url}'")
    logger.info(f"  Username: '{username}'")
    logger.info(f"  Password: {'***' if password else '(empty)'}")
    logger.info(f"  Knowledge Base: '{kb_name}'")
    logger.info(f"  OpenAI Model: {openai_model}")
    logger.info(f"  OpenAI API Key: {'Set' if openai_api_key else 'Not set'}")
    logger.info(f"  Number of queries: {len(queries)}")

    if not rag_api_url or not username or not password or not kb_name:
        missing = []
        if not rag_api_url: missing.append("RAG API URL")
        if not username: missing.append("Username")
        if not password: missing.append("Password")
        if not kb_name: missing.append("Knowledge Base Name")
        error_msg = f"Missing required fields: {', '.join(missing)}"
        logger.error(error_msg)
        st.error(error_msg)
    else:
        try:
            # Get reference answers from session state
            current_references = st.session_state.get('current_references', None)
            asyncio.run(run_evaluation(queries, kb_name, current_references))
        except Exception as e:
            logger.error(f"Error in asyncio.run: {str(e)}")
            st.error(f"Evaluation failed: {str(e)}")
        finally:
            # Ensure evaluation_running is always cleared
            st.session_state.evaluation_running = False
            # Force a rerun to update the download button state
            st.rerun()

# Display results
if st.session_state.results:
    st.subheader("Evaluation Results")

    # Prepare results for display
    try:
        results_df = pd.DataFrame(st.session_state.results)
        logger.info(f"DEBUG: Created DataFrame with {len(results_df)} rows")
    except Exception as e:
        logger.error(f"DEBUG: Error creating DataFrame: {str(e)}")
        st.error(f"Error displaying results: {str(e)}")
        results_df = pd.DataFrame()

    # Display metrics summary (computed from per-query metrics)
    if st.session_state.ragas_available:
        # Collect metrics from individual results (including reference-based metrics)
        all_metrics = {}
        # Define all possible metric names (basic + reference-based)
        basic_metrics = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
        reference_metrics = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']

        # Use appropriate metric set based on session state
        if st.session_state.get('enable_reference_metrics', False):
            metric_names = basic_metrics + reference_metrics
        else:
            metric_names = basic_metrics

        for result in st.session_state.results:
            for metric in metric_names:
                if metric in result and result[metric] is not None:
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(result[metric])

        if all_metrics:
            # Calculate total queries and mode for context
            total_queries = len(st.session_state.results)
            mode_info = "Full Mode (8 metrics)" if st.session_state.get('enable_reference_metrics', False) else "Basic Mode (4 metrics)"


            # Add explanation of metrics
            with st.expander("ℹ️ About RAGAS Metrics", expanded=False):
                if st.session_state.get('enable_reference_metrics', False):
                    st.write("""
                    **Reference-Free Metrics** (work without reference answers):
                    - **Faithfulness** 🧠: How well grounded the response is in the retrieved context
                    - **Answer Relevancy**: How relevant the response is to the original query
                    - **Context Relevancy** 🧠: How relevant the retrieved context is to the query
                    - **Context Precision Without Reference** 🧠: Precision of context retrieval without reference answers

                    **Reference-Based Metrics** (require reference answers for comparison):
                    - **Answer Similarity**: Semantic similarity between generated and reference answers
                    - **Answer Correctness**: Factual accuracy against reference answers
                    - **Context Precision** 🧠: More accurate precision using reference answers
                    - **Context Recall** 🧠: How well retrieved contexts cover the reference answer

                    🧠 = Context-dependent metrics | *All metrics range from 0.0 to 1.0, with higher scores indicating better performance.*
                    """)
                else:
                    st.write("""
                    **Context-dependent metrics** 🧠 require retrieved context/documents:
                    - **Faithfulness**: How well grounded the response is in the retrieved context
                    - **Context Relevancy**: How relevant the retrieved context is to the query
                    - **Context Precision Without Reference**: Precision of context retrieval without reference answers

                    **Response-only metrics** evaluate the generated response quality:
                    - **Answer Relevancy**: How relevant the response is to the original query

                    🧠 = Context-dependent metrics | *All metrics range from 0.0 to 1.0, with higher scores indicating better performance.*
                    """)

            st.write(f"### Average Metrics Summary")
            st.caption(f"Average scores across {total_queries} queries • {mode_info}")
            metrics_summary = {}
            for metric, values in all_metrics.items():
                if values:
                    metrics_summary[metric] = sum(values) / len(values)

            # Display metrics in columns with context indicators
            cols = st.columns(len(metrics_summary))
            context_dependent_metrics = {'faithfulness', 'context_relevancy', 'context_precision_without_reference'}

            for i, (metric, value) in enumerate(metrics_summary.items()):
                metric_label = metric.replace('_', ' ').title()
                if metric in context_dependent_metrics:
                    metric_label += " 🧠"  # Brain emoji to indicate context-dependent

                cols[i].metric(
                    label=metric_label,
                    value=f"{value:.2f}",
                )

            # Create bar chart of metrics by query
            if all_metrics:
                st.write("### Metrics by Query")
                chart_data = []
                for i, result in enumerate(st.session_state.results):
                    query_data = {"Query": f"Q{i+1}"}
                    for metric in metric_names:
                        if metric in result and result[metric] is not None:
                            query_data[metric.replace('_', ' ').title()] = result[metric]
                    chart_data.append(query_data)

                chart_df = pd.DataFrame(chart_data)
                fig = px.bar(
                    chart_df,
                    x="Query",
                    y=[col for col in chart_df.columns if col != "Query"],
                    barmode='group',
                    title="Metric Scores by Query"
                )
                st.plotly_chart(fig)

    # Display metrics table for all queries
    if st.session_state.ragas_available and all_metrics:
        st.write("### Metrics by Query")

        # Create table data
        table_data = []
        # Use the same metric set as the summary display
        basic_metrics = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
        reference_metrics = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']
        if st.session_state.get('enable_reference_metrics', False):
            metric_names = basic_metrics + reference_metrics
        else:
            metric_names = basic_metrics

        for i, result in enumerate(st.session_state.results):
            row = {
                "Query": f"Q{i+1}: {result['query'][:50]}..." if len(result['query']) > 50 else f"Q{i+1}: {result['query']}",
                "Response Time (s)": f"{result.get('response_time', 0):.2f}" if 'response_time' in result else "N/A"
            }

            # Add metric scores
            for metric in metric_names:
                if metric in result and result[metric] is not None:
                    row[metric.replace('_', ' ').title()] = f"{result[metric]:.3f}"
                else:
                    row[metric.replace('_', ' ').title()] = "N/A"

            table_data.append(row)

        if table_data:
            # Create DataFrame for the table
            table_df = pd.DataFrame(table_data)
            st.dataframe(table_df, use_container_width=True, hide_index=True)

    # Display response times
    if 'response_time' in results_df.columns:
        st.write("### Response Times")
        fig = px.bar(
            results_df,
            x=results_df.index,
            y='response_time',
            labels={'index': 'Query #', 'response_time': 'Time (s)'},
            title="Response Time by Query"
        )
        st.plotly_chart(fig)

    # Display individual results
    st.write("### Detailed Query Results")
    for i, result in enumerate(st.session_state.results):
        with st.expander(f"Query {i+1}: {result['query'][:50]}..."):
            st.write("**Query:**")
            st.write(result['query'])

            st.write("**Response:**")
            st.write(result['answer'] if 'answer' in result else result.get('response', 'No response'))

            # Display metrics for this query if available
            basic_metrics = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
            reference_metrics = ['answer_similarity', 'answer_correctness', 'context_precision', 'context_recall']
            if st.session_state.get('enable_reference_metrics', False):
                metric_names = basic_metrics + reference_metrics
            else:
                metric_names = basic_metrics
            query_metrics = {metric: result[metric] for metric in metric_names if metric in result and result[metric] is not None}

            if query_metrics:
                st.write("**Evaluation Scores:**")
                cols = st.columns(len(query_metrics))
                for idx, (metric, score) in enumerate(query_metrics.items()):
                    cols[idx].metric(
                        label=metric.replace('_', ' ').title(),
                        value=f"{score:.3f}"
                    )

            if 'contexts' in result and result['contexts']:
                st.write("**Retrieved Contexts:**")
                # Show contexts in a single text area to avoid nesting expanders
                all_contexts = ""
                for j, context in enumerate(result['contexts']):
                    all_contexts += f"--- Context {j+1} ---\n{context}\n\n"

                st.text_area(
                    f"Retrieved {len(result['contexts'])} context(s)",
                    value=all_contexts.strip(),
                    height=200,
                    disabled=True,
                    key=f"contexts_{i}"
                )

            # Display error if present
            if 'error' in result:
                st.error(f"Error: {result['error']}")

# Display logs if present in session state
if st.session_state.logs:
    with st.expander("System Logs", expanded=False):
        st.write(f"**{len(st.session_state.logs)} log entries**")

        # Show key operations summary
        operations = {}
        for log in st.session_state.logs:
            if isinstance(log, dict) and 'operation' in log:
                op = log['operation']
                operations[op] = operations.get(op, 0) + 1

        if operations:
            st.write("**Operations Summary:**")
            for op, count in operations.items():
                st.write(f"- {op}: {count}")

        # Show detailed logs
        st.write("**Detailed Logs:**")
        st.json(st.session_state.logs)
