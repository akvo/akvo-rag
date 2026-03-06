---
description: RAG Evaluation workflow - verify retrieval and generation quality
---

# RAG Evaluation Workflow

## Purpose
Ensure the RAG pipeline maintains high quality retrieval and generation using standardized metrics.

## Steps

### 1. Seed Evaluation Data
Ensure the database has the necessary prompts and test documents.

```bash
./dev.sh exec backend python -m app.seeder.seed_prompts
```

### 2. Run Retrieval Tests
Verify that the MCP integration correctly retrieves relevant documents.

```bash
./dev.sh exec backend ./test.sh tests/integration/test_mcp_retrieval.py
```

### 3. Run Generation Benchmarks
Verify the LLM output quality (using DeepSeek or OpenAI).

```bash
./dev.sh exec backend ./test.sh tests/integration/test_generation_quality.py
```

### 4. Continuous Evaluation (RAGAS)
If configured, run RAGAS evaluation suite.

```bash
./dev.sh exec backend python -m app.evaluation.run_ragas
```

## Completion Criteria
- [ ] Retrieval precision/recall meets threshold.
- [ ] Generation faithfulness and relevance verified.
- [ ] Latency within acceptable bounds.
