import os
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


__all__ = [
    "BaseDocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "PDFParser",
    "DocxParser",
    "TextParser",
    "get_parser_for_file",
]
