# Akvo RAG (Retrieval-Augmented Generation)

<p>
  <a href="https://github.com/rag-web-ui/rag-web-ui/blob/main/LICENSE"><img src="https://img.shields.io/github/license/rag-web-ui/rag-web-ui" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/node-%3E%3D18-green.svg" alt="Node"></a>
  <a href="#"><img src="https://github.com/rag-web-ui/rag-web-ui/actions/workflows/test.yml/badge.svg" alt="CI"></a>
</p>

---

## 📖 Introduction

The Akvo RAG is a software that allows users to chat with Knowledge Bases. This type of product already exists, but we want to enable the following capabilities:

1. Make it easy to add a “RAG feature” to any web application
2. Make it easy to add Knowledge Bases (and data pipelines)
3. Make it possible to automatically select the Knowledge Bases that are queried
4. Make it possible to self-host the entire system (data pipeline, RAG, LLM)

One of the key features (3.) that we want to make available is called Agent-Scoped Query Mode (ASQ Mode). It’s the ability to automatically determine what are the most appropriate Knowledge Bases to query in order to create the best possible response to the user.

The default and simpler approach is User-Scoped Query Mode (USQ Mode), in which the user can manually select the Knowledge Bases they want to query.

### 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Client                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Frontend UI (Port 80)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend API (Port 8000)                     │
│                    • FastAPI                                 │
│                    • Authentication                          │
│                    • Business Logic                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
┌──────────────────────┐    ┌─────────────────────────┐
│  MCP Server          │    │  Job Queue              │
│  (Port 8100)         │    │  • RabbitMQ (5672)      │
│  • Knowledge Base    │    │  • Celery Workers       │
│  • Vector Search     │    │  • Flower UI (5555)     │
└──────────────────────┘    └─────────────────────────┘
           │
           ▼
┌──────────────────────┐
│  LLM Provider        │
│  • OpenAI            │
│  • DeepSeek          │
│  • Ollama (Local)    │
└──────────────────────┘
```

### ✨ Key Features

- **Dynamic Prompt Service**: Centralized prompt management with versioning and database storage
  - 👉 See full documentation: [PROMPT_SERVICE.md](PROMPT_SERVICE.md)
- **RAG Evaluation**: Built-in RAGAS metrics for pipeline performance evaluation
  - 👉 See full documentation: [`backend/RAG_evaluation/README.md`](backend/RAG_evaluation/README.md)
- **Async Job Processing**: Celery + RabbitMQ for scalable background tasks
- **Multiple LLM Support**: OpenAI, DeepSeek, and local Ollama deployment
- **Monitoring Dashboard**: Flower UI for real-time job tracking
- **OpenAPI Integration**: RESTful APIs for programmatic access

---

## ⚠️ Important: External Dependency

**This project requires the MCP (Model Context Protocol) Server to function.**

Without a running MCP server, RAG Web UI cannot:
- Query knowledge bases
- Process documents
- Generate RAG responses

**You MUST set up the MCP server first** before proceeding with RAG Web UI installation.

→ [Jump to MCP Server Setup Instructions](#step-1-set-up-mcp-server-required-dependency)

---

## 🚀 Quick Start

### Prerequisites Check

Before starting, ensure you have:

- [ ] Docker & Docker Compose v2.0+
- [ ] Node.js 18+
- [ ] Python 3.9+
- [ ] 8GB+ RAM (16GB recommended)
- [ ] 10GB+ free disk space
- [ ] Ports 80, 5555, 5672, 8000, 8100 available

### Step 1: Set Up MCP Server (Required Dependency)

The MCP server provides the knowledge base query layer and **must be running** before starting RAG Web UI.

#### 1.1 Install and Start MCP Server

You have two options:

**Option A: Local Installation**

Follow the complete installation guide in the MCP server repository:

👉 **[Vector Knowledge Base MCP Server - Setup Guide](https://github.com/akvo/vector-knowledge-base-mcp-server/)**

The MCP server runs on **port 8100** by default.

**Option B: Use Test Server** (for quick testing only)
```
KNOWLEDGE_BASES_MCP=https://kb-mcp-server.akvotest.org/mcp/
KNOWLEDGE_BASES_API_KEY=supersecretapikey
KNOWLEDGE_BASES_API_ENDPOINT=https://kb-mcp-server.akvotest.org
```

> ⚠️ **Note**: The test server is for evaluation purposes only. For production, use your own MCP server installation.

#### 1.2 Verify MCP Server is Running (for Local Installation)

```bash
curl http://localhost:8100/api/health
```

If this fails, troubleshoot the MCP server before proceeding.

---

### Step 2: Set Up RAG Web UI

#### 2.1 Clone the Repository

```bash
git clone https://github.com/akvo/akvo-rag.git
cd akvo-rag
```

#### 2.2 Configure Environment Variables

```bash
cp .env.example .env
```

**Edit `.env` with your configuration.** See the [Complete Configuration Template](#-complete-env-configuration-template) below.


#### 2.3 Start Docker Services

```bash
docker compose -f docker-compose.dev.yml up -d
```

#### 2.4 Wait for Services to Initialize

```bash
# Watch the logs
docker compose logs -f

# Wait until you see messages like:
# "Application startup complete"
# "Uvicorn running on http://0.0.0.0:8000"
```

---

### Step 3: Verify Installation

#### 3.1 Check All Services

```bash
# Frontend UI
curl http://localhost:80

# Backend API Documentation
curl http://localhost:8000/docs

# Flower Dashboard (use browser)
open http://localhost:5555

# RabbitMQ Management (optional)
open http://localhost:15672
```

#### 3.2 Verify MCP Connection

```bash
# Check backend logs for MCP connection
docker compose logs backend | grep -i mcp

# Should see: "MCP discovery manager finished successfully" or similar
```

#### 3.3 Check Service Status

```bash
docker compose ps
```

**All services should show as "Up":**
- `frontend`
- `backend`
- `mysql`
- `rabbitmq`
- `celery-worker`
- `flower`

---

### Step 4: First-Time Setup

#### 4.1 Access the Web UI

Open your browser and navigate to:
```
http://localhost:80
```

#### 4.2 Create Admin Account

The first admin account must be created using a seeder script:
```bash
# Run the admin user seeder
docker compose exec backend python -m app.seeder.seed_admin_user

# Follow the interactive prompts to:
# - Set admin email
# - Set admin username
# - Set admin password
# - Confirm admin password
```

**Note**: This admin account can later approve new user registrations.

**Subsequent users** can:
1. Click "Sign Up" or "Register"
2. Wait for admin approval via the admin dashboard
3. Once approved, log in with their credentials

#### 4.3 Create Your First Knowledge Base

1. Navigate to **Knowledge Bases**
2. Click **Add New**
3. Upload a test document (PDF, TXT, or DOCX)
4. Wait for processing to complete
5. View in **Flower Dashboard** (http://localhost:5555)

#### 4.4 Test with a Query

1. Go to **Chat**
2. Select your knowledge base
3. Ask a test question related to your document
4. Verify the response uses information from your document

---

## 🔧 Complete .env Configuration Template

### Core Configuration

| Parameter                   | Description                | Default   | Required |
| --------------------------- | -------------------------- | --------- | -------- |
| MYSQL_SERVER                | MySQL Server Address       | localhost | ✅        |
| MYSQL_USER                  | MySQL Username             | postgres  | ✅        |
| MYSQL_PASSWORD              | MySQL Password             | postgres  | ✅        |
| MYSQL_DATABASE              | MySQL Database Name        | ragwebui  | ✅        |
| SECRET_KEY                  | JWT Secret Key             | -         | ✅        |
| ACCESS_TOKEN_EXPIRE_MINUTES | JWT Token Expiry (minutes) | 30        | ✅        |

### Celery & RabbitMQ Configuration

| Parameter       | Description                         | Default    | Required |
| --------------- | ----------------------------------- | ---------- | -------- |
|  RABBITMQ_USER  | RabbitMQ username                   | `rabbitmq` | ✅        |
|  RABBITMQ_PASS  | RabbitMQ password                   | `rabbitmq` | ✅        |
|  RABBITMQ_HOST  | RabbitMQ hostname or container name | `rabbitmq` | ✅        |
|  RABBITMQ_PORT  | RabbitMQ port                       | `5672`     | ✅        |

### Flower Monitoring Configuration

| Parameter         | Description               | Default    | Required |
| ----------------- | ------------------------- | ---------- | -------- |
|  FLOWER_USER      | Flower dashboard username | `admin`    | ✅        |
|  FLOWER_PASSWORD  | Flower dashboard password | `admin`    | ✅        |
|  FLOWER_PORT      | Port number for Flower UI | `5555`     | ✅        |

### MCP Configuration

| Parameter                    | Description                                | Example Value                          | Required |
| ---------------------------- | ------------------------------------------ | -------------------------------------- | -------- |
| KNOWLEDGE_BASES_MCP          | MCP Base URL (server endpoint)             | https://api.knowledge.example.com/mcp/ | ✅        |
| KNOWLEDGE_BASES_API_KEY      | API key for MCP authentication             | supersecretapikey                      | ✅        |
| KNOWLEDGE_BASES_API_ENDPOINT | MCP API query endpoint (used for requests) | https://api.knowledge.example.com      | ✅        |


### LLM Configuration

| Parameter         | Description           | Default                   | Applicable            |
| ----------------- | --------------------- | ------------------------- | --------------------- |
| CHAT_PROVIDER     | LLM Service Provider  | openai                    | ✅                     |
| OPENAI_API_KEY    | OpenAI API Key        | -                         | Required for OpenAI   |
| OPENAI_API_BASE   | OpenAI API Base URL   | https://api.openai.com/v1 | Optional for OpenAI   |
| OPENAI_MODEL      | OpenAI Model Name     | gpt-4                     | Required for OpenAI   |
| DEEPSEEK_API_KEY  | DeepSeek API Key      | -                         | Required for DeepSeek |
| DEEPSEEK_API_BASE | DeepSeek API Base URL | -                         | Required for DeepSeek |
| DEEPSEEK_MODEL    | DeepSeek Model Name   | -                         | Required for DeepSeek |
| OLLAMA_API_BASE   | Ollama API Base URL   | http://localhost:11434    | Required for Ollama   |
| OLLAMA_MODEL      | Ollama Model Name     | llama2                    | Required for Ollama   |

### Embedding Configuration

| Parameter                   | Description                | Default                | Applicable                    |
| --------------------------- | -------------------------- | ---------------------- | ----------------------------- |
| OPENAI_API_KEY              | OpenAI API Key             | -                      | Required for OpenAI Embedding |
| DASH_SCOPE_API_KEY          | DashScope API Key          | -                      | Required for DashScope        |


### Other Configuration

| Parameter | Description      | Default       | Required |
| --------- | ---------------- | ------------- | -------- |
| TZ        | Timezone Setting | Asia/Shanghai | ❌        |

---

## 🚧 Testing

### Backend Testing

The backend uses pytest for testing. All test commands run inside the Docker container and automatically install test dependencies as needed.

#### Prerequisites

Ensure Docker containers are running:

#### Test Commands

**Run All Tests**
```bash
cd backend
./test.sh
```
Runs the complete test suite with verbose output.

**Run Unit Tests Only**
```bash
cd backend
./test-unit.sh
```
Runs only unit tests, excluding integration and end-to-end tests.

**Run Tests in Watch Mode**
```bash
cd backend
./test-watch.sh
```

Continuously runs tests when files change. Useful during development.

---

## ⚡ Common Setup Issues

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| **Port 80 already in use** | Another service (Apache, Nginx) using port 80 | Stop conflicting service or change frontend port in `docker-compose.dev.yml` |
| **"Cannot connect to MCP server"** | MCP server not running | Verify MCP server: `curl http://localhost:8100/api/health` |
| **MySQL connection errors** | Incorrect credentials | Check `MYSQL_*` variables in `.env` match `docker-compose.dev.yml` |
| **Flower login fails** | Wrong credentials or not loaded | Verify `FLOWER_USER`/`FLOWER_PASSWORD` in `.env`, rebuild: `docker compose up -d --build` |
| **Tasks not in Flower** | Worker didn't load tasks | Restart worker: `docker compose restart celery-worker` |
| **"SECRET_KEY not found"** | Missing or invalid `.env` | Ensure `.env` exists and `SECRET_KEY` is set |
| **LLM API errors** | Invalid API key | Double-check API key for your provider (OpenAI, DeepSeek, etc.) |
| **Document upload fails** | Embedding service not configured | Verify `OPENAI_API_KEY` or `DASH_SCOPE_API_KEY` is set |
| **Containers keep restarting** | Resource limits or config errors | Check logs: `docker compose logs <service-name>` |
| **"Permission denied" on port 80** | Non-root user on Linux | Use port 8080 instead or run with sudo (not recommended) |

### Quick Diagnostic Commands

```bash
# Check all container status
docker compose ps

# View logs for specific service
docker compose logs backend
docker compose logs celery-worker
docker compose logs mysql

# Follow logs in real-time
docker compose logs -f

# Restart a specific service
docker compose restart backend

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

---

## ⚙️ Job Processing (Celery + RabbitMQ + Flower)

RAG Web UI supports asynchronous background task processing using Celery, RabbitMQ, and Flower.
This setup enables scalable execution of background jobs such as chat workflows, document embedding, and large knowledge base processing — without blocking FastAPI’s main thread.

**NOTE**: You can find Celery tasks code  under `app.tasks` folder.

### 🧩 Components Overview

| Component       | Description                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| 🐍 **Celery**   | Distributed task queue used for executing long-running jobs (e.g. chat generation, document chunking). |
| 🐇 **RabbitMQ** | Message broker that routes task messages between FastAPI and Celery workers.                           |
| 🌸 **Flower**   | Web-based monitoring UI for tracking Celery workers, tasks, and queues in real-time.                   |


### 🧠 How It Works

1. When an API endpoint (e.g. `/api/apps/jobs`) is called, a Celery task is queued into RabbitMQ.
2. The Celery worker process (running in its own container) listens for new jobs.
3. The worker executes the job asynchronously — for example, running a chat generation workflow or document embedding pipeline.
4. Job progress and results can be monitored in Flower or stored in your internal jobs database table.

This allows you to handle high-volume workloads, parallel processing, and non-blocking user responses.

**NOTE**: You don’t need to manually define `CELERY_BROKER_URL` or `CELERY_RESULT_BACKEND`.
They are automatically constructed inside `app/celery_app.py` using the RabbitMQ configuration above.

### 🌼 Monitoring Celery with Flower

Flower provides a **web-based monitoring dashboard** to observe workers and job progress.

**Access Flower Dashboard**
Open: http://localhost:5555

**Authentication**
Flower is password-protected to prevent unauthorized access.
Use the credentials defined in your `.env` file:

| Variable          | Default    | Description               |
| ----------------- | ---------- | ------------------------- |
| `FLOWER_USER`     | `admin`    | Username for Flower login |
| `FLOWER_PASSWORD` | `admin`    | Password for Flower login |

Login via:

```bash
Username: admin
Password: admin
```

#### 🌸 Flower Interface Overview

After logging in, you can:
1. View Registered Tasks
2. Track Task States
3. Monitor Workers
4. View Task History & Results

#### 🧾 Check Registered Tasks

To verify task registration inside a running container:

```bash
docker compose exec celery-worker celery -A app.celery_app inspect registered
```

Expected output:

```bash
-> celery@worker-name: OK
    * tasks.execute_chat_job_task
```

### 🧹 Debugging Tips

| Problem                            | Possible Cause                           | Solution                                                                                 |
| ---------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------- |
| Task not showing in Flower         | Task not registered or wrong module path | Ensure task module is inside `app/tasks/` and use correct `@celery_app.task(name="...")` |
| `NotRegistered('tasks.add')` error | Worker didn’t load the task              | Restart worker: `docker compose restart celery-worker`                                   |
| Flower not accessible              | Port conflict or container issue         | Check with `docker logs flower` and ensure port `5555` is exposed                        |
| Password not working               | `.env` not loaded correctly              | Rebuild containers after editing `.env`: `docker compose up -d --build`                  |

---

### 🔬 RAG Evaluation

Evaluate your RAG pipeline performance using RAGAS metrics with the built-in evaluation system.

```bash
# Start evaluation dashboard
./rag-evaluate

# Proper shutdown (prevents disk space issues)
./rag-evaluate-stop
# or use Ctrl-C (now handles cleanup automatically)
```

**⚠️ Important**: Always use proper shutdown methods. Improper termination can accumulate 1-2GB of Docker artifacts per session.

For complete evaluation documentation: [`backend/RAG_evaluation/README.md`](backend/RAG_evaluation/README.md)

---

## 📄 License

This project is licensed under the [Apache-2.0 License](LICENSE)
