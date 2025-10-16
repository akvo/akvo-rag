# import pytest

# from fastapi.testclient import TestClient
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import StaticPool
# from unittest.mock import AsyncMock, patch

# from app.main import app
# from app.db.session import get_db
# from app.models.base import Base
# from app.models.app import App, AppStatus
# from app.models.job import Job

# # ---------------------------------------------------------------------
# # ⚙️ Setup in-memory database for full integration-style test
# # ---------------------------------------------------------------------
# SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL,
#     connect_args={"check_same_thread": False},
#     poolclass=StaticPool,
# )
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()


# app.dependency_overrides[get_db] = override_get_db
# client = TestClient(app)


# @pytest.fixture(autouse=True)
# def setup_database():
#     """Create tables before each test and drop them after."""
#     Base.metadata.create_all(bind=engine)
#     yield
#     Base.metadata.drop_all(bind=engine)


# @pytest.fixture
# def sample_app():
#     """Insert a mock active App into the test DB."""
#     db = TestingSessionLocal()
#     app_entry = App(
#         app_id="app_001",
#         client_id="ac_001",
#         access_token="tok_abc123",
#         app_name="test_app",
#         domain="test.domain.com",
#         chat_callback_url="https://example.com/chat_callback",
#         upload_callback_url="https://example.com/upload_callback",
#         callback_token="cb_tok_123",
#         status=AppStatus.active,
#         knowledge_base_id=42,
#         scopes=["jobs.write"],
#     )
#     db.add(app_entry)
#     db.commit()
#     db.refresh(app_entry)
#     db.close()
#     return app_entry


# @pytest.fixture
# def sample_job_payload():
#     """Payload for creating a chat job."""
#     return {
#         "job": "chat",
#         "prompt": "Explain AI simply.",
#         "chats": [
#             {"role": "user", "content": "What is AI?"},
#             {"role": "assistant", "content": "AI means Artificial Intelligence."},
#         ],
#         "callback_url": "https://example.com/callback",
#         "callback_params": {"reply_to": "wa:+1234"},
#         "trace_id": "trace_abc_123",
#     }


# # ---------------------------------------------------------------------
# # 🧪 TESTS
# # ---------------------------------------------------------------------

# class TestJobsEndpointIntegration:
#     """Integration tests for /jobs endpoint."""

#     @pytest.mark.asyncio
#     @patch("app.api.api_v1.jobs.execute_chat_job", new_callable=AsyncMock)
#     def test_create_chat_job_success(
#         self, mock_execute_chat_job, sample_app, sample_job_payload
#     ):
#         """Should create a chat job and queue it for background execution."""

#         headers = {"Authorization": f"Bearer {sample_app.access_token}"}
#         response = client.post("/jobs", json=sample_job_payload, headers=headers)

#         assert response.status_code == 200
#         data = response.json()

#         # ✅ Validate response content
#         assert data["job_id"].startswith("job_")
#         assert data["status"] == "queued"
#         assert data["trace_id"] == "trace_abc_123"
#         assert "Chat job queued successfully." in data["message"]

#         # ✅ Check the job exists in the DB
#         db = TestingSessionLocal()
#         job = db.query(Job).filter(Job.id == data["job_id"]).first()
#         assert job is not None
#         assert job.status == "queued"
#         assert job.app_id == sample_app.app_id
#         assert job.data is not None
#         db.close()

#         # ✅ Ensure the background job was queued
#         mock_execute_chat_job.assert_not_called()  # background task won't run in sync mode

#     def test_create_chat_job_requires_auth(self, sample_job_payload):
#         """Should reject unauthenticated requests."""
#         response = client.post("/jobs", json=sample_job_payload)
#         assert response.status_code == 401

#     def test_create_chat_job_invalid_token(self, sample_job_payload):
#         """Should reject invalid tokens."""
#         headers = {"Authorization": "Bearer tok_invalid"}
#         response = client.post("/jobs", json=sample_job_payload, headers=headers)
#         assert response.status_code == 401

#     def test_create_chat_job_for_revoked_app(self, sample_app, sample_job_payload):
#         """Should reject requests for revoked app."""
#         # Revoke the app manually
#         db = TestingSessionLocal()
#         app_obj = db.query(App).filter(App.app_id == sample_app.app_id).first()
#         app_obj.status = AppStatus.revoked
#         db.commit()
#         db.close()

#         headers = {"Authorization": f"Bearer {sample_app.access_token}"}
#         response = client.post("/jobs", json=sample_job_payload, headers=headers)
#         assert response.status_code == 403
