import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.seeder.seed_admin_user import seed_admin_user
from app.seeder.seed_prompts import seed_prompts


def test_seed_admin_user_passwords_mismatch():
    mock_db = MagicMock()
    res = seed_admin_user(
        db=mock_db,
        email="admin@example.com",
        username="admin",
        password="pass1",
        confirm_password="pass2",
    )
    assert res is None
    mock_db.add.assert_not_called()


def test_seed_admin_user_missing_fields():
    mock_db = MagicMock()
    res = seed_admin_user(
        db=mock_db,
        email="",
        username="admin",
        password="p",
        confirm_password="p",
    )
    assert res is None


def test_seed_admin_user_success():
    mock_db = MagicMock()
    res = seed_admin_user(
        db=mock_db,
        email="superadmin@example.com",
        username="superadmin",
        password="SecretPassword123!",
        confirm_password="SecretPassword123!",
    )
    assert res is not None
    assert res.email == "superadmin@example.com"
    assert res.is_superuser is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_seed_prompts_all_flows():
    mock_db = MagicMock()
    # First call: definitions not found (new seed)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    with patch("app.seeder.seed_prompts.SessionLocal", return_value=mock_db):
        seed_prompts()
        assert mock_db.commit.called
        assert mock_db.close.called
