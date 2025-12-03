import os
import logging

from fastapi import UploadFile
from typing import List

logger = logging.getLogger(__name__)

BASE_UPLOAD_DIR = "/mnt/uploads"
UPLOAD_TMP_DIR = os.path.join(BASE_UPLOAD_DIR, "tmp")
UPLOAD_FAILED_DIR = os.path.join(BASE_UPLOAD_DIR, "failed")

# Ensure directories exist
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FAILED_DIR, exist_ok=True)


class FileStorageService:
    @staticmethod
    async def save_files(files: List[UploadFile]) -> list[str]:
        """
        Save incoming UploadFile objects to persistent tmp directory.
        Validates file integrity before saving.
        """
        saved_paths = []

        for file in files:
            try:
                # Reset file pointer to beginning
                await file.seek(0)

                # Read content
                content = await file.read()

                # ✅ CRITICAL: Validate content is not empty
                if not content or len(content) == 0:
                    logger.error(
                        f"❌ File '{file.filename}' has no content "
                        f"(size: {len(content) if content else 0} bytes)"
                    )
                    continue

                # ✅ Validate DOCX files are valid ZIP archives
                if file.filename.endswith((".docx", ".xlsx", ".pptx")):
                    import zipfile
                    from io import BytesIO

                    try:
                        with zipfile.ZipFile(BytesIO(content)) as zf:
                            # Quick validation - just check it can be opened
                            file_list = zf.namelist()
                            logger.info(
                                f"✅ Valid Office document: '{file.filename}' "
                                f"contains {len(file_list)} entries"
                            )
                    except zipfile.BadZipFile as e:
                        logger.error(
                            f"❌ Invalid Office document '{file.filename}': {e}"
                        )
                        logger.error(f"First 50 bytes: {content[:50]}")
                        logger.error(f"Last 50 bytes: {content[-50:]}")
                        # Move to failed directory
                        failed_path = os.path.join(
                            UPLOAD_FAILED_DIR, f"corrupted_{file.filename}"
                        )
                        with open(failed_path, "wb") as f:
                            f.write(content)
                        logger.error(f"Saved corrupted file to: {failed_path}")
                        continue

                # Save to disk
                dest_path = os.path.join(UPLOAD_TMP_DIR, file.filename)

                with open(dest_path, "wb") as f:
                    f.write(content)

                # ✅ Verify file was written correctly
                written_size = os.path.getsize(dest_path)
                if written_size != len(content):
                    logger.error(
                        f"❌ File size mismatch for '{file.filename}': "
                        f"expected {len(content)} bytes, wrote {written_size} bytes"  # noqa
                    )
                    os.remove(dest_path)  # Delete corrupted file
                    continue

                logger.info(
                    f"✅ Saved '{file.filename}' to {dest_path} "
                    f"({written_size:,} bytes)"
                )
                saved_paths.append(dest_path)

            except Exception as e:
                logger.exception(
                    f"❌ Unexpected error saving file '{file.filename}': {e}"
                )
                continue

        # Log summary
        if len(saved_paths) != len(files):
            logger.warning(
                f"⚠️ File save incomplete: received {len(files)} files, "
                f"successfully saved {len(saved_paths)} files"
            )

        return saved_paths

    @staticmethod
    def cleanup_files(file_paths: list[str]):
        """Delete successfully processed files."""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                logger.error(f"Failed to cleanup {path}: {e}")

    @staticmethod
    def mark_failed(file_paths: list[str]):
        """Move failed files to /mnt/uploads/failed for later inspection."""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    dest = os.path.join(
                        UPLOAD_FAILED_DIR, os.path.basename(path)
                    )
                    os.rename(path, dest)
                    logger.warning(f"⚠️ Moved failed file to: {dest}")
            except Exception as e:
                logger.error(f"Failed to mark as failed {path}: {e}")
