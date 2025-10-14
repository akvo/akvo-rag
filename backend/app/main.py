import logging

from app.api.api_v1.api import api_router
from app.api.openapi.api import router as openapi_router
from app.api.v1_api import v1_router
from app.core.config import settings
from app.startup.migarate import DatabaseMigrator
from fastapi import FastAPI

from app.api.api_v1.websocket.ws import ws_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(openapi_router, prefix="/openapi")
app.include_router(v1_router, prefix="/v1")
app.include_router(ws_router)


@app.on_event("startup")
async def startup_event():
    # Run database migrations
    migrator = DatabaseMigrator(settings.get_database_url)
    migrator.run_migrations()


@app.get("/")
def root():
    return {"message": "Welcome to RAG Web UI API"}


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }
