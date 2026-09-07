import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.models.prompt import PromptDefinition, PromptVersion, PromptNameEnum
from app.models.user import User
from app.models.job import Job
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.utils.callback_util import send_callback_async, send_callback
from app.api.api_v1.prompt import (
    get_prompt_by_name,
    list_all_prompts,
    create_or_update_prompt,
)


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def mock_current_user():
    return User(
        id=42,
        email="prompt_admin@example.com",
        username="promptadmin",
        hashed_password="pw",
        is_active=True,
    )


@pytest.fixture
def client(mock_db, mock_current_user):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==========================================
# 1. PROMPT ROUTER & SERVICE TESTS
# ==========================================


def test_get_prompt_by_name_service(mock_db):
    fake_prompt = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    q_opt = mock_db.query.return_value.options.return_value
    q_opt.filter_by.return_value.first.return_value = fake_prompt

    result = get_prompt_by_name(
        mock_db, PromptNameEnum.contextualize_q_system_prompt
    )
    assert result == fake_prompt


def test_list_all_prompts_service(mock_db):
    fake_prompts = [
        PromptDefinition(
            id=1, name=PromptNameEnum.contextualize_q_system_prompt
        ),
        PromptDefinition(id=2, name=PromptNameEnum.qa_flexible_prompt),
    ]
    mock_db.query.return_value.options.return_value.all.return_value = (
        fake_prompts
    )

    result = list_all_prompts(mock_db)
    assert len(result) == 2


def test_create_or_update_prompt_new_definition(mock_db):
    q_opt = mock_db.query.return_value.options.return_value
    q_opt.filter_by.return_value.first.return_value = None

    result = create_or_update_prompt(
        db=mock_db,
        name=PromptNameEnum.contextualize_q_system_prompt,
        content="You are an agricultural expert: {context}",
        user_id=42,
        reason="Initial seed",
    )
    assert result.name == PromptNameEnum.contextualize_q_system_prompt
    assert mock_db.add.called
    assert mock_db.commit.called


def test_create_or_update_prompt_existing_definition(mock_db):
    existing = PromptDefinition(
        id=5, name=PromptNameEnum.contextualize_q_system_prompt
    )
    v1 = PromptVersion(
        id=1,
        prompt_definition_id=5,
        version_number=1,
        content="Old version",
        is_active=True,
    )
    existing.versions = [v1]
    q_opt = mock_db.query.return_value.options.return_value
    q_opt.filter_by.return_value.first.return_value = existing

    result = create_or_update_prompt(
        db=mock_db,
        name=PromptNameEnum.contextualize_q_system_prompt,
        content="New updated version",
        user_id=42,
        reason="Updated prompt",
    )
    assert result.id == 5
    assert mock_db.commit.called


def test_create_prompt_endpoint(client: TestClient, monkeypatch):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    definition = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    v1 = PromptVersion(
        id=10,
        prompt_definition_id=1,
        version_number=1,
        content="System template",
        is_active=True,
        activated_by_user=User(id=42, username="promptadmin"),
        updated_at=now,
    )
    definition.versions = [v1]

    monkeypatch.setattr(
        "app.api.api_v1.prompt.create_or_update_prompt",
        lambda db, name, content, user_id, reason: definition,
    )

    response = client.post(
        "/api/prompt/",
        json={
            "name": PromptNameEnum.contextualize_q_system_prompt.value,
            "content": "System template",
            "activation_reason": "Initial activation",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == PromptNameEnum.contextualize_q_system_prompt.value
    assert data["active_version"]["content"] == "System template"


def test_update_prompt_endpoint(client: TestClient, monkeypatch):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    definition = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    v2 = PromptVersion(
        id=11,
        prompt_definition_id=1,
        version_number=2,
        content="Updated template",
        is_active=True,
        activated_by_user=User(id=42, username="promptadmin"),
        updated_at=now,
    )
    definition.versions = [v2]

    monkeypatch.setattr(
        "app.api.api_v1.prompt.create_or_update_prompt",
        lambda db, name, content, user_id, reason: definition,
    )

    response = client.put(
        f"/api/prompt/{PromptNameEnum.contextualize_q_system_prompt.value}",
        json={
            "content": "Updated template",
            "activation_reason": "Version 2 update",
        },
    )
    assert response.status_code == 200
    assert response.json()["active_version"]["version_number"] == 2


def test_list_prompts_endpoint(client: TestClient, monkeypatch):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    d1 = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    d1.versions = [
        PromptVersion(
            id=1,
            prompt_definition_id=1,
            version_number=1,
            content="p1",
            is_active=True,
            activated_by_user=User(id=42, username="admin"),
            updated_at=now,
        )
    ]
    monkeypatch.setattr(
        "app.api.api_v1.prompt.list_all_prompts",
        lambda db: [d1],
    )

    response = client.get("/api/prompt")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert (
        response.json()[0]["name"]
        == PromptNameEnum.contextualize_q_system_prompt.value
    )


def test_get_prompt_endpoint_success(client: TestClient, monkeypatch):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    d1 = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    d1.versions = [
        PromptVersion(
            id=1,
            prompt_definition_id=1,
            version_number=1,
            content="p1",
            is_active=True,
            activated_by_user=User(id=42, username="admin"),
            updated_at=now,
        )
    ]
    monkeypatch.setattr(
        "app.api.api_v1.prompt.get_prompt_by_name",
        lambda db, name: d1,
    )

    response = client.get(
        f"/api/prompt/{PromptNameEnum.contextualize_q_system_prompt.value}"
    )
    assert response.status_code == 200
    assert (
        response.json()["name"]
        == PromptNameEnum.contextualize_q_system_prompt.value
    )


def test_get_prompt_endpoint_not_found(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.api_v1.prompt.get_prompt_by_name",
        lambda db, name: None,
    )
    response = client.get(
        f"/api/prompt/{PromptNameEnum.contextualize_q_system_prompt.value}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Prompt not found"


def test_reactivate_prompt_version_success(
    client: TestClient, mock_db, monkeypatch
):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    prompt_def = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    v1 = PromptVersion(
        id=5,
        prompt_definition_id=1,
        version_number=1,
        content="Old content",
        is_active=False,
        updated_at=now,
    )
    prompt_def.versions = [v1]

    monkeypatch.setattr(
        "app.api.api_v1.prompt.get_prompt_by_name",
        lambda db, name: prompt_def,
    )
    mock_db.query.return_value.filter_by.return_value.first.return_value = v1

    prompt_name = PromptNameEnum.contextualize_q_system_prompt.value
    response = client.put(
        f"/api/prompt/{prompt_name}/reactivate/5",
        json={"reactivation_reason": "Rollback to version 1"},
    )
    assert response.status_code == 200
    assert v1.is_active is True
    assert v1.activation_reason == "Rollback to version 1"


def test_reactivate_prompt_version_not_found(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.api_v1.prompt.get_prompt_by_name",
        lambda db, name: None,
    )
    prompt_name = PromptNameEnum.contextualize_q_system_prompt.value
    response = client.put(
        f"/api/prompt/{prompt_name}/reactivate/5",
        json={"reactivation_reason": "Rollback"},
    )
    assert response.status_code == 404


def test_reactivate_prompt_version_mismatch(
    client: TestClient, mock_db, monkeypatch
):
    prompt_def = PromptDefinition(
        id=1, name=PromptNameEnum.contextualize_q_system_prompt
    )
    v_other = PromptVersion(
        id=99,
        prompt_definition_id=999,  # Mismatch
        version_number=1,
        content="Other content",
    )
    monkeypatch.setattr(
        "app.api.api_v1.prompt.get_prompt_by_name",
        lambda db, name: prompt_def,
    )
    mock_db.query.return_value.filter_by.return_value.first.return_value = (
        v_other
    )

    prompt_name = PromptNameEnum.contextualize_q_system_prompt.value
    response = client.put(
        f"/api/prompt/{prompt_name}/reactivate/99",
        json={"reactivation_reason": "Rollback"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Version not found for this prompt"


# ==========================================
# 2. CALLBACK UTIL TESTS
# ==========================================


@pytest.mark.asyncio
async def test_send_callback_async_no_url():
    job = Job(id="job_123", callback_params={"token": "abc"})
    # Should safely return without error
    await send_callback_async(callback_url="", job=job)


@pytest.mark.asyncio
async def test_send_callback_async_success():
    job = Job(id="job_123", callback_params={"meta": "test"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        await send_callback_async(
            callback_url="http://host.example/callback",
            job=job,
            output="Uploaded successfully",
            error=None,
        )

        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://host.example/callback"
        assert call_args[1]["json"]["status"] == "completed"
        assert call_args[1]["json"]["output"] == "Uploaded successfully"
        assert call_args[1]["json"]["job_id"] == "job_123"


@pytest.mark.asyncio
async def test_send_callback_async_http_status_error():
    job = Job(id="job_fail", callback_params=None)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_resp
        )

        # Should catch and log warning without raising
        await send_callback_async(
            callback_url="http://host.example/callback",
            job=job,
            error="Extraction failure",
        )
        assert mock_post.called


@pytest.mark.asyncio
async def test_send_callback_async_request_error():
    job = Job(id="job_req_err", callback_params=None)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError(
            "Connection refused", request=MagicMock()
        )

        await send_callback_async(
            callback_url="http://host.example/callback",
            job=job,
            output=None,
            error="Connection issue",
        )
        assert mock_post.called


def test_send_callback_sync_wrapper():
    job = Job(id="job_sync", callback_params={"key": "val"})
    with patch("app.utils.callback_util.asyncio.run") as mock_asyncio_run:
        send_callback(
            callback_url="http://host.example/sync-callback",
            job=job,
            output="Sync result",
        )
        assert mock_asyncio_run.called


def test_send_callback_sync_wrapper_runtime_error():
    job = Job(id="job_sync_err", callback_params={"key": "val"})
    with patch(
        "app.utils.callback_util.asyncio.run",
        side_effect=RuntimeError("Loop already running"),
    ):
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            send_callback(
                callback_url="http://host.example/sync-callback",
                job=job,
                output="Sync result",
            )
            assert mock_loop.create_task.called
