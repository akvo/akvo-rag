# Feature Specification: Unified Docker Compose & Local Infrastructure

> **Feature ID:** `001_unified_docker_compose_and_local_infrastructure_spec`  
> **Task Ref:** `TASK-MONO-101`  
> **Target Branch:** `epic/rag-monorepo-mcp`  
> **Status:** `PROPOSED (Under Review)`  
> **Estimated Effort:** `2.0 hrs (Vibe-Coding) / 1.5 days (Traditional)`  
> **Author:** Antigravity Architect / Senior Platform Engineer  
> **Upstream Reference:** [docs/lld/container_based_rag_platform_lld.md](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md) (Sections 3, 8, 9)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
The current Akvo-RAG setup relies on legacy `docker-compose.yml` configurations with MySQL 8.0, RabbitMQ, and Celery worker/beat containers. The new Container-Based Option C architecture transitions the entire platform to **PostgreSQL 17**, **Redis 7** (for MCP RPC queues & async ingestion), **ChromaDB**, **MinIO** (S3-compatible document storage), and the consolidated **`vector-kb-mcp`** microservice.

Without a unified, healthcheck-aware `docker-compose.yml` deployed on **Day 1**, developers cannot run or test individual microservices or database migrations locally against their target container runtime.

### 1.2 5W1H Discovery Lens

| Dimension | Specification |
|---|---|
| **Who** | Backend engineers, ML/AI engineers, and frontend developers working on Akvo-RAG monorepo. |
| **What** | Author a unified `docker-compose.yml` and `.env.example` orchestrating all 7 services (`postgres`, `redis`, `chromadb`, `minio`, `vector-kb-mcp`, `backend`, `frontend`) with healthchecks and persistent volumes. |
| **Where** | Workspace root: `docker-compose.yml`, `.env.example`. |
| **When** | **Phase 1, Step 1** — foundational prerequisite before writing any microservice code or running database migrations. |
| **Why** | Provides a reproducible local sandbox, eliminates race conditions on boot via healthchecks, enables independent datastore startup, and guarantees dev-to-prod environment parity. |
| **How** | Docker Compose v2 specification with declarative healthcheck probes (`pg_isready`, `redis-cli ping`, heartbeat), named bridge network (`akvo_rag_net`), and persistent named volumes. |

---

## 2. Architecture & Container Topology

### 2.1 Service Topology Matrix

```mermaid
graph TD
    subgraph Host["Host Machine / Developer Workspace"]
        Browser["Web Browser :3000"]
        HostAPI["REST Client / Host App :8000"]
        MinIOPort["MinIO Console :9001"]
    end

    subgraph DockerNetwork["Bridge Network: akvo_rag_net"]
        Frontend["frontend (:3000)<br/>Next.js 14 App"]
        Backend["backend (:8000)<br/>FastAPI Core Gateway"]
        VectorMCP["vector-kb-mcp (internal)<br/>Redis Worker & Retriever"]
        
        subgraph Datastores["Core Infrastructure Services"]
            PG[("postgres:17-alpine<br/>:5432 (akvo_rag)")]
            Redis[("redis:7-alpine<br/>:6379 (Queues & RPC)")]
            Chroma[("chromadb:latest<br/>:8000 (Vectors)")]
            MinIO[("minio:latest<br/>:9000 API / :9001 UI")]
        end
    end

    Browser --> Frontend
    HostAPI --> Backend
    MinIOPort --> MinIO

    Frontend --> Backend
    Backend --> PG
    Backend --> Redis
    Backend --> MinIO
    
    VectorMCP --> Redis
    VectorMCP --> PG
    VectorMCP --> Chroma
    VectorMCP --> MinIO
```

### 2.2 Container Startup Dependency & Healthcheck Flow

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / CI Runner
    participant Compose as Docker Compose Engine
    participant PG as postgres:17-alpine
    participant Redis as redis:7-alpine
    participant Chroma as chromadb
    participant MinIO as minio
    participant Vector as vector-kb-mcp
    participant Backend as backend (FastAPI)
    participant Frontend as frontend (Next.js)

    Dev->>Compose: docker compose up -d
    
    par Launch Foundation Datastores
        Compose->>PG: Boot Container (Port 5432)
        Compose->>Redis: Boot Container (Port 6379)
        Compose->>Chroma: Boot Container (Port 8000)
        Compose->>MinIO: Boot Container (Ports 9000, 9001)
    end

    loop Healthcheck Probing
        Compose->>PG: pg_isready -U postgres -d akvo_rag
        PG-->>Compose: Healthy (exit 0)
        Compose->>Redis: redis-cli ping
        Redis-->>Compose: Healthy (PONG)
        Compose->>Chroma: curl -f http://localhost:8000/api/v1/heartbeat
        Chroma-->>Compose: Healthy (200 OK)
        Compose->>MinIO: curl -f http://localhost:9000/minio/health/live
        MinIO-->>Compose: Healthy (200 OK)
    end

    Note over Compose, Vector: Datastores Healthy -> Launch Dependent Services
    
    par Launch Application Services
        Compose->>Vector: Boot vector-kb-mcp (depends_on: { postgres, redis, chroma, minio })
        Compose->>Backend: Boot backend (depends_on: { postgres, redis, minio })
    end

    Compose->>Frontend: Boot frontend (depends_on: { backend })
    Frontend-->>Dev: Platform 100% Ready at http://localhost:3000
```

---

## 3. Detailed Service Specifications

### 3.1 `postgres` (PostgreSQL 17 Relational Database)
* **Image:** `postgres:17-alpine`
* **Port Mapping:** `${POSTGRES_PORT:-5432}:5432`
* **Environment Variables:**
  * `POSTGRES_DB=${POSTGRES_DB:-akvo_rag}`
  * `POSTGRES_USER=${POSTGRES_USER:-postgres}`
  * `POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}`
* **Volume Mount:** `postgres_data:/var/lib/postgresql/data`
* **Healthcheck:**
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-akvo_rag}"]
    interval: 5s
    timeout: 5s
    retries: 5
    start_period: 5s
  ```

### 3.2 `redis` (Redis 7 In-Memory Broker & RPC Queue)
* **Image:** `redis:7-alpine`
* **Command:** `redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy noeviction`
* **Port Mapping:** `${REDIS_PORT:-6379}:6379`
* **Volume Mount:** `redis_data:/data`
* **Healthcheck:**
  ```yaml
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
    start_period: 3s
  ```

### 3.3 `chromadb` (ChromaDB Vector Store)
* **Image:** `chromadb/chroma:latest`
* **Port Mapping:** `${CHROMA_PORT:-8001}:8000` *(Maps host 8001 to container 8000 to avoid conflicts with backend)*
* **Environment Variables:**
  * `IS_PERSISTENT=TRUE`
  * `PERSIST_DIRECTORY=/chroma/chroma`
  * `ANONYMIZED_TELEMETRY=FALSE`
* **Volume Mount:** `chroma_data:/chroma/chroma`
* **Healthcheck:**
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/heartbeat || exit 1"]
    interval: 5s
    timeout: 5s
    retries: 5
    start_period: 5s
  ```

### 3.4 `minio` (S3-Compatible Object Storage)
* **Image:** `minio/minio:latest`
* **Command:** `server /data --console-address ":9001"`
* **Port Mapping:**
  * `${MINIO_PORT:-9000}:9000` (S3 API)
  * `${MINIO_CONSOLE_PORT:-9001}:9001` (Web UI Console)
* **Environment Variables:**
  * `MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}`
  * `MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}`
* **Volume Mount:** `minio_data:/data`
* **Healthcheck:**
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live || exit 1"]
    interval: 5s
    timeout: 5s
    retries: 5
    start_period: 5s
  ```
> **Note on Bucket Provisioning:** Bucket creation (`documents/`) is handled natively in Python code by `MinIOService` on startup (`if not client.bucket_exists("documents"): client.make_bucket("documents")`), eliminating the need for an external `minio/mc` sidecar container.

### 3.5 `vector-kb-mcp` (Vector Microservice Container)
* **Build Context:** `./vector-kb-mcp`
* **Dockerfile:** `vector-kb-mcp/Dockerfile`
* **Volumes:**
  * `./vector-kb-mcp:/app:delegated` (Live code mount for hot reloading)
* **Environment Variables:**
  * `REDIS_URL=redis://redis:6379/0`
  * `DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-akvo_rag}`
  * `CHROMA_HOST=chromadb`
  * `CHROMA_PORT=8000`
  * `MINIO_ENDPOINT=minio:9000`
  * `MINIO_ACCESS_KEY=${MINIO_ROOT_USER:-minioadmin}`
  * `MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD:-minioadmin}`
  * `OPENAI_API_KEY=${OPENAI_API_KEY}`
* **Depends On:**
  * `postgres`: `{ condition: service_healthy }`
  * `redis`: `{ condition: service_healthy }`
  * `chromadb`: `{ condition: service_healthy }`
  * `minio`: `{ condition: service_healthy }`

### 3.6 `backend` (FastAPI Core Gateway)
* **Build Context:** `./backend`
* **Dockerfile:** `backend/Dockerfile`
* **Port Mapping:** `${BACKEND_PORT:-8000}:8000`
* **Volumes:**
  * `./backend:/app:delegated` (Live code mount)
* **Environment Variables:**
  * `ENVIRONMENT=development`
  * `DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-akvo_rag}`
  * `REDIS_URL=redis://redis:6379/0`
  * `MINIO_ENDPOINT=minio:9000`
  * `MINIO_ACCESS_KEY=${MINIO_ROOT_USER:-minioadmin}`
  * `MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD:-minioadmin}`
  * `OPENAI_API_KEY=${OPENAI_API_KEY}`
  * `MCP_CONFIG_PATH=/app/mcp_config.json`
* **Depends On:**
  * `postgres`: `{ condition: service_healthy }`
  * `redis`: `{ condition: service_healthy }`
  * `minio`: `{ condition: service_healthy }`

### 3.7 `frontend` (Next.js 14 Web Dashboard)
* **Build Context:** `./frontend`
* **Port Mapping:** `${FRONTEND_PORT:-3000}:3000`
* **Volumes:**
  * `./frontend:/app`
  * `/app/node_modules`
* **Environment Variables:**
  * `NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT:-8000}`
* **Depends On:**
  * `backend`: `{ condition: service_started }`

---

## 4. Environment Variables Contract (`.env.example`)

The `.env.example` file provides default variables with zero credentials:

```dotenv
# ==============================================================================
# AKVO-RAG UNIFIED CONTAINER ENVIRONMENT CONFIGURATION
# ==============================================================================

# Application Environment
ENVIRONMENT=development
DEBUG=true

# AI Provider API Keys
OPENAI_API_KEY=YOUR_OPENAI_API_KEY

# PostgreSQL 17 Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=akvo_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag

# Redis 7 Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# ChromaDB Vector Store Configuration
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_HOST_PORT=8001

# MinIO Object Storage Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_DOCUMENTS=documents

# Service Port Mappings
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

---

## 5. Developer Experience & Local Execution Commands

### 5.1 Infrastructure-Only Boot (for developing `vector-kb-mcp` or running migrations):
```bash
# Spin up only supporting datastores
docker compose up -d postgres redis chromadb minio
```

### 5.2 Full Monorepo Platform Boot:
```bash
# Spin up all 7 containers with live rebuild
docker compose up -d --build
```

### 5.3 Teardown & Reset:
```bash
# Stop containers without losing data
docker compose down

# Full reset including volume wiping (Clean state)
docker compose down -v
```

---

## 6. Verification & Quality Gates

### 6.1 Automated Verification Tests
1. **Docker Compose Configuration Validation:**
   ```bash
   docker compose config --quiet
   # Assert: Exit code 0 (valid syntax and schema)
   ```
2. **Infrastructure Health Probe Assertion:**
   ```bash
   docker compose up -d postgres redis chromadb minio
   # Wait 10 seconds, then inspect health status:
   docker inspect --format='{{.State.Health.Status}}' akvo-rag-postgres-1
   # Assert: "healthy"
   docker inspect --format='{{.State.Health.Status}}' akvo-rag-redis-1
   # Assert: "healthy"
   docker inspect --format='{{.State.Health.Status}}' akvo-rag-chromadb-1
   # Assert: "healthy"
   docker inspect --format='{{.State.Health.Status}}' akvo-rag-minio-1
   # Assert: "healthy"
   ```

### 6.2 Manual Verification Steps
- Access MinIO console at `http://localhost:9001` with `minioadmin / minioadmin`.
- Connect to PostgreSQL 17: `docker exec -it akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "SELECT version();"`
- Ping Redis: `docker exec -it akvo-rag-redis-1 redis-cli ping` (returns `PONG`).

---

## 7. Subtask Estimation & Breakdown

| Subtask ID | Description | Touchpoints | Vibe Est. | Trad. Est. | Confidence |
|---|---|---|:---:|:---:|:---:|
| `SUB-101.1` | Author unified `docker-compose.yml` with 7 containers, healthchecks, volumes, and network aliases | `docker-compose.yml` `[OVERWRITE]` | 1.0 hr | 0.8 day | High (95%) |
| `SUB-101.2` | Update and standardize `.env.example` with zero-credential placeholders | `.env.example` `[MODIFY]` | 0.3 hr | 0.2 day | High (99%) |
| `SUB-101.3` | Test startup, healthcheck transitions, and datastore connectivity | CLI / Docker daemon | 0.7 hr | 0.5 day | High (95%) |
| **TOTAL** | | | **2.0 hrs** | **1.5 days** | **High** |

---

## 8. Definition of Done (DoD)

- [ ] `docker-compose.yml` passes `docker compose config` with zero warnings.
- [ ] Executing `docker compose up -d postgres redis chromadb minio` brings all 4 datastores to a `healthy` state in $< 30\text{s}$.
- [ ] Named volumes persist data across container restarts.
- [ ] `.env.example` is complete and contains zero sensitive credentials or machine-specific paths.
