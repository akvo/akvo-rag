from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.get_database_url,
    pool_size=1,  # default is 5 — increase for concurrency
    max_overflow=20,  # default is 10 — overflow connections allowed
    pool_timeout=30,  # how long to wait for a connection before error
    pool_recycle=1800,  # MySQL connections can die if idle too long
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
