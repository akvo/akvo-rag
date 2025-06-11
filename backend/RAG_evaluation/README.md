# Akvo RAG Evaluation System

A system to evaluate RAG (Retrieval-Augmented Generation) responses and iterate on settings that might affect quality.

## Quick Start

```bash
# 1. Make sure Akvo RAG is running
docker compose up -d

# 2. Run the evaluation dashboard
./rag-evaluate
```

Then open http://localhost:8501 in your browser.

## How It Works

The evaluation system:

1. Creates a dedicated virtual environment to avoid dependency conflicts
2. Installs required dependencies in the isolated environment
3. Configures and exposes the Streamlit port
4. Runs the evaluation dashboard in the virtual environment

This approach keeps the evaluation dependencies separate from the main system to prevent conflicts.

## Configuration

### Required Setup

Before running the evaluation, ensure:

1. A knowledge base with label "Living Income Benchmark Knowledge Base" exists
2. Akvo RAG containers are running with `docker compose up`

### Dashboard Settings

In the Streamlit UI, configure:

- **Connection Settings**: API URL, username, and password
- **Knowledge Base**: Label of the knowledge base to evaluate
- **Evaluation LLM**: OpenAI API key and model (required for RAGAS metrics)
- **Test Queries**: Modify or add queries for evaluation

## Features

- Evaluate RAG responses against RAGAS metrics
- Visualize response times and quality metrics
- Inspect retrieved contexts for each query
- View detailed system logs for debugging

## Troubleshooting

- **RAGAS metrics not showing**: Ensure you've provided an OpenAI API key
- **Connection errors**: Verify Akvo RAG is running and the API URL is correct
- **Dependency issues**: The system uses a virtual environment, so dependency conflicts should be resolved automatically

## Advanced Usage

You can pass additional parameters to the evaluation script:

```bash
# Use a different knowledge base
./rag-evaluate --kb "Your Knowledge Base Label"

# Use a different port
./rag-evaluate --port 8502

# Skip dependency and service checks
./rag-evaluate --skip-checks
```