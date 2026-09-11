import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.api_v1.auth import get_current_user as get_current_user_auth
from app.api.api_v1.knowledge_base import (
    get_minio_service,
    get_redis_client,
)
from app.core.security import get_current_app, get_current_user
from app.db.session import get_db
from app.main import app
from app.models.app import App, AppKnowledgeBase
from app.models.user import User
from mcp_clients.kb_mcp_endpoint_service import (
    KnowledgeBaseMCPEndpointService,
)


@pytest.fixture
def agriconnect_app_auth():
    """Mocks AgriConnect application and admin user auth credentials."""
    fake_user = User(
        id=10,
        username="agriconnect_admin",
        email="admin@agriconnect.akvo.org",
        is_active=True,
        is_superuser=False,
    )
    fake_app = App(
        id=10,
        app_id="app_agriconnect_123",
        client_id="client_agriconnect_123",
        app_name="AgriConnect",
        domain="agriconnect.akvo.org",
        default_chat_prompt=(
            "You are AgriConnect AI, an expert agronomy advisor "
            "supporting smallholder farmers in East Africa."
        ),
        chat_callback_url="https://agriconnect.akvo.org/callback/chat",
        upload_callback_url="https://agriconnect.akvo.org/callback/upload",
        access_token="test_access_token_agriconnect",
        scopes=["read", "write"],
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_current_user_auth] = lambda: fake_user
    app.dependency_overrides[get_current_app] = lambda: fake_app
    yield {"user": fake_user, "app": fake_app}
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_auth, None)
    app.dependency_overrides.pop(get_current_app, None)


@pytest.fixture
def mock_dependencies():
    """Mocks external I/O: MinIO storage, Redis client, MCP Dispatcher."""
    fake_redis = AsyncMock()
    fake_redis.rpush = AsyncMock(return_value=1)
    fake_redis.aclose = AsyncMock()

    fake_minio = MagicMock()
    fake_minio.client = MagicMock()
    fake_minio.client.bucket_exists.return_value = True
    fake_minio.client.put_object.return_value = MagicMock()
    fake_minio.upload_file.return_value = {
        "bucket": "documents",
        "object_name": "test_object",
        "etag": "test_etag",
        "size": 1024,
    }
    fake_minio.delete_file = MagicMock()

    fake_dispatcher = MagicMock()
    fake_dispatcher.call_tool = AsyncMock()

    fake_kb_service = KnowledgeBaseMCPEndpointService(
        dispatcher=fake_dispatcher
    )

    app.dependency_overrides[get_minio_service] = lambda: fake_minio
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    with patch(
        "app.api.api_v1.knowledge_base.KnowledgeBaseMCPEndpointService",
        return_value=fake_kb_service,
    ):
        yield {
            "redis": fake_redis,
            "minio": fake_minio,
            "dispatcher": fake_dispatcher,
            "kb_service": fake_kb_service,
        }

    app.dependency_overrides.pop(get_minio_service, None)
    app.dependency_overrides.pop(get_redis_client, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgriConnectFullIntegrationLifecycle:
    """
    Simulates complete AgriConnect host system journey:
    1. Agricultural Knowledge Base management
    2. Agronomic document upload to MinIO S3 & Redis queue
    3. Farmer chat query & grounded citation verification
    4. Streaming SSE response simulation
    5. Tenant isolation & input validation boundaries
    """

    async def test_agriconnect_full_lifecycle(
        self, agriconnect_app_auth, mock_dependencies
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            headers = {"X-API-Key": "agriconnect-live-key-abc"}

            # -----------------------------------------------------------
            # 1. Create Agricultural KB: "Kenya Avocado Extension"
            # -----------------------------------------------------------
            mock_dependencies["dispatcher"].call_tool.return_value = {
                "knowledge_base": {
                    "id": 101,
                    "name": "Kenya Avocado Extension",
                    "description": (
                        "Agronomic pest management and harvesting SOPs"
                    ),
                    "created_at": "2026-09-07T00:00:00Z",
                }
            }

            create_payload = {
                "name": "Kenya Avocado Extension",
                "description": (
                    "Agronomic pest management and harvesting SOPs"
                ),
                "embedding_model": "text-embedding-3-small",
            }
            kb_resp = await client.post(
                "/api/v1/knowledge-bases", json=create_payload, headers=headers
            )
            assert kb_resp.status_code == 200
            kb_data = kb_resp.json()
            assert kb_data["id"] == 101
            assert kb_data["name"] == "Kenya Avocado Extension"

            # -----------------------------------------------------------
            # 2. List Knowledge Bases
            # -----------------------------------------------------------
            mock_dependencies["dispatcher"].call_tool.return_value = {
                "knowledge_bases": [
                    {
                        "id": 101,
                        "name": "Kenya Avocado Extension",
                        "description": "Agronomic SOPs",
                        "created_at": "2026-09-07T00:00:00Z",
                        "documents": [],
                    }
                ]
            }

            list_resp = await client.get(
                "/api/v1/knowledge-bases", headers=headers
            )
            assert list_resp.status_code == 200
            kbs = list_resp.json()
            assert any(kb["id"] == 101 for kb in kbs)

            # -----------------------------------------------------------
            # 3. Upload Agricultural SOP PDF (MinIO S3 + Redis Ingestion)
            # -----------------------------------------------------------
            pdf_bytes = (
                b"%PDF-1.4\n% Kenya Avocado Pest Management SOP: "
                b"False Codling Moth control..."
            )
            files = {
                "file": (
                    "avocado_fcm_sop.pdf",
                    pdf_bytes,
                    "application/pdf",
                )
            }

            upload_resp = await client.post(
                "/api/v1/knowledge-bases/101/documents/upload",
                files=files,
                headers=headers,
            )
            assert upload_resp.status_code == 202
            upload_result = upload_resp.json()
            assert upload_result["status"] == "PROCESSING"
            assert "avocado_fcm_sop.pdf" in upload_result["filename"]
            assert upload_result["kb_id"] == 101

            # Assert MinIO and Redis were triggered
            assert mock_dependencies["minio"].upload_file.called
            assert mock_dependencies["redis"].rpush.called
            redis_call_args = mock_dependencies["redis"].rpush.call_args
            assert redis_call_args[0][0] == "document_ingestion"
            enqueued_task = json.loads(redis_call_args[0][1])
            assert enqueued_task["kb_id"] == 101
            assert enqueued_task["filename"] == "avocado_fcm_sop.pdf"

            # -----------------------------------------------------------
            # 4. Farmer WhatsApp Chat Simulation with Citations
            # -----------------------------------------------------------
            fake_messages = [
                SimpleNamespace(
                    role="user",
                    content=(
                        "How do I control false codling moth in my "
                        "avocado orchard?"
                    ),
                )
            ]
            fake_chat_session = SimpleNamespace(
                id=42,
                user_id=10,
                knowledge_bases=[SimpleNamespace(knowledge_base_id=101)],
                messages=fake_messages,
                content="You are AgriConnect assistant.",
            )

            class FakeChatQuery:

                def options(self, *args, **kwargs):
                    return self

                def filter(self, *args, **kwargs):
                    return self

                def order_by(self, *args, **kwargs):
                    return self

                def limit(self, *args, **kwargs):
                    return self

                def join(self, *args, **kwargs):
                    return self

                def first(self):
                    return fake_chat_session

                def all(self):
                    return fake_messages

            class FakeChatDB:

                def query(self, model):
                    return FakeChatQuery()

                def add(self, obj):
                    pass

                def commit(self):
                    pass

                def refresh(self, obj):
                    pass

                def close(self):
                    pass

            app.dependency_overrides[get_db] = lambda: FakeChatDB()

            async def fake_stream_mcp(*args, **kwargs):
                yield (
                    '0:"To control false codling moth (FCM), install '
                    'pheromone traps and remove fallen fruit."\n'
                )
                yield '0:" Regularly inspect avocado fruit clusters."\n'
                yield (
                    'd:{"finishReason":"stop","citations":[{"title":'
                    '"avocado_fcm_sop.pdf","source":"Avocado SOP"}]}\n'
                )

            with patch(
                "app.api.api_v1.chat.stream_mcp_response", fake_stream_mcp
            ):
                chat_payload = {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "How do I control false codling moth in "
                                "my orchard?"
                            ),
                        }
                    ]
                }
                chat_resp = await client.post(
                    "/api/v1/chat/42/messages",
                    json=chat_payload,
                    headers=headers,
                )
                assert chat_resp.status_code == 200
                response_text = chat_resp.text
                assert "false codling moth" in response_text
                assert "avocado_fcm_sop.pdf" in response_text

            app.dependency_overrides.pop(get_db, None)

    async def test_invalid_file_format_rejected(
        self, agriconnect_app_auth, mock_dependencies
    ):
        """Security check: non-whitelisted extension rejected with 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            files = {
                "file": (
                    "malicious_script.exe",
                    b"MZExecutableContent",
                    "application/octet-stream",
                )
            }
            resp = await client.post(
                "/api/v1/knowledge-bases/101/documents/upload",
                files=files,
            )
            assert resp.status_code == 400
            assert "Unsupported file format" in resp.json()["detail"]

    async def test_corrupt_pdf_magic_bytes_rejected(
        self, agriconnect_app_auth, mock_dependencies
    ):
        """Security check: corrupt magic bytes rejected with 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            files = {
                "file": (
                    "spoofed_extension.pdf",
                    b"NOT_A_PDF_HEADER_CONTENT",
                    "application/pdf",
                )
            }
            resp = await client.post(
                "/api/v1/knowledge-bases/101/documents/upload",
                files=files,
            )
            assert resp.status_code == 400
            assert "header does not match .pdf" in resp.json()["detail"]

    async def test_agriconnect_apps_jobs_upload_integration(
        self, agriconnect_app_auth, mock_dependencies
    ):
        """
        Verify AgriConnect's external AI service upload contract:
        POST /api/v1/apps/jobs with
            payload={"job": "upload", "knowledge_base_id": 101}
        and files=[("files", (filename, stream, type))].
        Asserts job is created and background upload task is dispatched.
        """
        # The background task (execute_upload_job) creates its own
        # MinIO/Redis via process_and_enqueue_upload, bypassing FastAPI DI.
        # Patch at the import site inside kb_mcp_endpoint_service.
        mock_upload_result = [
            {
                "id": "test-doc-uuid",
                "document_id": "test-doc-uuid",
                "upload_id": "test-doc-uuid",
                "filename": "maize_guide.pdf",
                "file_name": "maize_guide.pdf",
                "original_filename": "maize_guide.pdf",
                "status": "PROCESSING",
                "message": "File 'maize_guide.pdf' uploaded successfully",
                "skip_processing": False,
                "temp_path": "kb_101/test-doc-uuid_maize_guide.pdf",
                "kb_id": 101,
            }
        ]

        with patch(
            "app.services.document_upload_service.process_and_enqueue_upload",
            new_callable=AsyncMock,
            return_value=mock_upload_result,
        ) as mock_enqueue:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                headers = {
                    "Authorization": "Bearer test_access_token_agriconnect"
                }

                # Associate KB 101 with current app
                agriconnect_app_auth["app"].knowledge_bases = [
                    AppKnowledgeBase(knowledge_base_id=101, is_default=True)
                ]

                payload = json.dumps(
                    {
                        "job": "upload",
                        "knowledge_base_id": 101,
                        "callback_params": {
                            "kb_id": 101,
                            "source": "agriconnect",
                        },
                    }
                )
                files = [
                    (
                        "files",
                        (
                            "maize_guide.pdf",
                            b"%PDF-1.4\n% Maize pest management notes\n%%EOF",
                            "application/pdf",
                        ),
                    )
                ]

                resp = await client.post(
                    "/api/v1/apps/jobs",
                    data={"payload": payload},
                    files=files,
                    headers=headers,
                )

                assert resp.status_code == 200
                data = resp.json()
                assert "job_id" in data
                assert data["status"] == "pending"

                # Allow background task to execute
                import asyncio

                await asyncio.sleep(0.1)

                # Verify the centralized upload service was called
                assert mock_enqueue.called
                call_kwargs = mock_enqueue.call_args
                assert call_kwargs[1]["kb_id"] == 101 or (
                    len(call_kwargs[0]) > 0 and call_kwargs[0][0] == 101
                )
