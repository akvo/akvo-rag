from celery import Celery
from app.core.config import settings


CELERY_BROKER_URL = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//"  # noqa
CELERY_RESULT_BACKEND = "rpc://"

celery_app = Celery(
    "akvo_rag", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Connection and heartbeat settings - ADD THESE
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_heartbeat=30,  # Send heartbeat every 30 seconds (default is 10)
    broker_heartbeat_checkrate=2,  # Check every 2 heartbeats
    # Worker settings to prevent issues
    worker_prefetch_multiplier=1,  # Take 1 task at a time (prevents overload)
    # (prevents memory leaks)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 task
    worker_send_task_events=True,  # Enable task events for monitoring
    # RabbitMQ specific settings
    broker_pool_limit=10,  # Connection pool size
    broker_connection_timeout=30,  # Timeout for broker connections
)

celery_app.autodiscover_tasks(["app.tasks"])
