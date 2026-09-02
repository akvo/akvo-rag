from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .hashing import generate_chunk_id
from parser.base import ParsedDocument


@dataclass(frozen=True)
class DocumentChunkDTO:
    chunk_id: str
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        """
        Text chunker utilizing RecursiveCharacterTextSplitter.

        Args:
            chunk_size: Maximum character count per chunk.
            chunk_overlap: Overlapping character count between chunks.
            separators: List of custom split separators.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )

    def chunk_document(
        self, doc: ParsedDocument, kb_id: int
    ) -> List[DocumentChunkDTO]:
        """
        Chunk a parsed multi-page document into deterministic chunk DTOs.

        Args:
            doc: ParsedDocument instance.
            kb_id: The target knowledge base identifier.

        Returns:
            List of DocumentChunkDTO items.
        """
        chunks: List[DocumentChunkDTO] = []
        chunk_idx = 0

        for page in doc.pages:
            if not page.text or not page.text.strip():
                continue

            splits = self.splitter.split_text(page.text)
            for split_text in splits:
                cleaned_text = split_text.strip()
                if cleaned_text:
                    meta = {
                        **page.metadata,
                        "page_number": page.page_number,
                        "file_name": doc.file_name,
                        "kb_id": kb_id,
                    }

                    chunk_hash, chunk_id = generate_chunk_id(
                        kb_id=kb_id,
                        file_name=doc.file_name,
                        chunk_content=cleaned_text,
                        chunk_metadata=meta,
                    )

                    token_count = max(1, len(cleaned_text.split()))

                    chunks.append(
                        DocumentChunkDTO(
                            chunk_id=chunk_id,
                            chunk_index=chunk_idx,
                            content=cleaned_text,
                            content_hash=chunk_hash,
                            token_count=token_count,
                            metadata=meta,
                        )
                    )
                    chunk_idx += 1

        return chunks
