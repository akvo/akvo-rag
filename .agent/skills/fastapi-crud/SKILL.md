---
name: fastapi-crud
description: Step-by-step guide for adding new CRUD endpoints to the FastAPI backend. Use when creating new API resources with router, Pydantic schemas, service layer, and tests.
---

# FastAPI CRUD Skill

## Overview

Complete guide for adding a new CRUD resource to the FastAPI backend. Follow these steps in order.

## Steps

### 1. Create Pydantic Schemas

Create schemas in `backend/models/` using the multi-model pattern:

```python
# backend/models/resource.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ResourceBase(BaseModel):
    """Common fields shared across models."""
    name: str = Field(..., min_length=1, description="Resource name")
    description: Optional[str] = None


class ResourceCreate(ResourceBase):
    """Request body for creation (required fields)."""
    pass


class ResourceUpdate(BaseModel):
    """Request body for updates (all optional)."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None


class ResourceResponse(ResourceBase):
    """API response with all fields."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

### 2. Create SQLAlchemy Model

```python
# backend/models/resource.py (or dedicated DB models file)
from sqlalchemy import Column, Integer, String, DateTime, func
from db import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 3. Create Router

```python
# backend/routers/resource.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("/", response_model=list[ResourceResponse])
async def list_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """List all resources."""
    return db.query(Resource).all()


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Get a single resource."""
    resource = db.query(Resource).get(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.post(
    "/",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    data: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Create a new resource."""
    resource = Resource(**data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: int,
    data: ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Update a resource."""
    resource = db.query(Resource).get(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(resource, key, value)
    db.commit()
    db.refresh(resource)
    return resource


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    """Delete a resource."""
    resource = db.query(Resource).get(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(resource)
    db.commit()
```

### 4. Mount Router in main.py

```python
# backend/main.py
from routers.resource import router as resource_router

app.include_router(resource_router)
```

### 5. Create Database Migration

```bash
./dev.sh exec backend alembic revision --autogenerate -m "add resources table"
./dev.sh exec backend alembic upgrade head
```

### 6. Write Tests

```python
# backend/tests/test_resource.py
import pytest


class TestResourceCRUD:
    """Test CRUD operations for Resource."""

    def test_create_resource(self, client, auth_headers):
        response = client.post(
            "/api/resources/",
            json={"name": "Test", "description": "A test resource"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test"

    def test_list_resources(self, client, auth_headers):
        response = client.get(
            "/api/resources/", headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_resource_not_found(self, client, auth_headers):
        response = client.get(
            "/api/resources/9999", headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_resource(self, client, auth_headers, resource_id):
        response = client.patch(
            f"/api/resources/{resource_id}",
            json={"name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_resource(self, client, auth_headers, resource_id):
        response = client.delete(
            f"/api/resources/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
```

Run tests:
```bash
./dev.sh exec backend ./test.sh
```

### 7. Verify

```bash
./dev.sh exec backend flake8                    # Lint
./dev.sh exec backend ./test.sh                 # All tests (inside Docker)
```

## Auth Patterns Reference

| Pattern | Dependency | Returns |
|---------|-----------|---------|
| Optional auth | `current_user: Optional[User] = Depends(get_current_user)` | `None` if unauthenticated |
| Required auth | `current_user: User = Depends(get_current_user_required)` | Raises `401` if unauthenticated |

## Rule Compliance

- FastAPI Backend @fastapi-backend.md
- API Design @api-design.md
- Testing Strategy @testing-strategy.md
- Security Mandate @security-mandate.md
