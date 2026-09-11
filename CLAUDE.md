# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Akvo RAG is an intelligent dialogue system based on RAG (Retrieval-Augmented Generation) technology. The system combines document retrieval with large language models to provide accurate knowledge-based question answering. It features a FastAPI backend, Next.js frontend, PostgreSQL 17 database, ChromaDB vector store, MinIO S3 document storage, Redis 7 RPC queues, and an internal `vector-kb-mcp` microservice for knowledge base queries.

## Architecture

### Backend (Python FastAPI)
- **Location**: `backend/`
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL 17 with Alembic migrations (two isolated migration chains: `alembic_version` for backend, `alembic_version_vkb` for `vector-kb-mcp`)
- **Auth**: JWT + OAuth2
- **LLM Integration**: Supports OpenAI, DeepSeek, and Ollama (via LangChain/LangGraph)

### Frontend (Next.js)
- **Location**: `frontend/`
- **Framework**: Next.js 14 with TypeScript
- **UI**: Tailwind CSS + Shadcn/UI components
- **AI SDK**: Vercel AI SDK for streaming responses

### MCP Integration

The system uses an internal `vector-kb-mcp` microservice (containerized FastAPI + asyncpg + ChromaDB client) for knowledge base queries. The backend dispatches tool calls to this service via Redis RPC queues (`mcp:vector:requests` / `mcp:vector:responses:{id}`). Tools are declared declaratively in `backend/mcp_config.json` — no code changes required to add new tools.

### Key Services
- **Prompt Service** (`backend/app/services/`): Centralized, database-driven prompt management with versioning
- **Chat Service**: Multi-turn conversations with context and streaming responses
- **RAG Evaluation** (`backend/RAG_evaluation/`): RAGAS-based evaluation system with Streamlit dashboard
- **App Registration Service** (`backend/app/services/app_service.py`): Server-to-server app registration and token management with Argon2 hashing

## Development Commands

### Starting the Development Environment

```bash
# Start all services with dc.sh (recommended)
./dc.sh up -d --build

# Or standard docker compose
docker compose -f docker-compose.dev.yml up -d --build

# Production mode
docker compose up -d --build
```

### Backend Development

```bash
# Run all tests
cd backend
./test.sh

# Run unit tests only
./test-unit.sh

# Run tests in watch mode
./test-watch.sh

# Run database migrations (happens automatically on startup)
docker exec akvo-rag-backend-1 alembic upgrade head

# Seed default prompts into database
docker compose exec backend python -m app.seeder.seed_prompts

# Access backend shell
docker exec -it akvo-rag-backend-1 bash
```

### Frontend Development

```bash
# Install dependencies (inside container)
docker exec akvo-rag-frontend-1 pnpm install

# Build frontend
docker exec akvo-rag-frontend-1 pnpm build

# Lint frontend
docker exec akvo-rag-frontend-1 pnpm lint
```

### RAG Evaluation

```bash
# Start evaluation dashboard (from project root)
./rag-evaluate

# Proper shutdown (prevents Docker artifact accumulation)
./rag-evaluate-stop

# Headless evaluation with custom CSV
cd backend/RAG_evaluation
./run_headless.sh -u "username" -p "password" -a "http://localhost:8000" -k "Knowledge Base Name" -c "path/to/prompts.csv"

# Run E2E tests for evaluation system
./run_e2e_tests_headless_container.sh
```

## Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

**Core Settings:**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` (PostgreSQL 17)
- `SECRET_KEY`: JWT secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiry (default: 10080)
- `REDIS_URL`: Redis connection URL (e.g., `redis://redis:6379/0`)
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`: MinIO S3 credentials

**LLM Provider (Choose one):**
- OpenAI: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_MODEL`, `OPENAI_MODEL_FAST`, `OPENAI_MODEL_SYNTHESIS`
- DeepSeek: `DEEPSEEK_API_KEY`, `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL`, `DEEPSEEK_MODEL_FAST`, `DEEPSEEK_MODEL_SYNTHESIS`
- Ollama: `OLLAMA_API_BASE`, `OLLAMA_MODEL`, `OLLAMA_MODEL_FAST`, `OLLAMA_MODEL_SYNTHESIS`

Set `CHAT_PROVIDER=openai|deepseek|ollama` to select active provider.

## Important Architecture Details

### Prompt Service System

Prompts are stored in the database with versioning support, not in code. This enables runtime updates without redeployment.

- **Models**: `prompt_definitions` and `prompt_versions` tables
- **Service**: `PromptService` class handles fetching and fallback logic
- **Enum**: `PromptNameEnum` defines all recognized prompt types
- **Seeding**: Default prompts initialized via `python -m app.seeder.seed_prompts`

Key prompts: `contextualize_q_system_prompt`, `qa_flexible_prompt`, `qa_strict_prompt`

See `PROMPT_SERVICE.md` for detailed documentation.

### Database Migrations

Migrations managed with Alembic — **two independent migration chains**:

| Service | Migration Table | Location |
|---|---|---|
| `backend` | `alembic_version` | `backend/alembic/versions/` |
| `vector-kb-mcp` | `alembic_version_vkb` | `vector-kb-mcp/alembic/versions/` |

- **Auto-run**: Each service runs `alembic upgrade head` on container startup
- **Manual (backend)**: `docker exec akvo-rag-backend-1 alembic upgrade head`
- **Manual (vector-kb-mcp)**: `docker exec akvo-rag-vector-kb-mcp-1 alembic upgrade head`

### API Structure

**Internal API** (`/api/`):
- `auth.py`: Login, token refresh, user management
- `chat.py`: Chat endpoints with streaming support
- `knowledge_base.py`: KB management (depends on MCP server)
- `prompt.py`: Dynamic prompt CRUD operations
- `api_keys.py`: API key management for external access
- `websocket/`: WebSocket support for real-time features

**OpenAPI** (`/openapi/`):
- External API endpoints for third-party integrations
- Requires API key authentication

### MCP Client & Tool Dispatcher

The system defines and routes MCP tools/resources declaratively:
- **Declarative Config**: `backend/mcp_config.json`
- **Config Parser**: `backend/app/core/mcp_config.py` (`MCPConfigParser`)
- **Queue Dispatcher**: `backend/mcp_clients/queue_dispatcher.py` (`MCPQueueDispatcher` via Redis RPC)
- **Endpoint Adapter**: `backend/mcp_clients/kb_mcp_endpoint_service.py` (`KnowledgeBaseMCPEndpointService`)

### Testing

Tests use pytest and are containerized:
- **Location**: `backend/tests/`
- **Config**: `backend/pytest.ini`
- **Dependencies**: `backend/requirements-test.txt`

Test categories:
- Unit tests: Core logic, services, utilities
- Integration tests: Database, API endpoints
- E2E tests: RAG evaluation UI with Playwright

Always run tests inside the Docker container via the provided shell scripts.

## Access Points

After starting services:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health
- **MinIO Console**: http://localhost:9001
- **RAG Evaluation Dashboard**: http://localhost:8501 (when `./rag-evaluate` is running)

## Common Issues

- **MCP/vector-kb-mcp Timeout**: Check Redis queue depth: `docker exec akvo-rag-redis-1 redis-cli llen mcp:vector:requests`. Restart: `docker compose restart vector-kb-mcp`
- **Document stuck in PROCESSING**: Vector-kb-mcp logs (`docker compose logs vector-kb-mcp`) will show the ingestion error. Force-reset via psql: `UPDATE vkb_documents SET status='FAILED' WHERE status='PROCESSING';`
- **Ollama in Docker**: Use `host.docker.internal` instead of `localhost` (macOS/Windows) for `OLLAMA_API_BASE`
- **RAG Evaluation Cleanup**: Always use `./rag-evaluate-stop` or Ctrl-C to prevent 1-2GB Docker artifact accumulation per session
- **Playwright Dependencies**: After container restarts, E2E tests may fail. Run `./run_e2e_tests_headless_container.sh` which auto-installs missing dependencies
- **ChromaDB Permission Error**: `docker compose down chromadb && docker volume rm akvo-rag_chromadb_data && docker compose up -d chromadb` then re-ingest documents

## Contributing

- Follow Python PEP 8 coding standards
- Follow Conventional Commits for commit messages
- Branch naming: `feature/issue-number-description`
- Main branch for PRs: `main`
