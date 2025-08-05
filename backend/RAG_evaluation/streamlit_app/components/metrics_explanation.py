"""
Metrics Explanation Components for RAG Evaluation

This module contains Streamlit components for displaying comprehensive
explanations of RAGAS metrics used in the evaluation.
"""

import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from constants import METRICS_EXPLANATIONS, SHORT_METRICS_EXPLANATIONS


class MetricsExplanationManager:
    """Manages the display of metrics explanations in the RAG evaluation app."""
    
    @staticmethod
    def render_main_explanation() -> None:
        """Render the main comprehensive metrics explanation expandable section."""
        with st.expander("📖 Metrics Explanations", expanded=False):
            st.markdown(METRICS_EXPLANATIONS)
    
    @staticmethod
    def render_results_explanation(enable_reference_metrics: bool = False) -> None:
        """
        Render a shorter metrics explanation in the results section.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
        """
        with st.expander("ℹ️ About RAGAS Metrics", expanded=False):
            if enable_reference_metrics:
                st.markdown(SHORT_METRICS_EXPLANATIONS['reference_free'])
            else:
                st.markdown(SHORT_METRICS_EXPLANATIONS['basic_only'])
    
    @staticmethod
    def get_metric_display_name(metric_name: str, include_icons: bool = True) -> str:
        """
        Get a formatted display name for a metric with appropriate icons.
        
        Args:
            metric_name: Internal metric name (e.g., 'faithfulness')
            include_icons: Whether to include emoji icons
            
        Returns:
            Formatted display name
        """
        # Define metric categories for icons
        context_dependent_metrics = {
            'faithfulness', 'context_relevancy', 'context_precision_without_reference', 
            'context_precision', 'context_recall'
        }
        reference_based_metrics = {
            'answer_similarity', 'answer_correctness', 'context_precision', 'context_recall'
        }
        
        # Convert to title case
        display_name = metric_name.replace('_', ' ').title()
        
        if include_icons:
            # Add context-dependent icon
            if metric_name in context_dependent_metrics:
                display_name += " 🧠"
            
            # Add reference-based icon
            if metric_name in reference_based_metrics:
                display_name += " 📚"
        
        return display_name
    
    @staticmethod
    def render_metric_summary_info(total_queries: int, enable_reference_metrics: bool) -> None:
        """
        Render informational text about the metrics summary.
        
        Args:
            total_queries: Total number of queries evaluated
            enable_reference_metrics: Whether reference metrics are enabled
        """
        mode_info = "Full Mode (8 metrics)" if enable_reference_metrics else "Basic Mode (4 metrics)"
        st.write("### Average Metrics Summary")
        st.caption(f"Average scores across {total_queries} queries • {mode_info}")
    
    @staticmethod
    def render_mode_info_box(enable_reference_metrics: bool) -> None:
        """
        Render an information box explaining the current evaluation mode.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
        """
        if enable_reference_metrics:
            st.info("💡 Full mode requires reference answers for enhanced metrics like Answer Similarity and Answer Correctness.")
        else:
            st.info("ℹ️ Basic mode evaluates responses without requiring reference answers.")
    
    @staticmethod
    def get_metric_description(metric_name: str) -> str:
        """
        Get a brief description of what a metric measures.
        
        Args:
            metric_name: Internal metric name
            
        Returns:
            Brief description string
        """
        descriptions = {
            'faithfulness': "How well grounded the response is in the retrieved context",
            'context_relevancy': "How relevant the retrieved context is to the query",
            'answer_relevancy': "How relevant the response is to the original query",
            'context_precision_without_reference': "Precision of context retrieval without reference answers",
            'context_recall': "How well retrieved contexts cover the reference answer",
            'context_precision': "More accurate precision using reference answers",
            'answer_similarity': "Semantic similarity between generated and reference answers",
            'answer_correctness': "Factual accuracy against reference answers"
        }
        
        return descriptions.get(metric_name, "Evaluation metric")
    
    @staticmethod
    def render_metrics_legend() -> None:
        """Render a legend explaining the metric icons."""
        st.caption("🧠 = Context-dependent | 📚 = Reference-based | *All metrics range from 0.0 to 1.0, with higher scores indicating better performance.*")
    
    @staticmethod
    def render_evaluation_mode_explanation() -> str:
        """
        Get explanation text for the evaluation mode section.
        
        Returns:
            Markdown text explaining evaluation modes
        """
        return """
        **Basic Mode (4 metrics)**: Uses reference-free metrics that evaluate your RAG system 
        without requiring ground truth answers. Ideal for real-world evaluation scenarios.
        
        **Full Mode (8 metrics)**: Includes both reference-free and reference-based metrics 
        for comprehensive evaluation. Requires reference answers for enhanced analysis.
        """
    
    @staticmethod
    def get_metric_help_text(metric_name: str) -> str:
        """
        Get help text for metric tooltips.
        
        Args:
            metric_name: Internal metric name
            
        Returns:
            Help text for tooltips
        """
        help_texts = {
            'faithfulness': "Measures how well the generated answer is supported by the retrieved context. Higher scores indicate better factual consistency.",
            'context_relevancy': "Assesses the relevance of retrieved context to the query. Higher scores indicate better context retrieval.",
            'answer_relevancy': "Evaluates how well the answer addresses the original question. Higher scores indicate more relevant responses.",
            'context_precision_without_reference': "Measures precision of context retrieval without requiring reference answers. Higher scores indicate more precise retrieval.",
            'context_recall': "Measures how well retrieved contexts cover information in the reference answer. Higher scores indicate better coverage.",
            'context_precision': "More accurate precision measurement using reference answers for comparison. Higher scores indicate better precision.",
            'answer_similarity': "Compares semantic similarity between generated and reference answers. Higher scores indicate closer alignment.",
            'answer_correctness': "Evaluates factual accuracy against reference answers. Higher scores indicate better correctness."
        }
        
        return help_texts.get(metric_name, "RAGAS evaluation metric")