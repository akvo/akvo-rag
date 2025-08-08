#!/usr/bin/env python3
"""
Headless RAG evaluation runner script.

This script runs RAG evaluation with configurable parameters.
"""

import sys
import os
import json
import pandas as pd
from headless_evaluation import run_headless_evaluation


def main():
    """Main function to run headless evaluation with command-line arguments."""
    # Default values (can be overridden by environment variables or script parameters)
    kb_name = 'Living Income Benchmark Knowledge Base'
    openai_model = 'gpt-4o'
    output_file = ''
    username = 'admin@example.com'
    password = 'password'
    rag_api_url = 'http://localhost:8000'
    csv_file = ''
    metrics_mode = 'full'
    queries = None
    reference_answers = None
    save_performance_report = False

    # Get values from environment (set by shell script)
    kb_name = os.getenv('KB_NAME', kb_name)
    username = os.getenv('USERNAME', username)
    password = os.getenv('PASSWORD', password)
    rag_api_url = os.getenv('RAG_API_URL', rag_api_url)
    csv_file = os.getenv('CSV_FILE', csv_file)
    output_file = os.getenv('OUTPUT_FILE', output_file)
    metrics_mode = os.getenv('METRICS_MODE', metrics_mode)
    save_performance_report = os.getenv('SAVE_PERFORMANCE_REPORT', 'false').lower() == 'true'

    # Load queries and reference answers from CSV if provided
    if csv_file and csv_file.strip():
        try:
            print(f'Loading queries from CSV file: {csv_file}')
            df = pd.read_csv(csv_file)
            if 'prompt' in df.columns:
                queries = df['prompt'].tolist()
                print(f'Loaded {len(queries)} queries from CSV')
                
                # Check for reference answers
                if 'reference' in df.columns:
                    reference_answers = df['reference'].tolist()
                    print(f'Loaded {len(reference_answers)} reference answers from CSV')
                else:
                    print('No reference answers found in CSV (no "reference" column)')
            else:
                print('Error: CSV file must have a "prompt" column')
                sys.exit(1)
        except Exception as e:
            print(f'Error loading CSV file: {e}')
            sys.exit(1)

    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--kb' and i+1 < len(args):
            kb_name = args[i+1]
            i += 2
        elif args[i] == '--openai-model' and i+1 < len(args):
            openai_model = args[i+1]
            i += 2
        elif args[i] == '--output' and i+1 < len(args):
            output_file = args[i+1]
            i += 2
        elif args[i] == '--metrics-mode' and i+1 < len(args):
            metrics_mode = args[i+1]
            i += 2
        else:
            i += 1

    # Validate metrics mode
    valid_modes = ['basic', 'full', 'reference-only']
    if metrics_mode not in valid_modes:
        print(f'Error: Invalid metrics mode "{metrics_mode}". Valid options: {", ".join(valid_modes)}')
        sys.exit(1)

    # Print configuration
    print(f'Running evaluation on knowledge base: {kb_name}')
    print(f'Using model: {openai_model}')
    print(f'Using credentials: {username}')
    print(f'Using API URL: {rag_api_url}')
    print(f'Metrics mode: {metrics_mode}')
    if output_file:
        print(f'CSV output will be saved to: {output_file}')
    if queries:
        print(f'Using {len(queries)} queries from CSV file')
    else:
        print('Using default queries')
    
    if reference_answers:
        print(f'Reference answers provided: {len(reference_answers)} answers')
    else:
        print('No reference answers provided')
    
    # Validate reference-only mode requirements
    if metrics_mode == 'reference-only':
        if not reference_answers or not any(ref.strip() for ref in reference_answers):
            print('Error: reference-only mode requires reference answers in the CSV file')
            sys.exit(1)
        print('Reference-only mode: will only evaluate reference-based metrics')

    # Run evaluation
    results = run_headless_evaluation(
        kb_name=kb_name,
        queries=queries,
        reference_answers=reference_answers,
        openai_model=openai_model,
        username=username,
        password=password,
        rag_api_url=rag_api_url,
        metrics_mode=metrics_mode,
        save_performance_report=save_performance_report
    )

    # Output results with JSON serialization fix
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types for JSON serialization"""
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        return obj
    
    # Convert results to handle numpy types
    serializable_results = convert_numpy_types(results)
    
    # Handle CSV output if requested
    if output_file and output_file.strip():
        # Import CSV processor
        try:
            sys.path.append('/app/RAG_evaluation/streamlit_app/utils')
            from csv_handling import CSVProcessor
            
            # Generate CSV data
            rag_results = results.get('rag_results', [])
            if rag_results:
                # Generate CSV data using the new metrics_mode parameter
                csv_data = CSVProcessor.generate_results_csv(rag_results, metrics_mode=metrics_mode)
                
                if csv_data:
                    # Handle output path
                    if output_file.endswith('/') or output_file == '.':
                        # If output is a directory, generate default filename
                        from datetime import datetime
                        os.makedirs(output_file, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"rag_evaluation_results_{timestamp}.csv"
                        full_output_path = os.path.join(output_file, filename)
                    else:
                        full_output_path = output_file
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    # Write CSV file
                    with open(full_output_path, 'w', encoding='utf-8') as f:
                        f.write(csv_data)
                    print(f'CSV results saved to: {full_output_path}')
                else:
                    print('Warning: Failed to generate CSV data')
            else:
                print('Warning: No evaluation results available for CSV output')
        except Exception as e:
            print(f'Warning: Failed to generate CSV output: {str(e)}')
            print('Results will be output as JSON only')
    
    # Always output JSON results to stdout for backward compatibility
    if not output_file:
        print(json.dumps(serializable_results, indent=2))
    else:
        print('Evaluation completed successfully')


if __name__ == '__main__':
    main()