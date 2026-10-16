import asyncio
import os
import docx2txt

from .base import BaseDocumentParser, ParsedDocument, ParsedPage


class DocxParser(BaseDocumentParser):
    def _parse_sync(self, file_path: str, file_name: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"DOCX file not found at path: {file_path}"
            )

        text = docx2txt.process(file_path) or ""
        normalized_text = text.strip()

        page = ParsedPage(
            page_number=1,
            text=normalized_text,
            metadata={"page_number": 1, "file_name": file_name},
        )

        return ParsedDocument(
            file_name=file_name,
            total_pages=1,
            pages=[page],
            metadata={"file_name": file_name, "total_pages": 1},
        )

    async def parse(self, file_path: str, file_name: str) -> ParsedDocument:
        return await asyncio.to_thread(self._parse_sync, file_path, file_name)
