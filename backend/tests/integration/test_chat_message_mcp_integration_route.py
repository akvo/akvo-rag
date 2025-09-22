import pytest
import pytest_asyncio

from fastapi import FastAPI
from types import SimpleNamespace
from httpx import AsyncClient, ASGITransport

from app.schemas.chat import CreateMessagePayload
from app.api.api_v1.auth import get_current_user


# ------------------ Fixtures ------------------


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
def override_current_user(app):
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def db_mock(app: FastAPI):
    """Provide a fake DB via dependency override."""
    from app.db.session import get_db

    fake_kb = SimpleNamespace(id=3)
    fake_chat = SimpleNamespace(id=1, user_id=1, knowledge_bases=[fake_kb])

    class FakeQuery:
        def __init__(self, return_value=None):
            self._return_value = return_value

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

        def all(self):
            return [] if self._return_value is None else [self._return_value]

        def first(self):
            return self._return_value

    class FakeDB:
        def query(self, model):
            if "Chat" in str(model):
                return FakeQuery(fake_chat)
            return FakeQuery()

        def add_all(self, items): ...
        def add(self, item): ...
        def commit(self): ...

    async def override_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = override_get_db
    return FakeDB()


@pytest.fixture
def stub_langgraph(monkeypatch):
    """Stub out LangGraph processing so we don’t call the real engine."""

    async def fake_astream(inputs):
        yield "chunk1"
        yield "chunk2"

    fake_chain = SimpleNamespace(astream=fake_astream)

    def fake_factory(**kwargs):
        print("✅ Using fake create_stuff_documents_chain")
        return fake_chain

    monkeypatch.setattr(
        "app.services.chat_mcp_service.create_stuff_documents_chain",
        fake_factory,
        raising=False,
    )

    monkeypatch.setattr(
        "app.api.api_v1.extended.extend_chat.create_stuff_documents_chain",
        fake_factory,
        raising=False,
    )

    return {"chain": fake_chain}


@pytest.fixture
def stub_langgraph_failure(monkeypatch):
    """Stub LangGraph to raise an exception during streaming."""

    async def fake_astream(inputs):
        raise RuntimeError("Simulated LangGraph failure")

    fake_chain = SimpleNamespace(astream=fake_astream)

    def fake_factory(**kwargs):
        print("✅ Using fake failing create_stuff_documents_chain")
        return fake_chain

    monkeypatch.setattr(
        "app.services.chat_mcp_service.create_stuff_documents_chain",
        fake_factory,
        raising=False,
    )
    monkeypatch.setattr(
        "app.api.api_v1.extended.extend_chat.create_stuff_documents_chain",
        fake_factory,
        raising=False,
    )

    return {"chain": fake_chain}


# ------------------ Test Class ------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegrationEndpoint:

    async def test_integration_mcp_endpoint_success(
        self, client, stub_langgraph, db_mock, override_current_user
    ):
        payload = CreateMessagePayload(
            id="stringID",
            messages=[{"role": "user", "content": "Query KB"}],
        )

        response = await client.post(
            "/api/chat/1/messages/mcp_integration",
            json=payload.model_dump(),
        )

        assert response.status_code == 200

        # Collect streaming body
        text = response.text

        # Assert streamed chunks are present
        assert '0:"chunk1"' in text
        assert '0:"chunk2"' in text
        assert 'd:{"finishReason":"stop"' in text

    async def test_integration_mcp_endpoint_failure(
        self, client, stub_langgraph_failure, db_mock, override_current_user
    ):
        """Simulate LangGraph failure and ensure error is streamed."""
        payload = CreateMessagePayload(
            id="stringID",
            messages=[{"role": "user", "content": "Bad query"}],
        )

        response = await client.post(
            "/api/chat/1/messages/mcp_integration",
            json=payload.model_dump(),
        )

        assert response.status_code == 200

        text = response.text

        # Assert error chunk is present
        assert "3:" in text
        assert "Error generating response" in text
