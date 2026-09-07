from unittest.mock import AsyncMock, MagicMock
import pytest
from mcp_clients.kb_mcp_endpoint_service import (
    KnowledgeBaseMCPEndpointService,
)


@pytest.fixture
def mock_dispatcher():
    dispatcher = MagicMock()
    dispatcher.call_tool = AsyncMock()
    return dispatcher


@pytest.fixture
def service(mock_dispatcher):
    return KnowledgeBaseMCPEndpointService(dispatcher=mock_dispatcher)


@pytest.mark.asyncio
async def test_list_documents_by_kb_id_with_search_and_pagination(
    service, mock_dispatcher
):
    mock_dispatcher.call_tool.return_value = {
        "documents": [{"id": 1, "title": "Rice Guide"}],
        "total": 1,
    }
    docs = await service.list_documents_by_kb_id(
        kb_id=5,
        skip=10,
        limit=10,
        include_total=True,
        search="Rice",
    )
    assert docs["total"] == 1
    assert len(docs["documents"]) == 1
    mock_dispatcher.call_tool.assert_awaited_once_with(
        "knowledge_bases_mcp",
        "list_documents",
        {"kb_id": 5, "page": 2, "page_size": 10, "search": "Rice"},
    )


@pytest.mark.asyncio
async def test_list_documents_exclude_total(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "documents": [{"id": 2, "title": "Fertilizer Guide"}],
        "total": 1,
    }
    docs = await service.list_documents_by_kb_id(
        kb_id=5,
        skip=0,
        limit=10,
        include_total=False,
    )
    assert isinstance(docs, list)
    assert docs[0]["id"] == 2


@pytest.mark.asyncio
async def test_get_document_service(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "document": {"id": 10, "title": "Pest Control"}
    }
    doc = await service.get_document(kb_id=5, doc_id=10)
    assert doc["id"] == 10
    mock_dispatcher.call_tool.assert_awaited_once_with(
        "knowledge_bases_mcp", "get_document", {"document_id": 10}
    )


@pytest.mark.asyncio
async def test_delete_document_service(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {"status": "deleted"}
    res = await service.delete_document(kb_id=5, doc_id=12)
    assert isinstance(res, list)
    assert res[0]["status"] == "deleted"
    assert res[0]["doc_id"] == 12


@pytest.mark.asyncio
async def test_create_and_delete_knowledge_base(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "knowledge_base": {"id": 99, "name": "New KB"}
    }
    res = await service.create_kb(
        name="New KB",
        description="Desc",
        data={
            "embedding_model": "custom-embed",
            "embedding_dim": 768,
        },
    )
    assert res["id"] == 99

    mock_dispatcher.call_tool.return_value = {"status": "deleted"}
    del_res = await service.delete_kb(kb_id=99)
    assert del_res["status"] == "deleted"


@pytest.mark.asyncio
async def test_list_kbs_and_get_kb(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "knowledge_bases": [{"id": 1, "name": "KB 1"}],
        "total": 1,
    }
    kbs = await service.list_kbs(skip=0, limit=10, include_total=False)
    assert len(kbs) == 1
    assert kbs[0]["id"] == 1

    mock_dispatcher.call_tool.return_value = {
        "knowledge_base": {"id": 1, "name": "KB 1"}
    }
    kb = await service.get_kb(kb_id=1)
    assert kb["id"] == 1


@pytest.mark.asyncio
async def test_preview_documents_service(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "1": [{"chunk_id": 101, "text": "Crop rotation"}],
        "non_digit": "meta",
    }
    preview = await service.preview_documents(
        kb_id=5, preview_request={"doc_ids": [1]}
    )
    assert 1 in preview
    assert preview[1][0]["chunk_id"] == 101
    assert preview["non_digit"] == "meta"


@pytest.mark.asyncio
async def test_get_processing_tasks(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "1": {"status": "COMPLETED", "document_id": 1}
    }
    tasks = await service.get_processing_tasks(kb_id=5, task_ids=[1])
    assert 1 in tasks
    assert tasks[1]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_test_retrieval(service, mock_dispatcher):
    mock_dispatcher.call_tool.return_value = {
        "results": [{"chunk_id": 1, "score": 0.95}]
    }
    ret = await service.test_retrieval(kb_id=5, query="soil salinity", top_k=3)
    assert "results" in ret
    assert ret["results"][0]["score"] == 0.95


@pytest.mark.asyncio
async def test_cleanup_temp_files(service):
    res = await service.cleanup_temp_files()
    assert res["status"] == "cleaned"


@pytest.mark.asyncio
async def test_upload_and_process_documents_uploadfile(service):
    from io import BytesIO
    from fastapi import UploadFile

    f = UploadFile(
        filename="notes.txt",
        file=BytesIO(b"Soil nitrogen levels are adequate."),
    )
    result = await service.upload_and_process_documents(kb_id=5, files=[f])
    assert len(result) == 1
    assert result[0]["filename"] == "notes.txt"
    assert result[0]["status"] == "processed"


@pytest.mark.asyncio
async def test_upload_and_process_documents_local_path(service, tmp_path):
    test_file = tmp_path / "crop_guide.md"
    test_file.write_text("# Crop Guide\nOptimal planting seasons.")

    result = await service.upload_and_process_documents(
        kb_id=5, files=[str(test_file)]
    )
    assert len(result) == 1
    assert result[0]["filename"] == "crop_guide.md"
    assert result[0]["status"] == "processed"


@pytest.mark.asyncio
async def test_upload_and_process_documents_errors(service, tmp_path):
    with pytest.raises(ValueError, match="Invalid file input"):
        await service.upload_and_process_documents(
            kb_id=5, files=["non_existent_file.pdf"]
        )

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")
    with pytest.raises(ValueError, match="Empty file"):
        await service.upload_and_process_documents(
            kb_id=5, files=[str(empty_file)]
        )

    unsupported = tmp_path / "test.bin"
    unsupported.write_text("raw binary")
    with pytest.raises(ValueError, match="Unsupported file type"):
        await service.upload_and_process_documents(
            kb_id=5, files=[str(unsupported)]
        )


@pytest.mark.asyncio
async def test_get_documents_upload(service):
    res = await service.get_documents_upload(kb_id=5)
    assert res == []
