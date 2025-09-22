import pytest
import pytest_asyncio
from types import SimpleNamespace
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from app.schemas.chat import CreateMessagePayload
from app.api.api_v1.auth import get_current_user
from app.services import chat_mcp_service

# ------------------ App / Client Fixtures ------------------


@pytest.fixture
def app() -> FastAPI:
    """Return the FastAPI app."""
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
    """Stub current_user dependency."""
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


# ------------------ DB Fixture ------------------


@pytest.fixture
def stub_chat_db(app: FastAPI):
    """Provide a fake DB via dependency override."""
    from app.db.session import get_db

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
                knowledge_bases=[SimpleNamespace(id=3)],
                messages=fake_messages,
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

        def close(self):
            pass

    async def fake_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = fake_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ------------------ MCP Streaming Fixtures ------------------


@pytest.fixture
def stub_stream_mcp(monkeypatch):
    """Stub stream_mcp_response to yield test tokens."""

    async def fake_stream_mcp_response(**kwargs):
        for token in ["chunk1", "chunk2"]:
            yield f'0:"{token}"\n'
        yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'

    monkeypatch.setattr(
        chat_mcp_service, "stream_mcp_response", fake_stream_mcp_response
    )


# ------------------ System / Prompt Fixtures ------------------


@pytest.fixture
def stub_system_settings(monkeypatch):
    """Stub SystemSettingsService.get_top_k."""
    from app.services.system_settings_service import SystemSettingsService

    monkeypatch.setattr(SystemSettingsService, "get_top_k", lambda self: 10)


@pytest.fixture
def stub_prompt_service(monkeypatch):
    from app.services.prompt_service import PromptService

    # Contextualize prompt stub
    monkeypatch.setattr(
        PromptService,
        "get_full_contextualize_prompt",
        lambda self: "stub context",
    )

    # QA strict prompt stub must include {context} as input variable
    def stub_qa_strict_prompt(self, context_placeholder="{context}"):
        # Return a string including {context} so the chain validation passes
        return "stub system message {context} {input}"

    monkeypatch.setattr(
        PromptService,
        "get_full_qa_strict_prompt",
        stub_qa_strict_prompt,
    )


# ------------------ Stub LLM ------------------


@pytest.fixture
def stub_llm(monkeypatch):
    from app.services.llm.llm_factory import LLMFactory
    from langchain_core.runnables import Runnable
    from types import SimpleNamespace

    class FakeLLM(Runnable):
        async def astream(self, *args, **kwargs):
            for token in ["chunk1", "chunk2"]:
                yield token

        def invoke(self, *args, **kwargs):
            return SimpleNamespace(content="stub query")

    monkeypatch.setattr(LLMFactory, "create", lambda: FakeLLM())


# ------------------ Integration Tests ------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegrationEndpoint:

    async def test_success(
        self,
        client,
        app,
        override_current_user,
        stub_chat_db,
        stub_stream_mcp,
        stub_system_settings,
        stub_prompt_service,
        stub_llm,
    ):
        payload = CreateMessagePayload(
            id="stringID", messages=[{"role": "user", "content": "Query KB"}]
        )
        response = await client.post(
            "/api/chat/1/messages/mcp_integration", json=payload.model_dump()
        )
        assert response.status_code == 200
        text = response.text
        assert '0:"chunk1"' in text
        assert '0:"chunk2"' in text
        assert 'd:{"finishReason":"stop"' in text

    async def test_last_message_not_user(
        self,
        client,
        app,
        override_current_user,
        stub_chat_db,
        stub_system_settings,
    ):
        payload = CreateMessagePayload(
            id="stringID", messages=[{"role": "assistant", "content": "Hello"}]
        )
        response = await client.post(
            "/api/chat/1/messages/mcp_integration", json=payload.model_dump()
        )
        assert response.status_code == 400
        assert "Last message must be from user" in response.text

    async def test_chat_not_found(
        self, client, app, override_current_user, stub_system_settings
    ):
        # Override DB to return None
        from app.db.session import get_db

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

        app.dependency_overrides[get_db] = fake_get_db

        payload = CreateMessagePayload(
            id="stringID", messages=[{"role": "user", "content": "Hello"}]
        )
        response = await client.post(
            "/api/chat/1/messages/mcp_integration", json=payload.model_dump()
        )
        assert response.status_code == 404
        assert "Chat not found" in response.text
