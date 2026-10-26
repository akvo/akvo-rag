from unittest.mock import MagicMock
from storage.minio_storage import MinioStorageService
from core.config import Settings


def test_minio_storage_ensure_bucket():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    service = MinioStorageService(
        settings_override=Settings(MINIO_BUCKET_DOCUMENTS="test-bucket"),
        client_override=mock_client,
    )

    result = service.ensure_bucket("test-bucket")
    assert result is True
    mock_client.bucket_exists.assert_called_once_with("test-bucket")
    mock_client.make_bucket.assert_called_once_with("test-bucket")


def test_minio_storage_upload_and_download():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True

    # Mock get_object response
    mock_response = MagicMock()
    mock_response.read.return_value = b"sample document content"
    mock_client.get_object.return_value = mock_response

    service = MinioStorageService(
        settings_override=Settings(MINIO_BUCKET_DOCUMENTS="test-bucket"),
        client_override=mock_client,
    )

    # Upload
    uploaded_name = service.upload_file_bytes(
        data=b"sample document content",
        object_name="kb_1/doc.txt",
        content_type="text/plain",
    )
    assert uploaded_name == "kb_1/doc.txt"
    assert mock_client.put_object.called

    # Download
    downloaded = service.download_file_bytes("kb_1/doc.txt")
    assert downloaded == b"sample document content"
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()


def test_minio_storage_delete_and_exists():
    mock_client = MagicMock()
    mock_client.stat_object.return_value = MagicMock()

    service = MinioStorageService(
        settings_override=Settings(MINIO_BUCKET_DOCUMENTS="test-bucket"),
        client_override=mock_client,
    )

    assert service.object_exists("kb_1/doc.txt") is True
    assert service.delete_file("kb_1/doc.txt") is True
    mock_client.remove_object.assert_called_once_with(
        "test-bucket", "kb_1/doc.txt"
    )
