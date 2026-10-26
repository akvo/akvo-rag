from datetime import datetime
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import Chat
from app.models.user import User
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_current_user():
    return User(
        id=1,
        email="chatuser@example.com",
        username="chatuser",
        hashed_password="pw",
        is_active=True,
    )


@pytest.fixture
def client(mock_db, mock_current_user):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_update_chat_title_success(client, mock_db):
    fake_chat = Chat(
        id=10,
        user_id=1,
        title="Old Title",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        knowledge_bases=[],
        messages=[],
    )
    mock_db.query.return_value.filter.return_value.first.return_value = fake_chat

    response = client.put(
        "/api/v1/chat/10",
        json={"title": "New Conversation Title"},
    )
    assert response.status_code == 200
    assert fake_chat.title == "New Conversation Title"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(fake_chat)


def test_update_chat_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.put(
        "/api/v1/chat/999",
        json={"title": "Non-existent"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Chat not found"


def test_delete_chat_success(client, mock_db):
    fake_chat = Chat(
        id=10,
        user_id=1,
        title="To Delete",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        knowledge_bases=[],
        messages=[],
    )
    mock_db.query.return_value.filter.return_value.first.return_value = fake_chat

    response = client.delete("/api/v1/chat/10")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_db.delete.assert_called_once_with(fake_chat)
    mock_db.commit.assert_called_once()
