import logging
from datetime import datetime
from sqlalchemy.orm import Session
from getpass import getpass  # for password input

from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeBase
from app.models.user import User
from app.core import security
from app.core.minio import get_minio_client
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
from app.core.config import settings
from minio.error import MinioException


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def authenticate_superuser(email: str, password: str):
    """Authenticate user before allowing cleanup action."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print("❌ Invalid email or password")
            return None
        if not security.verify_password(password, user.hashed_password):
            print("❌ Invalid email or password")
            return None
        if not user.is_superuser:
            print("❌ User is not a superuser")
            return None
        if not user.is_active:
            print("❌ User is inactive")
            return None

        name = user.username or user.email
        print(f"✅ Welcome {name}, superuser authenticated")
        return user
    finally:
        db.close()


def preview_kbs(kb_ids=None, cutoff_date=None):
    """Preview KBs by ID list or cutoff date."""
    db: Session = SessionLocal()
    try:
        query = db.query(KnowledgeBase)
        if kb_ids:
            query = query.filter(KnowledgeBase.id.in_(kb_ids))
        elif cutoff_date:
            query = query.filter(KnowledgeBase.created_at < cutoff_date)

        kbs = query.all()
        if not kbs:
            print("No knowledge bases found for the given criteria")
            return []

        print(f"{len(kbs)} knowledge bases will be deleted:")
        for kb in kbs:
            print(f"- ID {kb.id} | Name: {kb.name} | Created: {kb.created_at}")
        return [kb.id for kb in kbs]
    finally:
        db.close()


def delete_kbs(kb_ids: list[int]):
    """Delete KBs list with cleanup (MinIO, vector store, DB)."""
    db: Session = SessionLocal()
    try:
        if not kb_ids:
            print("No knowledge bases found for deletion")
            return

        print(f"Deleting {len(kb_ids)} knowledge bases...")

        minio_client = get_minio_client()
        embeddings = EmbeddingsFactory.create()

        for kb_id in kb_ids:
            kb = (
                db.query(KnowledgeBase)
                .filter(KnowledgeBase.id == kb_id)
                .first()
            )
            if not kb:
                logger.warning(f"KB {kb_id} not found, skipping...")
                continue

            try:
                # Clean MinIO files
                try:
                    objects = minio_client.list_objects(
                        settings.MINIO_BUCKET_NAME, prefix=f"kb_{kb.id}/"
                    )
                    for obj in objects:
                        minio_client.remove_object(
                            settings.MINIO_BUCKET_NAME, obj.object_name
                        )
                    logger.info(f"MinIO cleanup completed for KB {kb.id}")
                except MinioException as me:
                    logger.warning(
                        f"MinIO cleanup failed for KB {kb.id}: {me}"
                    )

                # Clean vector store collection
                try:
                    vector_store = VectorStoreFactory.create(
                        store_type=settings.VECTOR_STORE_TYPE,
                        collection_name=f"kb_{kb.id}",
                        embedding_function=embeddings,
                    )
                    collection_name = f"kb_{kb.id}"
                    vector_store._store.delete_collection(collection_name)
                    logger.info(
                        f"Vector store cleanup completed for KB {kb.id}"
                    )
                except Exception as ve:
                    logger.warning(
                        f"Vector store cleanup failed for KB {kb.id}: {ve}"
                    )

                # Delete DB record
                db.delete(kb)
                db.commit()
                logger.info(f"Database record deleted for KB {kb.id}")

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete KB {kb_id}: {e}")

        logger.info("✅ All cleanup tasks completed.")
    finally:
        db.close()


if __name__ == "__main__":
    print("=== Knowledge Base Cleanup Tool ===")

    # --- LOGIN STEP ---
    email = input("Email: ").strip()
    password = getpass("Password: ")

    user = authenticate_superuser(email, password)
    if not user:
        print("❌ Authentication failed")
        exit(1)

    # --- MAIN ACTION ---
    action = input("Choose action (preview/delete): ").strip().lower()
    mode = input("Delete by (date/id): ").strip().lower()

    kb_ids = []
    cutoff_date = None

    if mode == "date":
        cutoff_date_str = input("Enter cutoff date (YYYY-MM-DD): ").strip()
        try:
            cutoff_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format! Use YYYY-MM-DD")
            exit(1)
        kb_ids = preview_kbs(cutoff_date=cutoff_date)

    elif mode == "id":
        id_str = input("Enter KB IDs (comma separated): ").strip()
        try:
            kb_ids = [int(x) for x in id_str.split(",") if x.strip().isdigit()]
        except ValueError:
            print("❌ Invalid IDs! Use comma-separated integers")
            exit(1)
        kb_ids = preview_kbs(kb_ids=kb_ids)

    else:
        print("❌ Unknown mode. Use 'date' or 'id'.")
        exit(1)

    if action == "delete" and kb_ids:
        confirm = (
            input(
                f"⚠️ Are you sure you want to delete {len(kb_ids)} KBs? (yes/no): "
            )
            .strip()
            .lower()
        )
        if confirm == "yes":
            delete_kbs(kb_ids)
        else:
            print("❌ Cancelled.")
