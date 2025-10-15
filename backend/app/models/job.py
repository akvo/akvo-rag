import uuid

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False, default="chat")
    status = Column(
        String,
        nullable=False,
        default="pending"
    ) # pending|running|completed|failed
    input_data = Column(Text) # JSON string of input (prompt, chats, etc.)
    output = Column(Text, nullable=True)
    callback_url = Column(String, nullable=True)
    callback_params = Column(Text, nullable=True)
    trace_id = Column(String, nullable=True)