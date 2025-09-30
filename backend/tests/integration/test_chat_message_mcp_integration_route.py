import pytest
import pytest_asyncio
from types import SimpleNamespace
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from unittest.mock import patch
from app.schemas.chat import CreateMessagePayload
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db

# ------------------ App / Client Fixtures ------------------


@pytest.fixture
def app() -> FastAPI:
    from app.main import app

    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c


@pytest.fixture
def override_current_user(app: FastAPI):
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


# ------------------ Chat DB Stub ------------------


@pytest.fixture
def stub_chat_db(app: FastAPI):
    class FakeMessage:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content

    fake_messages = [FakeMessage("user", "Hello")]

    class FakeQuery:
        def options(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(
                id=1,
                user_id=1,
                knowledge_bases=[SimpleNamespace(knowledge_base_id=3)],
                messages=fake_messages,
                content="Fake prompt content",
            )

        def all(self):
            return fake_messages

    class FakeDB:
        def query(self, model):
            return FakeQuery()

        def add(self, obj):
            pass

        def commit(self):
            pass

        def refresh(self, obj):
            pass

        def close(self):
            pass

    async def fake_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = fake_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ------------------ Integration Tests ------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegrationEndpoint:

    async def test_success(self, client, override_current_user, stub_chat_db):
        payload = CreateMessagePayload(
            id="test123", messages=[{"role": "user", "content": "Query KB"}]
        )

        async def fake_stream(*args, **kwargs):
            yield '0:"chunk1"\n'
            yield '0:"chunk2"\n'
            yield 'd:{"finishReason":"stop"}\n'

        # Patch stream_mcp_response in the router's module
        with patch(
            "app.api.api_v1.chat.stream_mcp_response",
            fake_stream,
        ):
            response = await client.post(
                "/api/chat/1/messages/mcp_integration",
                json=payload.model_dump(),
            )

        assert response.status_code == 200
        text = response.text
        assert '0:"chunk1"' in text
        assert '0:"chunk2"' in text
        assert 'd:{"finishReason":"stop"' in text

    async def test_last_message_not_user(
        self, client, override_current_user, stub_chat_db
    ):
        payload = CreateMessagePayload(
            id="test123", messages=[{"role": "assistant", "content": "Hello"}]
        )
        response = await client.post(
            "/api/chat/1/messages/mcp_integration", json=payload.model_dump()
        )
        assert response.status_code == 400
        assert "Last message must be from user" in response.text

    async def test_chat_not_found(self, client, override_current_user):
        async def fake_get_db():
            class DB:
                def query(self, model):
                    class Q:
                        def options(self, *args, **kwargs):
                            return self

                        def filter(self, *args, **kwargs):
                            return self

                        def first(self):
                            return None

                    return Q()

            yield DB()

        client._transport.app.dependency_overrides[get_db] = fake_get_db

        payload = CreateMessagePayload(
            id="test123", messages=[{"role": "user", "content": "Hello"}]
        )
        response = await client.post(
            "/api/chat/1/messages/mcp_integration", json=payload.model_dump()
        )
        assert response.status_code == 404
        assert "Chat not found" in response.text

    async def test_stream_failure(
        self, client, override_current_user, stub_chat_db
    ):
        payload = CreateMessagePayload(
            id="test123", messages=[{"role": "user", "content": "Bad query"}]
        )

        async def fail_stream(*args, **kwargs):
            yield "3:Error generating response\n"
            yield 'd:{"finishReason":"stop"}\n'

        with patch(
            "app.api.api_v1.chat.stream_mcp_response",
            fail_stream,
        ):
            response = await client.post(
                "/api/chat/1/messages/mcp_integration",
                json=payload.model_dump(),
            )

        assert response.status_code == 200
        text = response.text
        assert "3:" in text or "Error generating response" in text
        assert 'd:{"finishReason":"stop"' in text
