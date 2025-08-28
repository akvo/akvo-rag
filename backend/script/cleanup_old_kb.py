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


def preview_old_kbs(cutoff_date: datetime):
    """Preview all knowledge bases created before cutoff_date."""
    db: Session = SessionLocal()
    try:
        kbs = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.created_at < cutoff_date)
            .all()
        )
        if not kbs:
            print(f"No knowledge bases found before {cutoff_date}")
            return
        print(
            f"{len(kbs)} knowledge bases will be deleted (created_at < {cutoff_date.date()}):"
        )
        for kb in kbs:
            print(f"- ID {kb.id} | Name: {kb.name} | Created: {kb.created_at}")
    finally:
        db.close()


def delete_old_kbs(cutoff_date: datetime):
    """
    Delete all knowledge bases created before cutoff_date, including cleanup of
    MinIO objects, vector store collections, and database records.
    """
    db: Session = SessionLocal()
    try:
        kbs = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.created_at < cutoff_date)
            .all()
        )
        if not kbs:
            print(f"No knowledge bases found before {cutoff_date}")
            return

        print(f"Deleting {len(kbs)} knowledge bases...")

        # Initialize external services
        minio_client = get_minio_client()
        embeddings = EmbeddingsFactory.create()
        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name="",  # collection name will be set per KB
            embedding_function=embeddings,
        )

        for kb in kbs:
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
                    vector_store._store.delete_collection(f"kb_{kb.id}")
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
                logger.error(f"Failed to delete KB {kb.id}: {e}")

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
    cutoff_date_str = input("Enter cutoff date (YYYY-MM-DD): ").strip()

    # Validate date format
    try:
        cutoff_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format! Use YYYY-MM-DD")
        exit(1)

    if action == "preview":
        preview_old_kbs(cutoff_date)
    elif action == "delete":
        # Always show preview before confirmation
        print("\n")
        preview_old_kbs(cutoff_date)
        print("\n")
        confirm = (
            input(
                f"⚠️ Are you sure you want to delete all KBs before {cutoff_date.date()}? (yes/no): "
            )
            .strip()
            .lower()
        )
        if confirm == "yes":
            delete_old_kbs(cutoff_date)
        else:
            print("❌ Cancelled.")
    else:
        print("❌ Unknown action. Use 'preview' or 'delete'.")
