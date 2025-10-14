import pytest
from unittest.mock import Mock, patch
from app.services.app_service import AppService, DEFAULT_SCOPES
from app.schemas.app import AppRegisterRequest
from app.models.app import App, AppStatus


class TestAppService:
    """Test suite for AppService business logic."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def sample_register_data(self):
        return AppRegisterRequest(
            app_name="agriconnect",
            domain="agriconnect.akvo.org/api",
            default_chat_prompt="",
            chat_callback="https://agriconnect.akvo.org/api/ai/callback",
            upload_callback="https://agriconnect.akvo.org/api/kb/callback",
            callback_token="test_callback_token_123",
        )

    def test_generate_app_id_has_correct_prefix(self):
        """Test that generated app_id has 'app_' prefix."""
        app_id = AppService.generate_app_id()
        assert app_id.startswith("app_")
        assert len(app_id) > 4  # prefix + random part

    def test_generate_client_id_has_correct_prefix(self):
        """Test that generated client_id has 'ac_' prefix."""
        client_id = AppService.generate_client_id()
        assert client_id.startswith("ac_")
        assert len(client_id) > 3  # prefix + random part

    def test_generate_access_token_has_correct_prefix(self):
        """Test that generated access_token has 'tok_' prefix."""
        token = AppService.generate_access_token()
        assert token.startswith("tok_")
        assert len(token) > 4  # prefix + random part

    def test_create_app_generates_all_credentials(self, mock_db, sample_register_data):
        """Test that create_app generates all required credentials."""
        app, access_token = AppService.create_app(
            db=mock_db, register_data=sample_register_data
        )

        # Verify app object has correct attributes
        assert app.app_id.startswith("app_")
        assert app.client_id.startswith("ac_")
        assert app.app_name == "agriconnect"
        assert app.domain == "agriconnect.akvo.org/api"
        assert app.chat_callback_url == "https://agriconnect.akvo.org/api/ai/callback"
        assert app.upload_callback_url == "https://agriconnect.akvo.org/api/kb/callback"
        assert app.callback_token == "test_callback_token_123"
        assert app.status == AppStatus.active
        assert app.scopes == DEFAULT_SCOPES

        # Verify returned token
        assert access_token.startswith("tok_")

        # Verify DB operations
        mock_db.add.assert_called_once_with(app)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(app)

    def test_create_app_with_custom_scopes(self, mock_db, sample_register_data):
        """Test that create_app accepts custom scopes."""
        custom_scopes = ["custom.read", "custom.write"]
        app, _ = AppService.create_app(
            db=mock_db, register_data=sample_register_data, scopes=custom_scopes
        )

        assert app.scopes == custom_scopes

    def test_get_app_by_access_token(self, mock_db):
        """Test retrieving app by access token."""
        mock_app = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_app

        result = AppService.get_app_by_access_token(db=mock_db, access_token="tok_123")

        assert result == mock_app

    def test_get_app_by_app_id(self, mock_db):
        """Test retrieving app by app_id."""
        mock_app = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_app

        result = AppService.get_app_by_app_id(db=mock_db, app_id="app_123")

        assert result == mock_app

    def test_rotate_access_token(self, mock_db):
        """Test rotating access token."""
        mock_app = Mock()
        mock_app.access_token = "tok_old"

        new_token = AppService.rotate_access_token(db=mock_db, app=mock_app)

        assert new_token.startswith("tok_")
        assert new_token != "tok_old"
        assert mock_app.access_token == new_token
        mock_db.add.assert_called_once_with(mock_app)
        mock_db.commit.assert_called_once()

    def test_rotate_callback_token(self, mock_db):
        """Test rotating callback token."""
        mock_app = Mock()
        old_token = "old_callback_token"
        mock_app.callback_token = old_token
        new_token = "new_callback_token_123"

        AppService.rotate_callback_token(db=mock_db, app=mock_app, new_callback_token=new_token)

        assert mock_app.callback_token == new_token
        assert mock_app.callback_token != old_token
        mock_db.add.assert_called_once_with(mock_app)
        mock_db.commit.assert_called_once()

    def test_revoke_app(self, mock_db):
        """Test revoking an app."""
        mock_app = Mock()
        mock_app.status = AppStatus.active

        AppService.revoke_app(db=mock_db, app=mock_app)

        assert mock_app.status == AppStatus.revoked
        mock_db.add.assert_called_once_with(mock_app)
        mock_db.commit.assert_called_once()

    def test_is_app_active_returns_true_for_active(self):
        """Test is_app_active returns True for active app."""
        mock_app = Mock()
        mock_app.status = AppStatus.active

        assert AppService.is_app_active(mock_app) is True

    def test_is_app_active_returns_false_for_revoked(self):
        """Test is_app_active returns False for revoked app."""
        mock_app = Mock()
        mock_app.status = AppStatus.revoked

        assert AppService.is_app_active(mock_app) is False

    def test_is_app_active_returns_false_for_suspended(self):
        """Test is_app_active returns False for suspended app."""
        mock_app = Mock()
        mock_app.status = AppStatus.suspended

        assert AppService.is_app_active(mock_app) is False
