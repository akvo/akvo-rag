"""
Configuration Components for RAG Evaluation

This module contains Streamlit components for handling application configuration,
including connection settings, model selection, and validation.
"""

import streamlit as st
import os
from typing import Dict, Any, List, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from constants import DEFAULT_CONFIG
from utils.session_state import SessionStateManager


class ConfigurationManager:
    """Manages configuration settings and validation for the RAG evaluation app."""

    @staticmethod
    def render_sidebar_config() -> Dict[str, Any]:
        """
        Render the configuration sidebar and return current settings.

        Returns:
            Dict containing all configuration values
        """
        st.sidebar.header("Configuration")

        # Connection settings
        st.sidebar.subheader("Connection Settings")
        rag_api_url = st.sidebar.text_input(
            "RAG API URL",
            DEFAULT_CONFIG["rag_api_url"],
            help="If 'localhost' doesn't work (e.g., in Docker on macOS), try:\n- http://host.docker.internal:[YOUR_ENV_BACKEND_PORT]\n- or http://backend:8000",
        ).strip()

        username = st.sidebar.text_input(
            "Username", placeholder="Enter username"
        ).strip()

        password = st.sidebar.text_input(
            "Password", type="password", placeholder="Enter password"
        )

        # Knowledge base selection
        st.sidebar.subheader("Knowledge Base")
        kb_name = st.sidebar.text_input(
            "Knowledge Base Name", placeholder="Enter your knowledge base name"
        ).strip()

        # Update session state
        SessionStateManager.initialize_all_state()
        st.session_state.selected_kb = kb_name

        # LLM settings
        st.sidebar.subheader("Evaluation LLM")
        openai_api_key = st.sidebar.text_input(
            "OpenAI API Key",
            os.environ.get("OPENAI_API_KEY", ""),
            type="password",
        )

        # Get current evaluation mode for smart model recommendation
        current_mode = st.session_state.get('evaluation_mode', 'full')
        recommended_model = DEFAULT_CONFIG['model_recommendations'].get(current_mode, 'gpt-4o-mini')
        
        # Find recommended model index
        recommended_idx = 0
        try:
            recommended_idx = DEFAULT_CONFIG["openai_models"].index(recommended_model)
        except ValueError:
            pass
            
        openai_model = st.sidebar.selectbox(
            "Evaluation Model", 
            DEFAULT_CONFIG["openai_models"], 
            index=recommended_idx,
            help=f"🚀 Recommended for {current_mode} mode: {recommended_model} "
                 f"(5-10x faster than gpt-4o with similar quality)"
        )
        
        # Performance settings in expander
        with st.sidebar.expander("⚡ Performance Settings", expanded=False):
            use_batch_processing = st.checkbox(
                "Enable Batch Processing", 
                value=True,
                help="Process multiple queries concurrently for 50-70% speed improvement"
            )
            
            batch_size = st.slider(
                "Batch Size", 
                min_value=1, max_value=10, value=5,
                help="Number of queries per batch (higher = faster but more memory)"
            )
            
            max_concurrent = st.slider(
                "Max Concurrent", 
                min_value=1, max_value=8, value=3,
                help="Maximum concurrent API requests (higher = faster but may hit rate limits)"
            )
            
            # Show model performance info
            model_info = DEFAULT_CONFIG['model_performance'].get(openai_model, {})
            if model_info:
                st.info(f"**{openai_model}**: {model_info.get('speed', 'Unknown')} speed, "
                       f"{model_info.get('cost', 'Unknown')} cost, {model_info.get('quality', 'Unknown')} quality")

        return {
            "rag_api_url": rag_api_url,
            "username": username,
            "password": password,
            "kb_name": kb_name,
            "openai_api_key": openai_api_key,
            "openai_model": openai_model,
            "use_batch_processing": use_batch_processing,
            "batch_size": batch_size,
            "max_concurrent": max_concurrent,
        }

    @staticmethod
    def validate_configuration(
        config: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate the current configuration.

        Args:
            config: Configuration dictionary from render_sidebar_config()

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        required_fields = {
            "rag_api_url": "RAG API URL",
            "username": "Username",
            "password": "Password",
            "kb_name": "Knowledge Base Name",
        }

        missing = []
        for field, display_name in required_fields.items():
            if not config.get(field):
                missing.append(display_name)

        return len(missing) == 0, missing

    @staticmethod
    def render_ragas_status() -> None:
        """Render the RAGAS status in the sidebar."""
        if st.session_state.get("ragas_import_error"):
            st.sidebar.error(st.session_state.ragas_import_error)
        elif st.session_state.get("ragas_available"):
            st.sidebar.success("✅ RAGAS evaluation ready")

    @staticmethod
    def render_mode_selection() -> str:
        """
        Render evaluation mode selection and return the selected mode.

        Returns:
            str: Selected evaluation mode ('basic', 'full', or 'reference-only')
        """
        col1, col2 = st.columns([1, 3])

        with col1:
            evaluation_mode = st.radio(
                "Evaluation Mode",
                ["Basic (4 metrics)", "Full (8 metrics)", "Reference-Only (4 metrics)"],
                help="Basic: 4 reference-free metrics. Full: 8 metrics including reference-based ones. Reference-Only: Only reference-based metrics.",
            )

        with col2:
            if evaluation_mode == "Full (8 metrics)":
                st.info(
                    "💡 Full mode includes all metrics. Reference answers enable enhanced metrics like Answer Similarity and Answer Correctness."
                )
            elif evaluation_mode == "Reference-Only (4 metrics)":
                st.info(
                    "📚 Reference-only mode evaluates only reference-based metrics. Reference answers are required."
                )
            else:
                st.info(
                    "ℹ️ Basic mode evaluates responses using reference-free metrics only."
                )

        # Map display names to internal mode names
        mode_mapping = {
            "Basic (4 metrics)": "basic",
            "Full (8 metrics)": "full", 
            "Reference-Only (4 metrics)": "reference-only"
        }
        
        selected_mode = mode_mapping[evaluation_mode]
        enable_reference_metrics = selected_mode in ['full', 'reference-only']

        # Update session state
        SessionStateManager.update_ragas_mode(enable_reference_metrics)
        st.session_state.evaluation_mode = selected_mode

        return selected_mode

    @staticmethod
    def get_current_config() -> Dict[str, Any]:
        """
        Get current configuration from session state or defaults.

        Returns:
            Dict containing current configuration
        """
        return {
            "selected_kb": st.session_state.get("selected_kb", ""),
            "enable_reference_metrics": st.session_state.get(
                "enable_reference_metrics", False
            ),
            "ragas_available": st.session_state.get("ragas_available", False),
            "ragas_metrics": st.session_state.get("ragas_metrics", []),
            "ragas_metric_names": st.session_state.get(
                "ragas_metric_names", []
            ),
            "evaluation_running": st.session_state.get(
                "evaluation_running", False
            ),
        }

    @staticmethod
    def setup_openai_environment(api_key: str) -> None:
        """
        Set up OpenAI environment variable for evaluation.

        Args:
            api_key: OpenAI API key
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

    @staticmethod
    def log_configuration(config: Dict[str, Any], logger) -> None:
        """
        Log current configuration (safely, without exposing sensitive data).

        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        safe_config = {
            "rag_api_url": config.get("rag_api_url", ""),
            "username": config.get("username", ""),
            "password": "***" if config.get("password") else "(empty)",
            "kb_name": config.get("kb_name", ""),
            "openai_model": config.get("openai_model", ""),
            "openai_api_key": (
                "Set" if config.get("openai_api_key") else "Not set"
            ),
        }

        logger.info("Current configuration:")
        for key, value in safe_config.items():
            logger.info(f"  {key}: '{value}'")


def initialize_ragas_if_needed(enable_reference_metrics: bool) -> None:
    """
    Initialize RAGAS if needed based on current mode.

    Args:
        enable_reference_metrics: Whether reference metrics are enabled
    """
    from utils.ragas_setup import (
        setup_ragas,
    )  # Import here to avoid circular imports

    should_init = SessionStateManager.should_reinitialize_ragas(
        enable_reference_metrics
    )

    if should_init:
        with st.spinner("Setting up RAGAS metrics..."):
            ragas_available, metrics, metric_names, error_message = (
                setup_ragas(enable_reference_metrics)
            )
            SessionStateManager.update_ragas_state(
                ragas_available, metrics, metric_names, error_message
            )
            SessionStateManager.update_ragas_mode(enable_reference_metrics)
