# Akvo RAG Evaluation System

A system to evaluate RAG (Retrieval-Augmented Generation) responses and iterate on settings that might affect quality.

## Quick Start

```bash
# 1. Make sure Akvo RAG is running
docker compose up -d

# 2. Copy the Streamlit port override
cp backend/RAG_evaluation/docker-compose.override.yml .

# 3. Restart containers with the override
docker compose down
docker compose up -d

# 4. Install dependencies
docker exec -it akvo-rag-backend pip install -r /app/RAG_evaluation/requirements.txt

# 5. Run the evaluation dashboard
docker exec -it akvo-rag-backend python /app/RAG_evaluation/run_evaluation.py
```

Then open http://localhost:8501 in your browser.

## Configuration

### Required Setup

Before running the evaluation, ensure:

1. A knowledge base with label "Living Income Benchmark Knowledge Base" exists
2. Akvo RAG containers are running with `docker compose up`
3. Dependencies are installed

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
- **Dependency issues**: Run with `--install-deps` flag or manually install from requirements.txt

## Running Without Docker

If you prefer to run the evaluation system directly:

```bash
# Install dependencies
cd backend/RAG_evaluation
pip install -r requirements.txt

# Run the evaluation dashboard
python run_evaluation.py --kb "Your Knowledge Base Label"
```

Additional options:
- `--port` - Specify a custom port (default: 8501)
- `--skip-checks` - Skip dependency and service checks
- `--install-deps` - Automatically install missing dependencies