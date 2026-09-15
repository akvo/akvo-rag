import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.services.email_service import EmailService


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_register_user_success(client: TestClient, mock_db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def fake_refresh(instance):
        instance.id = 1
        instance.created_at = now
        instance.updated_at = now

    mock_db.refresh.side_effect = fake_refresh

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!",
            "is_superuser": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["is_active"] is False


def test_register_duplicate_email(client: TestClient, mock_db):
    existing_user = User(id=1, email="existing@example.com", username="u1")
    mock_db.query.return_value.filter.return_value.first.return_value = (
        existing_user
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "username": "unique",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"]


def test_register_duplicate_username(client: TestClient, mock_db):
    # First query for email returns None,
    # second query for username returns user
    existing_user = User(
        id=1, email="other@example.com", username="existing_user"
    )
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        existing_user,
    ]

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "unique@example.com",
            "username": "existing_user",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 400
    assert "username already exists" in response.json()["detail"]


def test_login_inactive_user(client: TestClient, mock_db):
    from app.core.security import get_password_hash

    inactive_user = User(
        id=2,
        username="inactive",
        email="inactive@example.com",
        hashed_password=get_password_hash("pass123"),
        is_active=False,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = (
        inactive_user
    )

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "inactive", "password": "pass123"},
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"]


def test_test_token_endpoint(client: TestClient):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fake_user = User(
        id=5,
        email="me@example.com",
        username="me",
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    response = client.post("/api/v1/auth/test-token")
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_user_me_endpoint(client: TestClient):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fake_user = User(
        id=5,
        email="me@example.com",
        username="me",
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "me"


def test_update_user_by_email_success(client: TestClient, mock_db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fake_admin = User(id=1, is_superuser=True, is_active=True)
    target_user = User(
        id=3,
        email="target@example.com",
        username="targetuser",
        is_active=False,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_current_user] = lambda: fake_admin
    mock_db.query.return_value.filter.return_value.first.return_value = (
        target_user
    )

    response = client.put(
        "/api/v1/auth/user",
        json={
            "email": "target@example.com",
            "username": "targetuser",
            "is_active": True,
            "is_superuser": True,
        },
    )
    assert response.status_code == 200
    assert target_user.is_active is True
    assert target_user.is_superuser is True


def test_update_user_by_email_not_found(client: TestClient, mock_db):
    fake_admin = User(id=1, is_superuser=True, is_active=True)
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.put(
        "/api/v1/auth/user",
        json={
            "email": "nonexistent@example.com",
            "username": "nonexistent",
            "is_active": True,
            "is_superuser": False,
        },
    )
    assert response.status_code == 404


def test_forgot_password_active_user(client: TestClient, mock_db, monkeypatch):
    user = User(
        id=1, email="active@example.com", username="active", is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user

    monkeypatch.setattr(
        EmailService, "generate_reset_token", lambda db, u: "token-xyz"
    )
    monkeypatch.setattr(
        EmailService, "send_password_reset_email", AsyncMock(return_value=True)
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "active@example.com"},
    )
    assert response.status_code == 200
    assert "instructions" in response.json()["message"]


def test_reset_password_success(client: TestClient, mock_db, monkeypatch):
    user = User(id=1, email="reset@example.com", username="resetuser")
    monkeypatch.setattr(
        EmailService, "verify_reset_token", lambda db, tok: user
    )
    monkeypatch.setattr(
        EmailService, "mark_token_as_used", lambda db, tok: None
    )

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "valid-tok", "new_password": "NewSecretPassword123!"},
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


def test_reset_password_invalid_token(
    client: TestClient, mock_db, monkeypatch
):
    monkeypatch.setattr(
        EmailService, "verify_reset_token", lambda db, tok: None
    )

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid-tok", "new_password": "NewSecretPassword123!"},
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


def test_verify_reset_token_success(client: TestClient, mock_db, monkeypatch):
    user = User(id=1, email="verified@example.com")
    monkeypatch.setattr(
        EmailService, "verify_reset_token", lambda db, tok: user
    )

    response = client.get("/api/v1/auth/verify-reset-token/valid-token-abc")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["email"] == "verified@example.com"


def test_verify_reset_token_invalid(client: TestClient, mock_db, monkeypatch):
    monkeypatch.setattr(
        EmailService, "verify_reset_token", lambda db, tok: None
    )

    response = client.get("/api/v1/auth/verify-reset-token/bad-token")
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


# ---------------------------------------------------------------------
# Direct EmailService Tests
# ---------------------------------------------------------------------
def test_email_service_generate_and_mark_token(mock_db):
    user = User(id=10, email="tok@example.com")
    token = EmailService.generate_reset_token(mock_db, user)
    assert token is not None
    assert len(token) > 20
    assert mock_db.add.called
    assert mock_db.commit.called

    # Mark token used
    mock_db.query.return_value.filter.return_value.first.return_value = (
        MagicMock()
    )
    success = EmailService.mark_token_as_used(mock_db, token)
    assert success is True

    # Mark token used for non-existent token
    mock_db.query.return_value.filter.return_value.first.return_value = None
    not_found = EmailService.mark_token_as_used(mock_db, "missing")
    assert not_found is False


def test_email_service_verify_reset_token(mock_db):
    from datetime import datetime, timedelta
    from app.models.password_reset_token import PasswordResetToken

    # 1. Non-existent token
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert EmailService.verify_reset_token(mock_db, "nonexistent") is None

    # 2. Expired token
    expired_token = PasswordResetToken(
        token="expired",
        expires_at=datetime.utcnow() - timedelta(days=1),
        used_at=None,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = (
        expired_token
    )
    assert EmailService.verify_reset_token(mock_db, "expired") is None

    # 3. Already used token
    used_token = PasswordResetToken(
        token="used",
        expires_at=datetime.utcnow() + timedelta(days=1),
        used_at=datetime.utcnow(),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = (
        used_token
    )
    assert EmailService.verify_reset_token(mock_db, "used") is None

    # 4. Valid token
    target_user = User(id=77, email="valid@example.com")
    valid_token = PasswordResetToken(
        token="valid",
        expires_at=datetime.utcnow() + timedelta(days=1),
        used_at=None,
    )
    valid_token.user = target_user
    mock_db.query.return_value.filter.return_value.first.return_value = (
        valid_token
    )
    assert EmailService.verify_reset_token(mock_db, "valid") == target_user


@pytest.mark.asyncio
async def test_email_service_send_email_mocked():
    from unittest.mock import patch

    with patch(
        "app.services.email_service.fm.send_message", new_callable=AsyncMock
    ) as mock_send:
        mock_send.return_value = None
        result = await EmailService.send_password_reset_email(
            email="recipient@example.com",
            reset_token="test-token",
            user_name="Farmer John",
        )
        assert result is True
        assert mock_send.called


@pytest.mark.asyncio
async def test_email_service_send_email_exception():
    from unittest.mock import patch

    with patch(
        "app.services.email_service.fm.send_message",
        side_effect=Exception("SMTP Connection timed out"),
    ):
        result = await EmailService.send_password_reset_email(
            email="recipient@example.com",
            reset_token="test-token",
            user_name="Farmer John",
        )
        assert result is False
