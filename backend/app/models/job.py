import uuid

from sqlalchemy import Column, String, Text
from app.models.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(
        String(100),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4())
    )
    app_id = Column(String(100), nullable=True)  # optional, for future use
    celery_task_id = Column(String(255), nullable=True)
    job_type = Column(String(75), nullable=False, default="chat")
    status = Column(
        String(50),
        nullable=False,
        default="pending"
    ) # pending|running|completed|failed
    input_data = Column(Text) # JSON string of input (prompt, chats, etc.)
    output = Column(Text, nullable=True)
    callback_url = Column(String(850), nullable=True)
    callback_params = Column(Text, nullable=True)
    trace_id = Column(String(110), nullable=True)