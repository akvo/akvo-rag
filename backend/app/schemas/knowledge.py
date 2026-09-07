from typing import Optional, List, Union
from pydantic import BaseModel


class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBaseUpdate(KnowledgeBaseBase):
    pass


class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: int


class PreviewRequest(BaseModel):
    document_ids: Optional[List[Union[int, str]]] = None
    file_paths: Optional[List[str]] = None
    chunk_size: int = 1000
    chunk_overlap: int = 200
