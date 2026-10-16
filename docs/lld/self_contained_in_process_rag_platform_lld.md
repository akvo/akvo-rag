# Self-Contained In-Process RAG Platform LLD
**System Low-Level Design (LLD): Reusable Multi-Sector In-Process RAG Architecture**

- **Document Identifier:** `LLD-001`
- **Target Systems:** `akvo-rag` + `vector-knowledge-base-mcp-server` + Host Application (`agriconnect` / `washconnect`)
- **Author / Roles:** System Architect, Technical Project Manager, Tech Leads
- **Status:** DISCONTINUED - Replaced by `docs/lld/container_based_rag_platform_lld.md`
- **Date:** 2026-08-31

---

## 1. Executive Summary & Architectural Motivation

Based on the RAG Platform Architecture Review, the current multi-namespace distributed deployment topology (~20 workloads across 3 namespaces, 3 databases on 2 engines, multiple Celery queues, and HTTP streaming MCP hops) is being replaced by a **Self-Contained In-Process Architecture**.

### Key Architectural Shifts
1. **In-Process RAG & Direct Retrieval:** `akvo-rag` and `vector-knowledge-base-mcp-server` are packaged into modular Python libraries (`akvo-rag-core` and `vector-kb-core`) imported directly by the host application process.
2. **Elimination of Intermediate Network Hops:** Direct Python function calls replace 4 internal HTTP hops, streaming MCP transport, and unauthenticated/unretried HTTP callbacks.
3. **Elimination of Redundant LLM Overhead:** The `ScopingAgent` LLM call (which previously made an LLM call whose tool-selection output was discarded) is removed from the default RAG graph path, saving 1.5s–3.0s and 1 model call per question.
4. **Single-Namespace Deployment:** Reduces per-partner infrastructure from ~20 workloads to **3 application workloads** (Web App, App Worker, Ingestion Worker) backed by 1 PostgreSQL database, 1 Redis broker, ChromaDB, and MinIO.

---

## 2. System Architecture Blueprint

```mermaid
flowchart TB
    subgraph HostApp["Host Application (AgriConnect / WASHConnect) - 1 Deployment"]
        direction TB
        CA["Channel Adapter (WhatsApp / Web)"]
        PIPE["Conversation Pipeline (Dedupe, Onboard, Intent)"]

        subgraph CorePackages["In-Process Python Libraries"]
            RAGC["akvo-rag-core<br/>(LangGraph Workflow, Prompt Resolver)"]
            RET["vector-kb-core<br/>(ChromaRetriever, Direct Search)"]
        end

        PIPE --> RAGC
        RAGC --> RET
    end

    subgraph BackgroundWorker["Ingestion Worker - 1 Deployment"]
        ING["Document Processor<br/>(PDF Parse, Embed, Index)"]
    end

    subgraph AppWorker["App Worker - 1 Deployment"]
        WRK["Celery Worker<br/>(Outbound WhatsApp, Retries, Beat)"]
    end

    subgraph Storage["Storage & Datastores"]
        VS[("ChromaDB<br/>(Vector Collections)")]
        PG[("PostgreSQL 17<br/>(App, Prompts, KB Metadata)")]
        MN[("MinIO / S3<br/>(Raw Document Files)")]
        RD[("Redis<br/>(Broker & Cache)")]
    end

    RET --> VS
    RET --> PG
    ING --> MN
    ING --> VS
    ING --> PG
    PIPE --> PG
    WRK --> RD
```

---

## 3. High-Level Phase Workflow

```mermaid
flowchart LR
    subgraph P1["Phase 1: vector-kb-core"]
        V1["TASK-VKB-101<br/>Scaffold Package & ABC"] --> V2["TASK-VKB-102<br/>ChromaRetriever Direct Search"]
        V2 --> V3["TASK-VKB-103<br/>Unit & Integration Tests"]
    end

    subgraph P2["Phase 2: akvo-rag-core"]
        R1["TASK-RAG-201<br/>Scaffold RAG Core Engine"] --> R2["TASK-RAG-202<br/>Direct Retriever Hook"]
        R2 --> R3["TASK-RAG-203<br/>Bypass ScopingAgent"]
        R3 --> R4["TASK-RAG-204<br/>Purge Startup MCP & Leaks"]
        R4 --> R5["TASK-RAG-205<br/>Multi-Tier Prompt Resolver"]
        R5 --> R6["TASK-RAG-206<br/>Unified Data Migration CLI & Script"]
    end

    subgraph P3["Phase 3: Ingestion Worker"]
        I1["TASK-VKB-301<br/>Embedding Model Guard"] --> I2["TASK-VKB-302<br/>SOP & Standard Metadata"]
        I2 --> I3["TASK-VKB-303<br/>Package Ingestion Worker"]
    end

    subgraph P4["Phase 4: Host App Integration"]
        H1["TASK-INT-401<br/>EmbeddedAIService Adapter"] --> H2["TASK-INT-402<br/>Single-Namespace Compose"]
    end

    subgraph P5["Phase 5: Verification & QA"]
        Q1["TASK-QA-501<br/>Golden Set E2E CI Harness"]
    end

    P1 --> P2
    P1 --> P3
    P2 --> P4
    P3 --> P4
    P4 --> P5
```

---

## 4. Master Task Matrix & Estimates

| Task Code | Title | Target Repository | Vibe-Coding Est. | Traditional Est. |
|---|---|---|---|---|
| **Phase 1** | **`vector-kb-core` Package Extraction** | | | |
| `TASK-VKB-101` | Scaffold `vector-kb-core` Package, Typed Interfaces & Structured Logging | `vector-kb-mcp-server` | **2.0 hrs** | 1.5 days |
| `TASK-VKB-102` | Implement `ChromaRetriever` with Direct Similarity Search | `vector-kb-mcp-server` | **3.0 hrs** | 2.5 days |
| `TASK-VKB-103` | Unit & Integration Test Suite for `vector-kb-core` | `vector-kb-mcp-server` | **1.5 hrs** | 1.0 day |
| **Phase 2** | **`akvo-rag-core` Package Extraction** | | | |
| `TASK-RAG-201` | Scaffold `akvo-rag-core` Package, LangGraph Engine & Structured Logging | `akvo-rag` | **3.5 hrs** | 3.0 days |
| `TASK-RAG-202` | Direct `Retriever` Integration (Delete FastMCP Client & Update Legacy Tests) | `akvo-rag` | **2.5 hrs** | 2.0 days |
| `TASK-RAG-203` | Short-Circuit `ScopingAgent` on Default RAG Path | `akvo-rag` | **1.5 hrs** | 1.0 day |
| `TASK-RAG-204` | Remove Startup MCP Discovery & Purge Domain Leaks | `akvo-rag` | **1.5 hrs** | 1.0 day |
| `TASK-RAG-205` | Multi-Tier Prompt Resolver & Prompt Reactivity Integration Test | `akvo-rag` | **3.0 hrs** | 2.5 days |
| `TASK-RAG-206` | PostgreSQL Database Adapter & Unified Data Migration CLI/Scripts (MySQL + Vector-KB PG) | `akvo-rag` | **2.0 hrs** | 1.5 days |
| **Phase 3** | **Ingestion Worker & Metadata Hardening** | | | |
| `TASK-VKB-301` | Add KB Embedding Model & Dimension Guard | `vector-kb-mcp-server` | **2.5 hrs** | 1.5 days |
| `TASK-VKB-302` | Enrich Documents & Chunks with Public-Sector Metadata | `vector-kb-mcp-server` | **2.0 hrs** | 1.5 days |
| `TASK-VKB-303` | Package Dedicated Background Ingestion Worker & Upload Task Contract | `vector-kb-mcp-server` | **2.0 hrs** | 1.0 day |
| **Phase 4** | **Host App In-Process Integration** | | | |
| `TASK-INT-401` | Build `EmbeddedAIService` Adapter in Host Application | Host App (`agriconnect`) | **3.5 hrs** | 2.5 days |
| `TASK-INT-402` | Unified Single-Namespace Docker Compose & Manifests | Host / Compose | **2.0 hrs** | 1.5 days |
| **Phase 5** | **Verification, QA & Golden Set Harness** | | | |
| `TASK-QA-501` | Golden Set Evaluation, Legacy Test Gate & CI Pipeline | `akvo-rag` | **3.5 hrs** | 2.5 days |
| **TOTAL** | | | **36.0 hrs (~4.5 working days)** | **28.0 days** |

---

## 5. Detailed Task Specifications

### Phase 1: `vector-kb-core` Package Extraction & Direct Retrieval

#### `TASK-VKB-101`: Scaffold `vector-kb-core` Package & Typed Interfaces
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**
  Extract the retrieval interfaces into an installable Python package `vector-kb-core`. This package will be directly imported by `akvo-rag-core` and host applications. Define strongly typed immutable data structures (`RetrievedChunk`, `QueryFilter`, `KBMetadata`) and the abstract base class `Retriever`.
* **Key Touchpoints:**
  - `packages/vector-kb-core/pyproject.toml` `[NEW]`
  - `packages/vector-kb-core/README.md` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/__init__.py` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/models.py` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/retriever.py` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/logging.py` `[NEW]`
* **Code Specification:**
  ```python
  # packages/vector-kb-core/src/vector_kb_core/models.py
  from dataclasses import dataclass, field
  from typing import Any, Dict, Optional

  @dataclass(frozen=True)
  class RetrievedChunk:
      content: str
      kb_id: int
      document_id: str
      chunk_id: str
      score: float
      metadata: Dict[str, Any] = field(default_factory=dict)

  # packages/vector-kb-core/src/vector_kb_core/retriever.py
  from abc import ABC, abstractmethod
  from typing import List, Optional
  from .models import RetrievedChunk

  class Retriever(ABC):
      @abstractmethod
      async def search(
          self,
          query: str,
          kb_ids: List[int],
          top_k: int = 4,
          score_threshold: Optional[float] = None,
          trace_id: Optional[str] = None
      ) -> List[RetrievedChunk]:
          """Search across multiple knowledge base collections directly in-memory."""
          pass
  ```
* **User Acceptance Criteria (UAC):**
  - Developers can install `vector-kb-core` as an independent Python library via `pip install -e ./packages/vector-kb-core`.
* **Technical Acceptance Criteria (TAC):**
  - `pyproject.toml` configures package build using `hatchling` or `setuptools`.
  - Zero dependencies on FastAPI, Celery, or FastMCP in `vector-kb-core`.
  - Emits structured contextual log records with `trace_id`, `event`, and duration via standard Python `logging`.
  - Type annotations pass `mypy --strict`.

---

#### `TASK-VKB-102`: Implement `ChromaRetriever` with Direct Similarity Search
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `3.0 hours`
* **Detailed Description:**
  Implement the concrete `ChromaRetriever` class inside `vector-kb-core`. It connects directly to ChromaDB, computes query embeddings using OpenAI or local embedding providers, queries multiple `kb_{id}` collections concurrently via `asyncio.gather`, merges and sorts the chunks by similarity score, and returns structured `List[RetrievedChunk]`. Base64 encoding/decoding is completely eliminated.
* **Key Touchpoints:**
  - `packages/vector-kb-core/src/vector_kb_core/chroma_retriever.py` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/embeddings.py` `[NEW]`
  - `main/app/services/kb_query_service.py` `[MODIFY]` (delegate to `ChromaRetriever`)
* **Code Specification:**
  ```python
  # packages/vector-kb-core/src/vector_kb_core/chroma_retriever.py
  import asyncio
  from typing import List, Optional
  import chromadb
  from openai import AsyncOpenAI
  from .models import RetrievedChunk
  from .retriever import Retriever

  class ChromaRetriever(Retriever):
      def __init__(self, chroma_client: chromadb.ClientAPI, openai_client: AsyncOpenAI, embedding_model: str = "text-embedding-3-small"):
          self.chroma = chroma_client
          self.openai = openai_client
          self.embedding_model = embedding_model

      async def search(self, query: str, kb_ids: List[int], top_k: int = 4, score_threshold: Optional[float] = None, trace_id: Optional[str] = None) -> List[RetrievedChunk]:
          emb_resp = await self.openai.embeddings.create(input=[query], model=self.embedding_model)
          query_vector = emb_resp.data[0].embedding

          tasks = [self._search_kb(kb_id, query_vector, top_k) for kb_id in kb_ids]
          results_nested = await asyncio.gather(*tasks, return_exceptions=True)

          all_chunks: List[RetrievedChunk] = []
          for r in results_nested:
              if isinstance(r, list):
                  all_chunks.extend(r)

          all_chunks.sort(key=lambda x: x.score, reverse=True)
          if score_threshold is not None:
              all_chunks = [c for c in all_chunks if c.score >= score_threshold]
          return all_chunks[:top_k]
  ```
* **User Acceptance Criteria (UAC):**
  - Vector similarity search latency drops to sub-100ms since no HTTP hops or serialization cycles occur.
* **Technical Acceptance Criteria (TAC):**
  - Directly queries Chroma collections named `kb_{id}`.
  - Returns raw Python dataclasses with chunk content, metadata, score, and document IDs.
  - Gracefully handles missing collections without raising uncaught exceptions.

---

#### `TASK-VKB-103`: Unit & Integration Test Suite for `vector-kb-core`
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**
  Implement unit tests with `pytest` and mock ChromaDB/OpenAI clients to verify similarity score sorting, multi-KB result merging, top-k truncation, and threshold filtering.
* **Key Touchpoints:**
  - `packages/vector-kb-core/tests/test_retriever.py` `[NEW]`
  - `packages/vector-kb-core/tests/conftest.py` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - CI pipeline can test the retrieval library in isolation without starting external services.
* **Technical Acceptance Criteria (TAC):**
  - Test suite passes with `pytest packages/vector-kb-core/tests`.
  - Covers edge cases: empty KB list, non-existent collection, empty search results, single KB vs multi-KB queries.

---

### Phase 2: `akvo-rag-core` Package Extraction & Workflow Streamlining

#### `TASK-RAG-201`: Scaffold `akvo-rag-core` Package & LangGraph Engine
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `3.5 hours`
* **Detailed Description:**
  Extract the LangGraph state machine from `backend/app/services/query_answering_workflow.py` into a reusable library `akvo-rag-core`. The workflow engine is stateless and accepts history, prompt configuration, and a `Retriever` instance per invocation.
* **Key Touchpoints:**
  - `packages/akvo-rag-core/pyproject.toml` `[NEW]`
  - `packages/akvo-rag-core/README.md` `[NEW]`
  - `packages/akvo-rag-core/src/akvo_rag_core/models.py` `[NEW]`
  - `packages/akvo-rag-core/src/akvo_rag_core/engine.py` `[NEW]`
  - `packages/akvo-rag-core/src/akvo_rag_core/workflow.py` `[NEW]`
  - `packages/akvo-rag-core/src/akvo_rag_core/logging.py` `[NEW]`
* **Code Specification:**
  ```python
  # packages/akvo-rag-core/src/akvo_rag_core/models.py
  from pydantic import BaseModel, Field
  from typing import List, Optional

  class ChatMessage(BaseModel):
      role: str # "user" | "assistant" | "system"
      content: str

  class RAGRequest(BaseModel):
      query: str
      history: List[ChatMessage] = Field(default_factory=list)
      kb_ids: List[int]
      system_prompt: Optional[str] = None
      top_k: int = 4
      trace_id: Optional[str] = None

  class Citation(BaseModel):
      source: str
      page: Optional[int] = None
      section: Optional[str] = None
      authority: Optional[str] = None
      version: Optional[str] = None
      text_snippet: str

  class RAGResponse(BaseModel):
      answer: str
      citations: List[Citation] = Field(default_factory=list)
      intent: str
      trace_id: Optional[str] = None
      grounded: bool
  ```
* **User Acceptance Criteria (UAC):**
  - Host applications can execute a complete RAG question-answering workflow in-process via `await rag_engine.run(request)`.
  - If ChromaDB or LLM calls fail or time out, the engine gracefully degrades and returns a safe fallback message without crashing the host application or WhatsApp webhook.
* **Technical Acceptance Criteria (TAC):**
  - `akvo-rag-core` does not import or depend on SQLAlchemy, MySQL, Celery, or RabbitMQ.
  - Preserves citation discipline (citations stripped if `[citation:N]` is omitted by the LLM).
  - Emits structured JSON event logs (`rag.query.received`, `rag.retrieval.complete`, `rag.generation.complete`) with `trace_id` and timing metrics.
  - Implements fallback circuit breaker: catches downstream connection/timeout exceptions, logs an `ERROR` event with `trace_id`, and returns `RAGResponse(answer="We are temporarily unable to access the reference manuals. Please try again shortly.", grounded=False)`.

---

#### `TASK-RAG-202`: Direct `Retriever` Integration (Delete FastMCP Client & Update Legacy Tests)
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `2.5 hours`
* **Detailed Description:**
  Replace `FastMCPClientService` and streaming HTTP transport with direct in-memory calls to `vector_kb_core.Retriever` inside the `retrieve_node` of the LangGraph state machine. Delete obsolete network transport code. Update existing unit tests in `backend/tests/` that mocked `FastMCPClientService` to instead assert against the direct `Retriever` interface.
* **Key Touchpoints:**
  - `packages/akvo-rag-core/src/akvo_rag_core/nodes/retrieve.py` `[NEW]`
  - `backend/mcp_clients/fastmcp_client_service.py` `[DELETE]`
  - `backend/mcp_clients/rest_mcp_client_service.py` `[DELETE]`
  - `backend/tests/unit/test_retrieval_service.py` `[MODIFY]`
* **Code Specification:**
  ```python
  # packages/akvo-rag-core/src/akvo_rag_core/nodes/retrieve.py
  from typing import Any, Dict
  from vector_kb_core import Retriever

  async def retrieve_node(state: Dict[str, Any], retriever: Retriever) -> Dict[str, Any]:
      query = state.get("contextualized_query") or state["query"]
      kb_ids = state.get("kb_ids", [])
      top_k = state.get("top_k", 4)
      trace_id = state.get("trace_id")

      chunks = await retriever.search(query=query, kb_ids=kb_ids, top_k=top_k, trace_id=trace_id)
      return {"retrieved_chunks": chunks, "context_text": "\n\n".join(c.content for c in chunks)}
  ```
* **User Acceptance Criteria (UAC):**
  - Completely eliminates network timeouts and streaming HTTP disconnections during retrieval.
* **Technical Acceptance Criteria (TAC):**
  - FastMCP transport code is deleted.
  - Direct retrieval node passes `List[RetrievedChunk]` straight to the generation node.
  - All existing unit tests pass (`backend/test-unit.sh`) with updated mock interfaces.

---

#### `TASK-RAG-203`: Short-Circuit `ScopingAgent` on Default RAG Path
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**
  In the legacy system, `ScopingAgent` made an extra LLM round trip to pick a tool, which failed schema validation and fell back to `query_knowledge_base`. This task removes `scoping_node` from the primary path and transitions directly from `contextualize` to `retrieve`.
* **Key Touchpoints:**
  - `packages/akvo-rag-core/src/akvo_rag_core/workflow.py` `[MODIFY]`
  - `backend/app/services/scoping_agent.py` `[MODIFY]` (bypass for standard path)
* **Code Specification:**
  ```python
  # Workflow transitions in LangGraph:
  workflow.add_node("classify_intent", classify_intent_node)
  workflow.add_node("contextualize", contextualize_node)
  workflow.add_node("retrieve", retrieve_node)
  workflow.add_node("generate", generate_node)
  workflow.add_node("filter_citations", filter_citations_node)

  workflow.add_edge("classify_intent", "contextualize")
  workflow.add_edge("contextualize", "retrieve")
  workflow.add_edge("retrieve", "generate")
  workflow.add_edge("generate", "filter_citations")
  ```
* **User Acceptance Criteria (UAC):**
  - Question response time drops by 1.5s–3.0s, and OpenAI cost per query decreases by 1 model call (~25%).
* **Technical Acceptance Criteria (TAC):**
  - Trace logs confirm that answering a knowledge question executes exactly 3 LLM calls (Intent -> Contextualize -> Generate) instead of 4.

---

#### `TASK-RAG-204`: Remove Startup MCP Discovery & Purge Domain Leaks
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `1.5 hours`
* **Detailed Description:**
  1. Remove blocking startup network discovery scripts from `backend/entrypoint.sh` and delete `mcp_discovery_manager.py` and `mcp_discovery.json`.
  2. In `chat_job_service.py:52`, remove `if role in ["farmer", "extension_officer"]: role = "user"` and replace with generic role mapping.
  3. Remove crop-calendar tool definitions from `mcp_servers_config.py`.
* **Key Touchpoints:**
  - `backend/entrypoint.sh` `[MODIFY]`
  - `backend/mcp_clients/mcp_discovery_manager.py` `[DELETE]`
  - `backend/app/services/chat_job_service.py` `[MODIFY]`
  - `backend/mcp_clients/mcp_servers_config.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Container starts in under 2 seconds.
  - Platform codebase contains zero agricultural assumptions and is ready for WASH, Health, etc.
* **Technical Acceptance Criteria (TAC):**
  - Grep for `farmer`, `crop_calendar`, `extension_officer` in `akvo-rag/backend/app/` returns zero hits.

---

#### `TASK-RAG-205`: Multi-Tier Prompt Resolver & Prompt Reactivity Integration Test
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `3.0 hours`
* **Detailed Description:**
  1. Implement a flexible `PromptResolver` that composes system prompts using a three-tier hierarchy:
     - **Platform Base:** Citation discipline, ungrounded fallback format (`"Information is missing on..."`).
     - **Sector Base:** Sector-wide rules (e.g. WASH public-health safety gates or Agronomy advice guidelines).
     - **Partner Overlay:** Partner name, tone, custom local instructions.
  2. Implement an automated integration test (`test_prompt_reactivity.py`) verifying that updating/activating a prompt version via API immediately reflects in subsequent chat responses in Mode 1 without server restarts.
* **Key Touchpoints:**
  - `packages/akvo-rag-core/src/akvo_rag_core/prompts.py` `[NEW]`
  - `backend/app/services/prompt_service.py` `[MODIFY]`
  - `backend/tests/integration/test_prompt_reactivity.py` `[NEW]`
* **Code Specification:**
  ```python
  # packages/akvo-rag-core/src/akvo_rag_core/prompts.py
  class PromptResolver:
      DEFAULT_BASE = (
          "You are a helpful and truthful assistant. Answer based ONLY on the provided context.\n"
          "Strictly use [citation:N] markers. If context lacks sufficient information, "
          "state clearly 'Information is missing on...' and do not speculate."
      )

      @classmethod
      def compose(cls, system_base: Optional[str] = None, sector_overlay: Optional[str] = None, partner_overlay: Optional[str] = None) -> str:
          parts = [system_base or cls.DEFAULT_BASE]
          if sector_overlay:
              parts.append(f"### Sector Guidelines:\n{sector_overlay}")
          if partner_overlay:
              parts.append(f"### Partner Specific Rules:\n{partner_overlay}")
          return "\n\n".join(parts)
  ```
* **User Acceptance Criteria (UAC):**
  - Sector modules (e.g. WASH) can inject strict safety constraints without changing platform code.
  - Changes to system prompts in the Next.js UI / API immediately alter chat playground responses in real time.
* **Technical Acceptance Criteria (TAC):**
  - Unit tests verify prompt hierarchy, variable interpolation, and strict citation rule preservation.
  - `backend/tests/integration/test_prompt_reactivity.py` passes: updates a prompt definition version, sends a chat request, and asserts output conforms to the updated instruction.

---

#### `TASK-RAG-206`: PostgreSQL Database Adapter & Unified Data Migration Tools (MySQL + Vector-KB PG)
* **Repository:** `akvo-rag`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**
  1. Update `backend/app/database/` and Alembic configuration in `akvo-rag` to natively connect to PostgreSQL 17 via `asyncpg` (`postgresql+asyncpg://...`), phasing out MySQL 8 dialect dependencies.
  2. Implement an automated, idempotent Python CLI migration script `backend/app/scripts/migrate_legacy_to_postgres.py` that reads:
     - Akvo-RAG legacy records from MySQL (`users`, `apps`, `api_keys`, `prompt_definitions`, `prompt_versions`, `system_settings`, `chats`, `chat_messages`).
     - Vector-KB legacy records from legacy PostgreSQL (`knowledge_bases`, `documents`, `document_chunks`).
     - Batch-inserts both cleanly into the consolidated PostgreSQL 17 database.
  3. Implement a fast native bash helper `backend/app/scripts/migrate_vector_kb_postgres.sh` utilizing native `pg_dump` and `psql` to stream vector-kb metadata across database instances in $< 5$ seconds.
  4. Enforce automated data integrity checks: assert 100% row count parity and exact primary key ID retention (`kb_id=1`, `kb_id=2`), and verify that user password hashes (bcrypt) and API keys authenticate cleanly against PostgreSQL.
  5. Ensure Standalone Product Mode (Mode 1) boots against PostgreSQL with zero MySQL dependencies.
* **Key Touchpoints:**
  - `backend/app/database/session.py` `[MODIFY]`
  - `backend/app/scripts/migrate_legacy_to_postgres.py` `[NEW]`
  - `backend/app/scripts/migrate_vector_kb_postgres.sh` `[NEW]`
  - `backend/alembic/env.py` `[MODIFY]`
  - `docker-compose.dev.yml` & `docker-compose.yml` `[MODIFY]`
* **Code Specification:**
  ```python
  # backend/app/scripts/migrate_legacy_to_postgres.py
  import asyncio
  import logging
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
  from sqlalchemy import select
  from app.models.user import User
  from app.models.app import App
  from app.models.api_key import ApiKey
  from app.models.prompt import PromptDefinition, PromptVersion

  AKVO_RAG_MODELS = [User, App, ApiKey, PromptDefinition, PromptVersion]

  async def migrate_akvo_rag_mysql(mysql_url: str, pg_url: str):
      mysql_engine = create_async_engine(mysql_url)
      pg_engine = create_async_engine(pg_url)

      async with AsyncSession(mysql_engine) as mysql_session, AsyncSession(pg_engine) as pg_session:
          for model in AKVO_RAG_MODELS:
              res = await mysql_session.execute(select(model))
              records = res.scalars().all()
              logging.info(f"Extracting {len(records)} rows from {model.__tablename__} (MySQL)...")
              for r in records:
                  await pg_session.merge(r)
              await pg_session.commit()
              pg_count = (await pg_session.execute(select(model))).scalars().all()
              assert len(records) == len(pg_count), f"Mismatch in {model.__tablename__}: {len(records)} vs {len(pg_count)}"
              logging.info(f"Successfully migrated {model.__tablename__}: {len(pg_count)} rows (100% match).")
  ```
  ```bash
  #!/usr/bin/env bash
  # backend/app/scripts/migrate_vector_kb_postgres.sh
  set -e
  echo "Streaming Vector-KB tables from legacy PostgreSQL to consolidated PostgreSQL 17..."
  pg_dump -h "${LEGACY_VKB_PG_HOST:-localhost}" -U "${LEGACY_VKB_PG_USER:-postgres}" -d "${LEGACY_VKB_PG_DB:-vector_kb}" \
    -t knowledge_bases -t documents -t document_chunks --data-only \
    | psql -h "${CONSOLIDATED_PG_HOST:-localhost}" -U "${CONSOLIDATED_PG_USER:-postgres}" -d "${CONSOLIDATED_PG_DB:-akvo_rag}"
  echo "Vector-KB data migration completed successfully in < 5s."
  ```
* **User Acceptance Criteria (UAC):**
  - Existing user accounts log into the Next.js Web UI with their existing passwords on PostgreSQL.
  - All existing API keys and KB IDs (`kb_1`, `kb_2`) authenticate and link without re-issuance or re-indexing.
  - Standalone Akvo-RAG boots up with `docker compose -f docker-compose.dev.yml up` with zero MySQL or RabbitMQ containers.
* **Technical Acceptance Criteria (TAC):**
  - Migration script and bash tool execute in $< 10$ seconds on production datasets.
  - Row counts and primary key IDs across `users`, `apps`, `api_keys`, `prompts`, `knowledge_bases`, and `documents` match 100%.
  - User login (`POST /api/auth/login`) and API key auth pass against PostgreSQL.
  - Standalone `docker-compose.dev.yml` boots: `frontend`, `backend`, `ingestion-worker`, `postgres`, `redis`, `chromadb`, `minio`.

---

### Phase 3: Dedicated Ingestion Worker & Metadata Hardening

#### `TASK-VKB-301`: Add KB Embedding Model & Dimension Guard
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `2.5 hours`
* **Detailed Description:**
  Add `embedding_model` (e.g. `text-embedding-3-small`) and `dimension` (e.g. `1536`) to the `knowledge_bases` database table and Chroma metadata. Enforce model verification at retrieval and ingestion time.
* **Key Touchpoints:**
  - `main/app/models/knowledge_base.py` `[MODIFY]`
  - `alembic/versions/xxxx_add_embedding_metadata.py` `[NEW]`
  - `packages/vector-kb-core/src/vector_kb_core/chroma_retriever.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Admins are alerted immediately if an environment variable change mismatches existing vector collections.
* **Technical Acceptance Criteria (TAC):**
  - Attempting to query or ingest with an incompatible embedding model raises `EmbeddingModelMismatchError` before running vector search.

---

#### `TASK-VKB-302`: Enrich Documents & Chunks with Public-Sector Metadata
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**
  Extend `Document` and `DocumentChunk` models to capture public-sector metadata (`doc_version`, `issuing_authority`, `effective_date`, `doc_type`, `jurisdiction`). Ensure chunk metadata stores these fields in ChromaDB and returns them in `RetrievedChunk.metadata`.
* **Key Touchpoints:**
  - `main/app/models/document.py` `[MODIFY]`
  - `main/app/models/document_chunk.py` `[MODIFY]`
  - `main/app/services/document_processor.py` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Citations cite specific manual editions and authorities (e.g. *"National Water Standard 2024, Page 12, Ministry of Water"*).
* **Technical Acceptance Criteria (TAC):**
  - Document chunker attaches document-level metadata to all Chroma chunk records.
  - Search results include metadata in citation objects.

---

#### `TASK-VKB-303`: Package Dedicated Background Ingestion Worker & Upload Task Contract
* **Repository:** `vector-knowledge-base-mcp-server`
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**
  1. Package the document processing service into a dedicated background Celery worker container (`ingestion-worker`). It listens to the Redis ingestion queue, downloads raw PDFs from MinIO, parses pages/OCR, writes chunk records to PostgreSQL 17, and creates Chroma vectors using `vector-kb-core`.
  2. Define the standard Celery upload task contract `process_document(document_id: str, kb_id: int)` published by Admin APIs in both Standalone Akvo-RAG (Mode 1) and Partner Host Apps (Mode 2).
* **Key Touchpoints:**
  - `Dockerfile.ingestion` `[NEW]`
  - `main/app/tasks/document_tasks.py` `[MODIFY]`
  - `docker-compose.yml` `[MODIFY]`
* **User Acceptance Criteria (UAC):**
  - Large document uploads process asynchronously in the background without degrading conversational query latency.
  - Document upload status in Web UI updates from `PROCESSING` $\rightarrow$ `INDEXED` upon task completion.
* **Technical Acceptance Criteria (TAC):**
  - Ingestion worker runs independently as a Docker container consuming from Redis.
  - Container entrypoint script executes `alembic upgrade head` on startup to ensure KB & document tables exist in PostgreSQL.
  - Task `process_document` catches parsing errors and updates document `status="FAILED"` with `error_message` in PostgreSQL.

---

### Phase 4: Host App In-Process Integration & Packaging

#### `TASK-INT-401`: Build `EmbeddedAIService` Adapter in Host Application
* **Repository:** Host App (`agriconnect` / new `washconnect`)
* **Vibe-Coding Estimate:** `3.5 hours`
* **Detailed Description:**
  Create `EmbeddedAIService` in the host application that satisfies the AI service interface by importing `akvo-rag-core` and `vector-kb-core` directly. In `routers/whatsapp.py`, replace the legacy `create_chat_job(...)` HTTP callback pattern with direct in-memory invocation.
* **Key Touchpoints:**
  - `host_app/backend/services/embedded_ai_service.py` `[NEW]`
  - `host_app/backend/routers/whatsapp.py` `[MODIFY]`
  - `host_app/backend/requirements.txt` `[MODIFY]`
* **Code Specification:**
  ```python
  # host_app/backend/requirements.txt (Standard Git URI installation)
  # akvo-rag-core @ git+https://github.com/akvo/akvo-rag.git@v1.0.0#subdirectory=packages/akvo-rag-core
  # vector-kb-core @ git+https://github.com/akvo/vector-knowledge-base-mcp-server.git@v1.0.0#subdirectory=packages/vector-kb-core

  # host_app/backend/services/embedded_ai_service.py
  from akvo_rag_core import RAGWorkflowEngine, RAGRequest, ChatMessage, PromptResolver
  from vector_kb_core import ChromaRetriever
  import chromadb
  from openai import AsyncOpenAI

  class EmbeddedAIService:
      def __init__(self, chroma_url: str, openai_api_key: str):
          self.chroma_client = chromadb.HttpClient(host=chroma_url.split(":")[0], port=int(chroma_url.split(":")[1]))
          self.openai_client = AsyncOpenAI(api_key=openai_api_key)
          self.retriever = ChromaRetriever(self.chroma_client, self.openai_client)
          self.engine = RAGWorkflowEngine(openai_client=self.openai_client)

      async def answer_question(self, query: str, history: list, kb_ids: list, sector_overlay: str = "", partner_overlay: str = "", trace_id: str = None) -> dict:
          system_prompt = PromptResolver.compose(sector_overlay=sector_overlay, partner_overlay=partner_overlay)
          req = RAGRequest(
              query=query,
              history=[ChatMessage(role=m["role"], content=m["content"]) for m in history],
              kb_ids=kb_ids,
              system_prompt=system_prompt,
              trace_id=trace_id
          )
          result = await self.engine.run(request=req, retriever=self.retriever)
          return {
              "answer": result.answer,
              "citations": [c.model_dump() for c in result.citations],
              "grounded": result.grounded
          }
  ```
* **User Acceptance Criteria (UAC):**
  - Incoming WhatsApp questions are answered directly in the conversation pipeline.
  - The 3 silent answer-loss paths (failed background callbacks) are eliminated.
* **Technical Acceptance Criteria (TAC):**
  - Zero network calls to `POST /api/jobs` or `POST /api/callback/ai`.
  - Packages install cleanly in host Docker image via `requirements.txt` Git URL or wheel.
  - Question answering executes end-to-end in-memory.

---

#### `TASK-INT-402`: Unified Single-Namespace Docker Compose Setup
* **Repository:** Root Workspace / Manifests
* **Vibe-Coding Estimate:** `2.0 hours`
* **Detailed Description:**
  Provide a single, streamlined `docker-compose.yml` for local development and single-namespace Kubernetes manifests containing:
  1. `app`: Host app (FastAPI + embedded RAG/Vector packages + Next.js frontend)
  2. `app-worker`: Host Celery worker (outbound WhatsApp messages and retries)
  3. `ingestion-worker`: Background document processing worker
  4. Datastores: PostgreSQL, Redis, ChromaDB, MinIO.
* **Key Touchpoints:**
  - `docker-compose.yml` `[MODIFY]`
  - `.env.example` `[NEW]`
  - `k8s/partner-namespace/` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Developers can run the entire platform locally with `docker compose up -d`.
* **Technical Acceptance Criteria (TAC):**
  - Stack boots in under 15 seconds.
  - Zero MySQL and zero RabbitMQ containers required.

---

#### `TASK-QA-501`: Golden Set Evaluation, Legacy Test Gate & CI Pipeline
* **Repository:** `akvo-rag/backend`
* **Vibe-Coding Estimate:** `3.5 hours`
* **Detailed Description:**
  1. **Legacy Test Baseline & Regression Gate:** Run and maintain the full existing test suite (`backend/test-unit.sh`, `backend/test.sh`). Ensure all existing unit and endpoint tests continue passing without regression after removing FastMCP and refactoring to the direct `Retriever` interface.
  2. **Golden Dataset Accuracy Benchmark:** Run the automated headless evaluation harness (`headless_evaluation.py`) against a golden benchmark dataset of Agronomy and WASH queries to measure faithfulness, answer relevancy, and latency.
  3. **CI Pipeline Automation:** Configure GitHub Actions to execute both the legacy test suite and golden benchmark in CI.
* **Key Touchpoints:**
  - `backend/tests/unit/` `[VERIFY GREEN]`
  - `backend/RAG_evaluation/headless_evaluation.py` `[MODIFY]`
  - `backend/RAG_evaluation/datasets/golden_benchmark.json` `[NEW]`
  - `.github/workflows/rag_evaluation.yml` `[NEW]`
* **User Acceptance Criteria (UAC):**
  - Automated CI verifies that all existing unit/endpoint tests pass and the in-process engine produces identical or superior answer quality compared to the legacy distributed architecture.
* **Technical Acceptance Criteria (TAC):**
  - All existing unit tests pass cleanly: `pytest backend/tests/unit -v`.
  - Faithfulness score $\ge 0.85$.
  - Answer relevancy score $\ge 0.85$.
  - Zero ungrounded answers produce fake citations.
  - Automated CI workflow runs both `pytest tests/unit` and `python -m RAG_evaluation.run_evaluation`.

---

## 6. Database Communication & Data Architecture in Option C

To support in-process execution without architectural bottlenecks, the data architecture separates the system into two distinct operational paths: **Live Retrieval** and **Document Ingestion**.

### 6.1 Dual-Path Operational Model

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OPTION C DATA ARCHITECTURE                             │
│                                                                                          │
│   PATH 1: LIVE RETRIEVAL / QUERY PATH                    PATH 2: DOCUMENT INGESTION PATH │
│   (Synchronous WhatsApp Question Answering)              (Asynchronous Background Admin) │
│                                                                                          │
│   WhatsApp Webhook                                       Admin PDF Upload                │
│          │                                                      │                        │
│          ▼                                                      ▼                        │
│   Host App Pipeline                                      Host App API                    │
│          │                                                      ├── Save PDF ──► MinIO   │
│          ▼                                                      ├── Create DB ─► Postgres│
│   akvo-rag-core (In-Process)                                    └── Task ─────► Redis    │
│          │                                                                         │     │
│          ▼                                                                         ▼     │
│   vector-kb-core (In-Process)                                    Ingestion Worker        │
│          │                                                              ├── Read PDF     │
│          │ (Direct In-Memory Search)                                    ├── Chunker      │
│          ▼                                                              ├── Store Chunks ─► Postgres
│   ChromaDB Service                                                      └── Embed & Index ─► Chroma
│   - Vectors (1536-dim)                                                                   │
│   - Text Content & Metadata                                                              │
│   * ZERO PostgreSQL queries during search                                                │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 The Live Query Path (In-Process Direct Retrieval)
* **ChromaDB Stores Chunk Text & Metadata:** When chunks are ingested, ChromaDB stores the embedding vector, raw chunk text, and all citation metadata (`page`, `source`, `doc_version`, `issuing_authority`).
* **Zero Relational Database Latency:** When `vector-kb-core` executes `ChromaRetriever.search()`, it queries ChromaDB directly (sub-100ms). It does **not** query PostgreSQL on the live conversation path, keeping query latency minimal.

### 6.3 The Ingestion & Management Path (Consolidated PostgreSQL)
* **Single PostgreSQL 17 Database:** Instead of 3 databases across 2 engines (MySQL 8 for Akvo RAG, PostgreSQL for Vector KB, PostgreSQL for AgriConnect), all relational metadata is stored in a **single PostgreSQL database** in the partner namespace.
* **Ingestion Worker:** A standalone background container (from `vector-knowledge-base-mcp-server`) consumes upload tasks from Redis, parses PDFs/docs, writes chunk records to PostgreSQL, computes embeddings, and writes vectors to ChromaDB collections.

### 6.4 Component Connectivity Matrix

| Component | Packaging / Execution | PostgreSQL 17 | ChromaDB | MinIO | Redis Broker | Purpose |
|---|---|---|---|---|---|---|
| **Host Web App** (FastAPI) | In-Process (`akvo-rag-core` + `vector-kb-core`) | **Yes** (Conversations, Prompts, KB Registry) | **Yes** (Direct read queries via `ChromaRetriever`) | **No** (Direct upload stream or presigned URLs) | **Yes** (Publishes ingestion tasks) | WhatsApp webhook, chat turn execution, Admin API |
| **App Worker** (Celery) | Container (`agriconnect`) | **Yes** (Tickets, customer profiles) | **No** | **No** | **Yes** (Worker consumer) | Outbound WhatsApp sends, retries, broadcasts |
| **Ingestion Worker** (Celery) | Container (`vector-kb-server`) | **Yes** (Document and chunk records) | **Yes** (Writes embeddings to collections) | **Yes** (Stores and reads raw PDF/Docx files) | **Yes** (Ingestion consumer) | Long-running PDF parsing, OCR, chunk embedding |

### 6.5 Database Schema Ownership & Migration Lifecycle

A common architectural question when adopting in-process libraries is: *Where do the database migrations live, and does the host application need to manage the RAG/vector schemas?*

#### 1. Pure & Stateless Python Libraries
The core libraries (**`akvo-rag-core`** and **`vector-kb-core`**) are deliberately designed as **pure computation and retrieval packages** with zero ORM, SQLAlchemy, or Alembic dependencies.
- `vector-kb-core` communicates directly with ChromaDB in-memory for vector search.
- `akvo-rag-core` executes the LangGraph workflow and prompt resolution in-memory.
- This ensures host applications (e.g. `washconnect`) experience zero SQL migration bloat from the RAG engine.

#### 2. Repository Schema Boundaries

| Repository | Component | Database Responsibility & Migrations |
|---|---|---|
| **`vector-knowledge-base-mcp-server`** | **Ingestion Worker** (Background Container) | **Owns KB & Ingestion Schemas:** Manages `knowledge_bases`, `documents`, and `document_chunks` tables in `alembic/versions/`. |
| **`akvo-rag`** | **Standalone Web App** (Mode 1 UI & API) | **Owns Prompt & Standalone Auth Schemas:** Manages prompt versioning, API keys, and playground sessions for the standalone developer UI. |
| **Host Application** (`agriconnect` / `washconnect`) | **Host Web App & Worker** (Mode 2 Embedded) | **Owns Host Domain Schemas Only:** Manages WhatsApp conversations, tickets, farmer/community profiles, and domain workflows in its own `alembic/versions/`. |

#### 3. Partner Namespace Deployment Lifecycle

When deploying a new host app namespace (e.g. `washconnect`):

```text
┌────────────────────────────────────────────────────────────────────────┐
│ PARTNER NAMESPACE (e.g. washconnect)                                   │
│                                                                        │
│  ┌──────────────────────────────┐     ┌─────────────────────────────┐  │
│  │ 1. Host Web App (WASHConnect)│     │ 2. Ingestion Worker         │  │
│  │                              │     │    (from vector-kb repo)    │  │
│  │ • Host Migrations:           │     │                             │  │
│  │   - conversations, users     │     │ • KB Migrations:            │  │
│  │ • Python Imports:            │     │   - knowledge_bases         │  │
│  │   - akvo-rag-core            │     │   - documents               │  │
│  │   - vector-kb-core           │     │   - document_chunks         │  │
│  └──────────────┬───────────────┘     └──────────────┬──────────────┘  │
│                 │                                    │                 │
│                 ▼                                    ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Single PostgreSQL 17 Database (All tables created automatically) │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Ingestion Worker Startup:** The `ingestion-worker` container runs its entrypoint with `alembic upgrade head`, creating the `knowledge_bases`, `documents`, and `document_chunks` tables in the single PostgreSQL instance.
2. **Host App Startup:** The host application runs its own migrations for conversations/users, then imports `akvo-rag-core` and `vector-kb-core` in-process.
3. **No Cross-Repo Migration Leakage:**
   - Host apps do **not** need to copy or maintain document chunking database schemas.
   - `akvo-rag` does **not** need to absorb the document chunk migrations from `vector-kb`.

### 6.6 Structured Logging & Observability Specification

In the legacy architecture, debugging a single farmer query failure required cross-referencing logs across 3 namespaces, HTTP headers, and Celery task IDs.

In Option C, because the entire query-answering workflow runs in-process, end-to-end observability is achieved through **Unified Structured JSON Logging** bound to a single `trace_id`.

#### 1. Standard JSON Log Schema
All core packages (`akvo-rag-core`, `vector-kb-core`) emit JSON logs via standard Python `logging`:

```json
{
  "timestamp": "2026-09-01T09:30:00.123Z",
  "level": "INFO",
  "logger": "akvo_rag_core.workflow",
  "trace_id": "8f3b6c2a-9e1d-4f0a-b2c3-d4e5f6a7b8c9",
  "event": "rag.retrieval.complete",
  "query_preview": "How to manage avocado root rot?",
  "kb_ids": [1, 2],
  "top_k": 4,
  "chunks_found": 4,
  "top_score": 0.884,
  "latency_ms": 64.2
}
```

#### 2. Workflow Event Lifecycle

| Event Name | Emitter | Key Logged Attributes | Purpose |
|---|---|---|---|
| `rag.query.received` | `akvo-rag-core` | `trace_id`, `query`, `history_length`, `kb_ids` | Records incoming query entry point |
| `rag.intent.classified` | `akvo-rag-core` | `trace_id`, `intent`, `latency_ms` | Verifies intent router decision (knowledge vs conversational) |
| `rag.contextualize.complete` | `akvo-rag-core` | `trace_id`, `rewritten_query`, `latency_ms` | Shows rewritten query for multi-turn conversations |
| `vector_kb.search.start` | `vector-kb-core` | `trace_id`, `kb_ids`, `top_k` | Marks start of ChromaDB similarity search |
| `vector_kb.search.complete` | `vector-kb-core` | `trace_id`, `chunks_found`, `top_score`, `latency_ms` | Direct vector search performance metric |
| `rag.generation.complete` | `akvo-rag-core` | `trace_id`, `prompt_tokens`, `completion_tokens`, `latency_ms` | LLM token usage and latency tracking |
| `rag.citations.filtered` | `akvo-rag-core` | `trace_id`, `raw_citations`, `valid_citations`, `grounded` | Enforces citation validity audit trail |

#### 3. Error Logging & Triage
When an exception occurs (e.g. ChromaDB connection failure, OpenAI rate limit, ungrounded query), the logger emits an `ERROR` event containing `trace_id`, `error_type`, `error_message`, and `stack_trace`. Developers can query `trace_id: "<id>"` in CloudWatch/Loki to inspect the entire execution graph in a single view.

---

## 7. Impact & Migration Strategy for Current Running Systems

This section defines what happens to the existing running deployments (`agriconnect2-namespace`, `agriconnect-rag-namespace`, `akvo-rag-namespace`, and `kb-mcp-server-namespace`) during and after the rollout of Option C.

### 7.1 What Happens to Existing Production Systems?

```mermaid
flowchart TB
    subgraph CurrentTopology["Current Legacy Production (3 Namespaces, ~20 Workloads)"]
        direction TB
        NS1["agriconnect2-namespace<br/>(App, Worker, Beat, Redis, Postgres 17, Media)"]
        NS2["agriconnect-rag-namespace<br/>(RAG Backend, Celery, Beat, MySQL 8, RabbitMQ)"]
        NS3["kb-mcp-server-namespace<br/>(KB REST/MCP, Celery, Postgres, RabbitMQ, Chroma, MinIO)"]
        NS1 <-->|"HTTP & Unauthenticated Callbacks"| NS2
        NS2 <-->|"FastMCP over HTTP"| NS3
    end

    subgraph TransitionPhase["Step-by-Step Transition & Coexistence"]
        direction TB
        C1["1. Database Migration: Consolidate MySQL prompts to PostgreSQL"]
        C2["2. Dual-Mode Coexistence: RAG operates in-process while legacy APIs stay live"]
        C3["3. Traffic Cutover: Point WhatsApp webhook to In-Process Pipeline"]
        C4["4. Decommissioning: Terminate NS2, RabbitMQ, MySQL, and MCP glue"]
    end

    subgraph TargetTopology["Option C Target Production (1 Namespace, 3 Workloads)"]
        direction TB
        TNS["partner-namespace<br/>• Assistant Web App (In-Process RAG + Retriever)<br/>• App Celery Worker<br/>• Ingestion Celery Worker<br/>• Single PostgreSQL 17 + Redis + ChromaDB + MinIO"]
    end

    CurrentTopology --> TransitionPhase
    TransitionPhase --> TargetTopology
```

### 7.2 Zero-Downtime Migration & Rollout Strategy

To guarantee that currently running production systems (both the Standalone Akvo-RAG Web UI and live WhatsApp partner instances) experience zero service interruption:

#### Step 1: Pre-Migration Validation in Isolation (Phases 1–3)
- All new packages (`vector-kb-core`, `akvo-rag-core`) and the `ingestion-worker` container are developed and tested against CI without touching live production pods.
- Existing Kubernetes deployments (`agriconnect2-namespace`, `agriconnect-rag-namespace`, `kb-mcp-server-namespace`) continue serving users normally.

#### Step 2: Database Initialization & Unified Legacy Data Migration (`TASK-RAG-206`)
- **Initialize Target Database:** Run `alembic upgrade head` on the target PostgreSQL 17 instance to instantiate clean schemas.
- **Run One-Click Migration CLI / Scripts:**
  - **Akvo-RAG MySQL Data:** Execute `python -m app.scripts.migrate_legacy_to_postgres` to batch-insert `users`, `apps`, `api_keys`, `prompt_definitions`, `prompt_versions`, `system_settings`, `chats`, and `chat_messages` from MySQL 8 to PostgreSQL 17 in $< 10$ seconds.
  - **Vector-KB PostgreSQL Data:** Execute `backend/app/scripts/migrate_vector_kb_postgres.sh` (or let the Python CLI execute it) to stream `knowledge_bases`, `documents`, and `document_chunks` into the consolidated PostgreSQL instance in $< 5$ seconds with 100% ID retention (`kb_id=1`, `kb_id=2`).
  - Automatically verifies 100% row count and ID parity across all tables.
- **Vector & Object Storage Continuity:** ChromaDB vector collections (`kb_{id}`) and MinIO files (`documents/`) remain untouched in their existing storage volumes—zero re-embedding or re-uploading required.

#### Step 3: Standalone Mode 1 Verification (Akvo-RAG Web UI)
- Boot the updated Standalone Akvo-RAG Web App connected to PostgreSQL 17.
- **Verification Gates:**
  1. Admins log in using their existing email & passwords (bcrypt hashes authenticate identically).
  2. Registered `apps` and `api_keys` authenticate against `/api/chat` and `/api/prompts`.
  3. Next.js Chat Playground queries existing ChromaDB collections in-process with sub-100ms response times.

#### Step 4: Traffic Cutover for Host Applications (Mode 2)
- In the host application (`agriconnect`), update the AI adapter configuration to `EMBEDDED_AI_SERVICE` (direct in-process `akvo-rag-core` + `vector-kb-core`).
- Incoming WhatsApp questions immediately execute in-memory with sub-second retrieval and zero external HTTP hops.

#### Step 5: Decommissioning Legacy Infrastructure
- Once traffic metrics confirm 100% of queries flow through the in-process pipeline, safely terminate legacy workloads:
  - Decommission duplicate `agriconnect-rag-namespace` pods.
  - Tear down legacy MySQL 8 container/Cloud SQL instance.
  - Decommission legacy RabbitMQ brokers and Celery Flower dashboards.

### 7.3 Infrastructure & Operational Impact Summary

| Resource / Dimension | Legacy Production (Today) | Option C Production (Target) | Impact / Net Benefit |
|---|---|---|---|
| **Kubernetes Namespaces per Partner** | 3 namespaces | **1 namespace** | Unified configuration & access control |
| **Workloads / Pods per Partner** | ~20 Deployments | **3 Deployments** (App, Worker, Ingestion) | **~70% reduction in cluster memory & CPU** |
| **Databases per Partner** | 3 instances (2 PostgreSQL, 1 MySQL) | **1 PostgreSQL 17 instance** | 1 backup routine, 1 migration toolchain |
| **Message Brokers per Partner** | 3 brokers (2 RabbitMQ, 1 Redis) | **1 Redis broker** | Reduced connection overhead & maintenance |
| **Internal Network Hops per Turn** | ~5 internal HTTP hops | **0 internal hops** | Sub-second latency, zero network dropouts |
| **Replication Time for New Partner** | 2–3 weeks of deployment & forking | **1–2 days (configuration only)** | Rapid deployment for WASH, Health, Agri |
| **Silent Answer-Loss Paths** | 3 failure paths (failed HTTP callbacks, unauthenticated endpoints, no retry) | **0 failure paths** | Reliable message delivery; WhatsApp answers never silently dropped |

---

## 8. Standalone Product & Dedicated Web UI Coexistence

A core requirement is ensuring that the **standalone Akvo-RAG web application, its Next.js Web UI, and developer tools continue to function completely**.

### 8.1 Dual-Deployment Modes (One Codebase, Two Shapes)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ AKVO RAG (The Repository)                                                              │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ akvo-rag-core (In-Process Engine Package)                                        │  │
│  │ - LangGraph workflow, PromptResolver, citation filtering, direct retriever hook  │  │
│  └────────────────────────┬─────────────────────────────────────────────────────────┘  │
│                           │                                                            │
│         ┌─────────────────┴────────────────────────┐                                   │
│         ▼                                          ▼                                   │
│  ┌─────────────────────────────────┐   ┌──────────────────────────────────────────┐    │
│  │ MODE 1: Standalone Web App      │   │ MODE 2: Embedded in Partner Apps         │    │
│  │ (With Full Dedicated Web UI)    │   │ (AgriConnect / WASHConnect)              │    │
│  │                                 │   │                                          │    │
│  │ • Next.js Web Dashboard         │   │ • No UI needed in partner namespace      │    │
│  │ • Chat Streaming & Playground   │   │ • Imported directly via Python package   │    │
│  │ • Prompt Version Management UI  │   │ • Runs inside WhatsApp webhook process   │    │
│  │ • User / App / API Key Auth     │   │                                          │    │
│  │ • Standalone REST /api/chat     │   │                                          │    │
│  │                                 │   │                                          │    │
│  │ * 100% Functional Standalone    │   │ * Zero extra microservices deployed      │    │
│  └─────────────────────────────────┘   └──────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Standalone Product Mode (Mode 1):**
   - The Next.js frontend (`frontend/`) and FastAPI backend (`backend/app/main.py`) remain fully operational.
   - The FastAPI backend delegates its internal RAG chat endpoints and WebSocket streaming to `akvo-rag-core`.
   - Admins and developers can run `docker compose -f docker-compose.dev.yml up` in `akvo-rag` to access the prompt versioning UI, knowledge base tester, chat playground, and app registry.
2. **Embedded Library Mode (Mode 2):**
   - Partner applications (such as AgriConnect or WASHConnect) import `akvo-rag-core` and `vector-kb-core` directly in memory.
   - This eliminates the need to deploy duplicate copies of the Web UI or separate MySQL/RabbitMQ infrastructure in partner namespaces.

### 8.2 Document Upload & KB Management in Standalone Mode 1

In Standalone Mode 1, the Akvo-RAG FastAPI backend manages Knowledge Base creation and document ingestion without requiring intermediate HTTP microservice hops:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ STANDALONE MODE 1: DOCUMENT UPLOAD & INGESTION ARCHITECTURE            │
│                                                                        │
│  Next.js Admin UI                                                      │
│        │                                                               │
│        ▼ (Multipart File Upload)                                       │
│  Akvo-RAG FastAPI Backend (POST /api/v1/knowledge-bases/{id}/documents)│
│        ├── 1. Save Raw File ────────► MinIO Bucket (documents/)        │
│        ├── 2. Create DB Record ─────► PostgreSQL 17 (status: PROCESSING)
│        └── 3. Enqueue Task ─────────► Redis Queue                      │
│                                            │                           │
│                                            ▼                           │
│                                 ingestion-worker Container             │
│                                 (from vector-kb codebase)              │
│                                            ├── Parse PDF & OCR         │
│                                            ├── Insert Chunks ──► Postgres
│                                            └── Compute Embeddings ──► Chroma
└────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Package Distribution & Installation for Partner Apps (`xxxconnect`)

Partner applications (`agriconnect`, `washconnect`, `healthconnect`) can install the in-process core packages via two standard mechanisms:

1. **Local Development Mode (Editable Install):**
   ```bash
   pip install -e /path/to/akvo-rag/packages/akvo-rag-core
   pip install -e /path/to/vector-knowledge-base-mcp-server/packages/vector-kb-core
   ```
2. **Production Container Mode (`requirements.txt` with Git URI / Tag):**
   ```text
   # Partner App requirements.txt
   akvo-rag-core @ git+https://github.com/akvo/akvo-rag.git@v1.0.0#subdirectory=packages/akvo-rag-core
   vector-kb-core @ git+https://github.com/akvo/vector-knowledge-base-mcp-server.git@v1.0.0#subdirectory=packages/vector-kb-core
   ```

### 8.4 1-Day Partner Onboarding Configuration Schema

To launch a brand new partner (e.g. `washconnect`) from scratch in under 1 day, the host application only needs to declare a single declarative configuration file:

```python
# washconnect/config/rag_config.py
from pydantic import BaseModel
from typing import List, Optional

class PartnerRAGConfig(BaseModel):
    sector: str = "wash"
    partner_name: str = "Kenya Water Trust"
    sector_overlay: str = (
        "Adhere strictly to the WHO Guidelines for Drinking-water Quality 4th Edition. "
        "Always recommend contacting a certified water technician for biological contamination."
    )
    partner_overlay: Optional[str] = "Service Region: Kisumu County. Hotlines: 0800-WATER."
    default_kb_ids: List[int] = [1, 2] # 1: Water Standards, 2: Pump Maintenance
    top_k: int = 4
    score_threshold: float = 0.65

# Instantiation in Host App:
# ai_service = EmbeddedAIService(config=PartnerRAGConfig())
```

### 8.5 Graceful Degradation & Timeout Circuit Breaker

To guarantee that WhatsApp webhooks or live conversations never hang or crash if downstream dependencies (ChromaDB or OpenAI) experience transient failure:

1. **Timeout Envelope:** In-process retrieval is bounded to a strict 5.0-second timeout; LLM generation is bounded to 15.0 seconds.
2. **Safe Fallback Response:** If an unhandled exception or timeout occurs:
   - Emits structured `ERROR` log containing `trace_id`, exception type, and stack trace.
   - Returns structured `RAGResponse`:
     ```python
     RAGResponse(
         answer="I am temporarily unable to access the knowledge manuals. Please try again shortly.",
         citations=[],
         grounded=False,
         intent="knowledge",
         trace_id=trace_id
     )
     ```
   - WhatsApp message sends cleanly to the user; conversation state remains uncorrupted.

### 8.6 Unified Environment Variables Contract (`.env.example`)

Both Standalone Mode 1 (`akvo-rag`) and Host Partner Mode 2 (`xxxconnect`) share the following unified configuration variables:

| Variable Name | Required By | Example / Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Mode 1 & Mode 2 | `sk-proj-...` | OpenAI API key for LLM generation and query embeddings |
| `DEFAULT_EMBEDDING_MODEL` | Mode 1 & Mode 2 | `text-embedding-3-small` | Embedding model for query vectors and document indexing |
| `DEFAULT_CHAT_MODEL` | Mode 1 & Mode 2 | `gpt-4o-mini` | Default LLM for intent classification and answer generation |
| `CHROMA_HOST` | Mode 1 & Mode 2 | `chromadb` | ChromaDB service hostname in the local/Kubernetes namespace |
| `CHROMA_PORT` | Mode 1 & Mode 2 | `8000` | ChromaDB HTTP service port |
| `MINIO_ENDPOINT` | Ingestion Worker & Mode 1 | `minio:9000` | MinIO / S3 object storage endpoint |
| `MINIO_ACCESS_KEY` | Ingestion Worker & Mode 1 | `minioadmin` | Object storage access key |
| `MINIO_SECRET_KEY` | Ingestion Worker & Mode 1 | `minioadmin` | Object storage secret key |
| `MINIO_BUCKET_NAME` | Ingestion Worker & Mode 1 | `documents` | S3 bucket name for raw uploaded PDF files |
| `DATABASE_URL` | Mode 1 & Ingestion Worker | `postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag` | PostgreSQL 17 async connection string |
| `REDIS_URL` | Mode 1, Mode 2 & Ingestion | `redis://redis:6379/0` | Redis broker URL for task queues and caching |

---

## 9. Scoping Agent: Current Removal Rationale & Future Improvements

### 9.1 Why `ScopingAgent` is Removed from the Default Path Today

In the legacy implementation (`backend/app/services/scoping_agent.py`), the `ScopingAgent` invoked an LLM to decide which MCP server and tool to call based on `mcp_discovery.json`.

#### The Flaws in the Legacy Design:
1. **Predetermined Outcome:** Partner applications (e.g. AgriConnect) already specify the target `knowledge_base_ids` explicitly in the request (`knowledge_base_ids: [1, 2]`), which instructed the scoping LLM: `"Use ONLY the provided knowledge_base_ids and do NOT choose new IDs"`.
2. **Broken Validation & Hardcoded Fallback:** The generated `mcp_discovery.json` file only listed weather tools and lacked `knowledge_bases_mcp`. Any suggestion to query the knowledge base failed schema validation in `_validate_input()`, triggering the hardcoded fallback:
   ```python
   fallback = {
       "server_name": "knowledge_bases_mcp",
       "tool_name": "query_knowledge_base",
       "input": {"query": query, "knowledge_base_ids": knowledge_base_ids}
   }
   ```
3. **Wasted Round Trip:** Every single farmer question paid for an extra LLM call (1.5s–3.0s latency and token cost) solely to arrive at a hardcoded fallback.

### 9.2 How KB & Tool Selection Works in Option C (Today)

Without `ScopingAgent`, the system determines scope through clean, deterministic application logic:
* **Knowledge Base Selection:** The host application / tenant configuration supplies the active `kb_ids` for the user's sector/scope (e.g., Avocado KB, Potato KB, National Water Standards). The in-process `ChromaRetriever` queries those collections concurrently and ranks chunks by cosine similarity.
* **Deterministic Tools vs Model Intuition:** High-stakes tools (such as water quality threshold comparisons, meter reading anomaly detection, and emergency pipe burst routing) are handled by deterministic rule engines (reusing the sourced rule pattern from `weather_advisory_service.py`) in the conversation pipeline rather than relying on ungrounded model judgment.

---

### 9.3 Future Improvements Roadmap for Dynamic Tool & KB Routing

When the platform expands to support multiple heterogeneous external tool servers (e.g. live weather APIs, government MIS/ERP systems, IoT sensors) or 20+ diverse knowledge bases, the following improvements can be introduced:

```mermaid
flowchart TD
    subgraph FutureRouting["Future Routing Architecture (When Scale Requires)"]
        direction TB
        Q["User Query"] --> Intent{"Intent & Pre-Filter"}

        Intent -->|"Standard Query (1-3 KBs)"| DirectRet["Direct Vector Retrieval<br/>(Parallel Chroma Search)"]

        Intent -->|"Large Corpus (20+ KBs)"| KBR["Future 1: Semantic KB Router<br/>(Embedding / Metadata Filter)"]
        KBR --> DirectRet

        Intent -->|"Dynamic Operational Query"| ToolRouter{"Future 2: Native Tool Calling"}
        ToolRouter -->|"MIS / Meter / Sensor"| LangGraphTools["LangGraph ToolNode<br/>(Standard OpenAI Tools API)"]
        ToolRouter -->|"External MCP"| MCPClient["Future 3: Dynamic MCP Client<br/>(Standardized FastMCP Client)"]
    end
```

#### Future Improvement 1: Semantic KB Router (Hierarchical Retrieval)
* **When to build:** When a single partner has $> 10$ distinct knowledge base collections.
* **Mechanism:** Maintain a lightweight vector index over Knowledge Base descriptions. The router embeds the user query, selects the top 2–3 most relevant KBs, and scopes retrieval to those collections automatically without querying all collections.

#### Future Improvement 2: Native LLM Tool-Calling (LangGraph `ToolNode`)
* **When to build:** When the assistant needs to autonomously choose between $\ge 3$ dynamic API tools (e.g., `lookup_meter_reading`, `get_soil_sensor_data`, `check_weather_forecast`).
* **Mechanism:** Replace custom JSON-in-markdown parsing with standard LLM Function/Tool Calling (OpenAI Tools API / Anthropic Tool Calling) using LangGraph's native `ToolNode`.

#### Future Improvement 3: Dynamic MCP Gateway for Third-Party Plugins
* **When to build:** When external third parties or ministry partners provide their own MCP-compliant microservices that must be plugged in dynamically at runtime.
* **Mechanism:** A dedicated `MCPToolGateway` that dynamically mounts external tools into the LangGraph tool-calling loop using standard MCP client SDKs, with resilient connection pooling and timeouts.
