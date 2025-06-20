#!/usr/bin/env python3
"""
Headless RAG evaluation runner script.

This script runs RAG evaluation with configurable parameters.
"""

import sys
import json
import pandas as pd
from headless_evaluation import run_headless_evaluation


def main():
    """Main function to run headless evaluation with command-line arguments."""
    # Default values (can be overridden by environment variables or script parameters)
    kb_name = 'Living Income Benchmark Knowledge Base'
    openai_model = 'gpt-4o'
    output_file = None
    username = 'admin@example.com'
    password = 'password'
    rag_api_url = 'http://localhost:8000'
    csv_file = ''
    queries = None

    # Get values from environment (set by shell script)
    import os
    kb_name = os.getenv('KB_NAME', kb_name)
    username = os.getenv('USERNAME', username)
    password = os.getenv('PASSWORD', password)
    rag_api_url = os.getenv('RAG_API_URL', rag_api_url)
    csv_file = os.getenv('CSV_FILE', csv_file)

    # Load queries from CSV if provided
    if csv_file and csv_file.strip():
        try:
            print(f'Loading queries from CSV file: {csv_file}')
            df = pd.read_csv(csv_file)
            if 'prompt' in df.columns:
                queries = df['prompt'].tolist()
                print(f'Loaded {len(queries)} queries from CSV')
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
        else:
            i += 1

    # Print configuration
    print(f'Running evaluation on knowledge base: {kb_name}')
    print(f'Using model: {openai_model}')
    print(f'Using credentials: {username}')
    print(f'Using API URL: {rag_api_url}')
    if queries:
        print(f'Using {len(queries)} queries from CSV file')
    else:
        print('Using default queries')

    # Run evaluation
    results = run_headless_evaluation(
        kb_name=kb_name,
        queries=queries,
        openai_model=openai_model,
        username=username,
        password=password,
        rag_api_url=rag_api_url
    )

    # Output results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f'Results saved to {output_file}')
    else:
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()