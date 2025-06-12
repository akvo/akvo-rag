# Akvo RAG Evaluation System

A system to evaluate RAG (Retrieval-Augmented Generation) responses and iterate on settings that might affect quality.

## Quick Start

```bash
# Just run the evaluation dashboard with all setup handled automatically
./rag-evaluate
```

Then open http://localhost:8501 in your browser.

## How It Works

The evaluation system:

1. Sets up Docker to ensure both the API and Streamlit ports are exposed
2. Creates a dedicated virtual environment to avoid dependency conflicts
3. Installs required dependencies in the isolated environment
4. Runs the evaluation dashboard in the virtual environment

This approach keeps the evaluation dependencies separate from the main system to prevent conflicts and ensures both the API and Streamlit are accessible.

## Configuration

### Required Setup

Before running the evaluation, ensure:

1. A knowledge base with name "Living Income Benchmark Knowledge Base" exists
2. Docker is installed and running

### Dashboard Settings

In the Streamlit UI, configure:

- **Connection Settings**: API URL, username, and password
- **Knowledge Base**: Name of the knowledge base to evaluate
- **Evaluation LLM**: OpenAI API key and model (required for RAGAS metrics)
- **Test Queries**: Modify or add queries for evaluation

## Features

- Evaluate RAG responses against RAGAS metrics
- Visualize response times and quality metrics
- Inspect retrieved contexts for each query
- View detailed system logs for debugging

## Troubleshooting

- **RAGAS metrics not showing**: Ensure you've provided an OpenAI API key
- **Connection errors**: The setup script should ensure the API is accessible, but if you have issues, try running:
  ```bash
  cd /path/to/akvo-rag
  docker compose -f docker-compose.dev.yml -f streamlit-override.yml up -d
  ```
- **Dependency issues**: The system uses a virtual environment, so dependency conflicts should be resolved automatically

## Advanced Usage

You can pass additional parameters to the evaluation script:

```bash
# Use a different knowledge base
./rag-evaluate --kb "Your Knowledge Base Name"

# Use a different port
./rag-evaluate --port 8502

# Skip dependency and service checks
./rag-evaluate --skip-checks
```
