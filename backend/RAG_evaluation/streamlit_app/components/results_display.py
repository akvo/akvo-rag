"""
Results Display Components for RAG Evaluation

This module contains Streamlit components for displaying evaluation results,
including metrics summaries, charts, and detailed query results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any, List
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from constants import BASIC_METRICS, REFERENCE_METRICS, CONTEXT_DEPENDENT_METRICS, REFERENCE_BASED_METRICS
from components.metrics_explanation import MetricsExplanationManager

logger = logging.getLogger("rag_evaluation")


class ResultsDisplayManager:
    """Manages the display of evaluation results and visualizations."""
    
    @staticmethod
    def render_all_results():
        """Render complete results section including metrics, charts, and details."""
        if not st.session_state.results:
            return
        
        st.subheader("Evaluation Results")
        
        try:
            # Prepare results DataFrame
            results_df = pd.DataFrame(st.session_state.results)
            logger.info(f"Created DataFrame with {len(results_df)} rows")
            
            # Display metrics summary if RAGAS is available
            if st.session_state.get('ragas_available'):
                ResultsDisplayManager._render_metrics_summary()
            
            # Display response times if available
            if 'response_time' in results_df.columns:
                ResultsDisplayManager._render_response_times(results_df)
            
            # Display metrics evaluation timing
            ResultsDisplayManager._render_metrics_timing()
            
            # Display detailed results
            ResultsDisplayManager._render_detailed_results()
            
            # Display logs if available
            if st.session_state.logs:
                ResultsDisplayManager._render_system_logs()
                
        except Exception as e:
            logger.error(f"Error displaying results: {str(e)}")
            st.error(f"Error displaying results: {str(e)}")
    
    @staticmethod
    def _render_metrics_summary():
        """Render metrics summary with averages and charts."""
        # Collect metrics from individual results
        all_metrics = {}
        enable_reference_metrics = st.session_state.get('enable_reference_metrics', False)
        
        if enable_reference_metrics:
            metric_names = BASIC_METRICS + REFERENCE_METRICS
        else:
            metric_names = BASIC_METRICS
        
        # Extract metrics from results
        for i, result in enumerate(st.session_state.results):
            for metric in metric_names:
                if metric in result and result[metric] is not None:
                    try:
                        value = result[metric]
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        if value is not None:
                            if metric not in all_metrics:
                                all_metrics[metric] = []
                            all_metrics[metric].append(float(value))
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Error processing metric {metric} for query {i+1}: {e}")
        
        if all_metrics:
            total_queries = len(st.session_state.results)
            
            # Render metrics explanation
            MetricsExplanationManager.render_results_explanation(enable_reference_metrics)
            
            # Render summary info
            MetricsExplanationManager.render_metric_summary_info(total_queries, enable_reference_metrics)
            
            # Calculate and display average metrics
            metrics_summary = {}
            for metric, values in all_metrics.items():
                if values:
                    metrics_summary[metric] = sum(values) / len(values)
            
            # Display metrics in columns
            if metrics_summary:
                cols = st.columns(len(metrics_summary))
                for i, (metric, value) in enumerate(metrics_summary.items()):
                    metric_label = MetricsExplanationManager.get_metric_display_name(metric, True)
                    cols[i].metric(
                        label=metric_label,
                        value=f"{value:.2f}",
                        help=MetricsExplanationManager.get_metric_help_text(metric)
                    )
            
            # Render metrics chart
            ResultsDisplayManager._render_metrics_chart(all_metrics, metric_names)
            
            # Render metrics table
            ResultsDisplayManager._render_metrics_table(metric_names)
    
    @staticmethod
    def _render_metrics_chart(all_metrics: Dict[str, List[float]], metric_names: List[str]):
        """Render bar chart of metrics by query."""
        if not all_metrics:
            return
        
        st.write("### Metrics by Query")
        chart_data = []
        
        for i, result in enumerate(st.session_state.results):
            query_data = {"Query": f"Q{i+1}"}
            for metric in metric_names:
                if metric in result and result[metric] is not None:
                    try:
                        value = result[metric]
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        if value is not None:
                            display_name = MetricsExplanationManager.get_metric_display_name(metric, False)
                            query_data[display_name] = float(value)
                    except (TypeError, ValueError):
                        pass
            chart_data.append(query_data)
        
        if chart_data:
            chart_df = pd.DataFrame(chart_data)
            fig = px.bar(
                chart_df,
                x="Query",
                y=[col for col in chart_df.columns if col != "Query"],
                barmode='group',
                title="Metric Scores by Query"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def _render_metrics_table(metric_names: List[str]):
        """Render detailed metrics table for all queries."""
        st.write("### Metrics by Query")
        
        table_data = []
        enable_reference_metrics = st.session_state.get('enable_reference_metrics', False)
        
        for i, result in enumerate(st.session_state.results):
            # Create base row structure
            if enable_reference_metrics:
                row = {
                    "Query_ID": f"Q{i+1}",
                    "Query": result['query'][:60] + "..." if len(result['query']) > 60 else result['query'],
                    "Reference_Answer": (result.get('reference_answer', '') or '')[:40] + "..." if len(result.get('reference_answer', '') or '') > 40 else (result.get('reference_answer', '') or ''),
                    "Response": (result.get('answer', result.get('response', '')) or '')[:60] + "..." if len(result.get('answer', result.get('response', '')) or '') > 60 else (result.get('answer', result.get('response', '')) or ''),
                    "Response Time (s)": f"{result.get('response_time', 0):.2f}" if 'response_time' in result else "N/A"
                }
            else:
                row = {
                    "Query_ID": f"Q{i+1}",
                    "Query": result['query'][:60] + "..." if len(result['query']) > 60 else result['query'],
                    "Response": (result.get('answer', result.get('response', '')) or '')[:60] + "..." if len(result.get('answer', result.get('response', '')) or '') > 60 else (result.get('answer', result.get('response', '')) or ''),
                    "Response Time (s)": f"{result.get('response_time', 0):.2f}" if 'response_time' in result else "N/A"
                }
            
            # Add metric scores
            for metric in metric_names:
                display_name = MetricsExplanationManager.get_metric_display_name(metric, False)
                if metric in result and result[metric] is not None:
                    try:
                        value = result[metric]
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        if value is not None:
                            row[display_name] = f"{float(value):.3f}"
                        else:
                            row[display_name] = "N/A"
                    except (TypeError, ValueError):
                        row[display_name] = "Error"
                else:
                    row[display_name] = "N/A"
            
            table_data.append(row)
        
        if table_data:
            table_df = pd.DataFrame(table_data)
            st.dataframe(table_df, use_container_width=True, hide_index=True)
    
    @staticmethod
    def _render_response_times(results_df: pd.DataFrame):
        """Render response times chart."""
        st.write("### Response Times")
        fig = px.bar(
            results_df,
            x=results_df.index,
            y='response_time',
            labels={'index': 'Query #', 'response_time': 'Time (s)'},
            title="Response Time by Query"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def _render_detailed_results():
        """Render detailed individual query results."""
        st.write("### Detailed Query Results")
        
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"Query {i+1}: {result['query'][:50]}..."):
                st.write("**Query:**")
                st.write(result['query'])
                
                st.write("**Response:**")
                st.write(result['answer'] if 'answer' in result else result.get('response', 'No response'))
                
                # Display metrics for this query
                enable_reference_metrics = st.session_state.get('enable_reference_metrics', False)
                if enable_reference_metrics:
                    metric_names = BASIC_METRICS + REFERENCE_METRICS
                else:
                    metric_names = BASIC_METRICS
                
                query_metrics = {}
                for metric in metric_names:
                    if metric in result and result[metric] is not None:
                        query_metrics[metric] = result[metric]
                
                if query_metrics:
                    st.write("**Evaluation Scores:**")
                    cols = st.columns(len(query_metrics))
                    for idx, (metric, score) in enumerate(query_metrics.items()):
                        display_name = MetricsExplanationManager.get_metric_display_name(metric, False)
                        cols[idx].metric(
                            label=display_name,
                            value=f"{score:.3f}",
                            help=MetricsExplanationManager.get_metric_help_text(metric)
                        )
                
                # Display contexts
                if 'contexts' in result and result['contexts']:
                    st.write("**Retrieved Contexts:**")
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
    
    @staticmethod
    def _render_system_logs():
        """Render system logs section."""
        with st.expander("System Logs", expanded=False):
            st.write(f"**{len(st.session_state.logs)} log entries**")
            
            # Show operations summary
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
    
    @staticmethod
    def _render_metrics_timing():
        """Render detailed metrics evaluation timing information."""
        # Check if we have performance data stored
        if not hasattr(st.session_state, 'performance_data') or not st.session_state.performance_data:
            return
            
        perf = st.session_state.performance_data
        rag_time = perf.get('rag_api_time', 0)
        ragas_time = perf.get('ragas_eval_time', 0)
        total_queries = len(st.session_state.results) if st.session_state.results else 1
        
        # Debug information - only show if there are issues
        debug_mode = st.sidebar.checkbox("🐛 Debug Mode", False)
        if debug_mode:
            st.write("🐛 **Debug Performance Data**:")
            st.write(f"- Performance keys: {list(perf.keys())}")
            st.write(f"- RAG API time: {rag_time}")
            st.write(f"- RAGAS eval time: {ragas_time}")
            st.write(f"- Total queries: {total_queries}")
        
        # Show timing section if we have any performance data (lowered threshold for debugging)
        if ragas_time >= 0 or rag_time >= 0 or debug_mode:
            st.write("### ⏱️ Metrics Evaluation Timing")
            if ragas_time == 0 and rag_time == 0:
                st.info("📊 Performance data available but timing values are zero - this may indicate a measurement issue.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "📊 Total Metrics Evaluation Time",
                    f"{ragas_time:.2f}s",
                    help="Total time spent evaluating all RAGAS metrics for all queries"
                )
                
            with col2:
                avg_metrics_time = ragas_time / total_queries if total_queries > 0 else 0
                st.metric(
                    "📈 Average Metrics Time per Query", 
                    f"{avg_metrics_time:.2f}s",
                    help="Average time to evaluate all metrics for a single query"
                )
            
            # Show timing breakdown
            if rag_time > 0 and ragas_time > 0:
                total_time = rag_time + ragas_time
                rag_pct = (rag_time / total_time) * 100
                ragas_pct = (ragas_time / total_time) * 100
                
                st.write("**⏳ Time Distribution:**")
                st.progress(rag_pct / 100)
                st.write(f"🔍 RAG Response Generation: {rag_time:.1f}s ({rag_pct:.1f}%)")
                st.progress(ragas_pct / 100)
                st.write(f"📊 Metrics Evaluation: {ragas_time:.1f}s ({ragas_pct:.1f}%)")
                
                if ragas_time > rag_time:
                    st.info("💡 **Insight**: Metrics evaluation took longer than RAG response generation. Consider using faster models like gpt-4o-mini for better performance.")
                elif rag_time > ragas_time * 2:
                    st.info("💡 **Insight**: RAG response generation is the main bottleneck. Consider optimizing your knowledge base or API performance.")