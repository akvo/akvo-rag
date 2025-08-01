from sqlalchemy import Column, String, Integer
from app.models.base import Base


class SystemSetting(Base):
    """
    Stores global system settings as key-value pairs.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    value = Column(String(255), nullable=False)
