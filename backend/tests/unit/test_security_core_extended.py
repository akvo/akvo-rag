from datetime import timedelta
from jose import jwt
from app.core import security
from app.core.config import settings


def test_password_hash_and_verification():
    raw = "agri_pass_123"
    hashed = security.get_password_hash(raw)
    assert hashed != raw
    assert security.verify_password(raw, hashed) is True
    assert security.verify_password("wrong_password", hashed) is False


def test_create_and_decode_access_token():
    payload = {"sub": "agriconnect_user", "scope": "read"}
    token = security.create_access_token(
        data=payload, expires_delta=timedelta(minutes=15)
    )
    assert token is not None

    decoded = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert decoded["sub"] == "agriconnect_user"
    assert decoded["scope"] == "read"
    assert "exp" in decoded


def test_create_access_token_default_expiry():
    token = security.create_access_token(data={"sub": "user_default"})
    decoded = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert decoded["sub"] == "user_default"
    assert "exp" in decoded


def test_get_current_user_and_errors():
    from unittest.mock import MagicMock
    import pytest
    from fastapi import HTTPException
    from app.models.user import User

    mock_db = MagicMock()
    # 1. User found and active
    active_user = User(id=1, username="test_user", is_active=True)
    mock_db.query.return_value.filter.return_value.first.return_value = (
        active_user
    )
    token = security.create_access_token(data={"sub": "test_user"})
    user = security.get_current_user(db=mock_db, token=token)
    assert user == active_user

    # 2. Inactive user
    inactive_user = User(id=2, username="inactive", is_active=False)
    mock_db.query.return_value.filter.return_value.first.return_value = (
        inactive_user
    )
    token_inactive = security.create_access_token(data={"sub": "inactive"})
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(db=mock_db, token=token_inactive)
    assert exc.value.status_code == 401
    assert "Inactive user" in exc.value.detail

    # 3. User not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(db=mock_db, token=token)
    assert exc.value.status_code == 401
    assert "Could not validate credentials" in exc.value.detail

    # 4. Invalid token
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(db=mock_db, token="invalid.token.here")
    assert exc.value.status_code == 401


def test_get_api_key_user_and_errors():
    from unittest.mock import MagicMock
    import pytest
    from fastapi import HTTPException
    from app.models.api_key import APIKey
    from app.models.user import User

    mock_db = MagicMock()

    # 1. Missing api_key header
    with pytest.raises(HTTPException) as exc:
        security.get_api_key_user(db=mock_db, api_key="")
    assert exc.value.status_code == 401
    assert "missing" in exc.value.detail

    # 2. Invalid api_key
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        security.get_api_key_user(db=mock_db, api_key="sk-unknown")
    assert exc.value.status_code == 401
    assert "Invalid API key" in exc.value.detail

    # 3. Inactive api_key
    fake_user = User(id=1, username="farmer_user", is_active=True)
    inactive_key = APIKey(id=1, key="sk-test", is_active=False, user=fake_user)
    mock_db.query.return_value.filter.return_value.first.return_value = (
        inactive_key
    )
    with pytest.raises(HTTPException) as exc:
        security.get_api_key_user(db=mock_db, api_key="sk-test")
    assert exc.value.status_code == 401
    assert "Inactive API key" in exc.value.detail

    # 4. Active api_key
    active_key = APIKey(id=2, key="sk-active", is_active=True, user=fake_user)
    mock_db.query.return_value.filter.return_value.first.return_value = (
        active_key
    )
    user = security.get_api_key_user(db=mock_db, api_key="sk-active")
    assert user == fake_user
