# Akvo RAG Evaluation System

A comprehensive system to evaluate RAG (Retrieval-Augmented Generation) responses using RAGAS metrics and iterate on settings that might affect quality. Supports both interactive dashboard evaluation and headless command-line evaluation.

## Quick Start

### Interactive Dashboard
```bash
# From the main akvo-rag directory
./rag-evaluate
```

Then open http://localhost:8501 in your browser.

### Headless Evaluation
```bash
# From the backend/RAG_evaluation directory
./run_headless.sh -u "username" -p "password" -a "https://your-rag-api.com" -k "Your Knowledge Base" -c "your_prompts.csv"
```

## How It Works

The evaluation system provides two modes of operation:

### Interactive Mode
1. Sets up Docker to ensure both the API and Streamlit ports are exposed
2. Creates a dedicated virtual environment to avoid dependency conflicts
3. Installs required dependencies in the isolated environment
4. Runs the evaluation dashboard in the virtual environment

### Headless Mode
1. Connects to your RAG API using provided credentials
2. Reads evaluation prompts from CSV file or uses defaults
3. Generates responses and retrieves context for each prompt
4. Evaluates responses using RAGAS metrics
5. Outputs comprehensive evaluation results in JSON format

This approach keeps the evaluation dependencies separate from the main system to prevent conflicts and ensures both the API and Streamlit are accessible.

## RAGAS Evaluation Metrics

The system evaluates RAG responses using four key RAGAS v0.2.15 metrics:

### Context-Dependent Metrics
These metrics require the retrieved context/documents and evaluate how well the RAG system uses them:

- **Faithfulness** (0.0-1.0): Measures how well grounded the response is in the retrieved context. Higher scores indicate the response is more factually consistent with the provided documents.

- **Context Relevancy** (0.0-1.0): Evaluates how relevant the retrieved context is to the user's query. Higher scores mean the retrieval system found more relevant documents.

- **Context Precision** (0.0-1.0): Measures the precision of context retrieval without requiring reference answers. Evaluates whether the most relevant contexts appear early in the retrieved results.

### Response-Only Metrics
These metrics evaluate the quality of the generated response itself:

- **Answer Relevancy** (0.0-1.0): Measures how relevant the generated response is to the original query. Higher scores indicate better alignment between the question asked and the answer provided.

All metrics return scores between 0.0 and 1.0, with higher scores indicating better performance.

## Headless Evaluation

### Basic Usage
```bash
# Evaluate with default prompts
./run_headless.sh -u "your_username" -p "your_password" -a "https://your-rag-api.com" -k "Your Knowledge Base Name"

# Evaluate with custom CSV prompts
./run_headless.sh -u "admin" -p "password" -a "http://localhost:8000" -k "My Knowledge Base" -c "custom_prompts.csv"
```

### CSV Format
Create a CSV file with a `prompt` column containing your evaluation queries:

```csv
prompt
"What is the investment climate in Kenya?"
"How do you apply for a business license?"
"What are the main challenges for farmers?"
```

### Command Line Options
- `-u USERNAME`: Authentication username
- `-p PASSWORD`: Authentication password  
- `-a API_URL`: RAG API URL (e.g., https://your-rag-api.com)
- `-k KB_NAME`: Knowledge base name to evaluate against
- `-c CSV_FILE`: Optional CSV file with custom prompts

### Output
The headless evaluation outputs comprehensive JSON results including:
- Individual query responses and contexts
- RAGAS metric scores for each query
- Response times and system metadata
- Detailed logs for debugging

## Configuration

### Required Setup

Before running the evaluation, ensure:

1. Docker is installed and running
2. Your RAG API is accessible and running
3. Knowledge base exists with the specified name
4. OpenAI API key is set in environment variable `OPENAI_API_KEY`

### Dashboard Settings

In the Streamlit UI, configure:

- **Connection Settings**: API URL, username, and password
- **Knowledge Base**: Name of the knowledge base to evaluate
- **Evaluation LLM**: OpenAI API key and model (required for RAGAS metrics)
- **Test Queries**: Modify or add queries for evaluation

## Features

- **Four RAGAS Metrics**: Comprehensive evaluation including context-dependent and response-only metrics
- **Dual Mode Operation**: Interactive dashboard and headless command-line evaluation
- **Custom CSV Input**: Evaluate with your own test prompts
- **Context Analysis**: Inspect retrieved contexts and citations for each query
- **Performance Metrics**: Visualize response times and quality metrics
- **Detailed Logging**: View system logs for debugging and analysis
- **External API Support**: Evaluate any RAG API, not just local instances

## Troubleshooting

- **RAGAS metrics not showing**: Ensure you've set the `OPENAI_API_KEY` environment variable
- **Context-based metrics failing**: Verify your RAG API returns proper context/citations in responses
- **Connection errors**: Ensure your RAG API is running and accessible at the specified URL
- **Authentication issues**: Verify username and password are correct for your RAG API
- **CSV format errors**: Ensure your CSV file has a `prompt` column with valid queries
- **Docker issues**: For local evaluation, ensure the RAG API container is running:
  ```bash
  cd /path/to/akvo-rag
  docker compose -f docker-compose.dev.yml up -d
  ```
- **Dependency conflicts**: The system uses isolated virtual environments to prevent conflicts

## Advanced Usage

### Interactive Dashboard
```bash
# From the main akvo-rag directory, use different options
../rag-evaluate --kb "Your Knowledge Base Name"
../rag-evaluate --port 8502
../rag-evaluate --skip-checks
```

### Environment Variables
Set these environment variables for headless evaluation:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export RAG_API_URL="https://your-rag-api.com"
export USERNAME="your-username"
export PASSWORD="your-password"
```

## End-to-End Testing

Automated tests verify the complete 8-metric evaluation workflow using Playwright to interact with the Streamlit UI.

### Prerequisites

**PRECONDITION**: From project root, run `./rag-evaluate` to start all containers and Streamlit UI.

```bash
cd /path/to/akvo-rag
./rag-evaluate  # This starts all containers including Streamlit on localhost:8501
```

**Environment**: Set your OpenAI API key
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Option 1: Container Testing (Headless)

In bash in the backend container, run `pytest` and end-to-end tests execute headless:

```bash
# Exec into the backend container
docker exec -it akvo-rag-backend-1 bash

# Navigate to RAG evaluation directory
cd RAG_evaluation

# Run E2E tests
pytest

# Run with verbose output to see detailed test execution
pytest tests/test_eight_metrics_e2e.py -v -s --tb=long
```

**What happens:**
- Tests run headless (no browser window)
- Uses configuration from `.env.test`
- Returns pass/fail with detailed output
- Takes 5-7 minutes to complete

**Verbose Output Options:**
- `-v`: Verbose test names and status
- `-s`: Show print statements and real-time output
- `--tb=long`: Full tracebacks on failures
- This shows step-by-step progress, metric values, and detailed verification

### Option 2: Host Testing (Headed Browser)

On your host, run the test script with headed browser:

```bash
./backend/RAG_evaluation/test-RAG-evaluation-ui-e2e.sh
```

**What happens:**
- Installs dependencies if needed in local virtual environment
- Opens browser window on your host
- Shows real-time automation of the UI
- Uses configuration from `.env.test`
- Browser stays open for 10 seconds at end for inspection

### Test Configuration

Edit `backend/RAG_evaluation/.env.test` to customize test parameters:

```bash
# RAG API Configuration
RAG_API_URL=http://localhost:8000
RAG_USERNAME=admin@example.com
RAG_PASSWORD=password
RAG_KNOWLEDGE_BASE=Living Income Benchmark Knowledge Base

# Test Data - CSV Upload (overrides individual queries if set)
# CSV_FILE_HOST=/path/to/your/test_queries.csv          # Path on host machine
# CSV_FILE_CONTAINER=/app/RAG_evaluation/test_data.csv  # Path inside container

# Test Data - Individual Queries (used if CSV not provided)
TEST_QUERY_1=What is the living income benchmark?
TEST_REFERENCE_1=The living income benchmark is a measure of income needed for a decent standard of living.

TEST_QUERY_2=How is the living income benchmark calculated?
TEST_REFERENCE_2=The living income benchmark is calculated based on cost of basic needs.

# Test Configuration
EVALUATION_TIMEOUT_SECONDS=420
BROWSER_SLOW_MO=1000
```

### Expected Results

**Success Criteria:**
- All 8 metrics calculated with numerical values (0.0-1.0)
- No "N/A" values for reference-based metrics  
- Full Mode (8 metrics) successfully selected
- Reference answers properly entered and used

**8 Metrics Verified:**
1. Faithfulness
2. Answer Relevancy  
3. Context Precision Without Reference
4. Context Relevancy
5. Answer Similarity 📚
6. Answer Correctness 📚  
7. Context Precision 📚
8. Context Recall 📚

*(📚 = Reference-based metrics requiring reference answers)*
