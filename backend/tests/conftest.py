import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fakeredis.aioredis as fake_aioredis

from app.core.config import settings
from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.core.mcp_config import MCPConfig
from mcp_clients.queue_dispatcher import MCPQueueDispatcher

API_PREFIX = settings.API_V1_STR


class ApiTestClient(TestClient):
    """TestClient that transparently supports route requests with or
    without API_PREFIX.
    """

    def request(self, method: str, url: str, *args, **kwargs):
        if (
            isinstance(url, str)
            and not url.startswith("http://")
            and not url.startswith("https://")
        ):
            clean_url = url if url.startswith("/") else f"/{url}"
            # Prefix routes that don't already include API_PREFIX
            if (
                not clean_url.startswith(settings.API_V1_STR)
                and not clean_url.startswith("/openapi")
                and clean_url not in ("/health", "/api/health", "/")
            ):
                clean_url = f"{settings.API_V1_STR}{clean_url}"
            url = clean_url
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def api_prefix():
    """Canonical API prefix (e.g. /api/v1)."""
    return settings.API_V1_STR


@pytest.fixture(scope="function")
def db():
    """Create an isolated in-memory SQLite DB per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db_session = TestingSessionLocal()
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal()

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(db):
    """Provide a FastAPI TestClient with isolated DB."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client with in-memory request-reply stubbing."""
    redis_mock = AsyncMock()
    redis_mock.rpush = AsyncMock(return_value=1)
    response_payload = (
        '{"status": "ok", "data": '
        '[{"content": "Sample text", "score": 0.95}]}'
    )
    redis_mock.blpop = AsyncMock(
        return_value=(
            "mcp:vector:responses:test-123",
            response_payload,
        )
    )
    redis_mock.delete = AsyncMock(return_value=1)
    return redis_mock


@pytest.fixture
def fake_redis():
    """Isolated fake async Redis instance with decoded responses."""
    return fake_aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def test_mcp_config():
    """Loads declarative mcp_config.json for test executions."""
    return MCPConfig.load_from_file("mcp_config.json")


@pytest.fixture
def mcp_dispatcher(test_mcp_config, fake_redis):
    """MCPQueueDispatcher instance with injected config and fake Redis."""
    return MCPQueueDispatcher(config=test_mcp_config, redis_client=fake_redis)


@pytest_asyncio.fixture
async def async_client(db):
    """FastAPI AsyncClient configured with mock isolated DB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
