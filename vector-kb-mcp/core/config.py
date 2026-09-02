from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Redis Queue Configuration
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    REQUEST_QUEUE: str = Field(default="mcp:vector:requests")
    RESPONSE_PREFIX: str = Field(default="mcp:vector:responses")
    RESPONSE_TTL_SECONDS: int = Field(default=60)

    # Database Configuration (PostgreSQL 17)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag"
    )

    # ChromaDB Vector Store Configuration
    CHROMA_HOST: str = Field(default="chromadb")
    CHROMA_PORT: int = Field(default=8000)

    # MinIO Object Storage Configuration
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_DOCUMENTS: str = Field(default="documents")
    MINIO_SECURE: bool = Field(default=False)

    # OpenAI API Configuration
    OPENAI_API_KEY: str = Field(default="")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")


settings = Settings()
