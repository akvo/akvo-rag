"""
CSV Handling Utilities for RAG Evaluation

This module provides utilities for processing CSV uploads, generating templates,
and converting evaluation results to CSV format.
"""

import pandas as pd
import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from constants import (
    CSV_TEMPLATES, CSV_PROMPT_COLUMNS, CSV_REFERENCE_COLUMNS, 
    FILE_PATTERNS, BASIC_METRICS, REFERENCE_METRICS
)

logger = logging.getLogger("rag_evaluation")


class CSVProcessor:
    """Handles all CSV-related operations for the RAG evaluation application."""
    
    @staticmethod
    def load_template(template_name: str, fallback_key: str) -> str:
        """
        Load template content from templates directory with fallback.
        
        Args:
            template_name: Name of template file to load
            fallback_key: Key in CSV_TEMPLATES for fallback content
            
        Returns:
            Template content as string
        """
        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "templates", template_name)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Template file not found: {template_path}")
            return CSV_TEMPLATES.get(fallback_key, "")
    
    @staticmethod
    def get_template_for_mode(enable_reference_metrics: bool) -> Tuple[str, str, str]:
        """
        Get appropriate template content and filename for the current mode.
        
        Args:
            enable_reference_metrics: Whether reference metrics are enabled
            
        Returns:
            Tuple of (template_content, filename, help_text)
        """
        if enable_reference_metrics:
            template_csv = CSVProcessor.load_template("full_template.csv", "full")
            template_filename = FILE_PATTERNS['full_template']
            help_text = "Download a CSV template with reference answers for full evaluation mode"
        else:
            template_csv = CSVProcessor.load_template("basic_template.csv", "basic")
            template_filename = FILE_PATTERNS['basic_template']
            help_text = "Download a basic CSV template for queries only"
        
        return template_csv, template_filename, help_text
    
    @staticmethod
    def detect_csv_format(df: pd.DataFrame) -> Tuple[bool, bool, Optional[str]]:
        """
        Detect CSV format and validate structure.
        
        Args:
            df: Pandas DataFrame from CSV
            
        Returns:
            Tuple of (has_prompts, has_references, error_message)
        """
        # Check for required prompt column
        prompt_col = None
        for col in CSV_PROMPT_COLUMNS:
            if col in df.columns:
                prompt_col = col
                break
        
        if not prompt_col:
            return False, False, f"CSV must contain one of these columns: {', '.join(CSV_PROMPT_COLUMNS)}"
        
        # Check for reference columns
        has_references = any(col in df.columns for col in CSV_REFERENCE_COLUMNS)
        
        return True, has_references, None
    
    @staticmethod
    def parse_csv_queries(df: pd.DataFrame) -> Tuple[List[str], Optional[List[str]], Optional[str]]:
        """
        Parse queries and references from uploaded CSV.
        
        Args:
            df: Pandas DataFrame from CSV upload
            
        Returns:
            Tuple of (queries, references_or_none, error_message_or_none)
        """
        try:
            has_prompts, has_references, error_msg = CSVProcessor.detect_csv_format(df)
            
            if not has_prompts:
                return [], None, error_msg
            
            # Find the prompt column
            prompt_col = None
            for col in CSV_PROMPT_COLUMNS:
                if col in df.columns:
                    prompt_col = col
                    break
            
            # Extract queries
            queries = df[prompt_col].dropna().astype(str).tolist()
            queries = [q.strip() for q in queries if q.strip()]
            
            # Extract references if available
            references = None
            if has_references:
                reference_col = None
                for col in CSV_REFERENCE_COLUMNS:
                    if col in df.columns:
                        reference_col = col
                        break
                
                if reference_col:
                    references = df[reference_col].fillna("").astype(str).tolist()
                    # Ensure same length as queries
                    while len(references) < len(queries):
                        references.append("")
                    references = references[:len(queries)]
            
            return queries, references, None
            
        except Exception as e:
            error_msg = f"Error parsing CSV: {str(e)}"
            logger.error(error_msg)
            return [], None, error_msg
    
    @staticmethod
    def generate_results_csv(results: List[Dict[str, Any]], 
                           enable_reference_metrics: bool = False) -> Optional[str]:
        """
        Convert evaluation results to CSV format.
        
        Args:
            results: List of evaluation result dictionaries
            enable_reference_metrics: Whether reference metrics are included
            
        Returns:
            CSV string or None if generation failed
        """
        if not results:
            logger.warning("No results provided for CSV generation")
            return None
        
        try:
            csv_data = []
            metric_names = BASIC_METRICS + REFERENCE_METRICS
            
            for i, result in enumerate(results):
                # Create base row structure based on mode
                if enable_reference_metrics:
                    row = {
                        "Query_ID": f"Q{i+1}",
                        "Query": result.get('query', ''),
                        "Reference_Answer": result.get('reference_answer', ''),
                        "Response": result.get('answer', result.get('response', '')),
                        "Response_Time_Seconds": result.get('response_time', 0),
                        "Context_Count": len(result.get('contexts', [])),
                        "Has_Error": 'Yes' if 'error' in result else 'No',
                        "Error_Message": result.get('error', '')
                    }
                else:
                    row = {
                        "Query_ID": f"Q{i+1}",
                        "Query": result.get('query', ''),
                        "Response": result.get('answer', result.get('response', '')),
                        "Response_Time_Seconds": result.get('response_time', 0),
                        "Context_Count": len(result.get('contexts', [])),
                        "Has_Error": 'Yes' if 'error' in result else 'No',
                        "Error_Message": result.get('error', '')
                    }
                
                # Add metric scores
                for metric in metric_names:
                    metric_key = metric.replace('_', ' ').title().replace(' ', '_')
                    if metric in result and result[metric] is not None:
                        row[metric_key] = f"{result[metric]:.4f}"
                    else:
                        row[metric_key] = 'N/A'
                
                # Add contexts as combined text field
                if 'contexts' in result and result['contexts']:
                    contexts_text = "\n\n--- CONTEXT SEPARATOR ---\n\n".join(result['contexts'])
                    row['Retrieved_Contexts'] = contexts_text
                else:
                    row['Retrieved_Contexts'] = ''
                
                csv_data.append(row)
            
            # Convert to DataFrame and then to CSV
            df = pd.DataFrame(csv_data)
            csv_result = df.to_csv(index=False)
            logger.info(f"Successfully generated CSV with {len(df)} rows")
            return csv_result
            
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}")
            return None
    
    @staticmethod
    def get_results_filename() -> str:
        """
        Generate a timestamped filename for results CSV.
        
        Returns:
            Filename string with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return FILE_PATTERNS['results_csv'].format(timestamp=timestamp)
    
    @staticmethod
    def validate_uploaded_file(uploaded_file) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded file before processing.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Tuple of (is_valid, error_message_or_none)
        """
        if uploaded_file is None:
            return False, "No file uploaded"
        
        if not uploaded_file.name.lower().endswith('.csv'):
            return False, "File must be a CSV file"
        
        if uploaded_file.size == 0:
            return False, "File is empty"
        
        if uploaded_file.size > 10 * 1024 * 1024:  # 10MB limit
            return False, "File too large (max 10MB)"
        
        return True, None
    
    @staticmethod
    def create_file_info_tuple(uploaded_file) -> Optional[Tuple[str, int]]:
        """
        Create a file info tuple for change detection.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Tuple of (filename, size) or None if no file
        """
        if uploaded_file is not None:
            return (uploaded_file.name, uploaded_file.size)
        return None
    
    @staticmethod
    def log_csv_processing(queries: List[str], references: Optional[List[str]], 
                          enable_reference_metrics: bool) -> None:
        """
        Log CSV processing results.
        
        Args:
            queries: Parsed queries
            references: Parsed references (optional)
            enable_reference_metrics: Whether reference metrics are enabled
        """
        logger.info(f"CSV processing completed:")
        logger.info(f"  Queries found: {len(queries)}")
        
        if references:
            ref_count = len([ref for ref in references if ref.strip()])
            logger.info(f"  Reference answers found: {ref_count}")
            logger.info(f"  Reference metrics enabled: {enable_reference_metrics}")
        else:
            logger.info(f"  No reference answers found")
        
        if queries:
            logger.info(f"  First query preview: {queries[0][:100]}...")


def parse_csv_queries(df: pd.DataFrame) -> Tuple[List[str], Optional[List[str]], Optional[str]]:
    """
    Legacy function wrapper for backwards compatibility.
    
    Args:
        df: Pandas DataFrame from CSV upload
        
    Returns:
        Tuple of (queries, references_or_none, error_message_or_none)
    """
    # First try the original function from headless_evaluation
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from headless_evaluation import parse_csv_queries as original_parse_csv_queries
        return original_parse_csv_queries(df)
    except ImportError:
        # Fallback to our implementation
        return CSVProcessor.parse_csv_queries(df)