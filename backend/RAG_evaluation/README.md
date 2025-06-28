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

The system evaluates RAG responses using comprehensive RAGAS v0.2.15 metrics. All metrics return scores between 0.0 and 1.0, with higher scores indicating better performance.

### Metrics Without a Reference Answer
These metrics are designed to evaluate the performance of your RAG pipeline without the need for a pre-written "golden" or ground truth answer, making them highly flexible for real-world applications.

#### 🧠 Faithfulness: How well-grounded is the response in the retrieved context?
This metric checks whether the generated answer is factually consistent with the information present in the provided context.

**Step 1: Statement Extraction**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to read the generated answer and break it down into a series of individual statements or claims.

**Step 2: Statement Verification**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** For each extracted statement, the language model is asked to determine if it can be directly inferred from the provided context. It essentially performs a fact-checking task, comparing each claim against the source text.

**Step 3: Score Calculation**
- **Process:** The faithfulness score is calculated as the ratio of the number of statements that are successfully verified against the context to the total number of statements extracted from the answer.

```
Faithfulness = Number of claims in answer supported by context / Total number of claims in answer
```

#### 🧠 Context Relevancy: How relevant is the retrieved context to the query?
This metric assesses the signal-to-noise ratio of your retrieved context, penalizing the inclusion of irrelevant information.

**Step 1: Identifying Critical Sentences**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to identify the essential sentences from the context that are crucial for answering the question.

**Step 2: Score Calculation**
- **Process:** The context relevancy score is the ratio of the number of identified critical sentences to the total number of sentences in the context.

```
Context Relevancy = Number of relevant sentences in context / Total number of sentences in context
```

#### Answer Relevancy: How relevant is the response to the original query?
This metric evaluates whether the generated answer directly addresses the user's question.

**Step 1: Generating Synthetic Questions**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is tasked with generating multiple potential questions for which the provided answer would be a suitable response.

**Step 2: Semantic Similarity Calculation**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** The original question and the newly generated synthetic questions are converted into numerical vectors (embeddings). The cosine similarity between the original question's embedding and the average of the synthetic questions' embeddings is then calculated. A high similarity suggests the answer was highly relevant to the original question.

#### 🧠 Context Precision Without Reference: Is the context that was retrieved actually used to formulate the answer?
This metric measures how much of the provided context was useful in generating the final answer.

**Step 1: Identifying Used Chunks**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to analyze the answer and the context. It then identifies which sentences or "chunks" from the context were directly used to construct the answer.

**Step 2: Score Calculation**
- **Process:** The score is the ratio of the number of context chunks that were deemed useful in generating the answer to the total number of chunks in the context.

### Metrics With a Reference Answer
These metrics require a ground truth or reference answer to compare against the generated output. They are typically used for more rigorous, benchmark-style evaluations.

#### 🧠📚 Context Recall: Does the retrieved context contain the information needed to answer the question?
This metric evaluates whether the retrieved context contains all the information present in the ground truth answer.

**Step 1: Statement Extraction from Ground Truth**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model breaks down the ground_truth answer into a set of individual statements.

**Step 2: Statement Verification against Context**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** For each statement from the ground truth, the model checks if it can be supported by the retrieved context.

**Step 3: Score Calculation**
- **Process:** The context recall score is the ratio of the number of ground truth statements supported by the context to the total number of statements in the ground truth.

```
Context Recall = Number of claims in ground truth supported by context / Total number of claims in ground truth
```

#### 🧠📚 Context Precision: Is the retrieved context relevant to the ground truth?
This metric is similar to Context Relevancy but uses the ground truth answer as the reference for relevance.

**Step 1: Identifying Relevant Chunks**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to determine if each chunk in the retrieved context is relevant for generating the ground_truth answer.

**Step 2: Score Calculation**
- **Process:** The score is the ratio of the number of relevant context chunks to the total number of retrieved chunks.

#### 📚 Answer Similarity: How semantically similar is the generated answer to the reference answer?
This metric gauges the semantic overlap between the generated and ground truth answers.

**Step 1: Embedding Generation**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** Both the generated answer and the ground_truth answer are converted into numerical vector embeddings.

**Step 2: Cosine Similarity**
- **Process:** The cosine similarity between the two embeddings is calculated. A score closer to 1 indicates a high degree of semantic similarity.

#### 📚 Answer Correctness: Is the generated answer factually and semantically correct compared to the reference answer?
This is a composite metric that considers both factual and semantic alignment with the ground truth.

**Step 1: Factual Comparison**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model analyzes both the generated answer and the ground_truth to identify a list of true positives (correct statements in both), false positives (incorrect statements in the answer), and false negatives (statements in the ground truth missed by the answer). An F1-score is then calculated based on these counts.

**Step 2: Semantic Similarity**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** The semantic similarity between the answer and ground_truth is calculated as described in the "Answer Similarity" metric.

**Step 3: Weighted Average**
- **Process:** The final answer correctness score is a weighted average of the factual F1-score and the semantic similarity score.

### Metric Icons
- 🧠 = Context-dependent metrics (require retrieved context)
- 📚 = Reference-based metrics (require reference answers)

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

### Embedding Model Selection

The evaluation system uses **RAGAS v0.2.15** which automatically selects embedding models for similarity calculations in metrics like Answer Similarity:

**Primary (Default)**: **OpenAI `text-embedding-ada-002`**
- Used when `OPENAI_API_KEY` is available
- Handles semantic similarity calculations between generated and reference answers
- Shares the same API rate limits as the evaluation LLM

**Fallback**: **`BAAI/bge-small-en-v1.5`** (Hugging Face)
- Local sentence-transformers model used when OpenAI embeddings are unavailable
- Reduces API costs but requires local compute resources

**Rate Limiting**: When using OpenAI embeddings with OpenAI LLMs (like `gpt-4o`), you may encounter 429 rate limiting errors as both services share API quotas. The system automatically retries with exponential backoff, but evaluations may take longer during high usage periods.

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

After running ./rag-evaluate on the host, in bash in the backend container, run `pytest` and end-to-end tests execute headless:

```bash
# Exec into the backend container
docker exec -it akvo-rag-backend-1 bash

# Navigate to RAG evaluation directory
cd RAG_evaluation

# Activate the virtual environment
source venv/bin/activate

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
