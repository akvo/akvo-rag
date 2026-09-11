# Developer Guide: Akvo RAG

This guide covers everything needed for day-to-day backend development: environment setup, hot-reload, migrations, adding new MCP tools, and running the test suite.

> **Related docs**: [Architecture Map](architecture_map.md) | [Troubleshooting](troubleshooting.md) | [PROMPT_SERVICE.md](../PROMPT_SERVICE.md)

---

## 1. Prerequisites

| Tool | Minimum Version | Notes |
|------|----------------|-------|
| Docker | 24.0+ | Docker Desktop or Docker Engine + CLI |
| Docker Compose | 2.20+ | Bundled with Docker Desktop |
| Git | 2.40+ | |
| Node.js | 18+ | Only for running frontend outside Docker |
| Python | 3.9+ | Only for running scripts outside Docker |

---

## 2. First-Time Setup

```bash
git clone https://github.com/akvo/akvo-rag.git
cd akvo-rag

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and OPENAI_API_KEY at minimum
```

Start the full development stack with hot-reload:

```bash
# Using the dc.sh shortcut wrapper
./dc.sh up -d --build

# Equivalently
docker compose -f docker-compose.dev.yml up -d --build
```

Seed the prompt templates (required on first run):

```bash
docker compose exec backend python -m app.seeder.seed_prompts
```

Verify all 7 containers are running:

```bash
docker compose -f docker-compose.dev.yml ps
```

Access the platform at **http://localhost:3000** and the API docs at **http://localhost:8000/docs**.

---

## 3. Hot-Reload Development

In `docker-compose.dev.yml`, the backend and vector-kb-mcp services mount their source directories as volumes and use `uvicorn --reload`. Code changes take effect immediately without rebuilding.

| Service | What reloads |
|---------|-------------|
| `backend` | `backend/app/**` and `backend/mcp_clients/**` |
| `vector-kb-mcp` | `vector-kb-mcp/app/**` |
| `frontend` | Next.js fast refresh on `frontend/app/**` |

---

## 4. Running Migrations

### Backend (core schema — `alembic_version`)

```bash
# Apply all pending migrations
docker exec akvo-rag-backend-1 alembic upgrade head

# Check current revision
docker exec akvo-rag-backend-1 alembic current

# Create a new migration
docker exec akvo-rag-backend-1 alembic revision --autogenerate -m "add_field_x_to_users"
```

### Vector KB MCP (KB schema — `alembic_version_vkb`)

```bash
# Apply all pending KB migrations
docker exec akvo-rag-vector-kb-mcp-1 alembic upgrade head

# Create a new migration
docker exec akvo-rag-vector-kb-mcp-1 alembic revision --autogenerate -m "add_field_x_to_vkb_documents"
```

> **Important**: `backend` migrations **only** manage tables in `alembic_version`. `vector-kb-mcp` migrations **only** manage tables in `alembic_version_vkb`. Never mix them.
>
> Migrations run automatically on both service startups, so a `docker compose restart` is sufficient for new migration files.

---

## 5. Interactive Shells

```bash
# Backend Python shell
docker exec -it akvo-rag-backend-1 bash

# Vector KB MCP shell
docker exec -it akvo-rag-vector-kb-mcp-1 bash

# PostgreSQL psql
docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag

# Redis CLI
docker exec -it akvo-rag-redis-1 redis-cli
```

---

## 6. Adding a New MCP Tool

Tools exposed to the LangGraph RAG agent are declared in [`backend/mcp_config.json`](../backend/mcp_config.json). The Redis RPC dispatcher loads this at startup — no code change to the dispatcher is required.

### Step 1: Implement the tool in `vector-kb-mcp`

Add the handler in `vector-kb-mcp/app/router/` and register it in the tool dispatch table.

```python
# vector-kb-mcp/app/router/tools.py (example pattern)
async def handle_my_new_tool(args: dict) -> dict:
    kb_id = args["kb_id"]
    # ... implementation
    return {"result": ...}

TOOL_HANDLERS = {
    ...
    "my_new_tool": handle_my_new_tool,
}
```

### Step 2: Declare the tool in `backend/mcp_config.json`

```json
{
  "name": "my_new_tool",
  "description": "Brief description for the LLM agent.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "kb_id": { "type": "integer", "description": "Knowledge base ID." }
    },
    "required": ["kb_id"]
  }
}
```

Add this JSON object to the `tools` array under `knowledge_bases_mcp.tools`.

### Step 3: Restart the services

```bash
./dc.sh restart backend vector-kb-mcp
```

The tool is now available to the LangGraph agent via the MCP client at `backend/mcp_clients/`.

---

## 7. Dynamic Prompt Management

Prompts are stored in the database and loaded at runtime by `PromptService`. To modify a prompt:

1. Open the Admin UI at http://localhost:3000/admin/prompts.
2. Edit the prompt text and save a new version.
3. Activate the new version — it takes effect immediately.

Or update via CLI seed file:

```bash
# After editing backend/app/seeder/prompts/*.py
docker compose exec backend python -m app.seeder.seed_prompts
```

See [PROMPT_SERVICE.md](../PROMPT_SERVICE.md) for the full `PromptNameEnum` reference.

---

## 8. Testing

### Backend (all tests with coverage)

```bash
docker exec akvo-rag-backend-1 python -m pytest tests/ -v --cov=app --cov=mcp_clients
```

### Backend (unit tests only — fast)

```bash
docker exec akvo-rag-backend-1 python -m pytest tests/unit -v
```

### Vector KB MCP tests

```bash
docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ -v
```

### Frontend lint + build verification

```bash
docker exec akvo-rag-frontend-1 pnpm lint
docker exec akvo-rag-frontend-1 pnpm build
```

### Linter (Python)

```bash
docker exec akvo-rag-backend-1 flake8 app/ mcp_clients/
```

### Test coverage gate

The project enforces **≥80% test coverage** as a CI quality gate. Ensure new code is tested before opening a PR.

---

## 9. API Documentation

FastAPI auto-generates interactive Swagger UI and ReDoc:

| Interface | URL |
|-----------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

All endpoints require JWT bearer tokens (except `/auth/login` and `/auth/register`). Tenant API endpoints require `Authorization: Bearer tok_...` application tokens.

---

## 10. Environment Variable Reference

See `.env.example` for all supported variables. Key groups:

- **Application Security**: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ENVIRONMENT`
- **AI Provider**: `CHAT_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_MODEL_FAST`, `OPENAI_MODEL_SYNTHESIS`
- **Database**: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Storage**: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_PORT`
- **Redis**: `REDIS_URL`
- **Ports**: `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT`, `REDIS_PORT`, `CHROMA_HOST_PORT`

Full reference: [README.md — Environment Configuration](../README.md#-environment-configuration)

---

## 11. Git Workflow

All commits follow the project convention:

```
[#issue_number] <type>(<scope>): <description>
```

Branch naming: `feature/<issue_number>-<description>`

See [`git-workflow.md`](../.agent/rules/git-workflow.md) for full commit and PR protocol.
