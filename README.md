# Akvo RAG

<p>
  <a href="https://github.com/akvo/akvo-rag/blob/main/LICENSE"><img src="https://img.shields.io/github/license/akvo/akvo-rag" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="#"><img src="https://img.shields.io/badge/node-%3E%3D18-green.svg" alt="Node 18+"></a>
  <a href="#"><img src="https://img.shields.io/badge/docker-compose-blue.svg" alt="Docker Compose"></a>
</p>

---

## 📖 Introduction

**Akvo RAG** is an intelligent question-answering system that enables users to chat with their own knowledge bases using **Retrieval-Augmented Generation (RAG)** technology. It is a self-hosted, container-native monorepo designed for easy integration into any host application (e.g. AgriConnect, CoM).

### Why Akvo RAG?

1. **Easy Integration** — Add RAG capabilities to any web application via a secure REST API and tenant token model.
2. **Simplified Data Management** — Upload and manage knowledge bases with a built-in async ingestion pipeline (MinIO S3 + Redis queues).
3. **Intelligent KB Selection** — Automatically determines which knowledge bases to query for optimal responses (ASQ mode).
4. **Full Self-Hosting** — Deploys the entire stack in Docker Compose with one command.

### Query Modes

- **Agent-Scoped Query (ASQ)** — System automatically selects the best knowledge bases for the query.
- **User-Scoped Query (USQ)** — User manually selects which knowledge bases to search.

---

## 🏗️ Architecture Overview

Akvo RAG runs as a **7-container monorepo** communicating over a private Docker bridge network:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Developer / End User                             │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ HTTP :3000
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  frontend  (Next.js 14, TypeScript, Tailwind, Shadcn/UI)   [Port 3000]  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ HTTP /api/v1/* → :8000
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  backend   (Python FastAPI, LangGraph, LLMFactory, PromptService)        │
│  [Port 8000]  JWT Auth · Redis RPC Dispatcher · MinIO S3 Client          │
└───────────────┬──────────────────┬────────────────────┬──────────────────┘
                │ Redis RPUSH/BLPOP │                    │ S3 API
                ▼                  ▼                    ▼
┌──────────────────────┐ ┌──────────────────┐  ┌────────────────────────┐
│  vector-kb-mcp       │ │  redis  :6379     │  │  minio  :9000 / :9001  │
│  (FastAPI, asyncpg,  │ │  (RPC queues,     │  │  (S3 document storage, │
│   ChromaDB client,   │ │   async ingestion │  │   bucket: documents/)  │
│   Redis RPC worker)  │ │   queues)         │  └────────────────────────┘
└──────────┬───────────┘ └──────────────────┘
           │ asyncpg        │ asyncpg
           ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  postgres  (PostgreSQL 17)  [Port 5432]                                  │
│  Tables: users, apps, chats, messages, prompt_definitions (alembic_version)│
│  Tables: vkb_knowledge_bases, vkb_documents (alembic_version_vkb)        │
└──────────────────────────────────────────────────────────────────────────┘
           │ HTTP :8000 (internal)
           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  chromadb  (ChromaDB vector store)  [Host: 8001 → Container: 8000]       │
└──────────────────────────────────────────────────────────────────────────┘
```

| Container | Image | Host Port | Purpose |
|---|---|---|---|
| `frontend` | Next.js 14 build | `:3000` | Web UI |
| `backend` | Python FastAPI | `:8000` | Core API + RAG graph |
| `vector-kb-mcp` | Python FastAPI | internal | Vector KB microservice (Redis worker) |
| `postgres` | `postgres:17-alpine` | `:5432` | Unified relational store |
| `redis` | `redis:7-alpine` | `:6379` | MCP RPC queues + async ingestion |
| `chromadb` | `chromadb/chroma:latest` | `:8001` → `:8000` | Vector embeddings |
| `minio` | `minio/minio:latest` | `:9000` / `:9001` | S3 document storage |

---

## ✨ Key Features

- **Dual-Tier LLM Routing** — `gpt-4o-mini` (FAST) for intent/routing nodes, `gpt-4o` (SYNTHESIS) for grounded answer generation. Reduces pre-retrieval latency by ~84%.
- **Dynamic Prompt Service** — Centralized, database-driven prompt management with versioning. No redeployment needed to update prompts. See [PROMPT_SERVICE.md](PROMPT_SERVICE.md).
- **OpenAI Prompt Caching** — Invariant system prompt layout ensures automatic prefix cache hits across recurring queries.
- **Redis RPC Queue IPC** — `backend` dispatches tool calls to `vector-kb-mcp` via `mcp:vector:requests` / `mcp:vector:responses:{id}` with correlation-ID request-reply.
- **MinIO S3 Document Storage** — Uploaded documents are stored in MinIO at `documents/kb_{id}/{doc_id}_{filename}` before async vector indexing.
- **Declarative MCP Extensibility** — Add new MCP microservices by editing `backend/mcp_config.json`. Zero code changes to the dispatcher.
- **Service-Owned Alembic Migrations** — `backend` owns `alembic_version`; `vector-kb-mcp` owns `alembic_version_vkb`. Fully isolated schema management.
- **RAG Evaluation** — Built-in RAGAS metrics (Faithfulness ≥ 0.85, Answer Relevancy ≥ 0.85, Groundedness ≥ 0.90). See [`backend/RAG_evaluation/README.md`](backend/RAG_evaluation/README.md).

---

## 🚀 Quick Start (< 15 minutes)

### Prerequisites

- [ ] Docker & Docker Compose v2.0+
- [ ] 8GB+ RAM (16GB recommended)
- [ ] 10GB+ free disk space
- [ ] Ports `3000`, `5432`, `6379`, `8000`, `8001`, `9000`, `9001` available

### Step 1: Clone & Configure

```bash
git clone https://github.com/akvo/akvo-rag.git
cd akvo-rag

# Copy and configure environment
cp .env.example .env
```

Open `.env` and set **at minimum**:
```dotenv
SECRET_KEY=your-strong-random-secret-key
OPENAI_API_KEY=your-openai-api-key   # or configure DeepSeek / Ollama
```

### Step 2: Start the Platform (Hot-Reload Development)

```bash
# Using the dc.sh wrapper (recommended for development)
./dc.sh up -d --build

# Or directly with docker compose
docker compose -f docker-compose.dev.yml up -d --build
```

> For **production**, use `docker compose up -d --build` (no hot-reload, optimized builds).

### Step 3: Seed Prompt Templates

```bash
docker compose exec backend python -m app.seeder.seed_prompts
```

### Step 4: Access the Platform

| Service | URL |
|---|---|
| **Web UI** | http://localhost:3000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **MinIO Console** | http://localhost:9001 |

> The first time, create your admin account:
> ```bash
> docker compose exec backend python -m app.seeder.seed_admin_user
> ```

---

## 🔧 Environment Configuration

Copy `.env.example` to `.env` and configure the following sections.

### Application Security

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing secret — use a strong random value | ✅ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes (default: `10080` = 7 days) | ✅ |
| `ENVIRONMENT` | `development` or `production` | ✅ |

### AI Provider (choose one)

**OpenAI** (default):
```dotenv
CHAT_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o                 # Synthesis model
OPENAI_MODEL_FAST=gpt-4o-mini       # Fast routing model
OPENAI_MODEL_SYNTHESIS=gpt-4o
OPENAI_API_BASE=https://api.openai.com/v1
```

**DeepSeek** (alternative):
```dotenv
CHAT_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MODEL_FAST=deepseek-chat
DEEPSEEK_MODEL_SYNTHESIS=deepseek-chat
```

**Ollama** (local LLM):
```dotenv
CHAT_PROVIDER=ollama
OLLAMA_API_BASE=http://host.docker.internal:11434
OLLAMA_MODEL=deepseek-r1:7b
OLLAMA_MODEL_FAST=qwen2.5:3b
OLLAMA_MODEL_SYNTHESIS=deepseek-r1:7b
```

### Database & Storage

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB` | `akvo_rag` | PostgreSQL 17 database name |
| `POSTGRES_USER` | `postgres` | Database username |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL (RPC + queues) |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO root username |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO root password |

### Port Overrides (Optional)

```dotenv
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379
CHROMA_HOST_PORT=8001
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
```

### Email (Password Reset)

```dotenv
SMTP_HOST=your-smtp-host
SMTP_PORT=465
SMTP_USER=noreply@yourorg.org
SMTP_PASS=your-smtp-password
SMTP_USE_TLS=true
WEBDOMAIN=your-public-domain.org
```

---

## 🧪 Testing

All test commands run inside Docker containers.

### Backend Tests

```bash
# All tests (integration + unit) with coverage report
docker exec akvo-rag-backend-1 python -m pytest tests/ -v --cov=app --cov=mcp_clients

# Unit tests only (fast)
docker exec akvo-rag-backend-1 python -m pytest tests/unit -v

# Linter check
docker exec akvo-rag-backend-1 flake8 app/ mcp_clients/
```

### Vector KB Microservice Tests

```bash
docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ -v
```

### Frontend Lint & Build

```bash
docker exec akvo-rag-frontend-1 pnpm lint
docker exec akvo-rag-frontend-1 pnpm build
```

### RAG Evaluation Dashboard

```bash
# Start evaluation dashboard (RAGAS metrics)
./rag-evaluate

# Stop cleanly (prevents Docker artifact accumulation)
./rag-evaluate-stop
```

> Target thresholds: **Faithfulness ≥ 0.85**, **Answer Relevancy ≥ 0.85**, **Groundedness ≥ 0.90**

---

## 🔌 Host Application Integration

Akvo RAG exposes a tenant API for host applications (e.g. AgriConnect) secured via Argon2-hashed application tokens (`tok_...`).

See [`backend/docs/APP_REGISTRATION.md`](backend/docs/APP_REGISTRATION.md) for full integration reference:
- App registration (`POST /api/v1/apps/register`)
- Tenant knowledge base access (`GET /api/v1/apps/knowledge-bases`)
- Document upload (`POST /api/v1/apps/knowledge-bases/{id}/documents/upload`)
- Chat with streaming SSE (`POST /api/v1/apps/jobs`)

---

## 🛠️ Common Troubleshooting

| Problem | Solution |
|---|---|
| **Containers not starting** | `docker compose logs <service>` — check for port conflicts or `.env` errors |
| **PostgreSQL connection errors** | Ensure `POSTGRES_PASSWORD` in `.env` matches container vars; restart: `docker compose restart postgres` |
| **MCP dispatcher timeout** | Check `docker compose logs vector-kb-mcp` — ensure Redis and ChromaDB are healthy |
| **Document processing stuck** | Inspect Redis queue: `docker exec akvo-rag-redis-1 redis-cli llen mcp:vector:requests` |
| **ChromaDB permission error** | `docker compose down -v chromadb && docker compose up -d chromadb` |
| **MinIO unreachable** | `curl http://localhost:9000/minio/health/live` — verify `MINIO_PORT` is not in use |
| **Frontend API errors** | Check `NEXT_PUBLIC_API_URL` in `.env` matches your backend port |
| **Ollama in Docker (macOS)** | Use `OLLAMA_API_BASE=http://host.docker.internal:11434` |

For detailed playbooks, see [`docs/troubleshooting.md`](docs/troubleshooting.md).

---

## 📋 Developer Guides

| Guide | Purpose |
|---|---|
| [`docs/dev-guide.md`](docs/dev-guide.md) | Local setup, hot-reloading, migrations, adding MCP tools, testing |
| [`docs/architecture_map.md`](docs/architecture_map.md) | Container topology, Redis RPC contracts, MinIO layout, ER diagram, API catalog |
| [`docs/admin-guide.md`](docs/admin-guide.md) | Knowledge base management, prompt editing, API key provisioning |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Debugging playbooks for all 7 containers |
| [`PROMPT_SERVICE.md`](PROMPT_SERVICE.md) | Dynamic prompt versioning and seeding |
| [`backend/docs/APP_REGISTRATION.md`](backend/docs/APP_REGISTRATION.md) | Universal host application tenant integration, webhooks, and SDK examples |
| [`backend/RAG_evaluation/README.md`](backend/RAG_evaluation/README.md) | RAGAS evaluation framework |

---

## 🔒 Security & Vulnerability Disclosure

We take security seriously. If you discover a security vulnerability in Akvo RAG:

1. **Do not open a public GitHub issue.**
2. Email the Akvo security team at **security@akvo.org** with:
   - Description of the vulnerability and steps to reproduce.
   - Potential impact assessment.
   - Any suggested mitigations.
3. We will respond within **5 business days** and coordinate a responsible disclosure timeline.

**Security best practices for operators:**
- Always set a strong, unique `SECRET_KEY` in production.
- Never expose PostgreSQL (`:5432`), Redis (`:6379`), ChromaDB (`:8001`), or MinIO (`:9000`) directly to the public internet.
- Rotate MinIO credentials and application tokens (`tok_...`) regularly.
- Use HTTPS behind a reverse proxy (e.g. Nginx, Caddy) in production.

---

## 📄 License

This project is licensed under the [Apache-2.0 License](LICENSE).
