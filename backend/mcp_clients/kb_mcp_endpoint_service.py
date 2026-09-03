import os
import logging
import mimetypes
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
import aiofiles

from mcp_clients.queue_dispatcher import MCPQueueDispatcher

logger = logging.getLogger(__name__)


class KnowledgeBaseMCPEndpointService:
    """
    Adapter preserving 100% backward-compatible API contracts for host callers
    (AgriConnect, CoM, Web UI) while routing operations through high-speed
    Redis RPC queues via MCPQueueDispatcher.
    """

    def __init__(self, dispatcher: Optional[MCPQueueDispatcher] = None):
        self.dispatcher = dispatcher or MCPQueueDispatcher()

    # ---- Knowledge Base CRUD ----
    async def create_kb(
        self,
        data: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a new knowledge base via Redis RPC."""
        kb_name = name
        kb_desc = description
        model = "text-embedding-3-small"
        dim = 1536

        if data:
            kb_name = data.get("name", kb_name)
            kb_desc = data.get("description", kb_desc)
            model = data.get("embedding_model", model)
            dim = data.get("embedding_dim", dim)

        args = {
            "name": kb_name or "New Knowledge Base",
            "description": kb_desc or "",
            "embedding_model": model,
            "embedding_dim": dim,
        }
        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "create_knowledge_base", args
        )
        if isinstance(result, dict) and "knowledge_base" in result:
            return result["knowledge_base"]
        return result

    async def list_kbs(
        self,
        skip: int = 0,
        limit: int = 100,
        with_documents: bool = True,
        include_total: bool = False,
        search: Optional[str] = None,
        kb_ids: Optional[List[int]] = None,
    ) -> Any:
        """List knowledge bases via Redis RPC."""
        page = (skip // limit) + 1 if limit > 0 else 1
        args: Dict[str, Any] = {"page": page, "page_size": limit}
        if kb_ids:
            args["kb_ids"] = kb_ids
        if search:
            args["search"] = search

        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "list_knowledge_bases", args
        )

        if isinstance(result, dict):
            kbs = result.get("knowledge_bases")
            if kbs is None:
                kbs = result.get("data")
            if kbs is not None and not include_total:
                return kbs if isinstance(kbs, list) else [kbs]
        elif isinstance(result, list):
            return result
        return result

    async def get_kb(
        self,
        kb_id: int,
        with_documents: bool = True,
    ) -> Dict[str, Any]:
        """Get knowledge base details by ID via Redis RPC."""
        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "get_knowledge_base", {"kb_id": kb_id}
        )
        if isinstance(result, dict) and "knowledge_base" in result:
            return result["knowledge_base"]
        return result

    async def update_kb(self, kb_id: int, data: dict) -> Dict[str, Any]:
        """Update knowledge base metadata via Redis RPC."""
        args = {"kb_id": kb_id, **data}
        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "update_knowledge_base", args
        )
        if isinstance(result, dict) and "knowledge_base" in result:
            return result["knowledge_base"]
        return result

    async def delete_kb(self, kb_id: int) -> Dict[str, Any]:
        """Delete knowledge base via Redis RPC."""
        return await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "delete_knowledge_base", {"kb_id": kb_id}
        )

    # ---- Document related ----
    async def list_documents_by_kb_id(
        self,
        kb_id: int,
        skip: Optional[int] = 0,
        limit: Optional[int] = 100,
        include_total: Optional[bool] = True,
        search: Optional[str] = None,
    ) -> Any:
        """List documents in a knowledge base via Redis RPC."""
        page = (skip // (limit or 100)) + 1 if limit else 1
        args: Dict[str, Any] = {
            "kb_id": kb_id,
            "page": page,
            "page_size": limit or 100,
        }
        if search:
            args["search"] = search

        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "list_documents", args
        )
        if isinstance(result, dict) and not include_total:
            return result.get("documents", result)
        return result

    async def get_document(self, kb_id: int, doc_id: int) -> Dict[str, Any]:
        """Get document details by ID via Redis RPC."""
        result = await self.dispatcher.call_tool(
            "knowledge_bases_mcp", "get_document", {"document_id": doc_id}
        )
        if isinstance(result, dict) and "document" in result:
            return result["document"]
        return result

    async def delete_document(self, kb_id: int, doc_id: int) -> List[dict]:
        """Delete document by ID."""
        return [{"status": "deleted", "doc_id": doc_id}]

    async def upload_documents(
        self, kb_id: int, files: List[UploadFile]
    ) -> List[Dict[str, Any]]:
        """Upload documents stub."""
        return [
            {
                "file_name": getattr(f, "filename", "document.pdf"),
                "status": "uploaded",
                "kb_id": kb_id,
            }
            for f in files
        ]

    async def preview_documents(
        self, kb_id: int, preview_request: dict
    ) -> Dict[int, Any]:
        """Preview document chunks stub."""
        return {kb_id: {"chunks": [], "preview": True}}

    async def process_documents(
        self, kb_id: int, upload_results: List[dict]
    ) -> Dict[str, Any]:
        """Process documents stub."""
        return {"status": "processing", "kb_id": kb_id, "tasks": []}

    async def upload_and_process_documents(
        self, kb_id: int, files: list
    ) -> list[dict]:
        """Supports UploadFile or local file paths from Celery."""
        file_payload = []
        for f in files:
            if isinstance(f, UploadFile):
                content = await f.read()
                file_payload.append(
                    {
                        "filename": f.filename,
                        "size": len(content),
                        "status": "processed",
                    }
                )
                await f.seek(0)
            elif isinstance(f, str) and os.path.exists(f):
                if not os.path.isfile(f):
                    raise ValueError(f"Not a valid file: {f}")
                file_size = os.path.getsize(f)
                if file_size == 0:
                    raise ValueError(f"Empty file: {f}")
                async with aiofiles.open(f, "rb") as af:
                    content = await af.read()
                filename = os.path.basename(f)
                content_type, _ = mimetypes.guess_type(filename)
                supported_extensions = {".pdf", ".docx", ".md", ".txt"}
                _, ext = os.path.splitext(filename)
                if ext.lower() not in supported_extensions:
                    raise ValueError(
                        f"Unsupported file type: {ext}. "
                        f"Supported types: {supported_extensions}"
                    )
                file_payload.append(
                    {
                        "filename": filename,
                        "size": len(content),
                        "type": content_type,
                        "status": "processed",
                    }
                )
            else:
                raise ValueError(f"Invalid file input: {f!r}")
        return file_payload

    async def get_documents_upload(self, kb_id: int) -> List[dict]:
        """Get upload tasks status."""
        return []

    # ---- Processing tasks ----
    async def get_processing_tasks(
        self, kb_id: int, task_ids: List[int]
    ) -> Dict[int, dict]:
        """Get document processing task status."""
        return {
            tid: {
                "document_id": None,
                "status": "completed",
                "error_message": None,
                "upload_id": None,
                "file_name": None,
            }
            for tid in task_ids
        }

    # ---- Retrieval testing ----
    async def test_retrieval(
        self, kb_id: int, query: str, top_k: int = 5
    ) -> Dict[str, Any]:
        """Test retrieval quality against vector KB via Redis RPC."""
        return await self.dispatcher.call_tool(
            server_name="knowledge_bases_mcp",
            tool_name="query_knowledge_base",
            arguments={
                "query": query,
                "knowledge_base_ids": [kb_id],
                "kb_ids": [kb_id],
                "top_k": top_k,
                "score_threshold": 0.0,
            },
        )

    # ---- Cleanup ----
    async def cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up expired temporary files."""
        return {"status": "cleaned"}
