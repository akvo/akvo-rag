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
            # When PromptVersion.content is queried, return a fake prompt
            if "PromptVersion" in str(model):
                return FakeQuery(("stub prompt",))
            # When Chat is queried, return fake chat
            if "Chat" in str(model):
                return FakeQuery(fake_chat)
            return FakeQuery()

        def add_all(self, items): ...
        def commit(self): ...

    async def override_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = override_get_db
    return FakeDB()


@pytest.fixture
def stub_mcp_server(monkeypatch):
    async def fake_mcp_stream(*args, **kwargs):
        yield "data: chunk1\n\n"
        yield "data: chunk2\n\n"

    # Stub stream_mcp_response (used directly in your endpoint)
    monkeypatch.setattr(
        "app.services.chat_mcp_service.stream_mcp_response",
        fake_mcp_stream,
    )

    # Stub workflow astream_events
    async def fake_astream_events(initial_state, stream_mode="values"):
        yield {
            "event": "on_chain_stream",
            "name": "generate",
            "data": {"chunk": "chunk1"},
        }
        yield {
            "event": "on_chain_stream",
            "name": "generate",
            "data": {"chunk": "chunk2"},
        }

    # Stub workflow ainvoke (final state after streaming)
    async def fake_ainvoke(initial_state):
        return {"answer": "stubbed final answer"}

    patch_path = "app.services.chat_mcp_service.query_answering_workflow"
    monkeypatch.setattr(
        f"{patch_path}.astream_events",
        fake_astream_events,
    )
    monkeypatch.setattr(
        f"{patch_path}.ainvoke",
        fake_ainvoke,
    )

    return {
        "stream": fake_mcp_stream,
        "astream_events": fake_astream_events,
        "ainvoke": fake_ainvoke,
    }


# ------------------ Test Class ------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegrationEndpoint:

    async def test_integration_mcp_endpoint_success(
        self, client, stub_mcp_server, db_mock, override_current_user
    ):
        payload = CreateMessagePayload(
            id="stringID", messages=[{"role": "user", "content": "Query KB"}]
        )

        response = await client.post(
            "/api/chat/1/messages/mcp_integration",
            json=payload.model_dump(),
        )

        assert response.status_code == 200
        text = response.text
        assert "chunk1" in text
        assert "chunk2" in text
