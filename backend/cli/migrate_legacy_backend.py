"""CLI script to migrate legacy backend MySQL data into PostgreSQL 17.

Executed directly within the backend container using SQLAlchemy &
mysql-connector-python.
"""
import argparse
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [backend_migrator] %(message)s",
)
logger = logging.getLogger("backend_migrator")

DEFAULT_SOURCE_URL = os.getenv(
    "LEGACY_MYSQL_URL",
    "mysql+mysqlconnector://root:root@legacy-mysql:3306/ragwebui",
)
DEFAULT_TARGET_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@postgres:5432/akvo_rag",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def sanitize(val: Any) -> Any:
    """Recursively remove null bytes from strings, dicts, lists."""
    if isinstance(val, str):
        return val.replace("\x00", "").replace("\u0000", "")
    elif isinstance(val, dict):
        return {sanitize(k): sanitize(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize(i) for i in val]
    return val


class LegacyBackendMigrator:
    """Handles migration of legacy MySQL backend tables into PostgreSQL."""

    def __init__(
        self,
        source_url: str = DEFAULT_SOURCE_URL,
        target_url: str = DEFAULT_TARGET_URL,
        dry_run: bool = False,
    ):
        self.source_url = source_url
        self.target_url = target_url
        self.dry_run = dry_run
        self.source_engine = create_engine(self.source_url)
        self.target_engine = create_engine(self.target_url)

    def run(self) -> Dict[str, int]:
        """Execute full backend migration sequence."""
        logger.info("=" * 60)
        logger.info("Starting Backend MySQL -> PostgreSQL 17 Migration")
        logger.info("Source:  %s", self.source_url)
        logger.info("Target:  %s", self.target_url)
        logger.info("Dry Run: %s", self.dry_run)
        logger.info("=" * 60)

        counts = {}

        with (
            self.source_engine.connect() as m_conn,
            self.target_engine.connect() as p_conn,
        ):
            # 1. Users
            counts["users"] = self._migrate_users(m_conn, p_conn)

            # 2. Apps
            counts["apps"] = self._migrate_apps(m_conn, p_conn)

            # 3. App Knowledge Bases
            counts["app_knowledge_bases"] = self._migrate_app_kbs(
                m_conn, p_conn
            )

            # 4. Chats
            counts["chats"] = self._migrate_chats(m_conn, p_conn)

            # 5. Messages
            counts["messages"] = self._migrate_messages(m_conn, p_conn)

            # 6. Chat Knowledge Bases
            counts["chat_knowledge_bases"] = self._migrate_chat_kbs(
                m_conn, p_conn
            )

            # 7. System Settings
            counts["system_settings"] = self._migrate_settings(
                m_conn, p_conn
            )

            if not self.dry_run:
                self._reset_sequences(p_conn)
                p_conn.commit()

        logger.info("=" * 60)
        logger.info("BACKEND MIGRATION SUMMARY:")
        for tbl, cnt in counts.items():
            logger.info("  • %-22s : %d", tbl, cnt)
        logger.info("=" * 60)
        return counts

    def _migrate_users(self, m_conn, p_conn) -> int:
        logger.info("Migrating users...")
        query = text("SELECT * FROM users ORDER BY id ASC")
        users = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(users)

        for u in users:
            check_stmt = text(
                "SELECT id FROM users WHERE id = :id OR email = :email"
            )
            exists = p_conn.execute(
                check_stmt, {"id": u["id"], "email": u["email"]}
            ).first()
            if not exists:
                insert_stmt = text("""
                    INSERT INTO users (
                        id, email, username, hashed_password,
                        is_active, is_superuser, created_at,
                        updated_at, approved_by, approved_at
                    ) VALUES (
                        :id, :email, :username, :hashed_password,
                        :is_active, :is_superuser, :created_at,
                        :updated_at, :approved_by, :approved_at
                    )
                """)
                p_conn.execute(
                    insert_stmt,
                    {
                        "id": u["id"],
                        "email": sanitize(u["email"]),
                        "username": sanitize(u["username"]),
                        "hashed_password": u["hashed_password"],
                        "is_active": bool(u.get("is_active", True)),
                        "is_superuser": bool(u.get("is_superuser", False)),
                        "created_at": u.get("created_at") or datetime.utcnow(),
                        "updated_at": u.get("updated_at") or datetime.utcnow(),
                        "approved_by": u.get("approved_by"),
                        "approved_at": u.get("approved_at"),
                    },
                )
        p_conn.commit()
        return len(users)

    def _migrate_apps(self, m_conn, p_conn) -> int:
        logger.info("Migrating apps...")
        query = text("SELECT * FROM apps ORDER BY id ASC")
        apps = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(apps)

        for a in apps:
            scopes = a.get("scopes")
            if isinstance(scopes, str):
                try:
                    scopes = json.loads(scopes)
                except Exception:
                    scopes = [scopes]
            elif not isinstance(scopes, list):
                scopes = []

            status = str(a.get("status") or "active").lower()
            if status not in ("active", "revoked", "suspended"):
                status = "active"

            check_stmt = text(
                "SELECT id FROM apps WHERE id = :id OR app_id = :app_id"
            )
            exists = p_conn.execute(
                check_stmt, {"id": a["id"], "app_id": a["app_id"]}
            ).first()
            if not exists:
                insert_stmt = text("""
                    INSERT INTO apps (
                        id, app_id, client_id, app_name, domain,
                        default_chat_prompt, chat_callback_url,
                        upload_callback_url, access_token, callback_token,
                        scopes, status, created_at, updated_at
                    ) VALUES (
                        :id, :app_id, :client_id, :app_name, :domain,
                        :default_chat_prompt, :chat_callback_url,
                        :upload_callback_url, :access_token, :callback_token,
                        :scopes, CAST(:status AS appstatus), :created_at,
                        :updated_at
                    )
                """)
                p_conn.execute(
                    insert_stmt,
                    {
                        "id": a["id"],
                        "app_id": sanitize(a["app_id"]),
                        "client_id": sanitize(a["client_id"]),
                        "app_name": sanitize(a["app_name"]),
                        "domain": sanitize(a["domain"]),
                        "default_chat_prompt": sanitize(
                            a.get("default_chat_prompt")
                        ),
                        "chat_callback_url": sanitize(
                            a["chat_callback_url"]
                        ),
                        "upload_callback_url": sanitize(
                            a["upload_callback_url"]
                        ),
                        "access_token": sanitize(a["access_token"]),
                        "callback_token": sanitize(a.get("callback_token")),
                        "scopes": json.dumps(scopes),
                        "status": status,
                        "created_at": a.get("created_at") or datetime.utcnow(),
                        "updated_at": a.get("updated_at") or datetime.utcnow(),
                    },
                )
        p_conn.commit()
        return len(apps)

    def _migrate_app_kbs(self, m_conn, p_conn) -> int:
        logger.info("Migrating app_knowledge_bases...")
        query = text("SELECT * FROM app_knowledge_bases ORDER BY id ASC")
        app_kbs = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(app_kbs)

        for akb in app_kbs:
            check_stmt = text(
                "SELECT id FROM app_knowledge_bases WHERE id = :id"
            )
            exists = p_conn.execute(check_stmt, {"id": akb["id"]}).first()
            if not exists:
                insert_stmt = text("""
                    INSERT INTO app_knowledge_bases (
                        id, app_id, knowledge_base_id, is_default,
                        created_at, updated_at
                    ) VALUES (
                        :id, :app_id, :knowledge_base_id, :is_default,
                        :created_at, :updated_at
                    )
                    ON CONFLICT (app_id, knowledge_base_id) DO NOTHING
                """)
                p_conn.execute(
                    insert_stmt,
                    {
                        "id": akb["id"],
                        "app_id": akb["app_id"],
                        "knowledge_base_id": akb["knowledge_base_id"],
                        "is_default": bool(akb.get("is_default", False)),
                        "created_at": (
                            akb.get("created_at") or datetime.utcnow()
                        ),
                        "updated_at": (
                            akb.get("updated_at") or datetime.utcnow()
                        ),
                    },
                )
        p_conn.commit()
        return len(app_kbs)

    def _migrate_chats(self, m_conn, p_conn) -> int:
        logger.info("Migrating chats...")
        query = text("SELECT * FROM chats ORDER BY id ASC")
        chats = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(chats)

        for c in chats:
            check_stmt = text("SELECT id FROM chats WHERE id = :id")
            exists = p_conn.execute(check_stmt, {"id": c["id"]}).first()
            if not exists:
                insert_stmt = text("""
                    INSERT INTO chats (
                        id, title, user_id, created_at, updated_at
                    ) VALUES (
                        :id, :title, :user_id, :created_at, :updated_at
                    )
                """)
                p_conn.execute(
                    insert_stmt,
                    {
                        "id": c["id"],
                        "title": sanitize(c["title"]),
                        "user_id": c["user_id"],
                        "created_at": c.get("created_at") or datetime.utcnow(),
                        "updated_at": c.get("updated_at") or datetime.utcnow(),
                    },
                )
        p_conn.commit()
        return len(chats)

    def _migrate_messages(self, m_conn, p_conn) -> int:
        logger.info("Migrating messages...")
        query = text("SELECT * FROM messages ORDER BY id ASC")
        messages = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(messages)

        for m in messages:
            check_stmt = text("SELECT id FROM messages WHERE id = :id")
            exists = p_conn.execute(check_stmt, {"id": m["id"]}).first()
            if not exists:
                insert_stmt = text("""
                    INSERT INTO messages (
                        id, chat_id, role, content, created_at, updated_at
                    ) VALUES (
                        :id, :chat_id, :role, :content, :created_at,
                        :updated_at
                    )
                """)
                p_conn.execute(
                    insert_stmt,
                    {
                        "id": m["id"],
                        "chat_id": m["chat_id"],
                        "role": sanitize(m["role"]),
                        "content": sanitize(m["content"]),
                        "created_at": m.get("created_at") or datetime.utcnow(),
                        "updated_at": m.get("updated_at") or datetime.utcnow(),
                    },
                )
        p_conn.commit()
        return len(messages)

    def _migrate_chat_kbs(self, m_conn, p_conn) -> int:
        logger.info("Migrating chat_knowledge_bases...")
        query = text("SELECT * FROM chat_knowledge_bases")
        chat_kbs = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(chat_kbs)

        for ckb in chat_kbs:
            insert_stmt = text("""
                INSERT INTO chat_knowledge_bases (
                    chat_id, knowledge_base_id
                ) VALUES (
                    :chat_id, :knowledge_base_id
                )
                ON CONFLICT (chat_id, knowledge_base_id) DO NOTHING
            """)
            p_conn.execute(
                insert_stmt,
                {
                    "chat_id": ckb["chat_id"],
                    "knowledge_base_id": ckb["knowledge_base_id"],
                },
            )
        p_conn.commit()
        return len(chat_kbs)

    def _migrate_settings(self, m_conn, p_conn) -> int:
        logger.info("Migrating system_settings...")
        query = text("SELECT * FROM system_settings ORDER BY id ASC")
        settings = m_conn.execute(query).mappings().all()
        if self.dry_run:
            return len(settings)

        for s in settings:
            insert_stmt = text("""
                INSERT INTO system_settings (
                    id, key, value
                ) VALUES (
                    :id, :key, :value
                )
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """)
            p_conn.execute(
                insert_stmt,
                {
                    "id": s["id"],
                    "key": sanitize(s["key"]),
                    "value": sanitize(s["value"]),
                },
            )
        p_conn.commit()
        return len(settings)

    def _reset_sequences(self, p_conn) -> None:
        logger.info("Resetting PostgreSQL sequences...")
        tables = [
            "users",
            "apps",
            "app_knowledge_bases",
            "chats",
            "messages",
            "system_settings",
        ]
        for tbl in tables:
            p_conn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), "
                    f"coalesce(max(id), 1)) FROM {tbl};"
                )
            )
        logger.info("PostgreSQL sequences reset successfully.")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build and configure CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Migrate legacy backend MySQL data into PostgreSQL 17."
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="Source legacy MySQL database SQLAlchemy URL.",
    )
    parser.add_argument(
        "--target-url",
        default=DEFAULT_TARGET_URL,
        help="Target PostgreSQL 17 database SQLAlchemy URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without modifying the target database.",
    )
    return parser


def main() -> None:
    """CLI execution entrypoint."""
    parser = build_arg_parser()
    args = parser.parse_args()
    migrator = LegacyBackendMigrator(
        source_url=args.source_url,
        target_url=args.target_url,
        dry_run=args.dry_run,
    )
    migrator.run()


if __name__ == "__main__":
    main()
