import os

from fastapi import UploadFile
from typing import List

BASE_UPLOAD_DIR = "/mnt/uploads"
UPLOAD_TMP_DIR = os.path.join(BASE_UPLOAD_DIR, "tmp")
UPLOAD_FAILED_DIR = os.path.join(BASE_UPLOAD_DIR, "failed")

# Ensure directories exist
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FAILED_DIR, exist_ok=True)


class FileStorageService:
    @staticmethod
    async def save_files(files: List[UploadFile]) -> list[str]:
        """Save incoming UploadFile objects to persistent tmp directory."""
        saved_paths = []
        for file in files:
            dest_path = os.path.join(UPLOAD_TMP_DIR, file.filename)
            with open(dest_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_paths.append(dest_path)
        return saved_paths

    @staticmethod
    def cleanup_files(file_paths: list[str]):
        """Delete successfully processed files."""
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)

    @staticmethod
    def mark_failed(file_paths: list[str]):
        """Move failed files to /mnt/uploads/failed for later inspection."""
        for path in file_paths:
            if os.path.exists(path):
                dest = os.path.join(UPLOAD_FAILED_DIR, os.path.basename(path))
                os.rename(path, dest)
