from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    kb_id: int
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchFilter:
    document_ids: Optional[List[str]] = None
    metadata_filter: Optional[Dict[str, Any]] = None
