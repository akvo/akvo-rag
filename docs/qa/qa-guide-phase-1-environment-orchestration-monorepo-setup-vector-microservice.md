# Phase 1 Manual QA & Verification Guide

> **Issue**: [#107](https://github.com/akvo/akvo-rag/issues/107) — `[RAG IMPROVEMENT] D8 - Phase 1: Environment Orchestration, Monorepo Setup & Vector Microservice`  
> **Target Branch / PR**: `phase-1/107-rag-improvement-d8-phase-1-environment-orchestration-monorepo-setup-vector-microservice` -> `epic/rag-monorepo-mcp` ([PR #116](https://github.com/akvo/akvo-rag/pull/116))

---

## 1. Overview & Scope

In **Phase 1**, the repository establishes a unified containerized monorepo infrastructure and a standalone, non-blocking `vector-kb-mcp` microservice. This microservice runs an asynchronous event loop over Redis lists using `BLPOP` / `RPUSH` for JSON-RPC message dispatching.

This QA guide details:
- How to execute automated unit and integration tests.
- How to perform **manual QA** by sending live JSON-RPC tool requests to the Redis queue and validating the microservice's responses in real time.
- How to verify the health and connectivity of all coordinated infrastructure services.

---

## 2. Prerequisites & Environment Setup

Ensure the container stack is up and healthy:

```bash
# Start the unified local development environment
docker compose up -d

# Verify all services are running and healthy
docker compose ps
```

Expected running containers:
- `akvo-rag-vector-kb-mcp-1`
- `akvo-rag-chromadb-1` (port 8001 -> 8000)
- `akvo-rag-redis-1` (port 6379)
- `akvo-rag-postgres-1` (port 5432)
- `akvo-rag-minio-1` (ports 9000, 9001)

---

## 3. Automated Test Suite Execution

Run the automated test runner scripts from the workspace root:

```bash
# 1. Run full test suite with statement coverage report (Target: >= 85%)
./vector-kb-mcp/test.sh

# 2. Run fast isolated unit tests (using mocks)
./vector-kb-mcp/test-unit.sh

# 3. Run live container integration tests (against live Redis & ChromaDB)
./vector-kb-mcp/test-integration.sh
```

**Quality Baseline**:
- **34 tests passing** (32 unit + 2 live integration).
- **96% statement coverage** across all `vector-kb-mcp` modules.
- Suite execution completes in $< 3.0\text{s}$.

---

## 4. Manual QA: Live Redis RPC Message Verification

The `vector-kb-mcp` service continuously polls the Redis list `mcp:vector:requests`. When a request is pushed, the worker processes the payload and pushes the JSON response to `mcp:vector:responses:{correlation_id}` with a 60-second TTL.

### Test Case 1: Knowledge Base Listing (`list_knowledge_bases`)
Sends an RPC request to list registered knowledge bases:

```bash
docker exec akvo-rag-redis-1 redis-cli LPUSH mcp:vector:requests '{"correlation_id": "qa-test-1", "tool_name": "list_knowledge_bases", "arguments": {}}'
docker exec akvo-rag-redis-1 redis-cli BLPOP mcp:vector:responses:qa-test-1 2
```

**Expected Response**:
```json
{"status": "ok", "data": {"knowledge_bases": []}}
```

---

### Test Case 2: Knowledge Base Inspection (`get_knowledge_base`)
Sends an RPC request with arguments to fetch KB metadata by ID:

```bash
docker exec akvo-rag-redis-1 redis-cli LPUSH mcp:vector:requests '{"correlation_id": "qa-test-2", "tool_name": "get_knowledge_base", "arguments": {"kb_id": 101}}'
docker exec akvo-rag-redis-1 redis-cli BLPOP mcp:vector:responses:qa-test-2 2
```

**Expected Response**:
```json
{"status": "ok", "data": {"id": 101, "status": "ACTIVE"}}
```

---

### Test Case 3: Error Boundary & Unknown Tool Handling
Validates that invalid tool calls are trapped gracefully without crashing the worker event loop:

```bash
docker exec akvo-rag-redis-1 redis-cli LPUSH mcp:vector:requests '{"correlation_id": "qa-test-3", "tool_name": "unknown_tool", "arguments": {}}'
docker exec akvo-rag-redis-1 redis-cli BLPOP mcp:vector:responses:qa-test-3 2
```

**Expected Response**:
```json
{"status": "error", "error": "Unknown tool: 'unknown_tool'"}
```

---

### Test Case 4: Malformed JSON Payload Resiliency
Validates that corrupt JSON payloads are logged and dropped without interrupting ongoing worker polling:

```bash
docker exec akvo-rag-redis-1 redis-cli LPUSH mcp:vector:requests '{invalid_json_payload'
```

**Expected Behavior**:
The worker logs an error (`Failed to parse incoming JSON payload`) and immediately continues polling without crashing.

---

## 5. Microservice Log Inspection

To observe incoming RPC requests and connection lifecycles in real time:

```bash
docker compose logs -f vector-kb-mcp
```

**Expected Startup Log Sequence**:
```text
[INFO] [vector-kb-mcp] Initializing vector-kb-mcp worker...
[INFO] [vector-kb-mcp] Connected to Redis: redis://redis:6379/0
[INFO] [vector-kb-mcp] Connected to ChromaDB: chromadb:8000
[INFO] [vector-kb-mcp] Registered 9 tool handlers.
[INFO] [vector-kb-mcp] Listening for tool requests on queue: 'mcp:vector:requests'...
```

---

## 6. Infrastructure Services Health Verification

| Service | Protocol / Port | Verification Command | Expected Status |
|---|---|---|---|
| **ChromaDB** | HTTP `8001` (mapped to `8000`) | `curl -s http://localhost:8001/api/v2/heartbeat` | Returns timestamp/heartbeat object |
| **Redis 7** | TCP `6379` | `docker exec akvo-rag-redis-1 redis-cli ping` | `PONG` |
| **PostgreSQL 17** | TCP `5432` | `docker exec akvo-rag-postgres-1 psql -U akvo -d akvo_rag -c "\l"` | Lists `akvo_rag` database |
| **MinIO S3** | HTTP `9000` (API), `9001` (UI) | `curl -s http://localhost:9000/minio/health/live` | `200 OK` (Web UI at `http://localhost:9001`) |

---

## 7. Next Steps & End-to-End Testing Roadmap

- **Phase 1** *(Current)*: Verified standalone microservice RPC worker, local infrastructure, and isolated parsers/retriever.
- **Phase 2** *(Next)*: Implementation of SQLAlchemy 2.0 models, Alembic migrations for PostgreSQL, and metadata enrichment.
- **Phase 3**: Integration of the FastAPI LangGraph chat workflow directly with the `vector-kb-mcp` Redis queue, enabling full UI-based chat playground manual QA.
