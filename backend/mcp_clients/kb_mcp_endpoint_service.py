import json
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, UploadFile
import httpx
from app.core.config import settings


class KnowledgeBaseMCPEndpointService:
    """
    Async service to communicate with the MCP Knowledge Base API.
    Handles KB CRUD, documents, retrieval testing, and processing tasks.
    """

    def __init__(self):
        self.base_url = settings.KNOWLEDGE_BASES_API_ENDPOINT.rstrip("/")
        self.api_key = settings.KNOWLEDGE_BASES_API_KEY
        self.headers = {"Authorization": f"API-Key {self.api_key}"}

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[List[tuple]] = None,
    ) -> Any:
        """
        Generic async request to MCP.
        Handles JSON body, query params, or multipart file uploads.
        """
        url = f"{self.base_url}/api/v1/knowledge-base{endpoint}"

        async with httpx.AsyncClient() as client:
            request_kwargs = {"headers": self.headers, "params": params}
            if files:
                request_kwargs["files"] = files
            elif data:
                request_kwargs["json"] = data

            response = await client.request(method, url, **request_kwargs)

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except json.JSONDecodeError:
                detail = response.text
            raise HTTPException(
                status_code=response.status_code, detail=detail
            )

        return response.json() if response.content else None

    # ---- Knowledge Base CRUD ----
    async def create_kb(self, data: dict) -> Dict[str, Any]:
        """
        Create new knowledge base.
        """
        return await self._request("POST", "", data=data)

    async def list_kbs(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge bases from KB MCP Server
        """
        return await self._request(
            "GET", "", params={"skip": skip, "limit": limit}
        )

    async def get_kb(self, kb_id: int) -> Dict[str, Any]:
        """
        Get knowledge base by ID.
        """
        return await self._request("GET", f"/{kb_id}")

    async def update_kb(self, kb_id: int, data: dict) -> Dict[str, Any]:
        """
        Update knowledge base.
        """
        return await self._request("PUT", f"/{kb_id}", data=data)

    async def delete_kb(self, kb_id: int) -> Dict[str, Any]:
        """
        Delete knowledge base and all associated resources.
        """
        return await self._request("DELETE", f"/{kb_id}")

    # ---- Document related ----
    async def get_document(self, kb_id: int, doc_id: int) -> Dict[str, Any]:
        """
        Get document details by ID.
        """
        return await self._request("GET", f"/{kb_id}/documents/{doc_id}")

    async def upload_documents(
        self, kb_id: int, files: List[UploadFile]
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple documents to MCP.
        Sends as multipart/form-data.
        """
        file_payload = []
        for f in files:
            content = await f.read()  # Read file bytes for httpx
            file_payload.append(
                ("files", (f.filename, content, f.content_type))
            )
            await f.seek(0)  # Reset pointer so MCP can read UploadFile again

        return await self._request(
            "POST", f"/{kb_id}/documents/upload", files=file_payload
        )

    async def preview_documents(
        self, kb_id: int, preview_request: dict
    ) -> Dict[int, Any]:
        """
        Preview multiple documents' chunks.
        """
        return await self._request(
            "POST", f"/{kb_id}/documents/preview", data=preview_request
        )

    async def process_documents(
        self, kb_id: int, upload_results: List[dict]
    ) -> Dict[str, Any]:
        """
        Process multiple documents asynchronously.
        """
        return await self._request(
            "POST", f"/{kb_id}/documents/process", data=upload_results
        )

    # ---- Processing tasks ----
    async def get_processing_tasks(
        self, kb_id: int, task_ids: List[int]
    ) -> Dict[int, dict]:
        """
        Get status of multiple processing tasks for a knowledge base.
        task_ids is a list of integers;
        MCP expects comma-separated query param.
        """
        task_ids_str = ",".join(str(tid) for tid in task_ids)
        params = {"task_ids": task_ids_str}
        return await self._request(
            "GET", f"/{kb_id}/documents/tasks", params=params
        )

    # ---- Retrieval testing ----
    async def test_retrieval(
        self, kb_id: int, query: str, top_k: int = 5
    ) -> Dict[str, Any]:
        payload = {"kb_id": kb_id, "query": query, "top_k": top_k}
        return await self._request("POST", "/test-retrieval", data=payload)

    # ---- Cleanup ----
    async def cleanup_temp_files(self) -> Dict[str, Any]:
        """
        Trigger cleanup of expired temporary files in MCP.
        """
        return await self._request("POST", "/cleanup")
