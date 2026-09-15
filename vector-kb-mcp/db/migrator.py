import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Tuple

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from core.config import settings

logger = logging.getLogger("vector-kb-mcp")


class DatabaseMigrator:
    """
    Vector KB MCP database auto-migrator matching the backend
    DatabaseMigrator architecture.
    """

    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.db_url = db_url
        self.alembic_cfg = self._get_alembic_config()

    def _get_sync_db_url(self) -> str:
        url = self.db_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://"
            )
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url

    @contextmanager
    def database_connection(self) -> Generator[Connection, None, None]:
        """Context manager for synchronous database connection with timeout."""
        sync_url = self._get_sync_db_url()
        connect_args = {}
        if not sync_url.startswith("sqlite"):
            connect_args["connect_timeout"] = 3

        engine = create_engine(sync_url, connect_args=connect_args)
        try:
            with engine.connect() as connection:
                yield connection
        except Exception as e:
            logger.error(
                "Database connection error during migration check: %s", e
            )
            raise
        finally:
            engine.dispose()

    def check_migration_needed(self) -> Tuple[bool, str, str]:
        """
        Check if vector-kb-mcp database migration is needed.
        """
        with self.database_connection() as connection:
            context = MigrationContext.configure(
                connection, opts={"version_table": "alembic_version_vkb"}
            )
            current_rev = context.get_current_revision()
            heads = context.get_current_heads()

        if not heads:
            logger.warning(
                "No migration heads found for Vector KB. "
                "Database might not be initialized."
            )
            return True, current_rev or "None", "head"

        head_rev = heads[0]
        return current_rev != head_rev, current_rev or "None", head_rev

    def _get_alembic_config(self) -> Config:
        """Create and configure Alembic config for vector-kb-mcp."""
        project_root = Path(__file__).resolve().parents[1]
        alembic_cfg = Config(project_root / "alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        return alembic_cfg

    def run_migrations(self) -> None:
        """Run database migrations if needed."""
        try:
            needs_migration, current_rev, head_rev = (
                self.check_migration_needed()
            )

            if needs_migration:
                logger.info(
                    "Current Vector KB revision: %s, upgrading to: %s",
                    current_rev,
                    head_rev,
                )
                self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)

                command.upgrade(self.alembic_cfg, "head")

                logger.info(
                    "Vector KB database migrations completed successfully"
                )
            else:
                logger.info(
                    "Vector KB database is already at the latest version: %s",
                    current_rev,
                )
        except Exception as e:
            logger.error("Error during Vector KB database migration: %s", e)
            raise


def run_vkb_migrations(db_url: str = settings.DATABASE_URL) -> None:
    """Convenience helper function to run migrations on startup."""
    migrator = DatabaseMigrator(db_url=db_url)
    migrator.run_migrations()
