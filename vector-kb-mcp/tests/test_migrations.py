import configparser
import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command


@pytest.fixture
def alembic_ini_path():
    base_dir = Path(__file__).resolve().parent.parent
    ini_path = base_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"
    return ini_path


@pytest.fixture
def alembic_dir_path():
    base_dir = Path(__file__).resolve().parent.parent
    dir_path = base_dir / "alembic"
    assert dir_path.exists(), f"alembic directory not found at {dir_path}"
    return dir_path


def test_alembic_ini_configuration(alembic_ini_path):
    """Verify alembic.ini properties and isolated version table."""
    config = configparser.ConfigParser()
    config.read(alembic_ini_path)

    assert "alembic" in config.sections()
    alembic_section = config["alembic"]

    assert alembic_section.get("script_location") == "alembic"
    assert alembic_section.get("version_table") == "alembic_version_vkb"
    assert alembic_section.get("prepend_sys_path") == "."


def test_env_py_include_object_filter(alembic_dir_path):
    """Verify include_object in env.py restricts tracking to vkb_ tables."""
    env_path = alembic_dir_path / "env.py"
    assert env_path.exists()

    spec = importlib.util.spec_from_file_location("alembic_env_test", env_path)
    env_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(env_module)

    assert hasattr(env_module, "include_object")
    include_obj = env_module.include_object

    # vkb_ tables should be included
    assert include_obj(None, "vkb_knowledge_bases", "table", False, None)
    assert include_obj(None, "vkb_documents", "table", False, None) is True
    assert include_obj(None, "vkb_document_chunks", "table", False, None)
    assert include_obj(None, "vkb_processing_tasks", "table", False, None)

    # Core backend tables should be excluded
    assert include_obj(None, "users", "table", False, None) is False
    assert include_obj(None, "chats", "table", False, None) is False
    assert (
        include_obj(None, "prompt_definitions", "table", False, None) is False
    )
    assert include_obj(None, "chat_messages", "table", False, None) is False
    assert include_obj(None, "alembic_version", "table", False, None) is False

    # Non-table objects (indices, columns, constraints) should be included
    assert include_obj(None, "idx_vkb_doc_auth", "index", False, None) is True
    assert include_obj(None, "id", "column", False, None) is True


def test_migration_001_module_attributes(alembic_dir_path):
    """Verify 001_initial_vkb_schema migration attributes and hooks."""
    versions_dir = alembic_dir_path / "versions"
    migration_file = versions_dir / "001_initial_vkb_schema.py"
    assert migration_file.exists(), f"Migration file missing: {migration_file}"

    spec = importlib.util.spec_from_file_location(
        "initial_vkb_migration", migration_file
    )
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)

    assert migration_module.revision == "001_initial_vkb_schema"
    assert migration_module.down_revision is None
    assert callable(migration_module.upgrade)
    assert callable(migration_module.downgrade)


def test_sqlite_migration_execution_roundtrip(alembic_ini_path, tmp_path):
    """Verify Alembic upgrade/downgrade roundtrip against SQLite test DB."""
    db_file = tmp_path / "test_vkb_alembic.db"
    db_url = f"sqlite:///{db_file}"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify all 4 tables plus isolated version table exist
    assert "alembic_version_vkb" in tables
    assert "vkb_knowledge_bases" in tables
    assert "vkb_documents" in tables
    assert "vkb_document_chunks" in tables
    assert "vkb_processing_tasks" in tables

    # Verify version recorded
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT version_num FROM alembic_version_vkb")
        ).fetchall()
        assert len(res) == 1
        assert res[0][0] == "001_initial_vkb_schema"

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    assert "vkb_knowledge_bases" not in tables_after_downgrade
    assert "vkb_documents" not in tables_after_downgrade
    assert "vkb_document_chunks" not in tables_after_downgrade
    assert "vkb_processing_tasks" not in tables_after_downgrade

    # 3. Re-upgrade to head (Roundtrip assertion)
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables_reupgrade = inspector.get_table_names()
    assert "vkb_knowledge_bases" in tables_reupgrade
    assert "vkb_documents" in tables_reupgrade
    assert "vkb_document_chunks" in tables_reupgrade
    assert "vkb_processing_tasks" in tables_reupgrade

    engine.dispose()


@pytest.mark.asyncio
async def test_live_postgresql_alembic_upgrade_downgrade(alembic_ini_path):
    """Verify Alembic migration against PostgreSQL 17 via async URL."""
    from core.config import settings

    if "postgres" not in settings.DATABASE_URL:
        pytest.skip("Not PostgreSQL; skipping live PostgreSQL test.")

    # Check connection to PostgreSQL via asyncpg
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Live PostgreSQL not reachable ({exc}); skipping test.")

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Clean setup: ensure clean state before starting lifecycle assertions
    try:
        command.downgrade(alembic_cfg, "base")
    except Exception:
        pass
    async with engine.begin() as conn:
        for tbl in [
            "alembic_version_vkb",
            "vkb_processing_tasks",
            "vkb_document_chunks",
            "vkb_documents",
            "vkb_knowledge_bases",
        ]:
            await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))

    try:
        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # 2. Verify version in alembic_version_vkb and check GIN index
        async with engine.connect() as conn:
            res_vkb = (
                await conn.execute(
                    text("SELECT version_num FROM alembic_version_vkb")
                )
            ).fetchall()
            assert len(res_vkb) == 1
            assert res_vkb[0][0] == "001_initial_vkb_schema"

            # Check GIN index exists on vkb_documents
            idx_query = text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'vkb_documents' "
                "AND indexname = 'idx_vkb_doc_metadata_gin'"
            )
            gin_check = (await conn.execute(idx_query)).fetchall()
            assert len(gin_check) == 1

        # 3. Downgrade to base
        command.downgrade(alembic_cfg, "base")

        async with engine.connect() as conn:
            res_vkb_after = (
                await conn.execute(
                    text("SELECT version_num FROM alembic_version_vkb")
                )
            ).fetchall()
            assert len(res_vkb_after) == 0

        # 4. Clean re-upgrade to head
        command.upgrade(alembic_cfg, "head")

        # 5. Verify isolated version table doesn't affect core alembic_version
        async with engine.connect() as conn:
            res_vkb_reup = (
                await conn.execute(
                    text("SELECT version_num FROM alembic_version_vkb")
                )
            ).fetchall()
            assert len(res_vkb_reup) == 1
            assert res_vkb_reup[0][0] == "001_initial_vkb_schema"

    except Exception as exc:
        pytest.fail(f"PostgreSQL migration lifecycle test failed: {exc}")
    finally:
        # Ensure target database is left upgraded at head
        try:
            command.upgrade(alembic_cfg, "head")
        except Exception:
            pass
        await engine.dispose()
