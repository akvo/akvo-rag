from typing import Optional
from sqlalchemy.orm import Session
from app.models.system_setting import SystemSetting

DEFAULT_TOP_K = 4


class SystemSettingsService:
    """Service for managing global system settings."""
    
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_setting(self, key: str) -> SystemSetting:
        """Retrieve a setting by its key."""
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            raise ValueError(f"Setting with key '{key}' not found.")
        return setting

    def update_setting(self, key: str, value: str) -> SystemSetting:
        """Update a setting's value by its key."""
        setting = self.get_setting(key)
        setting.value = value
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def get_top_k(self) -> int:
        """Retrieve the global top_k value with fallback to default."""
        try:
            setting = self.get_setting("top_k")
            return int(setting.value)
        except ValueError:
            # Setting not found, return default
            return DEFAULT_TOP_K

    def update_top_k(self, top_k: int) -> SystemSetting:
        """Update the global top_k value with validation."""
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        return self.update_setting("top_k", str(top_k))
