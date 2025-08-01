import pytest
from unittest.mock import Mock
from app.services.system_settings_service import SystemSettingsService, DEFAULT_TOP_K


class TestSystemSettingsService:
    """Test suite for SystemSettingsService business logic."""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    def test_get_top_k_returns_default_when_setting_not_found(self, mock_db):
        """Test that get_top_k returns default value when setting doesn't exist."""
        # Mock query chain to return None (setting not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = SystemSettingsService(mock_db)
        result = service.get_top_k()
        
        assert result == DEFAULT_TOP_K

    def test_get_top_k_returns_stored_value(self, mock_db):
        """Test that get_top_k returns the stored value when setting exists."""
        # Mock setting with value "8"
        mock_setting = Mock()
        mock_setting.value = "8"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_setting
        
        service = SystemSettingsService(mock_db)
        result = service.get_top_k()
        
        assert result == 8

    def test_update_top_k_validates_positive_integers(self, mock_db):
        """Test that update_top_k validates input and rejects invalid values."""
        service = SystemSettingsService(mock_db)
        
        # Test invalid values are rejected
        with pytest.raises(ValueError, match="top_k must be a positive integer"):
            service.update_top_k(0)
            
        with pytest.raises(ValueError, match="top_k must be a positive integer"):
            service.update_top_k(-1)

    def test_update_top_k_accepts_valid_values(self, mock_db):
        """Test that update_top_k accepts valid positive integers."""
        # Mock existing setting
        mock_setting = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_setting
        
        service = SystemSettingsService(mock_db)
        
        # Should not raise an exception
        result = service.update_top_k(5)
        
        # Verify the setting value was updated
        assert mock_setting.value == "5"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_setting)
        assert result == mock_setting

    def test_get_setting_raises_error_for_nonexistent_key(self, mock_db):
        """Test that get_setting raises ValueError for non-existent keys."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = SystemSettingsService(mock_db)
        
        with pytest.raises(ValueError, match="Setting with key 'nonexistent' not found"):
            service.get_setting("nonexistent")

    def test_update_setting_updates_existing_setting(self, mock_db):
        """Test that update_setting properly updates an existing setting."""
        # Mock existing setting
        mock_setting = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_setting
        
        service = SystemSettingsService(mock_db)
        result = service.update_setting("test_key", "new_value")
        
        # Verify the setting was updated
        assert mock_setting.value == "new_value"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_setting)
        assert result == mock_setting