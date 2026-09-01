# Container-Based RAG Platform & Monorepo Consolidation LLD
**System Low-Level Design (LLD): Decoupled Multi-Container RAG Platform with Queue-Driven MCP Extensibility**

- **Document Identifier:** `LLD-002`
- **Target Repository:** `akvo-rag` (Consolidated Monorepo)
- **Author / Roles:** System Architect, Tech Leads, Engineering Management
- **Status:** APPROVED / READY FOR IMPLEMENTATION
- **Date:** 2026-09-01

---

## 1. Executive Summary & Management Directives

Based on architectural reviews and management directives, the RAG platform is transitioning to a **Container-Based Monorepo Architecture** with **Queue-Driven MCP Extensibility**:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ CONTAINER-BASED MONOREPO ARCHITECTURE (Option C Target)                                          │
│                                                                                                  │
│  ┌────────────────────────┐      ┌─────────────────────────┐      ┌───────────────────────────┐  │
│  │   akvo-rag-frontend    │      │    akvo-rag-backend     │      │       REDIS QUEUE         │  │
│  │      (Next.js 14)      │─────►│        (FastAPI)        │─────►│ • mcp:vector:requests     │  │
│  │ • Prompt & KB Web UI   │ HTTP │ • RAG LangGraph Orchestr│      │ • mcp:image:requests      │  │
│  │ • Chat Playground      │      │ • mcp_config Dispatcher │      │ • document_ingestion      │  │
│  └────────────────────────┘      └────────────┬────────────┘      └─────────────┬─────────────┘  │
│                                               │                                 │                │
│           ┌───────────────────────────────────┼─────────────────────────────────┼──────────┐     │
│           ▼                                   ▼                                 ▼          ▼     │
│  ┌─────────────────┐                 ┌─────────────────┐             ┌──────────────┐ ┌────────┐ │
│  │  PostgreSQL 17  │                 │      MinIO      │             │  vector-mcp  │ │ Other  │ │
│  │ (Consolidated:  │                 │ (Object Storage:│             │  Container   │ │ MCPs   │ │
│  │  Users, Prompts,│                 │  documents/     │             │ (ChromaRetr) │ │(Image, │ │
│  │  KBs, Chunks)   │                 │  raw files)     │             └──────┬───────┘ │Weathr) │ │
│  └─────────────────┘                 └─────────────────┘                    │         └────────┘ │
│                                                                             ▼                    │
│                                                                      ┌──────────────┐            │
│                                                                      │   ChromaDB   │            │
│                                                                      │ (Vector Store│            │
│                                                                      └──────────────┘            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Core Architectural Decisions:
1. **Discontinuation of Standalone `vector-knowledge-base-mcp-server` Repo:**
   - All document ingestion, chunking, OpenAI embeddings, and ChromaDB retrieval code is migrated directly into `akvo-rag/services/vector_kb_mcp/`.
2. **Container-Based Microservice Isolation:**
   - `akvo-rag-backend`, `akvo-rag-frontend`, `vector-mcp`, and any `other_mcp` (e.g. image recognition, weather) run as dedicated, isolated Docker containers within the same Docker Compose / Kubernetes network.
3. **Replacement of HTTP/SSE MCP Calls with High-Speed Redis Queue Request-Reply:**
   - Internal HTTP/HTTPS FastMCP streaming hops between `akvo-rag` and MCP servers are eliminated.
   - Requests are published to designated Redis queues (`mcp:vector:requests`) with correlation IDs, returning results in $< 5\text{ms}$.
4. **Declarative MCP Extensibility via `mcp_config`:**
   - A static configuration file (`mcp_config.json` / `mcp_config.yaml`) defines all active MCP tools and their request/reply queues.
   - New external tools (e.g., Image Recognition, Weather, Sensor APIs) can be attached dynamically as independent containers without modifying the core RAG engine.
5. **Unified Data Layer (PostgreSQL 17 + MinIO + ChromaDB):**
   - Single PostgreSQL 17 database replaces MySQL and handles all tables (`users`, `apps`, `api_keys`, `prompts`, `knowledge_bases`, `documents`, `document_chunks`).
   - MinIO provides dedicated S3-compatible document storage.
   - ChromaDB serves as the dedicated vector database.

---

## 2. System Architecture Blueprint

```mermaid
flowchart TB
    subgraph Clients["Clients & Host Applications"]
        WebAdmin["Admin / Developer Browser<br/>(http://localhost:3000)"]
        PartnerApp["Partner Host App (xxxconnect / WhatsApp)<br/>(POST /api/chat)"]
    end

    subgraph AkvoStack["Akvo-RAG Containerized Platform (docker-compose.yml)"]
        direction TB

        Frontend["akvo-rag-frontend (Next.js 14)<br/>• Port: 3000:3000<br/>• Prompt Management & Chat Playground"]
        
        Backend["akvo-rag-backend (FastAPI)<br/>• Port: 8000:8000<br/>• LangGraph RAG Engine<br/>• mcp_config Dispatcher"]
        
        Queue[("redis (Redis 7 Queue & Cache)<br/>• Port: 6379:6379<br/>• Request-Reply RPC Queues<br/>• Ingestion Task Queue")]

        subgraph MCPContainers["Pluggable MCP Containers Tier"]
            VectorMCP["vector-mcp (Vector Retrieval & Ingestion)<br/>• Consumes: mcp:vector:requests<br/>• Queries ChromaDB & Embeds Chunks"]
            OtherMCP["other_mcp (e.g., image_recognition, weather)<br/>• Consumes: mcp:image:requests<br/>• Vision / External Tool Processing"]
        end

        subgraph PersistentStorage["Unified Storage Tier (Docker Volumes)"]
            PG[("postgres (PostgreSQL 17)<br/>• Port: 5432:5432<br/>• Vol: postgres_data<br/>• Users, Prompts, KBs, Chunks")]
            Chroma[("chromadb (Chroma Vector DB)<br/>• Port: 8000:8000<br/>• Vol: chroma_data<br/>• Collections: kb_1, kb_2...")]
            MinIO[("minio (Object Storage)<br/>• Ports: 9000 (API), 9001 (Console)<br/>• Vol: minio_data<br/>• Bucket: documents/")]
        end
    end

    subgraph CloudAPIs["External Cloud Providers"]
        OpenAI["OpenAI API (api.openai.com:443)<br/>• text-embedding-3-small<br/>• gpt-4o-mini"]
    end

    %% Client Inbound
    WebAdmin -->|HTTP 3000| Frontend
    Frontend -->|REST / SSE 8000| Backend
    PartnerApp -->|POST /api/chat 8000| Backend

    %% Backend Integrations
    Backend -->|SQLAlchemy asyncpg: 5432| PG
    Backend -->|S3 Upload PDF: 9000| MinIO
    Backend -->|Publish Request: 6379| Queue
    Backend -->|HTTPS: 443| OpenAI

    %% Queue-Driven MCP Dispatch
    Queue <-->|Request-Reply RPC| VectorMCP
    Queue <-->|Request-Reply RPC| OtherMCP

    %% Vector MCP Integrations
    VectorMCP -->|HTTP: 8000| Chroma
    VectorMCP -->|Read/Write Chunks: 5432| PG
    VectorMCP -->|Fetch PDF: 9000| MinIO
    VectorMCP -->|Embeddings: 443| OpenAI
```

---

## 3. Container Topology & Service Breakdown

The Docker Compose file (`docker-compose.yml`) defines 7 primary containers:

| Container Name | Build / Image | Option C Role | Port Mapping | Storage Volumes |
|---|---|---|---|---|
| **`frontend`** | `akvo-rag/frontend` (Next.js 14) | Admin Web Dashboard, Prompt Editor, Chat Playground UI | `3000:3000` | Code bind mount |
| **`backend`** | `akvo-rag/backend` (FastAPI) | Core API, Auth, LangGraph RAG Workflow, `mcp_config` Dispatcher | `8000:8000` | Code bind mount |
| **`vector-mcp`** | `akvo-rag/services/vector_kb_mcp` | Vector similarity search worker and PDF document ingestion worker | Internal | Code bind mount |
| **`postgres`** | `postgres:17-alpine` | Unified relational database for users, prompts, KB metadata, and document chunks | `5432:5432` | `postgres_data:/var/lib/postgresql/data` |
| **`chromadb`** | `chromadb/chroma:latest` | Vector database storing embeddings per knowledge base collection | `8000:8000` | `chroma_data:/chroma/chroma` |
| **`minio`** | `minio/minio:latest` | S3-compatible object storage for uploaded PDF files | `9000:9000`, `9001:9001` | `minio_data:/data` |
| **`redis`** | `redis:7-alpine` | Ultra-fast message broker for MCP request-reply RPC and ingestion queues | `6379:6379` | `redis_data:/data` |

---

## 4. `mcp_config` & Queue-Based Request-Reply Dispatcher

### 4.1 Configuration Schema (`mcp_config.json`)

The `mcp_config.json` file is mounted into `akvo-rag-backend` at startup:

```json
{
  "mcp_servers": [
    {
      "id": 1,
      "mcp_name": "vector",
      "request_queue": "mcp:vector:requests",
      "response_prefix": "mcp:vector:responses",
      "timeout_ms": 5000,
      "tools": [
        {
          "name": "query_knowledge_base",
          "description": "Perform semantic similarity search over document chunks in target knowledge bases",
          "parameters": {
            "query": "string",
            "kb_ids": "array[integer]",
            "top_k": "integer",
            "score_threshold": "number"
          }
        }
      ],
      "enabled": true
    },
    {
      "id": 2,
      "mcp_name": "image_recognition",
      "request_queue": "mcp:image:requests",
      "response_prefix": "mcp:image:responses",
      "timeout_ms": 10000,
      "tools": [
        {
          "name": "analyze_crop_image",
          "description": "Detect pest and disease symptoms from uploaded plant photos",
          "parameters": {
            "image_url": "string",
            "crop_type": "string"
          }
        }
      ],
      "enabled": false
    }
  ]
}
```

### 4.2 Ultra-Fast Queue Request-Reply Protocol (Correlation ID)

```mermaid
sequenceDiagram
    autonumber
    participant RAG as akvo-rag-backend (FastAPI)
    participant Redis as Redis Queue Broker
    participant Worker as vector-mcp Container
    participant Chroma as ChromaDB

    Note over RAG, Worker: Step 1: Dispatch Tool Request
    RAG->>RAG: Generate correlation_id = uuid4()
    RAG->>Redis: RPUSH mcp:vector:requests { correlation_id, tool, input }
    
    Note over RAG, Worker: Step 2: Worker Processing
    Redis->>Worker: BLPOP mcp:vector:requests
    Worker->>Chroma: Query Vector Collection (kb_ids: [1, 2])
    Chroma-->>Worker: Return Top Chunks
    
    Note over Worker, RAG: Step 3: Reply via Correlation Key
    Worker->>Redis: RPUSH mcp:vector:responses:{correlation_id} { status: 'ok', data: chunks }
    Worker->>Redis: EXPIRE mcp:vector:responses:{correlation_id} 60
    
    Note over RAG, Redis: Step 4: Await & Return Result
    RAG->>Redis: BLPOP mcp:vector:responses:{correlation_id} (timeout=5s)
    Redis-->>RAG: Return Chunks (< 5ms queue overhead)
    RAG->>RAG: Continue LangGraph Answer Generation
```

### 4.3 Python MCP Queue Dispatcher Implementation

```python
# backend/app/services/mcp_queue_dispatcher.py
import json
import uuid
import asyncio
import redis.asyncio as redis
from typing import Dict, Any, Optional

class MCPQueueDispatcher:
    def __init__(self, redis_url: str, config_path: str = "mcp_config.json"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        with open(config_path, "r") as f:
            self.config = json.load(f)
        self.servers = {s["mcp_name"]: s for s in self.config.get("mcp_servers", []) if s.get("enabled")}

    async def call_tool(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any], timeout_seconds: float = 5.0) -> Dict[str, Any]:
        server = self.servers.get(mcp_name)
        if not server:
            raise ValueError(f"MCP Server '{mcp_name}' is not configured or disabled.")

        correlation_id = str(uuid.uuid4())
        request_queue = server["request_queue"]
        response_queue = f"{server['response_prefix']}:{correlation_id}"

        payload = {
            "correlation_id": correlation_id,
            "tool": tool_name,
            "arguments": arguments,
            "response_queue": response_queue
        }

        # 1. Push request to worker queue
        await self.redis.rpush(request_queue, json.dumps(payload))

        # 2. Wait for response on unique correlation key
        raw_resp = await self.redis.blpop(response_queue, timeout=int(timeout_seconds))
        if not raw_resp:
            raise TimeoutError(f"MCP tool '{mcp_name}.{tool_name}' timed out after {timeout_seconds}s")

        _, data = raw_resp
        return json.loads(data)
```

---

## 5. Repository Consolidation Plan (`vector-kb` $\rightarrow$ `akvo-rag`)

### 5.1 Monorepo Folder Structure

```text
akvo-rag/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI REST & SSE endpoints
│   │   ├── core/                 # Config & Security
│   │   ├── models/               # SQLAlchemy Models (Users, Prompts, KBs, Documents)
│   │   ├── services/             # RAG LangGraph & Prompt Services
│   │   │   └── mcp_queue_dispatcher.py # Dynamic Queue-backed MCP caller
│   │   └── seeder/               # Seed admin, prompts
│   ├── alembic/                  # Consolidated Alembic migrations
│   └── mcp_config.json           # Static MCP configuration file
├── frontend/                     # Next.js 14 Web Dashboard & Chat Playground
├── services/
│   └── vector_kb_mcp/            # Merged from vector-knowledge-base-mcp-server
│       ├── Dockerfile            # Container build for vector-mcp
│       ├── requirements.txt      # PDF parsing & ChromaDB dependencies
│       ├── main.py               # Redis Queue Worker entrypoint
│       ├── parser/               # PDF, DOCX, OCR extraction
│       ├── chunker/              # Token chunking & metadata enrichment
│       └── retriever/            # Direct ChromaDB vector querying
└── docker-compose.yml            # Complete 7-container local composition
```

### 5.2 Discontinuation & Porting Checklist
1. Copy `vector-knowledge-base-mcp-server/main/app/services/` (document parsers, chunkers, text extractors) into `akvo-rag/services/vector_kb_mcp/`.
2. Convert the FastMCP HTTP listener into a high-performance **Redis Queue Worker** that listens on `mcp:vector:requests`.
3. Consolidate `knowledge_bases`, `documents`, and `document_chunks` models into `akvo-rag/backend/app/models/`.
4. Archive `vector-knowledge-base-mcp-server` repository in GitHub.

---

## 6. Database Consolidation & Migration (PostgreSQL 17)

### 6.1 Unified Schema Registry

All tables live inside a single PostgreSQL 17 database:

```mermaid
erDiagram
    USERS ||--o{ CHATS : owns
    APPS ||--o{ API_KEYS : has
    APPS ||--o{ CHATS : records
    PROMPT_DEFINITIONS ||--o{ PROMPT_VERSIONS : tracks
    
    KNOWLEDGE_BASES ||--o{ DOCUMENTS : contains
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : splits
    
    USERS {
        int id PK
        string email
        string hashed_password
        string role
    }
    PROMPT_DEFINITIONS {
        int id PK
        string name
        string prompt_type
    }
    KNOWLEDGE_BASES {
        int id PK
        string name
        string description
        boolean is_active
    }
    DOCUMENTS {
        string id PK
        int kb_id FK
        string title
        string file_path
        string status
    }
    DOCUMENT_CHUNKS {
        string id PK
        string document_id FK
        int chunk_index
        text content
        json metadata_
    }
```

### 6.2 Automated Legacy Data Migration Script (`migrate_legacy_to_consolidated_postgres.py`)

A single Python CLI command extracts all data from legacy MySQL 8 and legacy Vector-KB PostgreSQL and populates PostgreSQL 17:

```bash
python -m app.scripts.migrate_legacy_to_consolidated_postgres \
  --mysql-url "mysql+pymysql://user:pass@mysql:3306/akvo_rag" \
  --legacy-pg-url "postgresql://user:pass@legacy_vkb:5432/vector_kb" \
  --target-pg-url "postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag"
```

---

## 7. Runtime Interaction Sequence Diagrams

### 7.1 Real-Time Conversational Turn with Queue-Backed Vector Retrieval

```mermaid
sequenceDiagram
    autonumber
    actor User as User / WhatsApp / Web
    participant Backend as akvo-rag-backend (FastAPI)
    participant Redis as Redis Queue (Broker)
    participant VectorMCP as vector-mcp Container
    participant Chroma as ChromaDB
    participant OpenAI as OpenAI API

    User->>Backend: 1. POST /api/chat { query, kb_ids: [1, 2] }
    Backend->>Backend: 2. Load Prompts from PostgreSQL 17
    
    critical Queue-Backed Vector Retrieval
        Backend->>Redis: 3. RPUSH mcp:vector:requests { correlation_id: 'abc-123', tool: 'query_knowledge_base', kb_ids: [1, 2], query }
        Redis->>VectorMCP: 4. BLPOP mcp:vector:requests
        VectorMCP->>OpenAI: 5. Generate Query Embedding (text-embedding-3-small)
        OpenAI-->>VectorMCP: Return 1536-dim Vector
        VectorMCP->>Chroma: 6. Parallel Query Collections: kb_1, kb_2
        Chroma-->>VectorMCP: Return Ranked Document Chunks
        VectorMCP->>Redis: 7. RPUSH mcp:vector:responses:abc-123 { chunks }
        Redis-->>Backend: 8. BLPOP Return Chunks (< 5ms latency)
    end
    
    Backend->>OpenAI: 9. LLM Grounded Answer Generation (gpt-4o-mini)
    OpenAI-->>Backend: Return Answer with [citation:N] references
    Backend-->>User: 10. Return RAGResponse { answer, citations, grounded: true }
```

### 7.2 Asynchronous Document Ingestion Flow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Manager
    participant Frontend as akvo-rag-frontend (Next.js)
    participant Backend as akvo-rag-backend (FastAPI)
    participant MinIO as MinIO Object Storage
    participant PG as PostgreSQL 17
    participant Redis as Redis Queue
    participant VectorMCP as vector-mcp Container
    participant Chroma as ChromaDB
    participant OpenAI as OpenAI API

    Admin->>Frontend: 1. Upload PDF Manual
    Frontend->>Backend: 2. POST /api/v1/knowledge-bases/{id}/documents (Multipart)
    Backend->>MinIO: 3. Save Raw PDF to Bucket: documents/
    Backend->>PG: 4. Insert Record (Status: PROCESSING)
    Backend->>Redis: 5. RPUSH document_ingestion { document_id, kb_id }
    Backend-->>Frontend: 6. 202 Accepted (Shows "Processing" in UI)
    
    Redis->>VectorMCP: 7. Worker Consumes Task from document_ingestion
    VectorMCP->>MinIO: 8. Download Raw PDF File
    VectorMCP->>VectorMCP: 9. Parse Pages, OCR & Chunk Text
    VectorMCP->>OpenAI: 10. Compute Batch Embeddings
    OpenAI-->>VectorMCP: Return Chunk Vectors
    VectorMCP->>Chroma: 11. Upsert Embeddings into Collection kb_{id}
    VectorMCP->>PG: 12. Save Chunk Records & Update Status = INDEXED
    Frontend->>Backend: 13. Poll KB Status -> Shows "Indexed"
```

---

## 8. Master Task Matrix & Implementation Phases

| Task Code | Title | Component / Path | Vibe-Coding Est. | Traditional Est. |
|---|---|---|---|---|
| **Phase 1** | **Codebase Consolidation & Monorepo Setup** | | | |
| `TASK-MONO-101` | Migrate `vector-kb` Parsing & Chunking Code into `services/vector_kb_mcp/` | `services/vector_kb_mcp/` | **2.5 hrs** | 2.0 days |
| `TASK-MONO-102` | Build `vector-mcp` Dockerfile & Redis Worker Entrypoint | `services/vector_kb_mcp/Dockerfile` | **2.0 hrs** | 1.5 days |
| **Phase 2** | **Unified Database & Migration Strategy** | | | |
| `TASK-DB-201` | Consolidate SQLAlchemy Models (`knowledge_bases`, `documents`, `chunks`) | `backend/app/models/` | **2.0 hrs** | 1.5 days |
| `TASK-DB-202` | Create Unified PostgreSQL 17 Alembic Migrations | `backend/alembic/` | **1.5 hrs** | 1.0 day |
| `TASK-DB-203` | Automated Data Migration CLI (MySQL + Vector-KB PG $\rightarrow$ PostgreSQL 17) | `backend/app/scripts/` | **2.0 hrs** | 1.5 days |
| **Phase 3** | **Queue-Backed MCP Dispatcher & `mcp_config`** | | | |
| `TASK-MCP-301` | Implement `mcp_config.json` Schema & Parser | `backend/app/core/` | **1.0 hr** | 1.0 day |
| `TASK-MCP-302` | Build `MCPQueueDispatcher` (Redis Request-Reply with Correlation ID) | `backend/app/services/` | **3.0 hrs** | 2.5 days |
| `TASK-MCP-303` | Integrate `MCPQueueDispatcher` into LangGraph RAG Engine | `backend/app/services/` | **2.5 hrs** | 2.0 days |
| **Phase 4** | **Document Ingestion & MinIO Storage** | | | |
| `TASK-ING-401` | Integrate MinIO Client for Document Uploads in FastAPI Backend | `backend/app/services/` | **1.5 hrs** | 1.0 day |
| `TASK-ING-402` | Build Celery/Redis Async Ingestion Consumer in `vector-mcp` | `services/vector_kb_mcp/` | **2.0 hrs** | 1.5 days |
| **Phase 5** | **Docker Compose Orchestration & Extensibility Verification** | | | |
| `TASK-OPS-501` | Author Unified `docker-compose.yml` for All 7 Services | Root `docker-compose.yml` | **2.0 hrs** | 1.5 days |
| `TASK-OPS-502` | Create Mock External MCP Container (e.g. `mock-image-mcp`) & Verify Config Plug-in | `services/mock_mcp/` | **1.5 hrs** | 1.0 day |
| `TASK-OPS-503` | End-to-End Golden Set Accuracy & Legacy Test Gate | `backend/RAG_evaluation/` | **2.5 hrs** | 2.0 days |
| **TOTAL** | | | **26.0 hrs (~3.5 working days)** | **20.0 days** |

---

## 9. Verification & Quality Gates

1. **Legacy Test Gate:**
   - Execute unit tests: `docker exec akvo-rag-backend-1 python -m pytest tests/unit -v`.
   - All tests must pass cleanly against PostgreSQL 17.
2. **Queue Request-Reply Latency Assertion:**
   - Benchmark `MCPQueueDispatcher.call_tool("vector", ...)`: Must return in $< 10\text{ms}$ queue overhead (excluding Chroma/OpenAI compute).
3. **Multi-MCP Extensibility Gate:**
   - Add mock tool to `mcp_config.json` $\rightarrow$ verify backend dynamically discovers and routes tool calls to the mock queue without code alterations.
4. **Golden Set RAGAS Evaluation:**
   - Run headless evaluation harness (`backend/RAG_evaluation/headless_evaluation.py`) asserting:
     - Faithfulness $\ge 0.85$
     - Answer Relevancy $\ge 0.85$
     - Groundedness $\ge 0.90$
