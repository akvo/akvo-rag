import json
from unittest.mock import patch, AsyncMock
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from models import Base, KnowledgeBase, Document, DocumentChunk
from db.session import (
    engine as default_engine,
    AsyncSessionLocal,
    get_db_session,
    get_db,
    close_db_engine,
)
from cli.migrate_legacy_data import (
    LegacyDataMigrator,
    build_arg_parser,
    main as cli_main,
)


# =====================================================================
# Fixtures for Testing Async DB Session and Migrator
# =====================================================================


@pytest_asyncio.fixture
async def async_test_engine():
    """Create an isolated in-memory SQLite async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def legacy_source_db():
    """Temporary legacy SQLite DB representing standalone Postgres/MySQL."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE knowledge_bases (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                knowledge_base_id INTEGER NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                file_size BIGINT NOT NULL,
                content_type VARCHAR(100) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE document_chunks (
                id VARCHAR(64) PRIMARY KEY,
                kb_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                chunk_metadata TEXT,
                hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            )
        )

        # Seed sample legacy data
        conn.execute(
            text(
                """
            INSERT INTO knowledge_bases (id, name, description)
            VALUES (1, 'Legacy Agri Manuals', 'Old agricultural docs'),
                   (2, 'Legacy Water Standards', 'Historic WASH protocols');
            """
            )
        )
        conn.execute(
            text(
                """
            INSERT INTO documents (
                id, knowledge_base_id, file_name, file_path, file_size,
                content_type, file_hash
            )
            VALUES (101, 1, 'crops.pdf', 'uploads/crops.pdf', 1024,
                    'application/pdf', 'hash101'),
                   (102, 1, 'soil.pdf', 'uploads/soil.pdf', 2048,
                    'application/pdf', 'hash102'),
                   (201, 2, 'water_purity.pdf', 'uploads/water.pdf', 4096,
                    'application/pdf', 'hash201');
            """
            )
        )
        for i in range(1, 11):
            doc_id = 101 if i <= 5 else (102 if i <= 8 else 201)
            kb_id = 1 if doc_id in (101, 102) else 2
            chunk_meta = json.dumps({"page": i, "section": f"Section {i}"})
            conn.execute(
                text(
                    f"""
                INSERT INTO document_chunks (
                    id, kb_id, document_id, file_name, chunk_metadata, hash
                )
                VALUES (
                    'chunk-id-{i}', {kb_id}, {doc_id}, 'doc_{doc_id}.pdf',
                    '{chunk_meta}', 'chunk-hash-{i}'
                );
                """
                )
            )
    return engine


# =====================================================================
# Unit Tests: Async Session Manager (`db/session.py`)
# =====================================================================


def test_async_engine_configuration():
    """Verify default async engine connection pooling properties."""
    assert default_engine is not None
    assert hasattr(default_engine, "pool")
    assert AsyncSessionLocal is not None


@pytest.mark.asyncio
async def test_get_db_session_auto_commit(async_test_engine):
    """Verify get_db_session automatically commits transactions on success."""
    session_factory = async_sessionmaker(
        bind=async_test_engine, class_=AsyncSession, expire_on_commit=False
    )

    with patch("db.session.AsyncSessionLocal", session_factory):
        async with get_db_session() as session:
            kb = KnowledgeBase(
                name="Session Test KB",
                embedding_model="text-embedding-3-small",
                embedding_dim=1536,
            )
            session.add(kb)

    # Verify record was committed and is readable in a new session
    async with session_factory() as verify_session:
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.name == "Session Test KB"
        )
        result = await verify_session.execute(stmt)
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.name == "Session Test KB"


@pytest.mark.asyncio
async def test_get_db_session_rollback_on_exception(async_test_engine):
    """Verify get_db_session automatically rolls back on unhandled error."""
    session_factory = async_sessionmaker(
        bind=async_test_engine, class_=AsyncSession, expire_on_commit=False
    )

    with patch("db.session.AsyncSessionLocal", session_factory):
        with pytest.raises(ValueError, match="Simulated Transaction Failure"):
            async with get_db_session() as session:
                kb = KnowledgeBase(
                    name="Rollback KB",
                    embedding_model="text-embedding-3-small",
                    embedding_dim=1536,
                )
                session.add(kb)
                raise ValueError("Simulated Transaction Failure")

    # Verify record was NOT committed
    async with session_factory() as verify_session:
        stmt = select(KnowledgeBase).where(KnowledgeBase.name == "Rollback KB")
        result = await verify_session.execute(stmt)
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_get_db_generator():
    """Verify get_db() async generator yields session and cleans up."""
    gen = get_db()
    session = await anext(gen)
    assert isinstance(session, AsyncSession)
    try:
        await gen.asend(None)
    except StopAsyncIteration:
        pass


@pytest.mark.asyncio
async def test_close_db_engine():
    """Verify close_db_engine executes without raising errors."""
    await close_db_engine()


# =====================================================================
# Unit Tests: Legacy Data Migration CLI (`cli/migrate_legacy_data.py`)
# =====================================================================


@pytest.mark.asyncio
async def test_migrator_dry_run(legacy_source_db, async_test_engine):
    """Verify --dry-run counts source rows without modifying target DB."""
    migrator = LegacyDataMigrator(
        source_url="sqlite:///:memory:",
        target_url="sqlite+aiosqlite:///:memory:",
        batch_size=5,
        dry_run=True,
        source_engine=legacy_source_db,
        target_engine=async_test_engine,
    )

    counts = await migrator.migrate_all()
    assert counts["knowledge_bases"] == 2
    assert counts["documents"] == 3
    assert counts["document_chunks"] == 10

    # Ensure target DB is completely empty
    async with AsyncSession(async_test_engine) as session:
        kb_res = await session.execute(select(KnowledgeBase))
        doc_res = await session.execute(select(Document))
        chunk_res = await session.execute(select(DocumentChunk))

        assert len(kb_res.scalars().all()) == 0
        assert len(doc_res.scalars().all()) == 0
        assert len(chunk_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_migrator_full_migration(legacy_source_db, async_test_engine):
    """Verify ETL migration from source to target with defaults/metadata."""
    migrator = LegacyDataMigrator(
        source_url="sqlite:///:memory:",
        target_url="sqlite+aiosqlite:///:memory:",
        batch_size=4,
        dry_run=False,
        source_engine=legacy_source_db,
        target_engine=async_test_engine,
    )

    counts = await migrator.migrate_all()
    assert counts["knowledge_bases"] == 2
    assert counts["documents"] == 3
    assert counts["document_chunks"] == 10

    # Verify target DB records and defaults
    async with AsyncSession(async_test_engine) as session:
        # Check KnowledgeBases
        kb1 = (
            await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == 1)
            )
        ).scalar_one()
        assert kb1.name == "Legacy Agri Manuals"
        assert kb1.is_active is True
        assert kb1.embedding_model == "text-embedding-3-small"
        assert kb1.embedding_dim == 1536

        # Check Documents
        doc101 = (
            await session.execute(select(Document).where(Document.id == 101))
        ).scalar_one()
        assert doc101.knowledge_base_id == 1
        assert doc101.file_name == "crops.pdf"
        assert doc101.status == "INDEXED"
        assert doc101.doc_type == "LEGACY"

        # Check DocumentChunks
        chunk1 = (
            await session.execute(
                select(DocumentChunk).where(DocumentChunk.id == "chunk-id-1")
            )
        ).scalar_one()
        assert chunk1.kb_id == 1
        assert chunk1.document_id == 101
        assert chunk1.chunk_index == 0
        assert chunk1.chunk_metadata == {"page": 1, "section": "Section 1"}
        assert chunk1.content_hash == "chunk-hash-1"


@pytest.mark.asyncio
async def test_migrator_idempotency(legacy_source_db, async_test_engine):
    """Verify re-running migration multiple times is completely idempotent."""
    migrator = LegacyDataMigrator(
        source_url="sqlite:///:memory:",
        target_url="sqlite+aiosqlite:///:memory:",
        batch_size=5,
        dry_run=False,
        source_engine=legacy_source_db,
        target_engine=async_test_engine,
    )

    # Run 1
    counts1 = await migrator.migrate_all()
    assert counts1["knowledge_bases"] == 2
    assert counts1["documents"] == 3
    assert counts1["document_chunks"] == 10

    # Run 2 (Should execute ON CONFLICT DO NOTHING without raising errors)
    counts2 = await migrator.migrate_all()
    assert counts2["knowledge_bases"] == 2
    assert counts2["documents"] == 3
    assert counts2["document_chunks"] == 10

    # Total counts in DB should remain strictly 2, 3, 10
    async with AsyncSession(async_test_engine) as session:
        kbs = (await session.execute(select(KnowledgeBase))).scalars().all()
        docs = (await session.execute(select(Document))).scalars().all()
        chunks = (await session.execute(select(DocumentChunk))).scalars().all()

        assert len(kbs) == 2
        assert len(docs) == 3
        assert len(chunks) == 10


@pytest.mark.asyncio
async def test_migrator_chunk_batching(async_test_engine):
    """Verify chunk migration handles multiple batches via fetchmany."""
    src_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with src_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE knowledge_bases ("
                "id INT PRIMARY KEY, name TEXT, description TEXT, "
                "created_at TIMESTAMP, updated_at TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE documents ("
                "id INT PRIMARY KEY, knowledge_base_id INT, file_name TEXT, "
                "file_path TEXT, file_size INT, content_type TEXT, "
                "file_hash TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE document_chunks ("
                "id TEXT PRIMARY KEY, kb_id INT, document_id INT, "
                "file_name TEXT, chunk_metadata TEXT, hash TEXT, "
                "created_at TIMESTAMP)"
            )
        )

        conn.execute(
            text("INSERT INTO knowledge_bases (id, name) VALUES (1, 'B KB')")
        )
        conn.execute(
            text(
                "INSERT INTO documents ("
                "id, knowledge_base_id, file_name, file_path, "
                "file_size, content_type, file_hash) "
                "VALUES (1, 1, 'f.pdf', 'p', 1, 'pdf', 'h')"
            )
        )
        for i in range(15):
            conn.execute(
                text(
                    "INSERT INTO document_chunks ("
                    "id, kb_id, document_id, file_name, chunk_metadata, hash) "
                    f"VALUES ('chk-{i}', 1, 1, 'f.pdf', '{{}}', 'h-{i}')"
                )
            )

    migrator = LegacyDataMigrator(
        source_url="sqlite:///:memory:",
        target_url="sqlite+aiosqlite:///:memory:",
        batch_size=5,  # 15 items in 3 batches of 5
        dry_run=False,
        source_engine=src_engine,
        target_engine=async_test_engine,
    )

    counts = await migrator.migrate_all()
    assert counts["document_chunks"] == 15

    async with AsyncSession(async_test_engine) as session:
        chunks = (await session.execute(select(DocumentChunk))).scalars().all()
        assert len(chunks) == 15


@pytest.mark.asyncio
async def test_migrator_missing_optional_fields(async_test_engine):
    """Verify ETL properly handles NULL / invalid JSON in legacy metadata."""
    src_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with src_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE knowledge_bases ("
                "id INT PRIMARY KEY, name TEXT, description TEXT, "
                "created_at TIMESTAMP, updated_at TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE documents ("
                "id INT PRIMARY KEY, knowledge_base_id INT, file_name TEXT, "
                "file_path TEXT, file_size INT, content_type TEXT, "
                "file_hash TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE document_chunks ("
                "id TEXT PRIMARY KEY, kb_id INT, document_id INT, "
                "file_name TEXT, chunk_metadata TEXT, hash TEXT, "
                "created_at TIMESTAMP)"
            )
        )

        conn.execute(
            text(
                "INSERT INTO knowledge_bases (id, name, description) "
                "VALUES (1, 'Null KB', NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO documents ("
                "id, knowledge_base_id, file_name, file_path, "
                "file_size, content_type, file_hash) "
                "VALUES (1, 1, 'null_doc.pdf', 'p', 10, 'pdf', 'h')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO document_chunks ("
                "id, kb_id, document_id, file_name, chunk_metadata, hash) "
                "VALUES ("
                "'chk-null', 1, 1, 'null_doc.pdf', 'bad-json', 'h-null'"
                ")"
            )
        )

    migrator = LegacyDataMigrator(
        source_url="sqlite:///:memory:",
        target_url="sqlite+aiosqlite:///:memory:",
        batch_size=10,
        dry_run=False,
        source_engine=src_engine,
        target_engine=async_test_engine,
    )

    counts = await migrator.migrate_all()
    assert counts["knowledge_bases"] == 1
    assert counts["documents"] == 1
    assert counts["document_chunks"] == 1

    async with AsyncSession(async_test_engine) as session:
        kb = (
            await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == 1)
            )
        ).scalar_one()
        assert kb.description is None

        chunk = (
            await session.execute(
                select(DocumentChunk).where(DocumentChunk.id == "chk-null")
            )
        ).scalar_one()
        assert isinstance(chunk.chunk_metadata, dict)


def test_cli_argument_parsing():
    """Verify CLI argument parser configuration and defaults."""
    parser = build_arg_parser()

    # 1. Test basic args
    args = parser.parse_args(
        [
            "--source-url",
            "mysql+pymysql://root:pass@localhost:3306/legacy_db",
            "--batch-size",
            "250",
            "--dry-run",
        ]
    )
    assert (
        args.source_url == "mysql+pymysql://root:pass@localhost:3306/legacy_db"
    )
    assert args.batch_size == 250
    assert args.dry_run is True

    # 2. Test alias flag --source-mysql-url
    args_alias = parser.parse_args(
        [
            "--source-mysql-url",
            "mysql+pymysql://root:pass@localhost:3306/legacy_db",
        ]
    )
    assert (
        args_alias.source_url
        == "mysql+pymysql://root:pass@localhost:3306/legacy_db"
    )
    assert args_alias.batch_size == 500
    assert args_alias.dry_run is False


def test_cli_main_entrypoint():
    """Verify CLI main entrypoint executes migrator.migrate_all via asyncio."""
    with patch(
        "cli.migrate_legacy_data.build_arg_parser"
    ) as mock_parser_builder:
        mock_parser = mock_parser_builder.return_value
        mock_args = mock_parser.parse_args.return_value
        mock_args.source_url = "sqlite:///:memory:"
        mock_args.target_pg_url = "sqlite+aiosqlite:///:memory:"
        mock_args.batch_size = 100
        mock_args.dry_run = True

        with patch.object(
            LegacyDataMigrator, "migrate_all", new_callable=AsyncMock
        ) as mock_migrate:
            mock_migrate.return_value = {
                "knowledge_bases": 0,
                "documents": 0,
                "document_chunks": 0,
            }
            cli_main()
            mock_migrate.assert_awaited_once()
