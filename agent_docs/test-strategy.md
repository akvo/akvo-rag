# Test Strategy: Akvo RAG

## 1. Risk Assessment
The highest risks in Akvo RAG are:
- **Hallucinations**: AI generating incorrect or ungrounded answers.
- **Context Leakage**: Accessing or retrieving from unauthorized Knowledge Bases.
- **Processing Failures**: Background jobs (embedding/parsing) failing silently.
- **Integration Fragility**: Breaking changes in the MCP Server or LLM APIs.

## 2. Test Pyramid

| Layer | Type | Frequency | Goal |
| :--- | :--- | :--- | :--- |
| **Unit** | `pytest` | Every PR | Logic in services, utilities, and schemas. |
| **Integration** | `pytest` | Daily/Pre-release | API endpoints, DB operations, RabbitMQ task triggering. |
| **Performance**| `Locust` / `k6` | Weekly | Verify <1000ms TTFT under load and validate Semantic Cache hit latency (<300ms). |
| **RAG Evaluation**| **RAGAS** | Post-ingestion | Quantitative quality, specifically tuning for High Context Precision to save tokens. |
| **E2E** | **Playwright**| Pre-release | Key user flows: Login -> Ingest -> Chat. |

## 3. Quality Gates

| Gate | Criteria | Blocking? |
| :--- | :--- | :--- |
| **Backend Unit** | 100% Pass, >80% code coverage | Yes |
| **Static Analysis**| `ruff` / `mypy` zero errors | Yes |
| **Performance** | TTFT P95 < 1s; Cache Hit Latency P95 < 300ms | Warning |
| **RAG Evaluation**| Faithfulness > 0.85, Context Precision > 0.85 (strict filtering) | Warning |
| **E2E Business** | Critical flows (Dashboard/Chat) pass | Yes |

## 4. RAG Evaluation Metrics (RAGAS)
We use a specialized evaluation suite for the AI layer, prioritizing token efficiency:
1. **Context Precision (Token Saver)**: Is the retrieved context actually useful? High precision means the re-ranker is successfully filtering out noise, saving LLM tokens.
2. **Faithfulness**: Is the answer derived solely from the context?
3. **Answer Relevancy**: Does the answer address the user's prompt?
4. **Context Recall**: Does the context contain all info from a ground truth answer?

## 5. Tooling & Environment
- **Frameworks**: `pytest` (Backend), `Playwright` (E2E), `RAGAS` (AI Eval).
- **Environment**: Tests run within Docker containers (`./test.sh`) to ensure parity with production.
- **Monitoring**: Flower for tracking async task execution during integration tests.

## 6. Verification Commands
- **All Backend Tests**: `./dev.sh exec backend ./test.sh`
- **Unit Backend Tests**: `./dev.sh exec backend ./test-unit.sh`
- **RAG Evaluation**: `./rag-evaluate` (Interactive) or `./backend/RAG_evaluation/run_headless.sh` (Headless).
- **E2E UI Tests**: `./backend/RAG_evaluation/run_e2e_tests_headless_container.sh`
