"""
Streamlit application for RAG evaluation.

This module provides a Streamlit-based UI for evaluating RAG responses
from the Akvo RAG system.
"""

import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from typing import List, Dict, Any
import json
import os
import logging

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
st.set_page_config(page_title="Akvo RAG Evaluation", page_icon="📊", layout="wide")
st.title("Akvo RAG Evaluation Dashboard")

# Initialize session state
if "logs" not in st.session_state:
    st.session_state.logs = []
if "results" not in st.session_state:
    st.session_state.results = []
if "evaluation_running" not in st.session_state:
    st.session_state.evaluation_running = False
if "selected_kb" not in st.session_state:
    st.session_state.selected_kb = "Living Income Benchmark Knowledge Base"
if "ragas_metrics" not in st.session_state:
    st.session_state.ragas_metrics = []
if "ragas_available" not in st.session_state:
    st.session_state.ragas_available = False
if "ragas_import_error" not in st.session_state:
    st.session_state.ragas_import_error = None

# Configuration section
st.sidebar.header("Configuration")

# Connection settings
st.sidebar.subheader("Connection Settings")
rag_api_url = st.sidebar.text_input("Akvo RAG API URL", "http://localhost:8000")
username = st.sidebar.text_input("Username", "admin@example.com")
password = st.sidebar.text_input("Password", "password", type="password")

# Knowledge base selection
st.sidebar.subheader("Knowledge Base")
kb_name = st.sidebar.text_input("Knowledge Base Name", "Living Income Benchmark Knowledge Base")
st.session_state.selected_kb = kb_name

# RAGAS setup
def initialize_ragas():
    """Initialize RAGAS and check available metrics."""
    ragas_available, metrics, metric_names, error_message = setup_ragas()
    st.session_state.ragas_available = ragas_available
    st.session_state.ragas_metrics = metrics
    st.session_state.ragas_metric_names = metric_names if ragas_available else []
    st.session_state.ragas_import_error = error_message

# LLM for evaluation
st.sidebar.subheader("Evaluation LLM")
openai_api_key = st.sidebar.text_input("OpenAI API Key", os.environ.get("OPENAI_API_KEY", ""), type="password")
openai_model = st.sidebar.selectbox("Evaluation Model", ["gpt-4o", "gpt-4", "gpt-3.5-turbo-16k"], index=0)

# Check if RAGAS is available
if not st.session_state.ragas_available and not st.session_state.ragas_import_error:
    with st.spinner("Setting up RAGAS..."):
        initialize_ragas()

# Display RAGAS status
if st.session_state.ragas_import_error:
    st.sidebar.error(st.session_state.ragas_import_error)
elif st.session_state.ragas_available:
    st.sidebar.success(f"RAGAS metrics available: {', '.join(st.session_state.ragas_metric_names)}")

# Test queries
st.subheader("Test Queries")
test_queries = st.text_area("Enter test queries (one per line)", "\n".join(DEFAULT_TEST_QUERIES), height=200)
queries = [q.strip() for q in test_queries.split("\n") if q.strip()]

# Function to run evaluation
async def run_evaluation(queries: List[str], kb_name: str):
    """Run RAG evaluation on the given queries"""
    st.session_state.evaluation_running = True
    st.session_state.logs = []
    st.session_state.results = []

    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Starting evaluation...")

    # Progress callback to update the UI during evaluation
    def update_progress(i, total, query, result):
        # Update progress bar
        progress_bar.progress((i + 1) / total)
        # Update status text
        status_text.text(f"Processing query {i+1}/{total}: {query[:50]}...")
        # Update results in session state
        if len(st.session_state.results) <= i:
            st.session_state.results.append(result)
        else:
            st.session_state.results[i] = result

    # RAGAS status callback
    def update_ragas_status(message):
        status_text.text(message)

    try:
        # Set OpenAI API key for evaluation if provided
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            
        # Run evaluation using our core evaluation logic
        eval_results = await evaluate_queries(
            queries=queries,
            kb_name=kb_name,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            rag_api_url=rag_api_url,
            username=username,
            password=password,
            progress_callback=update_progress,
            ragas_status_callback=update_ragas_status
        )
        
        # Update the results for display
        rag_results = eval_results.get("rag_results", [])
        ragas_results = eval_results.get("ragas_results", {})
        
        logger.info(f"DEBUG: Got {len(rag_results)} RAG results")
        logger.info(f"DEBUG: RAGAS results keys: {list(ragas_results.keys())}")
        logger.info(f"DEBUG: RAGAS success: {ragas_results.get('success', 'Not found')}")
        
        st.session_state.results = rag_results
        st.session_state.ragas_results = ragas_results  # Store RAGAS results separately
        
        # Store logs in session state
        st.session_state.logs = eval_results.get("logs", [])
        
        # Update progress bar to complete
        progress_bar.progress(1.0)
        status_text.text("Evaluation complete!")
        
        logger.info(f"DEBUG: Session state results length: {len(st.session_state.results)}")
        logger.info(f"DEBUG: Session state has ragas_results: {'ragas_results' in st.session_state}")
        
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}")
        status_text.text(f"Error: {str(e)}")
    
    st.session_state.evaluation_running = False

# Run evaluation button
if st.button("Run Evaluation", disabled=st.session_state.evaluation_running):
    asyncio.run(run_evaluation(queries, kb_name))

# Display results
logger.info(f"DEBUG: Checking results display - results length: {len(st.session_state.results) if st.session_state.results else 0}")
logger.info(f"DEBUG: Results exist: {bool(st.session_state.results)}")

if st.session_state.results:
    logger.info(f"DEBUG: Displaying {len(st.session_state.results)} results")
    st.subheader("Evaluation Results")

    # Prepare results for display
    try:
        results_df = pd.DataFrame(st.session_state.results)
        logger.info(f"DEBUG: Created DataFrame with {len(results_df)} rows")
    except Exception as e:
        logger.error(f"DEBUG: Error creating DataFrame: {str(e)}")
        st.error(f"Error displaying results: {str(e)}")
        results_df = pd.DataFrame()

    # Display metrics if available
    ragas_results = getattr(st.session_state, 'ragas_results', None)
    logger.info(f"DEBUG: RAGAS results for display: {ragas_results is not None}")
    logger.info(f"DEBUG: RAGAS available: {st.session_state.ragas_available}")
    
    if ragas_results and "success" in ragas_results and st.session_state.ragas_available:
        logger.info(f"DEBUG: Displaying RAGAS metrics - success: {ragas_results.get('success')}")
        metrics_data = ragas_results.get("metrics", {})
        metric_names = ragas_results.get("metric_names", [])
        
        if metrics_data:
            try:
                logger.info(f"DEBUG: Rendering metrics with data: {metrics_data}")
                st.write("### Metrics Summary")
                metrics_summary = {}
                for metric in metric_names:
                    if metric in metrics_data:
                        values = metrics_data[metric]
                        logger.info(f"DEBUG: Processing metric {metric}: {values}")
                        if isinstance(values, list) and values:
                            metrics_summary[metric] = sum(values) / len(values)
                logger.info(f"DEBUG: Computed metrics summary: {metrics_summary}")
            except Exception as e:
                logger.error(f"DEBUG: Error in metrics display: {str(e)}")
                st.error(f"Error displaying metrics: {str(e)}")
            
            # Display metrics in columns
            cols = st.columns(len(metrics_summary))
            for i, (metric, value) in enumerate(metrics_summary.items()):
                cols[i].metric(
                    label=metric.replace('_', ' ').title(),
                    value=f"{value:.2f}",
                )
            
            # Create bar chart of metrics by query
            if metric_names and metrics_data:
                st.write("### Metrics by Query")
                chart_data = []
                for i, query in enumerate(queries):
                    query_data = {"Query": f"Q{i+1}"}
                    for metric in metric_names:
                        if metric in metrics_data and i < len(metrics_data[metric]):
                            query_data[metric.replace('_', ' ').title()] = metrics_data[metric][i]
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
    st.write("### Individual Query Results")
    for i, result in enumerate(st.session_state.results):
        with st.expander(f"Query {i+1}: {result['query'][:50]}..."):
            st.write("**Query:**")
            st.write(result['query'])

            st.write("**Response:**")
            st.write(result['answer'] if 'answer' in result else result.get('response', 'No response'))

            if 'contexts' in result and result['contexts']:
                st.write("**Retrieved Contexts:**")
                for j, context in enumerate(result['contexts']):
                    st.write(f"Context {j+1}:")
                    st.text(context)

            # Display metrics for this query if available
            ragas_results = None
            for res in st.session_state.results:
                if "ragas_results" in res:
                    ragas_results = res.get("ragas_results")
                    break
                    
            if ragas_results and "success" in ragas_results and st.session_state.ragas_available:
                metrics_data = ragas_results.get("metrics", {})
                metric_names = ragas_results.get("metric_names", [])
                
                if metrics_data:
                    st.write("**Metrics:**")
                    query_metrics = {}
                    for metric in metric_names:
                        if metric in metrics_data and i < len(metrics_data[metric]):
                            query_metrics[metric] = metrics_data[metric][i]
                    st.json(query_metrics)

            # Display error if present
            if 'error' in result:
                st.error(f"Error: {result['error']}")

# Display logs if present in session state
if st.session_state.logs:
    with st.expander("System Logs", expanded=False):
        st.json(st.session_state.logs)