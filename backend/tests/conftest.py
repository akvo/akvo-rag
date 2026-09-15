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
from app.models.user import User
from app.core.security import get_password_hash
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
    from app.api.api_v1.knowledge_base import get_redis_client

    instance = fake_aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_redis_client, None)


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


@pytest.fixture
def admin_user(db):
    """Fixture for an active superuser."""
    user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_superuser=True,
    )
    user.hashed_password = get_password_hash("adminpass")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(db, client, admin_user):
    """Fixture returning a valid JWT access token for an active superuser."""
    res = client.post(
        f"{API_PREFIX}/auth/token",
        data={"username": admin_user.username, "password": "adminpass"},
    )
    return res.json().get("access_token")


@pytest.fixture
def regular_user(db):
    """Fixture for an active non-superuser."""
    user = User(
        id=2,
        username="regular_user",
        email="user@example.com",
        is_active=True,
        is_superuser=False,
    )
    user.hashed_password = get_password_hash("userpass")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(db, client, regular_user):
    """Fixture returning a valid JWT access token for a regular non-superuser."""
    res = client.post(
        f"{API_PREFIX}/auth/token",
        data={"username": regular_user.username, "password": "userpass"},
    )
    return res.json().get("access_token")
