import asyncio
import os
from typing import List
import pypdf

from .base import BaseDocumentParser, ParsedDocument, ParsedPage


class PDFParser(BaseDocumentParser):
    def _parse_sync(self, file_path: str, file_name: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at path: {file_path}")

        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        pages: List[ParsedPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                ParsedPage(
                    page_number=idx,
                    text=text,
                    metadata={"page_number": idx, "file_name": file_name}
                )
            )

        return ParsedDocument(
            file_name=file_name,
            total_pages=total_pages,
            pages=pages,
            metadata={"file_name": file_name, "total_pages": total_pages}
        )

    async def parse(self, file_path: str, file_name: str) -> ParsedDocument:
        return await asyncio.to_thread(self._parse_sync, file_path, file_name)
