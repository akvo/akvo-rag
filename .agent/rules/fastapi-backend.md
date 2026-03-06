---
trigger: model_decision
description: When writing or modifying Python backend code (FastAPI routers, models, services, tests)
---

## FastAPI Backend Standards

### Code Style

- Follow **PEP 8** guidelines
- Use **Black** formatter with **79 character** line limit
- Use **flake8** for linting
- Run linter: `./dev.sh exec backend flake8`

### Pydantic v2 Multi-Model Pattern

Always use the multi-model pattern for API schemas:

| Model | Purpose |
|-------|---------|
| `Base` | Common fields shared across models |
| `Create` | Request body for creation (required fields) |
| `Update` | Request body for updates (all optional) |
| `Response` | API response with all fields |

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str = Field(..., description="User email")
    name: str = Field(..., min_length=1)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1)

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

### FastAPI Router Conventions

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/", response_model=list[UserResponse])
async def list_users(): ...

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate): ...
```

### Prompt Management

Prompts are managed via `PromptService` and stored in the database. Never hardcode system prompts for RAG.

```python
from app.services.prompt_service import PromptService
from app.models.prompt import PromptNameEnum

# In service or router:
prompt_service = PromptService(db)
system_prompt = prompt_service.get_active_prompt_content(PromptNameEnum.qa_flexible_prompt)
```

### Architecture

- **SQLAlchemy ORM** for database models.
- **Alembic** for migrations (auto-run on startup).
- **Service layer** in `backend/app/services/` holds business logic.
- **Celery + RabbitMQ** for async background tasks (e.g., embedding, chat jobs).
- **MCP Integration** for knowledge base queries.

### Testing

- Use **pytest** with class-based grouping: `class TestUserCRUD:`
- **All tests MUST run inside Docker.**
- Run all tests: `./dev.sh exec backend ./test.sh`
- Run unit tests: `./dev.sh exec backend ./test-unit.sh`
- Always test happy path + at least 2 error paths.

### Related Rules
- API Design @api-design.md
- Docker Commands @docker-commands.md
- Testing Strategy @testing-strategy.md
- MCP Integration @mcp-integration.md
