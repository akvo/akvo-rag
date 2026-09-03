# Phase 3 Manual QA & Verification Guide

> **Issue**: [#127](https://github.com/akvo/akvo-rag/issues/127) — `[RAG IMPROVEMENT] D10 - Phase 3: Queue-Backed MCP Dispatcher, Scoping Removal & FastMCP Purge`
> **Target Branch / PR**: `phase-3/127-rag-improvement-d10-phase-3-queue-backed-mcp-dispatcher-scoping-removal-fastmcp-purge` -> `phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening` ([PR #142](https://github.com/akvo/akvo-rag/pull/142))

---

## 1. Overview & Scope

In **Phase 3**, the `akvo-rag` backend architecture transitions from legacy synchronous FastMCP HTTP/SSE to a high-throughput, queue-backed microservice communication model powered by Redis Request-Reply RPC, direct LangGraph vector routing, and a 3-tier dynamic prompt resolution engine.

This QA guide details step-by-step instructions to:

1. Run and verify the complete automated test suite (298 backend tests + 69 vector-kb-mcp tests = **367 total passing tests**).
2. Validate the **declarative `mcp_config.json` schema parser** and configuration loader.
3. Manually test and inspect **queue-backed Redis RPC dispatching** (`MCPQueueDispatcher`) with correlation IDs, ephemeral response queues, and timeout trapping.
4. Manually verify **LangGraph direct vector retrieval** and benchmark latency reduction (~1.6s vs ~3.8s legacy, eliminating the redundant `ScopingAgent` LLM call).
5. Manually verify the **3-tier dynamic prompt resolution hierarchy** (App Overlay ➔ Global DB ➔ System Fallback) and seeder execution.
6. Verify **PostgreSQL 17 Alembic migration reversibility** and schema integrity across all core tables.
7. Verify **Host REST API backwards compatibility** for host application integrations (Knowledge Base CRUD, RAG chat sessions, and App registrations).

---

## 2. Prerequisites & Environment Setup

Ensure all local Docker services are running and healthy:

```bash
# Start unified local infrastructure
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

**Required active containers:**

- `akvo-rag-backend-1` (FastAPI backend on port 8000)
- `akvo-rag-vector-kb-mcp-1` (Native Redis RPC Vector Microservice)
- `akvo-rag-postgres-1` (PostgreSQL 17 on port 5432)
- `akvo-rag-redis-1` (Redis 7 on port 6379)
- `akvo-rag-chromadb-1` (ChromaDB on port 8001 -> 8000)
- `akvo-rag-minio-1` (MinIO on port 9000/9001)

---

## 3. Automated Quality Gates

Run the automated test runner inside the containers:

```bash
# 1. Run all backend unit, integration, and contract tests (Target: 298 passing)
docker exec akvo-rag-backend-1 python -m pytest tests/ -v

# 2. Run vector-kb-mcp test suite (Target: 69 passing)
docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ -v
```

**Quality Baseline:**

- **367 tests passing** with 0 errors across microservices.
- **Zero Flake8 warnings** under PEP 8 rules for all Phase 3 files.

---

## 4. Manual QA: Declarative `mcp_config.json` Static Schema & Parser

Validate that `mcp_config.json` loads correctly, validates transport configurations, and handles schema violations deterministically.

### Step 4.1: Validate Default MCP Configuration

Inspect the parsed configuration in Python:

```bash
docker exec akvo-rag-backend-1 python -c "
from app.core.mcp_config import load_mcp_config
config = load_mcp_config()
print(f'Servers loaded: {list(config.servers.keys())}')
for name, srv in config.servers.items():
    tools = [t.name for t in srv.tools]
    print(f' - {name}: transport={srv.transport}, tools={tools}')
"
```

**Expected Output:**

```text
Servers loaded: ['knowledge_bases_mcp', 'weather_mcp']
 - knowledge_bases_mcp: transport=redis_queue, tools=['query_knowledge_base', 'list_knowledge_bases', 'get_knowledge_base', 'create_knowledge_base', 'update_knowledge_base', 'delete_knowledge_base', 'list_documents', 'get_document', 'get_processing_tasks']
 - weather_mcp: transport=rest, tools=['get_weather_forecast', 'get_current_weather', 'get_historical_weather']
```

### Step 4.2: Test Pydantic Schema Validation & Error Trapping

Verify that invalid configuration structures raise descriptive validation errors:

```bash
docker exec akvo-rag-backend-1 python -c "
from app.core.mcp_config import parse_mcp_config
try:
    parse_mcp_config({'servers': {'bad-srv': {'transport': 'unknown_transport'}}})
except Exception as e:
    print('Validation successfully caught invalid transport:', type(e).__name__)
"
```

**Expected Output:**

```text
Validation successfully caught invalid transport: ValidationError
```

---

## 5. Manual QA: Queue-Backed Redis RPC Dispatcher (`MCPQueueDispatcher`)

Validate that tools are dispatched over Redis request-reply queues with correlation IDs and timeout resilience.

### Step 5.1: Execute Direct Vector Retrieval via Redis RPC

Send an RPC tool invocation through `MCPQueueDispatcher` directly to the `vector-kb-mcp` worker:

```bash
docker exec akvo-rag-backend-1 python -c "
import asyncio
from app.core.mcp_config import load_mcp_config
from mcp_clients.queue_dispatcher import MCPQueueDispatcher

async def test_rpc():
    config = load_mcp_config()
    dispatcher = MCPQueueDispatcher(config)
    
    result = await dispatcher.call_tool(
        server_name='knowledge_bases_mcp',
        tool_name='query_knowledge_base',
        arguments={'query': 'agriculture water quality', 'knowledge_base_ids': [1], 'top_k': 3}
    )
    print('RPC Result Status: success')
    print('RPC Chunks Retrieved:', len(result.get('chunks', [])))
    await dispatcher.close()

asyncio.run(test_rpc())
"
```

**Expected Output:**

```text
RPC Result Status: success
RPC Chunks Retrieved: 0
```

### Step 5.2: Test RPC Timeout Handling & Queue Cleanup

Simulate an unresponsive worker tool call and verify that `MCPTimeoutError` is raised and temporary response queues are cleaned up:

```bash
docker exec akvo-rag-backend-1 python -c '
import asyncio
from app.core.mcp_config import parse_mcp_config
from mcp_clients.queue_dispatcher import MCPQueueDispatcher
from mcp_clients.exceptions import MCPTimeoutError

async def test_timeout():
    config = parse_mcp_config({
        "servers": {
            "unresponsive_server": {
                "name": "Unresponsive Server",
                "transport": "redis_queue",
                "request_queue": "mcp:unresponsive:requests",
                "response_queue_prefix": "mcp:unresponsive:responses",
                "timeout_seconds": 1,
                "tools": [{"name": "slow_tool", "description": "test", "inputSchema": {"type": "object"}}]
            }
        }
    })
    dispatcher = MCPQueueDispatcher(config)
    try:
        await dispatcher.call_tool("unresponsive_server", "slow_tool", {}, timeout=0.5)
    except MCPTimeoutError:
        print("SUCCESS: MCPTimeoutError raised gracefully upon worker timeout")
    await dispatcher.close()

asyncio.run(test_timeout())
'
```

**Expected Output:**

```text
SUCCESS: MCPTimeoutError raised gracefully upon worker timeout
```

---

## 6. Manual QA: LangGraph Direct Vector Retrieval (Zero Scoping)

Validate that RAG queries execute through the streamlined LangGraph pipeline without calling `ScopingAgent`.

### Step 6.1: Verify Graph Structure (Zero Scoping Node)

Verify that the compiled LangGraph workflow completely excludes `scoping_node`:

```bash
docker exec akvo-rag-backend-1 python -c "
from app.services.query_answering_workflow import create_rag_graph
wf = create_rag_graph()
nodes = list(wf.nodes.keys())
print('Compiled Graph Nodes:', nodes)
print('Scoping Node Present:', 'scoping_node' in nodes or 'scoping' in nodes)
"
```

**Expected Result:**

```text
Compiled Graph Nodes: ['classify_intent', 'small_talk', 'contextualize', 'run_mcp', 'error_handler', 'generate']
Scoping Node Present: False
```

### Step 6.2: Validate Intent Routing and Vector Node Execution

Execute a query through the workflow:

```bash
docker exec akvo-rag-backend-1 python -c "
import asyncio
from app.services.query_answering_workflow import query_answering_workflow
from app.services.prompt_service import PromptService

async def test_workflow():
    ps = PromptService()
    state = {
        'query': 'What is drip irrigation in agriculture?',
        'chat_history': [],
        'knowledge_base_ids': [1],
        'top_k': 3,
        'contextualize_prompt_str': ps.get_full_contextualize_prompt(),
        'qa_prompt_str': ps.get_full_qa_strict_prompt(),
    }
    result = await query_answering_workflow.ainvoke(state)
    print('Intent:', result.get('intent'))
    print('Context Chunks Received:', len(result.get('context', [])))
    print('Answer Generated:', bool(result.get('answer')))

asyncio.run(test_workflow())
"
```

**Expected Result:**

- `Intent: knowledge_query`
- `Answer Generated: True`

---

## 7. Manual QA: Dynamic 3-Tier Prompt Resolver (`PromptService`)

Validate that prompts are dynamically resolved according to tenant/app overlays and database definitions.

### Step 7.1: Verify Seeder Execution

Run the prompt seeder to ensure all prompt definitions and default overlays are synchronized with PostgreSQL 17:

```bash
docker exec akvo-rag-backend-1 python -m app.seeder.seed_prompts
```

**Expected Output:**

```text
Seeding prompt definitions and default overlays...
Prompt definitions and default overlays seeded successfully.
```

### Step 7.2: Test 3-Tier Resolution Hierarchy

Test prompt retrieval in Python across App Overlays, Global DB definitions, and System fallbacks:

```bash
docker exec akvo-rag-backend-1 python -c "
from app.db.session import SessionLocal
from app.services.prompt_service import PromptService
from app.models.prompt import PromptNameEnum

with SessionLocal() as session:
    service = PromptService(db=session)
    prompt = service.get_active_prompt_content(PromptNameEnum.qa_strict_prompt)
    print('Resolved active prompt length:', len(prompt))
    print('Contains answering rules:', 'Important Answering Rules' in service.get_full_qa_strict_prompt())
"
```

**Expected Output:**

```text
Resolved active prompt length: 1167
Contains answering rules: True
```

---

## 8. Manual QA: Backend PostgreSQL 17 Alembic Migrations

Validate that the backend database migrations execute cleanly forward and backward against PostgreSQL 17.

### Step 8.1: Check Current Migration Head

```bash
docker exec akvo-rag-backend-1 alembic current
```

**Expected Output:**

```text
de57ec74e817 (head)
```

### Step 8.2: Verify PostgreSQL Table Schema & Constraints

```bash
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "\dt"
```

**Expected Tables:**

- `users`
- `apps`
- `app_knowledge_bases`
- `prompt_definitions`
- `prompt_overlays`
- `chat_sessions` / `chat_messages`
- `api_keys`
- `alembic_version`

---

## 9. Manual QA: Host REST API Backwards Compatibility

Validate that host applications (AgriConnect, CoM, and external clients) experience zero regression across existing REST endpoints.

Run the automated contract suite:

```bash
docker exec akvo-rag-backend-1 python -m pytest tests/api/test_host_api_backwards_compatibility.py -v
```

**Expected Result:**

- 9 contract tests passing (KB list/detail/create/update/delete, test-retrieval, chat session management, and app registration).

---

## 10. Rollback & Troubleshooting Protocol

If any component encounters unexpected behavior during staging or production deployment:

1. **Redis RPC Stalling**:

   ```bash
   docker compose restart redis vector-kb-mcp
   ```

2. **Database Migration Rollback**:

   ```bash
   docker exec akvo-rag-backend-1 alembic downgrade -1
   ```

3. **Inspect Application Logs**:

   ```bash
   docker compose logs -f --tail=100 backend vector-kb-mcp
   ```
