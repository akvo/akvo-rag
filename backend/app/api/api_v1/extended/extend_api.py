from fastapi import APIRouter

from app.api.api_v1.extended import (
    prompt,
    system_settings,
)

api_router = APIRouter()

api_router.include_router(prompt.router, prefix="/prompt", tags=["prompt"])
api_router.include_router(
    system_settings.router,
    prefix="/system-settings",
    tags=["system-settings"]
)
