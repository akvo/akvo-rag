import os
import asyncio
import logging
import aiofiles
import mimetypes

from typing import Any, Dict, List, Optional
from fastapi import HTTPException, UploadFile, status
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


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
        timeout: float = 30.0,
        retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> Any:
        """
        Generic async request to MCP with retries and error handling.
        Handles JSON body, query params, or multipart file uploads.
        """

        url = f"{self.base_url}/api/v1/knowledge-base{endpoint}"
        request_kwargs = {
            "headers": self.headers,
            "params": params,
            "timeout": timeout,
        }

        if files:
            request_kwargs["files"] = files
        elif data:
            request_kwargs["json"] = data

        last_exception: Optional[Exception] = None

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, **request_kwargs
                    )

                if response.is_error:
                    try:
                        detail = response.json().get("detail", response.text)
                    except Exception:
                        detail = response.text

                    logger.warning(
                        f"MCP error (status={response.status_code}) "
                        f"for {method} {url}: {detail}"
                    )

                    # Retry only for transient errors
                    if (
                        response.status_code in (502, 503, 504)
                        and attempt < retries - 1
                    ):
                        await asyncio.sleep(backoff_factor * (2**attempt))
                        continue

                    raise HTTPException(
                        status_code=response.status_code,
                        detail=detail,
                    )

                return response.json() if response.content else None

            except httpx.TimeoutException as e:
                last_exception = e
                logger.error(f"Timeout calling {method} {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_factor * (2**attempt))
                    continue
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Upstream MCP server did not respond in time.",
                )
            except httpx.RequestError as e:
                last_exception = e
                logger.error(f"Request error calling {method} {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_factor * (2**attempt))
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Could not connect to MCP server.",
                )

        # If we exhaust retries without raising inside the loop
        if last_exception:
            ex_msg = f"Request failed after {retries}"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{ex_msg} attempts: {last_exception}",
            )

    # ---- Knowledge Base CRUD ----
    async def create_kb(self, data: dict) -> Dict[str, Any]:
        return await self._request("POST", "", data=data)

    async def list_kbs(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self._request(
            "GET", "", params={"skip": skip, "limit": limit}
        )

    async def get_kb(self, kb_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/{kb_id}")

    async def update_kb(self, kb_id: int, data: dict) -> Dict[str, Any]:
        return await self._request("PUT", f"/{kb_id}", data=data)

    async def delete_kb(self, kb_id: int) -> Dict[str, Any]:
        return await self._request("DELETE", f"/{kb_id}")

    # ---- Document related ----
    async def get_document(self, kb_id: int, doc_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/{kb_id}/documents/{doc_id}")

    async def upload_documents(
        self, kb_id: int, files: List[UploadFile]
    ) -> List[Dict[str, Any]]:
        file_payload = []
        for f in files:
            content = await f.read()
            file_payload.append(
                ("files", (f.filename, content, f.content_type))
            )
            await f.seek(0)
        return await self._request(
            "POST", f"/{kb_id}/documents/upload", files=file_payload
        )

    async def preview_documents(
        self, kb_id: int, preview_request: dict
    ) -> Dict[int, Any]:
        return await self._request(
            "POST", f"/{kb_id}/documents/preview", data=preview_request
        )

    async def process_documents(
        self, kb_id: int, upload_results: List[dict]
    ) -> Dict[str, Any]:
        return await self._request(
            "POST", f"/{kb_id}/documents/process", data=upload_results
        )

    async def upload_and_process_documents(
        self, kb_id: int, files: list
    ) -> list[dict]:
        """
        Supports either:
            - List[UploadFile] (FastAPI form uploads), or
            - List[str] (local file paths from Celery)
        """
        file_payload = []

        for f in files:
            if isinstance(f, UploadFile):
                # 🧩 Handle FastAPI upload object
                content = await f.read()
                file_payload.append(
                    ("files", (f.filename, content, f.content_type))
                )
                await f.seek(0)
            elif isinstance(f, str) and os.path.exists(f):
                # 🧠 Handle local file path
                async with aiofiles.open(f, "rb") as af:
                    content = await af.read()
                filename = os.path.basename(f)
                content_type, _ = mimetypes.guess_type(filename)
                file_payload.append(
                    (
                        "files",
                        (
                            filename,
                            content,
                            content_type or "application/octet-stream",
                        ),
                    )
                )
            else:
                raise ValueError(f"Invalid file input: {f!r}")

        return await self._request(
            "POST", f"/{kb_id}/documents/full-process", files=file_payload
        )

    async def get_documents_upload(self, kb_id: int) -> List[dict]:
        return await self._request("GET", f"/{kb_id}/documents/upload")

    # ---- Processing tasks ----
    async def get_processing_tasks(
        self, kb_id: int, task_ids: List[int]
    ) -> Dict[int, dict]:
        task_ids_str = ",".join(str(tid) for tid in task_ids)
        params = {"task_ids": task_ids_str}

        async def _fire_and_forget():
            try:
                await self._request(
                    "GET", f"/{kb_id}/documents/tasks", params=params
                )
            except Exception as e:
                logger.warning(
                    f"Fire-and-forget task fetch failed for kb_id={kb_id}: {e}"
                )

        asyncio.create_task(_fire_and_forget())

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
        payload = {"kb_id": kb_id, "query": query, "top_k": top_k}
        return await self._request("POST", "/test-retrieval", data=payload)

    # ---- Cleanup ----
    async def cleanup_temp_files(self) -> Dict[str, Any]:
        return await self._request("POST", "/cleanup")
