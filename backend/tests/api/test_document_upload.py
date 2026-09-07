import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.api_v1.auth import get_current_user as get_current_user_auth
from app.core.security import get_current_user
from app.models.user import User
from app.services.minio_service import get_minio_service


@pytest.fixture
def override_user_auth(client: TestClient):
    """Override user authentication to provide a mock superuser."""
    fake_user = User(
        id=1,
        email="admin@akvo.org",
        is_active=True,
        is_superuser=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_current_user_auth] = lambda: fake_user
    yield fake_user
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_user_auth in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_auth]


@pytest.fixture
def mock_minio_service():
    """Mock MinIOService for upload endpoints."""
    mock_svc = MagicMock()
    mock_svc.default_bucket = "documents"
    mock_svc.upload_file.return_value = {
        "bucket": "documents",
        "object_name": "kb_1/doc-123_sample.pdf",
        "etag": "mock-etag-123",
        "size": 1024,
    }
    app.dependency_overrides[get_minio_service] = lambda: mock_svc
    yield mock_svc
    if get_minio_service in app.dependency_overrides:
        del app.dependency_overrides[get_minio_service]


@pytest.mark.unit
class TestDocumentUploadAPI:
    """Integration test suite for upload endpoint, security and Redis."""

    def test_upload_single_pdf_success(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should stream valid PDF to MinIO and push task to Redis queue."""
        pdf_content = b"%PDF-1.4 sample pdf content for testing\n%%EOF"
        files = {
            "file": (
                "water_sop.pdf",
                io.BytesIO(pdf_content),
                "application/pdf",
            )
        }

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 202
        data = response.json()
        assert data["filename"] == "water_sop.pdf"
        assert data["status"] == "PROCESSING"
        assert data["kb_id"] == 1
        assert "id" in data

        # Verify MinIO upload was called
        mock_minio_service.upload_file.assert_called_once()

    def test_upload_multiple_documents_success(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should accept multiple files and queue each to Redis queue."""
        pdf_content = b"%PDF-1.4 first pdf file\n%%EOF"
        txt_content = b"This is a plain text document."

        files = [
            (
                "files",
                ("guide.pdf", io.BytesIO(pdf_content), "application/pdf"),
            ),
            ("files", ("notes.txt", io.BytesIO(txt_content), "text/plain")),
        ]

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 202
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["filename"] == "guide.pdf"
        assert data[0]["status"] == "PROCESSING"
        assert data[1]["filename"] == "notes.txt"
        assert data[1]["status"] == "PROCESSING"

    def test_upload_unsupported_file_extension(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should reject unsupported executable / script files."""
        sh_content = b"#!/bin/bash\necho 'hello'"
        files = {"file": ("script.sh", io.BytesIO(sh_content), "text/x-sh")}

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    def test_upload_invalid_magic_bytes_pdf(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should reject files disguised as PDF with bad magic bytes."""
        fake_pdf_content = b"NOT_A_PDF_HEADER corrupted data"
        files = {
            "file": (
                "fake.pdf",
                io.BytesIO(fake_pdf_content),
                "application/pdf",
            )
        }

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 400
        assert "Invalid file content" in response.json()["detail"]

    def test_upload_empty_file_rejected(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should reject zero-byte files with 400 Bad Request."""
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_filename_path_traversal_sanitized(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should sanitize filename to prevent path traversal attacks."""
        pdf_content = b"%PDF-1.4 valid pdf content\n%%EOF"
        files = {
            "file": (
                "../../etc/passwd.pdf",
                io.BytesIO(pdf_content),
                "application/pdf",
            )
        }

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 202
        data = response.json()
        assert ".." not in data["filename"]
        assert "/" not in data["filename"]
        assert data["filename"].endswith("passwd.pdf")

    def test_upload_minio_failure_handling(
        self, client, override_user_auth, mock_minio_service, fake_redis
    ):
        """Should return 500 when storage fails without leaking secrets."""
        mock_minio_service.upload_file.side_effect = RuntimeError(
            "MinIO connection reset"
        )

        pdf_content = b"%PDF-1.4 valid pdf content\n%%EOF"
        files = {
            "file": ("sop.pdf", io.BytesIO(pdf_content), "application/pdf")
        }

        with patch(
            "app.api.api_v1.knowledge_base.get_redis_client",
            return_value=fake_redis,
        ):
            response = client.post(
                "/api/knowledge-base/1/documents/upload", files=files
            )

        assert response.status_code == 500
        assert "Document storage failed" in response.json()["detail"]
