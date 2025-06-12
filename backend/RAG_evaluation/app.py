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
import time
import os
import logging
import importlib
from packaging import version

# Set up logging for the evaluation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_evaluation")

# Import our chat utility
from chat_util import RagChatUtil

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

# Sample test questions
DEFAULT_TEST_QUERIES = [
    "What is the living income benchmark?",
    "How is the living income benchmark calculated?",
    "What factors influence the living income benchmark?",
    "How does the living income benchmark differ from minimum wage?",
    "What is the purpose of establishing a living income benchmark?"
]

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
def setup_ragas():
    """Set up RAGAS for evaluation and determine available metrics."""
    st.session_state.ragas_metrics = []
    st.session_state.ragas_available = False

    try:
        # Check if ragas is installed
        ragas_spec = importlib.util.find_spec("ragas")
        if ragas_spec is None:
            st.session_state.ragas_import_error = "RAGAS package is not installed. Install with 'pip install ragas'"
            return False

        # Import RAGAS
        import ragas

        # Log RAGAS version
        ragas_version = ragas.__version__
        logger.info(f"RAGAS version: {ragas_version}")

        # Import evaluate function
        from ragas import evaluate

        # Attempt to import metrics based on version
        metrics = []
        metric_names = []

        # Import basic metrics that should be available in all versions
        from ragas.metrics import faithfulness
        metrics.append(faithfulness)
        metric_names.append("faithfulness")

        # Try importing newer API metrics
        try:
            from ragas.metrics import answer_relevancy
            metrics.append(answer_relevancy)
            metric_names.append("answer_relevancy")
        except ImportError:
            logger.info("answer_relevancy metric not available")

        try:
            from ragas.metrics import context_precision
            metrics.append(context_precision)
            metric_names.append("context_precision")
        except ImportError:
            logger.info("context_precision metric not available")

        try:
            from ragas.metrics import context_relevancy
            metrics.append(context_relevancy)
            metric_names.append("context_relevancy")
        except ImportError:
            logger.info("context_relevancy metric not available")

        # Store available metrics
        st.session_state.ragas_metrics = metrics
        st.session_state.ragas_metric_names = metric_names
        st.session_state.ragas_available = True

        return True
    except Exception as e:
        logger.error(f"Error setting up RAGAS: {str(e)}")
        st.session_state.ragas_import_error = f"Error setting up RAGAS: {str(e)}"
        return False

# LLM for evaluation
st.sidebar.subheader("Evaluation LLM")
openai_api_key = st.sidebar.text_input("OpenAI API Key", os.environ.get("OPENAI_API_KEY", ""), type="password")
openai_model = st.sidebar.selectbox("Evaluation Model", ["gpt-4o", "gpt-4", "gpt-3.5-turbo-16k"], index=0)

# Check if RAGAS is available
if not st.session_state.ragas_available and not st.session_state.ragas_import_error:
    with st.spinner("Setting up RAGAS..."):
        setup_ragas()

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

    # Set OpenAI API key for evaluation if provided
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key

    # Create chat utility
    chat_util = RagChatUtil(
        base_url=rag_api_url,
        username=username,
        password=password
    )

    # Enable instrumentation
    chat_util.enable_instrumentation()

    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Process each query
    eval_data = []
    for i, query in enumerate(queries):
        status_text.text(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")

        # Generate RAG response
        start_time = time.time()
        rag_result = await chat_util.generate_rag_response(query, kb_name)
        end_time = time.time()

        # Update logs
        st.session_state.logs.extend(chat_util.get_logs())

        # Format data for RAGAS evaluation
        if "error" not in rag_result:
            contexts = [item["page_content"] for item in rag_result.get("contexts", [])]
            eval_data.append({
                "query": query,
                "ground_truths": [""],  # No ground truth for now
                "answer": rag_result["response"],
                "contexts": contexts,
                "response_time": end_time - start_time
            })

            # Store result
            st.session_state.results.append({
                "query": query,
                "response": rag_result["response"],
                "contexts": contexts,
                "kb_id": rag_result.get("kb_id"),
                "chat_id": rag_result.get("chat_id"),
                "response_time": end_time - start_time
            })
        else:
            # Store error result
            st.session_state.results.append({
                "query": query,
                "response": rag_result["response"],
                "contexts": [],
                "error": rag_result.get("error", "Unknown error"),
                "response_time": end_time - start_time
            })

        # Update progress
        progress_bar.progress((i + 1) / len(queries))

    # Only run RAGAS evaluation if we have data, OpenAI API key, and RAGAS is available
    if eval_data and openai_api_key and st.session_state.ragas_available and st.session_state.ragas_metrics:
        status_text.text("Running RAGAS evaluation...")

        try:
            # Prepare data for RAGAS
            eval_df = pd.DataFrame(eval_data)

            # Create LLM for evaluation
            from ragas.llms import LangchainLLM
            from langchain_openai import ChatOpenAI

            eval_llm = LangchainLLM(llm=ChatOpenAI(model=openai_model))

            # Run evaluation with available metrics
            metrics = st.session_state.ragas_metrics
            metric_names = st.session_state.ragas_metric_names

            status_text.text(f"Evaluating with metrics: {', '.join(metric_names)}...")

            # Import evaluate function
            from ragas import evaluate

            # Run evaluation
            result = evaluate(
                eval_df,
                metrics=metrics,
                llm=eval_llm
            )

            # Store evaluation results
            for i, row in result.items():
                for j, item in enumerate(eval_data):
                    if j < len(st.session_state.results):
                        st.session_state.results[j][i] = row[j]

        except Exception as e:
            status_text.text(f"Error running evaluation: {str(e)}")
            logger.error(f"RAGAS evaluation error: {str(e)}")
    elif not openai_api_key:
        status_text.text("Skipping RAGAS evaluation: OpenAI API key not provided")
    elif not st.session_state.ragas_available:
        status_text.text("Skipping RAGAS evaluation: RAGAS not available")

    status_text.text("Evaluation complete!")
    st.session_state.evaluation_running = False

# Run evaluation button
if st.button("Run Evaluation", disabled=st.session_state.evaluation_running):
    asyncio.run(run_evaluation(queries, kb_name))

# Display results
if st.session_state.results:
    st.subheader("Evaluation Results")

    # Prepare results for display
    results_df = pd.DataFrame(st.session_state.results)

    # Display metrics if available
    if st.session_state.ragas_available:
        metrics_cols = st.session_state.ragas_metric_names
        available_metrics = [col for col in metrics_cols if col in results_df.columns]

        if available_metrics:
            st.write("### Metrics Summary")
            metrics_summary = {}
            for metric in available_metrics:
                if metric in results_df.columns:
                    metrics_summary[metric] = results_df[metric].mean()

            # Display metrics in columns
            cols = st.columns(len(metrics_summary))
            for i, (metric, value) in enumerate(metrics_summary.items()):
                cols[i].metric(
                    label=metric.replace('_', ' ').title(),
                    value=f"{value:.2f}",
                )

            # Create bar chart of metrics
            st.write("### Metrics by Query")
            fig = px.bar(
                results_df,
                x=results_df.index,
                y=available_metrics,
                labels={'index': 'Query #', 'value': 'Score'},
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
            st.write(result['response'])

            if 'contexts' in result and result['contexts']:
                st.write("**Retrieved Contexts:**")
                for j, context in enumerate(result['contexts']):
                    st.write(f"Context {j+1}:")
                    st.text(context)

            # Display metrics for this query if available
            if st.session_state.ragas_available:
                available_metrics = [m for m in st.session_state.ragas_metric_names if m in result]
                if available_metrics:
                    st.write("**Metrics:**")
                    metrics_data = {metric: result.get(metric, 'N/A') for metric in available_metrics}
                    st.json(metrics_data)

            # Display error if present
            if 'error' in result:
                st.error(f"Error: {result['error']}")

# Display logs
if st.session_state.logs:
    with st.expander("System Logs", expanded=False):
        st.json(st.session_state.logs)
