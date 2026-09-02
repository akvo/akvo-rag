# Feature Specification: Vector-KB Dockerfile & Native Async Redis Worker

> **Feature ID:** `003_mono_103_vector_kb_dockerfile_and_native_async_redis_worker_spec`  
> **Task Ref:** `TASK-MONO-103`  
> **Target Branch:** `epic/rag-monorepo-mcp`  
> **Status:** `PROPOSED (Under Review)`  
> **Estimated Effort:** `2.0 hrs (Vibe-Coding) / 1.5 days (Traditional)`  
> **Author:** Antigravity Architect / Systems & Cloud Engineer  
> **Source Repository:** `vector-knowledge-base-mcp-server` (`/Users/galihpratama/Sites/vector-knowledge-base-mcp-server`)  
> **Upstream Reference:** [docs/lld/container_based_rag_platform_lld.md](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md) (Sections 4, 8, 9)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
In the legacy implementation, the vector knowledge base operated as a FastMCP HTTP server on port 8000. This design introduced significant networking friction:
1. **HTTP Reconnect & Discovery Fragility:** Required `MCPDiscoveryManager` in the backend with continuous polling and reconnect loops.
2. **Serialization Overhead:** Forced base64 serialization of document chunks and payload wrapping.
3. **Container Inefficiency:** Depended on separate Celery workers and RabbitMQ brokers for background processing.

`TASK-MONO-103` establishes the containerized runtime and native **Async Redis Queue Worker** (`vector-kb-mcp/main.py`) that consumes tool calls directly from Redis `mcp:vector:requests` with **$< 5\text{ms}$ latency**, dispatches execution to `ChromaRetriever` or KB handlers, and replies via correlation ID keys.

### 1.2 5W1H Discovery Lens

| Dimension | Specification |
|---|---|
| **Who** | `vector-kb-mcp` container, `akvo-rag-backend` (`MCPQueueDispatcher`), and Docker Compose. |
| **What** | Author the container runtime (`Dockerfile`), configuration module (`core/config.py`), and async Redis event loop (`main.py`) handling tool dispatch and graceful shutdown. |
| **Where** | `vector-kb-mcp/Dockerfile`, `vector-kb-mcp/main.py`, `vector-kb-mcp/core/config.py`, `vector-kb-mcp/core/logging.py`. |
| **When** | **Phase 1, Step 3** — immediately after `TASK-MONO-102` (Parsers & Retrievers). |
| **Why** | Provides a sub-5ms RPC transport for vector retrieval and KB management, completely eliminating FastMCP HTTP dependencies and discovery polling loops. |
| **How** | Python 3.11 `redis.asyncio` with non-blocking `BLPOP` on `mcp:vector:requests`, error boundary isolation, correlation ID reply routing (`RPUSH`), and graceful signal handling (SIGTERM/SIGINT). |

---

## 2. Architecture & Queue Protocol Design

### 2.1 Request-Reply RPC Protocol with Correlation ID

```mermaid
sequenceDiagram
    autonumber
    participant Backend as akvo-rag-backend (FastAPI)
    participant Redis as Redis Queue Broker (:6379)
    participant Worker as vector-kb-mcp Container (main.py)
    participant Retriever as ChromaRetriever
    participant Chroma as ChromaDB Container

    Note over Backend, Worker: 1. Request Enqueue
    Backend->>Backend: Generate correlation_id = uuid4()
    Backend->>Redis: RPUSH mcp:vector:requests <br/>{ correlation_id, tool_name: "query_knowledge_base", arguments: { query, kb_ids, top_k } }
    
    Note over Worker, Redis: 2. Worker Dequeue & Processing
    Redis->>Worker: BLPOP mcp:vector:requests 0
    Worker->>Worker: Parse JSON & validate tool_name in TOOL_HANDLERS
    Worker->>Retriever: search(query, kb_ids, top_k)
    Retriever->>Chroma: Query Vector Collections
    Chroma-->>Retriever: Document Chunks
    Retriever-->>Worker: List[RetrievedChunk]
    
    Note over Worker, Backend: 3. Reply via Dedicated Correlation Key
    Worker->>Redis: RPUSH mcp:vector:responses:{correlation_id} <br/>{ status: "ok", data: [...] }
    Worker->>Redis: EXPIRE mcp:vector:responses:{correlation_id} 60
    
    Redis-->>Backend: BLPOP mcp:vector:responses:{correlation_id} 5s
    Backend->>Backend: Deserialize & continue LangGraph execution
```

### 2.2 Error Handling & Timeout Protocol

```mermaid
flowchart TD
    Req[Incoming Request on mcp:vector:requests] --> JSONCheck{Valid JSON?}
    JSONCheck -- No --> ErrJSON[Reply status: error, message: 'Invalid JSON payload']
    JSONCheck -- Yes --> ToolCheck{Tool registered in TOOL_HANDLERS?}
    ToolCheck -- No --> ErrTool[Reply status: error, message: 'Unknown tool: ...']
    ToolCheck -- Yes --> Exec[Execute Async Handler]
    
    Exec --> Success{Execution Succeeded?}
    Success -- Yes --> ReplyOK[RPUSH mcp:vector:responses:id with status: 'ok', data: result]
    Success -- No --> ReplyErr[RPUSH mcp:vector:responses:id with status: 'error', error: str(exc)]
    
    ReplyOK --> SetTTL[EXPIRE mcp:vector:responses:id 60s]
    ReplyErr --> SetTTL
```

---

## 3. Detailed Technical Specifications

### 3.1 `vector-kb-mcp/Dockerfile`

```dockerfile
# Build Stage / Production Runtime
FROM python:3.11-slim

# Set working directory and environment
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install minimal OS dependencies (curl for healthchecks, postgresql-client for alembic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Run as non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Entrypoint executes the native async Redis worker event loop
CMD ["python", "main.py"]
```

---

### 3.2 Configuration Engine (`vector-kb-mcp/core/config.py`)

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Redis Queue Configuration
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    REQUEST_QUEUE: str = Field(default="mcp:vector:requests")
    RESPONSE_PREFIX: str = Field(default="mcp:vector:responses")
    RESPONSE_TTL_SECONDS: int = Field(default=60)

    # Database Configuration (PostgreSQL 17)
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag")

    # ChromaDB Vector Store Configuration
    CHROMA_HOST: str = Field(default="chromadb")
    CHROMA_PORT: int = Field(default=8000)

    # MinIO Object Storage Configuration
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_DOCUMENTS: str = Field(default="documents")
    MINIO_SECURE: bool = Field(default=False)

    # OpenAI API Configuration
    OPENAI_API_KEY: str = Field(default="")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

---

### 3.3 Main Redis Worker Event Loop (`vector-kb-mcp/main.py`)

```python
import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any, Callable, Awaitable

import chromadb
import redis.asyncio as redis
from openai import AsyncOpenAI

from core.config import settings
from retriever.chroma_retriever import ChromaRetriever

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [vector-kb-mcp] %(message)s"
)
logger = logging.getLogger("vector-kb-mcp")

class VectorMCPWorker:
    def __init__(self):
        self.running = False
        self.redis_client: redis.Redis = None
        self.chroma_client = None
        self.openai_client = None
        self.retriever: ChromaRetriever = None
        self.tool_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}

    async def initialize(self):
        logger.info("Initializing vector-kb-mcp worker...")
        
        # 1. Initialize Redis connection
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await self.redis_client.ping()
        logger.info(" Connected to Redis: %s", settings.REDIS_URL)

        # 2. Initialize Chroma client
        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        logger.info(" Connected to ChromaDB: %s:%d", settings.CHROMA_HOST, settings.CHROMA_PORT)

        # 3. Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # 4. Initialize ChromaRetriever
        self.retriever = ChromaRetriever(
            chroma_client=self.chroma_client,
            openai_client=self.openai_client,
            embedding_model=settings.DEFAULT_EMBEDDING_MODEL
        )

        # 5. Register tool handlers (Phase 1 includes retrieval and stub handlers for DB CRUD)
        self.tool_handlers = {
            "query_knowledge_base": self._handle_query_kb,
            "list_knowledge_bases": self._handle_list_kbs_stub,
            "get_knowledge_base": self._handle_get_kb_stub,
            "create_knowledge_base": self._handle_create_kb_stub,
            "update_knowledge_base": self._handle_update_kb_stub,
            "delete_knowledge_base": self._handle_delete_kb_stub,
            "list_documents": self._handle_list_docs_stub,
            "get_document": self._handle_get_doc_stub,
            "get_processing_tasks": self._handle_get_tasks_stub,
        }
        logger.info(" Registered %d tool handlers.", len(self.tool_handlers))

    # --- Tool Handlers ---
    async def _handle_query_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        kb_ids = args.get("kb_ids", [])
        top_k = args.get("top_k", 4)
        score_threshold = args.get("score_threshold")

        chunks = await self.retriever.search(
            query=query,
            kb_ids=kb_ids,
            top_k=top_k,
            score_threshold=score_threshold
        )
        return {"chunks": [c.__dict__ for c in chunks]}

    # Stubs for Phase 2 DB model integration
    async def _handle_list_kbs_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"knowledge_bases": []}

    async def _handle_get_kb_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": args.get("kb_id"), "status": "ACTIVE"}

    async def _handle_create_kb_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "created", "kb_id": 1}

    async def _handle_update_kb_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "updated"}

    async def _handle_delete_kb_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "deleted"}

    async def _handle_list_docs_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"documents": []}

    async def _handle_get_doc_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"document": {}}

    async def _handle_get_tasks_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"tasks": []}

    # --- Event Loop ---
    async def run(self):
        self.running = True
        logger.info(" Listening for tool requests on queue: '%s'...", settings.REQUEST_QUEUE)

        while self.running:
            try:
                # Non-blocking pop with 1s timeout to allow clean shutdown checks
                item = await self.redis_client.blpop(settings.REQUEST_QUEUE, timeout=1)
                if not item:
                    continue

                _, raw_payload = item
                asyncio.create_task(self._process_message(raw_payload))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in worker event loop: %s", e, exc_info=True)
                await asyncio.sleep(0.5)

    async def _process_message(self, raw_payload: str):
        try:
            msg = json.loads(raw_payload)
            correlation_id = msg.get("correlation_id")
            tool_name = msg.get("tool") or msg.get("tool_name", "query_knowledge_base")
            args = msg.get("arguments", {})
            response_queue = msg.get("response_queue") or f"{settings.RESPONSE_PREFIX}:{correlation_id}"

            if not correlation_id:
                logger.error("Missing correlation_id in payload: %s", raw_payload)
                return

            handler = self.tool_handlers.get(tool_name)
            if not handler:
                response = {"status": "error", "error": f"Unknown tool: '{tool_name}'"}
            else:
                try:
                    result = await handler(args)
                    response = {"status": "ok", "data": result}
                except Exception as ex:
                    logger.error("Error executing handler for tool '%s': %s", tool_name, ex, exc_info=True)
                    response = {"status": "error", "error": str(ex)}

            # Send response back via correlation key
            await self.redis_client.rpush(response_queue, json.dumps(response))
            await self.redis_client.expire(response_queue, settings.RESPONSE_TTL_SECONDS)

        except Exception as e:
            logger.error("Failed to parse message: %s", e, exc_info=True)

    async def shutdown(self):
        logger.info("Initiating graceful shutdown...")
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Shutdown complete.")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    worker = VectorMCPWorker()

    def handle_signal():
        logger.info("Received termination signal.")
        loop.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    try:
        loop.run_until_complete(worker.initialize())
        loop.run_until_complete(worker.run())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
```

---

## 4. Verification & Quality Gates

### 4.1 Automated Worker Integration Tests (`vector-kb-mcp/tests/test_redis_worker.py`)
1. **Request-Reply RPC Flow Test:**
   - Push mock request to `mcp:vector:requests` with `correlation_id = "test-123"`.
   - Verify worker processes message and pushes response to `mcp:vector:responses:test-123`.
   - Assert response status is `"ok"` and TTL is set to 60s.
2. **Error Isolation Test:**
   - Push request with invalid `tool_name = "non_existent_tool"`.
   - Verify worker replies with `status: "error"` without crashing the main loop.
3. **Graceful Shutdown Test:**
   - Trigger `worker.shutdown()` $\rightarrow$ verify loop breaks cleanly and Redis connections close without hanging.

---

## 5. Subtask Estimation & Breakdown

| Subtask ID | Description | Touchpoints | Vibe Est. | Trad. Est. | Confidence |
|---|---|---|:---:|:---:|:---:|
| `SUB-103.1` | Create `vector-kb-mcp/Dockerfile` and non-root user runtime | `vector-kb-mcp/Dockerfile` `[NEW]` | 0.4 hr | 0.3 day | High (99%) |
| `SUB-103.2` | Implement `vector-kb-mcp/core/config.py` Pydantic settings | `vector-kb-mcp/core/config.py` `[NEW]` | 0.3 hr | 0.2 day | High (99%) |
| `SUB-103.3` | Implement `vector-kb-mcp/main.py` async event loop, `TOOL_HANDLERS`, and correlation ID responses | `vector-kb-mcp/main.py` `[NEW]` | 0.9 hr | 0.7 day | High (95%) |
| `SUB-103.4` | Implement signal handling (SIGTERM/SIGINT) for graceful container termination | `vector-kb-mcp/main.py` `[MODIFY]` | 0.4 hr | 0.3 day | High (95%) |
| **TOTAL** | | | **2.0 hrs** | **1.5 days** | **High** |

---

## 6. Definition of Done (DoD)

- [ ] `vector-kb-mcp/Dockerfile` builds cleanly with zero errors.
- [ ] `vector-kb-mcp/main.py` starts, connects to Redis and ChromaDB, and listens on `mcp:vector:requests`.
- [ ] Enqueuing a request to `mcp:vector:requests` returns a formatted response on `mcp:vector:responses:{correlation_id}` in $< 5\text{ms}$ (excluding OpenAI embed compute).
- [ ] Container handles `docker stop` (SIGTERM) gracefully within 5 seconds without dropping in-flight requests.
