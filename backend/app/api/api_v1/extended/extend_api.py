from fastapi import APIRouter

from app.api.api_v1.extended import (
    extend_chat,
    extend_knowledge_base,
    prompt,
    system_settings,
)

api_router = APIRouter()

api_router.include_router(
    extend_knowledge_base.router,
    prefix="/knowledge-base",
    tags=["knowledge-base"],
)
api_router.include_router(extend_chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(prompt.router, prefix="/prompt", tags=["prompt"])
api_router.include_router(
    system_settings.router,
    prefix="/system-settings",
    tags=["system-settings"]
)
