# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Akvo RAG is an intelligent dialogue system based on RAG (Retrieval-Augmented Generation) technology. The system combines document retrieval with large language models to provide accurate knowledge-based question answering. It features a FastAPI backend, Next.js frontend, MySQL database, and integrates with an external MCP (Model Context Protocol) server for knowledge base queries.

## Architecture

### Backend (Python FastAPI)
- **Location**: `backend/`
- **Framework**: FastAPI with async support
- **Database**: MySQL 8.0 with Alembic migrations
- **Auth**: JWT + OAuth2
- **LLM Integration**: Supports OpenAI, DeepSeek, and Ollama (via Langchain)

### Frontend (Next.js)
- **Location**: `frontend/`
- **Framework**: Next.js 14 with TypeScript
- **UI**: Tailwind CSS + Shadcn/UI components
- **AI SDK**: Vercel AI SDK for streaming responses

### MCP Integration
The system depends on an external MCP server (Vector Knowledge Base MCP Server) for knowledge base queries. The MCP client discovery manager (`backend/mcp_clients/`) handles connection management and tool/resource discovery.

### Key Services
- **Prompt Service** (`backend/app/services/`): Centralized, database-driven prompt management with versioning
- **Chat Service**: Multi-turn conversations with context and streaming responses
- **RAG Evaluation** (`backend/RAG_evaluation/`): RAGAS-based evaluation system with Streamlit dashboard
- **App Registration Service** (`backend/app/services/app_service.py`): Server-to-server app registration and token management with Argon2 hashing

## Development Commands

### Starting the Development Environment

```bash
# Start all services (backend, frontend, db, nginx)
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
- `MYSQL_SERVER`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `SECRET_KEY`: JWT secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiry (default: 10080)

**MCP Configuration (Required):**
- `KNOWLEDGE_BASES_MCP`: MCP server base URL (e.g., `https://api.knowledge.example.com/mcp/`)
- `KNOWLEDGE_BASES_API_KEY`: MCP authentication key
- `KNOWLEDGE_BASES_API_ENDPOINT`: MCP API endpoint

**LLM Provider (Choose one):**
- OpenAI: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_MODEL`
- DeepSeek: `DEEPSEEK_API_KEY`, `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL`
- Ollama: `OLLAMA_API_BASE`, `OLLAMA_MODEL`

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

Migrations managed with Alembic:
- **Location**: `backend/alembic/versions/`
- **Auto-run**: Migrations execute automatically on backend container startup
- **Manual**: `docker exec akvo-rag-backend-1 alembic upgrade head`

### API Structure

**Internal API** (`/api/v1/`):
- `auth.py`: Login, token refresh, user management
- `chat.py`: Chat endpoints with streaming support
- `knowledge_base.py`: KB management (depends on MCP server)
- `prompt.py`: Dynamic prompt CRUD operations
- `api_keys.py`: API key management for external access
- `websocket/`: WebSocket support for real-time features

**OpenAPI** (`/openapi/`):
- External API endpoints for third-party integrations
- Requires API key authentication

### MCP Client Discovery

The system discovers MCP tools/resources at startup:
- **Discovery Manager**: `backend/mcp_clients/`
- **Result Cache**: `backend/mcp_discovery.json`
- **Connection**: Configured via `KNOWLEDGE_BASES_MCP` environment variable

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
- **Frontend**: http://127.0.0.1.nip.io
- **API Docs**: http://127.0.0.1.nip.io/docs
- **Health Check**: http://127.0.0.1.nip.io/api/health
- **RAG Evaluation Dashboard**: http://localhost:8501 (when `./rag-evaluate` is running)
- **App Registration API**: http://localhost:8000/v1/apps/* (see `backend/docs/APP_REGISTRATION.md`)

## Common Issues

- **MCP Connection Failures**: Verify `KNOWLEDGE_BASES_MCP` settings and ensure the external MCP server is running
- **Ollama in Docker**: Use `host.docker.internal` instead of `localhost` (macOS/Windows) or `172.17.0.1` (Linux)
- **RAG Evaluation Cleanup**: Always use `./rag-evaluate-stop` or Ctrl-C to prevent 1-2GB Docker artifact accumulation per session
- **Playwright Dependencies**: After container restarts, E2E tests may fail. Run `./run_e2e_tests_headless_container.sh` which auto-installs missing dependencies

## Contributing

- Follow Python PEP 8 coding standards
- Follow Conventional Commits for commit messages
- Branch naming: `feature/issue-number-description`
- Main branch for PRs: `main`
