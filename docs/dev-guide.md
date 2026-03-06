# Developer Guide: Akvo RAG

This guide provides technical overview and monitoring instructions for developers maintaining Akvo RAG.

## 1. API Documentation

Akvo RAG is built with FastAPI and provides an interactive Swagger UI for exploring and testing all available endpoints.

![API Docs](images/api-docs.png)

- **URL**: Typically accessible at `/docs` (e.g., `http://localhost:8000/docs`).
- **Capabilities**: Test authentication, triggers ingestion jobs, and perform raw RAG queries via the REST API.

## 2. Background Task Monitoring

The system uses Celery with RabbitMQ for processing long-running jobs (like PDF embedding). You can monitor these jobs using **Flower**.

![Flower Dashboard](images/flower.png)

- **Dashboard**: View active, succeeded, and failed tasks.
- **Worker Health**: Monitor the resource usage and health of your ingestion workers.
- **Broker**: Inspect the RabbitMQ message queue status.

## 3. High-Level Architecture

Akvo RAG follows a decoupled architecture:
1. **Frontend**: Next.js application for the user interface.
2. **Backend**: FastAPI for the core logic and orchestration.
3. **Workers**: Celery workers for heavy processing.
4. **Vector Store**: ChromaDB (default) for fast semantic retrieval.
5. **Database**: MySQL for structured data and user state.

## 4. Key Developer Features
- **Semantic Caching**: Reduces cost and latency by caching high-confidence LLM responses.
- **Context Re-ranking**: Uses advanced pipelines to ensure only the most relevant context is sent to the LLM, staying within token budgets.
- **MCP Integration**: Supports Model Context Protocol for integrating with external knowledge sources.
