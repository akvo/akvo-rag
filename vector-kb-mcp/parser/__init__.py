import os
import tempfile
from .base import BaseDocumentParser, ParsedDocument, ParsedPage
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .text_parser import TextParser


def get_parser_for_file(file_name: str) -> BaseDocumentParser:
    """
    Factory function returning the appropriate parser based on file extension.

    Args:
        file_name: The file name or path.

    Returns:
        Instance of BaseDocumentParser.

    Raises:
        ValueError: If the file extension is not supported.
    """
    _, ext = os.path.splitext(file_name.lower())
    if ext == ".pdf":
        return PDFParser()
    elif ext in (".docx", ".doc"):
        return DocxParser()
    elif ext in (".txt", ".md", ".markdown"):
        return TextParser()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


async def parse_file_bytes(raw_bytes: bytes, file_name: str) -> ParsedDocument:
    """
    Write raw bytes to a temporary file and parse using the appropriate parser.
    Ensures safe temporary file cleanup after parsing.

    Args:
        raw_bytes: Raw binary content of the file.
        file_name: File name (used to resolve parser strategy).

    Returns:
        ParsedDocument containing pages and metadata.
    """
    suffix = os.path.splitext(file_name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw_bytes)
        temp_path = tmp.name

    try:
        parser = get_parser_for_file(file_name)
        return await parser.parse(temp_path, file_name)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


__all__ = [
    "BaseDocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "PDFParser",
    "DocxParser",
    "TextParser",
    "get_parser_for_file",
    "parse_file_bytes",
]
