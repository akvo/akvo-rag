from fastapi import APIRouter

from app.api.api_v1.extended import (
    extend_api_keys,
    extend_chat,
    extend_auth,
    extend_knowledge_base,
    prompt,
)

api_router = APIRouter()

api_router.include_router(extend_auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    extend_knowledge_base.router,
    prefix="/knowledge-base",
    tags=["knowledge-base"],
)
api_router.include_router(extend_chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(
    extend_api_keys.router, prefix="/api-keys", tags=["api-keys"]
)
api_router.include_router(prompt.router, prefix="/prompt", tags=["prompt"])
