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

## Usage

1. **Upload via Streamlit UI**: Use the file uploader in the web interface
2. **Headless evaluation**: Pass these files to the command-line evaluation scripts
3. **Testing**: Use these as examples when creating your own CSV files

## Format

These files follow the basic CSV format:
```csv
prompt
Your question here
Another question here
```

For Full mode evaluation (8 metrics), you would need files with both `prompt` and `reference_answer` columns. You can download the Full mode template from the Streamlit UI to see the required format.