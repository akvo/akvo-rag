# Product Brief: Akvo RAG

## Problem Statement
Organizations and individuals often struggle to efficiently query their own vast collections of documents (PDFs, TXT, DOCX) using modern AI. Existing RAG solutions are often either too complex to self-host, too rigid for easy integration, or lack intelligent automation in selecting the right knowledge source.

## Target Users
- **Developers**: Needing a plug-and-play RAG API for their own applications, with strong cost-control mechanisms.
- **Enterprise Teams**: Requiring a self-hosted, secure knowledge base that feels as fast as native ChatGPT.
- **Researchers**: Seeking a flexible tool to evaluate different RAG configurations, re-rankers, and LLMs.

## Value Proposition
Akvo RAG provides an **ultra-fast, cost-optimized, and self-hosted** intelligent question-answering system. It bridges the gap between raw data and LLMs by offering:
1. **Intelligent Source Selection**: ASQ mode automatically picks the best KB.
2. **Cost-Aware Performance Strategy**: Semantic caching drastically lowers API costs, and context re-ranking prevents bloated token windows.
3. **Developer-First Design**: Easy-to-use REST APIs and a clean, highly responsive Next.js UI using server-sent events.
4. **Operational Excellence**: Built-in monitoring (Flower), job queues (Celery), and evaluation metrics (RAGAS).
5. **Data Sovereignty**: Complete control over data and models via local deployment options.

## Core Features (MVP)
- **Multi-Format Document Ingestion**: Support for PDF, TXT, and DOCX.
- **Dual Query Modes**: User-Scoped (Manual) and Agent-Scoped (Autonomous).
- **Semantic Caching & Re-ranking**: High-performance layers to drop latency and API costs.
- **Knowledge Base Management**: Isolated storage and querying for different domains.
- **Prompt Engineering Service**: Versioned and managed system prompts.
- **Async Processing**: Scalable background embedding and querying.
- **RAG Evaluation**: Quantitative performance tracking.

## Success Metrics
- **Performance**: Time-to-First-Token (TTFT) < 1 second.
- **Cost Efficiency**: Minimized context window sizes (high Context Precision via re-ranking) and high Semantic Cache hit rates.
- **Query Accuracy**: Measured via RAGAS (Faithfulness, Answer Relevance).
- **Ingestion Speed**: Time taken to embed and index new documents.
- **Ease of Setup**: Time from clone to first query.

## Constraints & Assumptions
- Requires an external MCP (Model Context Protocol) server for vector storage.
- Assumes Docker-based deployment environment.
- Hardware requirements (8GB+ RAM) for local LLM usage.
