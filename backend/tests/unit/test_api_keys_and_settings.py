from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.api_key import APIKey
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.api_key import APIKeyUpdate
from app.services.api_key import APIKeyService
from app.services.system_settings_service import SystemSettingsService


@pytest.fixture
def auth_user():
    fake_user = User(
        id=99,
        email="test_admin@example.com",
        username="test_admin",
        is_active=True,
        is_superuser=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield fake_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_db():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: fake_db
    yield fake_db
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(auth_user, mock_db):
    return TestClient(app)


# ---------------------------------------------------------------------
# API Keys Router Tests
# ---------------------------------------------------------------------


def test_read_api_keys(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    fake_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Test AgriConnect Key",
        user_id=99,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService,
        "get_api_keys",
        lambda db, user_id, skip, limit: [fake_key],
    )

    response = client.get("/api/v1/api-keys")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Test AgriConnect Key"


def test_create_api_key_endpoint(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    fake_key = APIKey(
        id=2,
        key="akvo_key_456",
        name="Created Key",
        user_id=99,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService,
        "create_api_key",
        lambda db, user_id, name: fake_key,
    )

    response = client.post("/api/v1/api-keys", json={"name": "Created Key"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 2
    assert data["name"] == "Created Key"


def test_update_api_key_success(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    fake_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Original Name",
        user_id=99,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    updated_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Updated Name",
        user_id=99,
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: fake_key
    )
    monkeypatch.setattr(
        APIKeyService,
        "update_api_key",
        lambda db, api_key, update_data: updated_key,
    )

    response = client.put(
        "/api/v1/api-keys/1", json={"name": "Updated Name", "is_active": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["is_active"] is False


def test_update_api_key_not_found(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: None
    )
    response = client.put(
        "/api/v1/api-keys/999", json={"name": "Missing", "is_active": True}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "API key not found"


def test_update_api_key_forbidden(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    other_user_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Other Key",
        user_id=12345,  # Mismatch from current_user.id (99)
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: other_user_key
    )
    response = client.put(
        "/api/v1/api-keys/1",
        json={"name": "Forbidden Edit", "is_active": True},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_delete_api_key_success(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    fake_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Delete Me",
        user_id=99,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: fake_key
    )
    monkeypatch.setattr(
        APIKeyService, "delete_api_key", lambda db, api_key: fake_key
    )

    response = client.delete("/api/v1/api-keys/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_delete_api_key_forbidden(client: TestClient, monkeypatch):
    now = datetime.now(timezone.utc)
    other_user_key = APIKey(
        id=1,
        key="akvo_key_123",
        name="Other Key",
        user_id=12345,  # Mismatch
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: other_user_key
    )
    response = client.delete("/api/v1/api-keys/1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_delete_api_key_not_found(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        APIKeyService, "get_api_key", lambda db, api_key_id: None
    )
    response = client.delete("/api/v1/api-keys/999")
    assert response.status_code == 404


# ---------------------------------------------------------------------
# System Settings Router Tests
# ---------------------------------------------------------------------


def test_get_top_k_setting_success(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        SystemSettingsService,
        "get_setting",
        lambda self, key: SystemSetting(id=1, key="top_k", value="5"),
    )
    response = client.get("/api/v1/system-settings/top_k")
    assert response.status_code == 200
    assert response.json()["key"] == "top_k"
    assert response.json()["value"] == "5"


def test_get_top_k_setting_not_found(client: TestClient, monkeypatch):
    def fake_get_error(self, key):
        raise ValueError("Setting top_k not found")

    monkeypatch.setattr(SystemSettingsService, "get_setting", fake_get_error)
    response = client.get("/api/v1/system-settings/top_k")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_top_k_setting_success(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        SystemSettingsService,
        "update_top_k",
        lambda self, val: SystemSetting(id=1, key="top_k", value=str(val)),
    )
    response = client.put("/api/v1/system-settings/top_k", json={"top_k": 8})
    assert response.status_code == 200
    assert response.json()["value"] == "8"


def test_update_top_k_setting_error(client: TestClient, monkeypatch):
    def fake_update_error(self, val):
        raise ValueError("Invalid top_k value")

    monkeypatch.setattr(
        SystemSettingsService, "update_top_k", fake_update_error
    )
    response = client.put("/api/v1/system-settings/top_k", json={"top_k": 1})
    assert response.status_code == 404


# ---------------------------------------------------------------------
# APIKeyService Direct Service Tests
# ---------------------------------------------------------------------


def test_api_key_service_methods(mock_db):
    now = datetime.now(timezone.utc)
    key_obj = APIKey(
        id=1,
        key="sk-123456",
        name="Service Key",
        user_id=42,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    # get_api_keys
    q_filter = mock_db.query.return_value.filter.return_value
    q_filter.offset.return_value.limit.return_value.all.return_value = [
        key_obj
    ]
    keys = APIKeyService.get_api_keys(mock_db, user_id=42, skip=0, limit=10)
    assert len(keys) == 1
    assert keys[0].id == 1

    # create_api_key
    created = APIKeyService.create_api_key(mock_db, user_id=42, name="New Key")
    assert created.user_id == 42
    assert created.name == "New Key"
    assert created.key.startswith("sk-")
    assert mock_db.add.called
    assert mock_db.commit.called

    # get_api_key
    mock_db.query.return_value.filter.return_value.first.return_value = key_obj
    fetched = APIKeyService.get_api_key(mock_db, api_key_id=1)
    assert fetched == key_obj

    # get_api_key_by_key
    fetched_by_str = APIKeyService.get_api_key_by_key(mock_db, key="sk-123456")
    assert fetched_by_str == key_obj

    # update_api_key
    update_data = APIKeyUpdate(name="Updated Service Key", is_active=False)
    updated = APIKeyService.update_api_key(mock_db, key_obj, update_data)
    assert updated.name == "Updated Service Key"
    assert updated.is_active is False

    # update_last_used
    used = APIKeyService.update_last_used(mock_db, key_obj)
    assert used.last_used_at is not None

    # delete_api_key
    APIKeyService.delete_api_key(mock_db, key_obj)
    assert mock_db.delete.called
