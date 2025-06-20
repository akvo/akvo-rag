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
        # Update the results for display (metrics are now stored per-query)
        st.session_state.results = eval_results.get("rag_results", [])
        
        # Store logs in session state
        st.session_state.logs = eval_results.get("logs", [])
        
        # Update progress bar to complete
        progress_bar.progress(1.0)
        status_text.text("Evaluation complete!")
        
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}")
        status_text.text(f"Error: {str(e)}")
    
    st.session_state.evaluation_running = False

# Run evaluation button
if st.button("Run Evaluation", disabled=st.session_state.evaluation_running):
    asyncio.run(run_evaluation(queries, kb_name))

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
        # Collect metrics from individual results
        all_metrics = {}
        metric_names = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
        
        for result in st.session_state.results:
            for metric in metric_names:
                if metric in result:
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(result[metric])
        
        if all_metrics:
            st.write("### Metrics Summary")
            metrics_summary = {}
            for metric, values in all_metrics.items():
                if values:
                    metrics_summary[metric] = sum(values) / len(values)
            
            # Display metrics in columns
            cols = st.columns(len(metrics_summary))
            for i, (metric, value) in enumerate(metrics_summary.items()):
                cols[i].metric(
                    label=metric.replace('_', ' ').title(),
                    value=f"{value:.2f}",
                )
            
            # Create bar chart of metrics by query
            if all_metrics:
                st.write("### Metrics by Query")
                chart_data = []
                for i, result in enumerate(st.session_state.results):
                    query_data = {"Query": f"Q{i+1}"}
                    for metric in metric_names:
                        if metric in result:
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
            query_metrics = {}
            metric_names = ['faithfulness', 'answer_relevancy', 'context_precision_without_reference', 'context_relevancy']
            
            for metric in metric_names:
                if metric in result:
                    query_metrics[metric] = result[metric]
            
            # Display metrics if we found any
            if query_metrics:
                st.write("**Metrics:**")
                st.json(query_metrics)

            # Display error if present
            if 'error' in result:
                st.error(f"Error: {result['error']}")

# Display logs if present in session state
if st.session_state.logs:
    with st.expander("System Logs", expanded=False):
        st.json(st.session_state.logs)