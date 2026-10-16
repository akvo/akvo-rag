import io
import pytest
from unittest.mock import MagicMock
from minio.error import S3Error
from urllib3.response import HTTPResponse

from app.services.minio_service import MinIOService, get_minio_service
from app.core.config import Settings


@pytest.mark.unit
class TestMinIOService:
    """Unit test suite for MinIOService."""

    @pytest.fixture
    def mock_minio_client(self):
        client = MagicMock()
        client.bucket_exists.return_value = True
        return client

    @pytest.fixture
    def custom_settings(self):
        return Settings(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="test_access",
            MINIO_SECRET_KEY="test_secret",
            MINIO_BUCKET_DOCUMENTS="documents",
            MINIO_SECURE=False,
        )

    def test_init_bucket_exists(self, mock_minio_client, custom_settings):
        """Service should check if bucket exists and not re-create."""
        mock_minio_client.bucket_exists.return_value = True

        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        assert service.default_bucket == "documents"
        mock_minio_client.bucket_exists.assert_called_with("documents")
        mock_minio_client.make_bucket.assert_not_called()

    def test_init_bucket_created_if_missing(
        self, mock_minio_client, custom_settings
    ):
        """Service should create bucket on startup if it does not exist."""
        mock_minio_client.bucket_exists.return_value = False

        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        assert service.default_bucket == "documents"
        mock_minio_client.bucket_exists.assert_called_with("documents")
        mock_minio_client.make_bucket.assert_called_once_with("documents")

    def test_upload_file_stream(self, mock_minio_client, custom_settings):
        """Upload streaming file buffer directly without loading to RAM."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        file_content = b"%PDF-1.4 sample pdf content stream"
        file_stream = io.BytesIO(file_content)

        mock_put_result = MagicMock()
        mock_put_result.etag = "abc123etag"
        mock_minio_client.put_object.return_value = mock_put_result

        result = service.upload_file(
            file_data=file_stream,
            object_name="kb_1/doc-123_sample.pdf",
            content_type="application/pdf",
        )

        assert result["bucket"] == "documents"
        assert result["object_name"] == "kb_1/doc-123_sample.pdf"
        assert result["etag"] == "abc123etag"
        assert result["size"] == len(file_content)

        mock_minio_client.put_object.assert_called_once()
        call_kwargs = mock_minio_client.put_object.call_args.kwargs
        assert call_kwargs["bucket_name"] == "documents"
        assert call_kwargs["object_name"] == "kb_1/doc-123_sample.pdf"
        assert call_kwargs["length"] == len(file_content)
        assert call_kwargs["content_type"] == "application/pdf"

    def test_upload_file_bytes(self, mock_minio_client, custom_settings):
        """Upload raw bytes helper."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        data = b"Hello world from bytes"
        mock_put_result = MagicMock()
        mock_put_result.etag = "bytes-etag"
        mock_minio_client.put_object.return_value = mock_put_result

        result = service.upload_file_bytes(
            data=data,
            object_name="kb_1/test.txt",
            content_type="text/plain",
        )

        assert result == "kb_1/test.txt"
        mock_minio_client.put_object.assert_called_once()

    def test_get_file_stream(self, mock_minio_client, custom_settings):
        """Retrieve binary stream from MinIO."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        mock_response = MagicMock()
        mock_minio_client.get_object.return_value = mock_response

        stream = service.get_file_stream("kb_1/test.txt")
        assert stream == mock_response
        mock_minio_client.get_object.assert_called_once_with(
            "documents", "kb_1/test.txt"
        )

    def test_download_file_bytes(self, mock_minio_client, custom_settings):
        """Download raw bytes and ensure connection release."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        mock_response = MagicMock()
        mock_response.read.return_value = b"downloaded file content"
        mock_minio_client.get_object.return_value = mock_response

        data = service.download_file_bytes("kb_1/test.txt")
        assert data == b"downloaded file content"
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_delete_file_success(self, mock_minio_client, custom_settings):
        """Delete file returns True on success."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        result = service.delete_file("kb_1/test.txt")
        assert result is True
        mock_minio_client.remove_object.assert_called_once_with(
            "documents", "kb_1/test.txt"
        )

    def test_delete_file_failure(self, mock_minio_client, custom_settings):
        """Delete file returns False on S3Error."""
        service = MinIOService(
            settings_override=custom_settings,
            client_override=mock_minio_client,
        )

        # Construct S3Error with mock response
        mock_resp = MagicMock(spec=HTTPResponse)
        mock_resp.status = 404
        mock_resp.data = b"<Error><Code>NoSuchKey</Code></Error>"
        mock_resp.headers = {}
        s3_err = S3Error(
            code="NoSuchKey",
            message="Object not found",
            resource="kb_1/test.txt",
            request_id="req-123",
            host_id="host-123",
            response=mock_resp,
        )
        mock_minio_client.remove_object.side_effect = s3_err

        result = service.delete_file("kb_1/test.txt")
        assert result is False

    def test_get_minio_service_singleton(self):
        """Dependency provider should return MinIOService instance."""
        svc = get_minio_service()
        assert isinstance(svc, MinIOService)
