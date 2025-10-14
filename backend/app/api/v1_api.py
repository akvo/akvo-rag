from fastapi import APIRouter
from app.api.api_v1 import apps

v1_router = APIRouter()

v1_router.include_router(
    apps.router, prefix="/apps", tags=["apps"]
)
