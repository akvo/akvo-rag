import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from starlette.websockets import WebSocketState, WebSocketDisconnect
from pydantic import ValidationError

from app.models.user import User
from app.models.chat import Chat, ChatKnowledgeBase
from app.schemas.knowledge import KnowledgeBaseResponse
from app.api.api_v1.websocket.ws_chat import (
    ChatMessage,
    ChatPayload,
    safe_send_json,
    authenticate_and_get_user,
    get_or_create_chat,
    validate_chat_payload,
    websocket_chat,
)


@pytest.mark.asyncio
async def test_safe_send_json_connected():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    await safe_send_json(mock_ws, {"status": "ok"})
    mock_ws.send_json.assert_called_once_with({"status": "ok"})


@pytest.mark.asyncio
async def test_safe_send_json_disconnected():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.DISCONNECTED
    await safe_send_json(mock_ws, {"status": "ok"})
    mock_ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_safe_send_json_exception_handled():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.send_json.side_effect = RuntimeError("Socket error")
    # Should not raise
    await safe_send_json(mock_ws, {"status": "ok"})


@pytest.mark.asyncio
async def test_authenticate_and_get_user_invalid_type():
    mock_ws = AsyncMock()
    mock_ws.receive_json.return_value = {"type": "not_auth"}
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()

    with pytest.raises(WebSocketDisconnect):
        await authenticate_and_get_user(mock_ws, mock_db)

    mock_ws.close.assert_called_once_with(code=4000)


@pytest.mark.asyncio
async def test_authenticate_and_get_user_missing_ids():
    mock_ws = AsyncMock()
    mock_ws.receive_json.return_value = {"type": "auth", "visitor_id": "v1"}
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()

    with pytest.raises(WebSocketDisconnect):
        await authenticate_and_get_user(mock_ws, mock_db)

    mock_ws.close.assert_called_once_with(code=4001)


@pytest.mark.asyncio
async def test_authenticate_and_get_user_new_visitor_success():
    mock_ws = AsyncMock()
    mock_ws.receive_json.return_value = {
        "type": "auth",
        "visitor_id": "v123",
        "kb_id": 5,
    }
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def fake_refresh(u):
        u.id = 42

    mock_db.refresh.side_effect = fake_refresh

    fake_kb_dict = {"id": 5, "name": "KB5", "description": "Desc5"}

    with patch(
        "app.api.api_v1.websocket.ws_chat.KnowledgeBaseMCPEndpointService.get_kb",
        new_callable=AsyncMock,
        return_value=fake_kb_dict,
    ):
        user, kb = await authenticate_and_get_user(mock_ws, mock_db)
        assert user.email == "visitor-v123@visitors.mail"
        assert user.id == 42
        assert kb.id == 5
        assert kb.name == "KB5"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_and_get_user_existing_visitor_kb_not_found():
    mock_ws = AsyncMock()
    mock_ws.receive_json.return_value = {
        "type": "auth",
        "visitor_id": "v123",
        "kb_id": 99,
    }
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()
    existing_user = User(id=1, email="visitor-v123@visitors.mail", username="v123")
    mock_db.query.return_value.filter.return_value.first.return_value = existing_user

    with patch(
        "app.api.api_v1.websocket.ws_chat.KnowledgeBaseMCPEndpointService.get_kb",
        new_callable=AsyncMock,
        side_effect=Exception("KB not found"),
    ):
        with pytest.raises(WebSocketDisconnect):
            await authenticate_and_get_user(mock_ws, mock_db)

        mock_ws.close.assert_called_once_with(code=4003)


def test_get_or_create_chat_existing():
    mock_db = MagicMock()
    user = User(id=1, email="test@example.com")
    existing_chat = Chat(id=10, user_id=1, title="Old Chat")
    mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.first.return_value = (
        existing_chat
    )

    result = get_or_create_chat(mock_db, user, kb_id=2)
    assert result == existing_chat
    mock_db.add.assert_not_called()


def test_get_or_create_chat_new():
    mock_db = MagicMock()
    user = User(id=1, email="test@example.com")
    mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.first.return_value = (
        None
    )

    def fake_refresh(c):
        c.id = 99

    mock_db.refresh.side_effect = fake_refresh

    result = get_or_create_chat(mock_db, user, kb_id=2)
    assert result.id == 99
    assert result.user_id == 1
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_validate_chat_payload_valid():
    mock_ws = AsyncMock()
    valid_data = {
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
    payload = await validate_chat_payload(mock_ws, valid_data)
    assert payload is not None
    assert len(payload.messages) == 1
    assert payload.messages[0].role == "user"
    assert payload.messages[0].content == "Hello!"


@pytest.mark.asyncio
async def test_validate_chat_payload_invalid():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    invalid_data = {"messages": [{"role": "invalid_role", "content": ""}]}
    payload = await validate_chat_payload(mock_ws, invalid_data)
    assert payload is None
    mock_ws.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_chat_full_flow():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()

    user = User(id=1, email="visitor-v1@visitors.mail")
    kb = KnowledgeBaseResponse(id=10, name="KB10", description="Desc")
    chat = Chat(id=100, user_id=1, title="Test Chat")
    chat.knowledge_bases = [ChatKnowledgeBase(knowledge_base_id=10)]

    # Mock sequence of incoming messages:
    # 1. Invalid message type ("ping")
    # 2. Invalid chat payload (empty content)
    # 3. Last message is assistant role
    # 4. Valid chat message
    # 5. Client disconnect
    mock_ws.receive_json.side_effect = [
        {"type": "other"},
        {"type": "chat", "messages": [{"role": "user", "content": ""}]},
        {"type": "chat", "messages": [{"role": "assistant", "content": "Hello"}]},
        {"type": "chat", "messages": [{"role": "user", "content": "Tell me a joke"}]},
        WebSocketDisconnect(),
    ]

    async def fake_stream_response(**kwargs):
        yield "Part 1 "
        yield "Part 2"

    with patch("app.api.api_v1.websocket.ws_chat.get_db", return_value=iter([mock_db])), patch(
        "app.api.api_v1.websocket.ws_chat.authenticate_and_get_user",
        new_callable=AsyncMock,
        return_value=(user, kb),
    ), patch(
        "app.api.api_v1.websocket.ws_chat.get_or_create_chat",
        return_value=chat,
    ), patch(
        "app.api.api_v1.websocket.ws_chat.stream_mcp_response",
        side_effect=fake_stream_response,
    ):
        await websocket_chat(mock_ws)

    mock_ws.accept.assert_called_once()
    mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_chat_unhandled_exception():
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_db = MagicMock()

    with patch("app.api.api_v1.websocket.ws_chat.get_db", return_value=iter([mock_db])), patch(
        "app.api.api_v1.websocket.ws_chat.authenticate_and_get_user",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Fatal startup error"),
    ):
        await websocket_chat(mock_ws)

    mock_ws.close.assert_called_once_with(code=1011)
    mock_db.close.assert_called_once()
