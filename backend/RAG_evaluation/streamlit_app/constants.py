"""
Constants and configuration values for RAG Evaluation application.

This module contains all constant values, default configurations,
and static content used throughout the application.
"""

from typing import List, Dict, Any

# Default test queries
DEFAULT_TEST_QUERIES: List[str] = [
    "What is the living income benchmark?",
    "How is the living income benchmark calculated?",
    "What factors influence the living income benchmark?",
    "How does the living income benchmark differ from minimum wage?",
    "What is the purpose of establishing a living income benchmark?"
]

# Metric categories
BASIC_METRICS: List[str] = [
    'faithfulness', 
    'answer_relevancy', 
    'context_precision_without_reference', 
    'context_relevancy'
]

REFERENCE_METRICS: List[str] = [
    'answer_similarity', 
    'answer_correctness', 
    'context_precision', 
    'context_recall'
]

ALL_METRICS: List[str] = BASIC_METRICS + REFERENCE_METRICS

# Context-dependent and reference-based metric categorization
CONTEXT_DEPENDENT_METRICS: set = {
    'faithfulness', 
    'context_relevancy', 
    'context_precision_without_reference', 
    'context_precision', 
    'context_recall'
}

REFERENCE_BASED_METRICS: set = {
    'answer_similarity', 
    'answer_correctness', 
    'context_precision', 
    'context_recall'
}

# CSV column mapping
CSV_PROMPT_COLUMNS: List[str] = ['prompt', 'query', 'question']
CSV_REFERENCE_COLUMNS: List[str] = ['reference_answer', 'reference', 'answer', 'expected_answer']

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    'rag_api_url': 'http://localhost:8000',
    'openai_models': ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo-16k'],
    'default_model': 'gpt-4o'
}

# UI Messages
UI_MESSAGES: Dict[str, str] = {
    'csv_success_with_refs': "✅ Loaded {query_count} queries with {ref_count} reference answers from CSV",
    'csv_success_no_refs': "✅ Loaded {query_count} queries from CSV (no reference answers)",
    'full_mode_enabled': "🎯 Full evaluation mode enabled with reference answers!",
    'full_mode_no_refs': "⚠️ Full mode selected but no reference answers found in CSV. Only basic metrics will be available.",
    'basic_mode_with_refs': "⚠️ Reference answers found but Basic mode selected. Switch to Full mode to use reference-based metrics.",
    'queries_prepared_with_refs': "✅ {query_count} queries prepared with {ref_count} reference answers",
    'queries_missing_refs': "⚠️ {missing_count} queries missing reference answers",
    'queries_prepared_basic': "✅ {query_count} queries prepared for basic evaluation",
    'no_queries_entered': "⚠️ No queries entered",
    'ragas_ready': "✅ RAGAS evaluation ready",
    'evaluation_complete': "Evaluation complete!",
    'evaluation_starting': "Starting evaluation...",
    'missing_fields': "Missing required fields: {fields}"
}

# Comprehensive metrics explanation markdown
METRICS_EXPLANATIONS: str = """
## Metrics Without a Reference Answer
These metrics are designed to evaluate the performance of your RAG pipeline without the need for a pre-written "golden" or ground truth answer, making them highly flexible for real-world applications.

### 🧠 Faithfulness: How well-grounded is the response in the retrieved context?
This metric checks whether the generated answer is factually consistent with the information present in the provided context.

**Step 1: Statement Extraction**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to read the generated answer and break it down into a series of individual statements or claims.

**Step 2: Statement Verification**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** For each extracted statement, the language model is asked to determine if it can be directly inferred from the provided context. It essentially performs a fact-checking task, comparing each claim against the source text.

**Step 3: Score Calculation**
- **Process:** The faithfulness score is calculated as the ratio of the number of statements that are successfully verified against the context to the total number of statements extracted from the answer.

Faithfulness = Number of claims in answer supported by context / Total number of claims in answer

### 🧠 Context Relevancy: How relevant is the retrieved context to the query?
This metric assesses the signal-to-noise ratio of your retrieved context, penalizing the inclusion of irrelevant information.

**Step 1: Identifying Critical Sentences**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to identify the essential sentences from the context that are crucial for answering the question.

**Step 2: Score Calculation**
- **Process:** The context relevancy score is the ratio of the number of identified critical sentences to the total number of sentences in the context.

Context Relevancy = Number of relevant sentences in context / Total number of sentences in context

### Answer Relevancy: How relevant is the response to the original query?
This metric evaluates whether the generated answer directly addresses the user's question.

**Step 1: Generating Synthetic Questions**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is tasked with generating multiple potential questions for which the provided answer would be a suitable response.

**Step 2: Semantic Similarity Calculation**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** The original question and the newly generated synthetic questions are converted into numerical vectors (embeddings). The cosine similarity between the original question's embedding and the average of the synthetic questions' embeddings is then calculated. A high similarity suggests the answer was highly relevant to the original question.

### 🧠 Context Precision Without Reference: Is the context that was retrieved actually used to formulate the answer?
This metric measures how much of the provided context was useful in generating the final answer.

**Step 1: Identifying Used Chunks**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to analyze the answer and the context. It then identifies which sentences or "chunks" from the context were directly used to construct the answer.

**Step 2: Score Calculation**
- **Process:** The score is the ratio of the number of context chunks that were deemed useful in generating the answer to the total number of chunks in the context.

## Metrics With a Reference Answer
These metrics require a ground truth or reference answer to compare against the generated output. They are typically used for more rigorous, benchmark-style evaluations.

### 🧠📚 Context Recall: Does the retrieved context contain the information needed to answer the question?
This metric evaluates whether the retrieved context contains all the information present in the ground truth answer.

**Step 1: Statement Extraction from Ground Truth**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model breaks down the ground_truth answer into a set of individual statements.

**Step 2: Statement Verification against Context**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** For each statement from the ground truth, the model checks if it can be supported by the retrieved context.

**Step 3: Score Calculation**
- **Process:** The context recall score is the ratio of the number of ground truth statements supported by the context to the total number of statements in the ground truth.

Context Recall = Number of claims in ground truth supported by context / Total number of claims in ground truth

### 🧠📚 Context Precision: Is the retrieved context relevant to the ground truth?
This metric is similar to Context Relevancy but uses the ground truth answer as the reference for relevance.

**Step 1: Identifying Relevant Chunks**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model is prompted to determine if each chunk in the retrieved context is relevant for generating the ground_truth answer.

**Step 2: Score Calculation**
- **Process:** The score is the ratio of the number of relevant context chunks to the total number of retrieved chunks.

### 📚 Answer Similarity: How semantically similar is the generated answer to the reference answer?
This metric gauges the semantic overlap between the generated and ground truth answers.

**Step 1: Embedding Generation**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** Both the generated answer and the ground_truth answer are converted into numerical vector embeddings.

**Step 2: Cosine Similarity**
- **Process:** The cosine similarity between the two embeddings is calculated. A score closer to 1 indicates a high degree of semantic similarity.

### 📚 Answer Correctness: Is the generated answer factually and semantically correct compared to the reference answer?
This is a composite metric that considers both factual and semantic alignment with the ground truth.

**Step 1: Factual Comparison**
- **Model Used:** Language Model (e.g., GPT-3.5 Turbo, GPT-4o)
- **Process:** The language model analyzes both the generated answer and the ground_truth to identify a list of true positives (correct statements in both), false positives (incorrect statements in the answer), and false negatives (statements in the ground truth missed by the answer). An F1-score is then calculated based on these counts.

**Step 2: Semantic Similarity**
- **Model Used:** Embedding Model (e.g., text-embedding-3-small)
- **Process:** The semantic similarity between the answer and ground_truth is calculated as described in the "Answer Similarity" metric.

**Step 3: Weighted Average**
- **Process:** The final answer correctness score is a weighted average of the factual F1-score and the semantic similarity score.
"""

# Short metrics explanations for results display
SHORT_METRICS_EXPLANATIONS: Dict[str, str] = {
    'reference_free': """
**Reference-Free Metrics** (work without reference answers):
- **Faithfulness** 🧠: How well grounded the response is in the retrieved context
- **Answer Relevancy**: How relevant the response is to the original query
- **Context Relevancy** 🧠: How relevant the retrieved context is to the query
- **Context Precision Without Reference** 🧠: Precision of context retrieval without reference answers

**Reference-Based Metrics** (require reference answers for comparison):
- **Answer Similarity** 📚: Semantic similarity between generated and reference answers
- **Answer Correctness** 📚: Factual accuracy against reference answers
- **Context Precision** 🧠📚: More accurate precision using reference answers
- **Context Recall** 🧠📚: How well retrieved contexts cover the reference answer

🧠 = Context-dependent | 📚 = Reference-based | *All metrics range from 0.0 to 1.0, with higher scores indicating better performance.*
""",
    'basic_only': """
**Context-dependent metrics** 🧠 require retrieved context/documents:
- **Faithfulness**: How well grounded the response is in the retrieved context
- **Context Relevancy**: How relevant the retrieved context is to the query
- **Context Precision Without Reference**: Precision of context retrieval without reference answers

**Response-only metrics** evaluate the generated response quality:
- **Answer Relevancy**: How relevant the response is to the original query

🧠 = Context-dependent metrics | *All metrics range from 0.0 to 1.0, with higher scores indicating better performance.*
"""
}


# File naming patterns
FILE_PATTERNS: Dict[str, str] = {
    'results_csv': "rag_evaluation_results_{timestamp}.csv",
    'basic_template': "query_template_basic.csv",
    'full_template': "query_template_with_references.csv"
}