import httpx
from fastapi import HTTPException, UploadFile
from typing import Optional, List, Dict, Any
from app.core.config import settings


class KnowledgeBaseMCPEndpointService:
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
        files: Optional[dict] = None,
    ) -> Any:
        url = f"{self.base_url}/api/v1/knowledge-base{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                json=data,
                params=params,
                files=files,
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code, detail=response.text
            )

        return response.json() if response.content else None

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
        """
        Send UploadFile list as multipart/form-data.
        """
        file_payload = [
            ("files", (f.filename, await f.read(), f.content_type))
            for f in files
        ]

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
