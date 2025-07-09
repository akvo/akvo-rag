# Example CSV Inputs

This directory contains example CSV files that can be used to test the RAG evaluation system.

## Files

### `kenya_prompts.csv`
- **Type**: Multi-query CSV with prompts only (Basic mode compatible)
- **Queries**: 4 investment-related questions about Kenya
- **Use case**: Testing basic evaluation mode without reference answers
- **Columns**: `prompt`

### `single_query.csv`  
- **Type**: Single query CSV (Basic mode compatible)
- **Queries**: 1 investment climate question about Kenya
- **Use case**: Testing simple single-query evaluation
- **Columns**: `prompt`

### `kenya_drylands_full_evaluation.csv`
- **Type**: Full evaluation CSV with prompts and reference answers (Full mode compatible)
- **Queries**: 20 comprehensive investment-related questions about Kenya Drylands
- **Use case**: Testing full 8-metric evaluation mode with reference answers
- **Columns**: `prompt`, `reference_answer`
- **Source**: Converted from RAG Test data with NotebookLM outputs as reference answers
- **Content**: Investment climate, challenges, ASAL regions, government support, and sector-specific questions

## Usage

1. **Upload via Streamlit UI**: Use the file uploader in the web interface
2. **Headless evaluation**: Pass these files to the command-line evaluation scripts
3. **Testing**: Use these as examples when creating your own CSV files

## Format

### Basic Mode Format (4 metrics)
Files like `kenya_prompts.csv` and `single_query.csv`:
```csv
prompt
Your question here
Another question here
```

### Full Mode Format (8 metrics)  
Files like `kenya_drylands_full_evaluation.csv`:
```csv
prompt,reference_answer
Your question here,Expected answer with detailed explanation
Another question here,Another comprehensive reference answer
```

The `kenya_drylands_full_evaluation.csv` file demonstrates the full format with real-world investment questions and comprehensive reference answers from NotebookLM, making it ideal for testing all 8 RAGAS metrics including Answer Similarity and Answer Correctness.