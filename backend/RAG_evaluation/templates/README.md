# CSV Templates

This directory contains CSV templates for the RAG evaluation system.

## Templates

### `basic_template.csv`
- **Purpose**: Template for Basic mode (4 metrics) evaluation
- **Columns**: `prompt`
- **Use case**: When you don't have reference answers for queries

### `full_template.csv`
- **Purpose**: Template for Full mode (8 metrics) evaluation  
- **Columns**: `prompt`, `reference_answer`
- **Use case**: When you have reference answers for enhanced metrics like Answer Similarity and Answer Correctness

## Usage

These templates are automatically served by the Streamlit application when users click "Download CSV Template". The appropriate template is selected based on the evaluation mode:

- **Basic Mode**: Downloads `basic_template.csv` content
- **Full Mode**: Downloads `full_template.csv` content

## Customization

You can modify these templates to:
- Change the example questions
- Add more sample rows
- Update the reference answers

Changes will be reflected in the downloaded templates immediately.