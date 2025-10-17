from fastapi import APIRouter
from app.api.api_v1 import apps
from app.api.api_v1 import jobs
from app.api import test_route

v1_router = APIRouter()

v1_router.include_router(
    apps.router, prefix="/apps", tags=["apps"]
)
v1_router.include_router(
    jobs.router, prefix="/apps", tags=["apps"]
)

v1_router.include_router(
    test_route.router, prefix="/test", tags=["test"]
)
