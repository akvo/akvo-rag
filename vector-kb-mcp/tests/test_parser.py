import os
import tempfile
from unittest.mock import patch
import pypdf
import pytest

from parser import get_parser_for_file, parse_file_bytes
from parser.base import ParsedDocument
from parser.docx_parser import DocxParser
from parser.pdf_parser import PDFParser
from parser.text_parser import TextParser


@pytest.mark.asyncio
async def test_text_parser_txt():
    parser = TextParser()
    with tempfile.NamedTemporaryFile(
        suffix=".txt", mode="w+", encoding="utf-8", delete=False
    ) as f:
        f.write("Hello World!\nPlain text file test.\n\nParagraph two.")
        temp_path = f.name

    try:
        doc = await parser.parse(temp_path, "sample.txt")
        assert isinstance(doc, ParsedDocument)
        assert doc.file_name == "sample.txt"
        assert doc.total_pages == 1
        assert len(doc.pages) == 1
        assert "Hello World!" in doc.pages[0].text
        assert "Paragraph two." in doc.pages[0].text
        assert doc.pages[0].page_number == 1
        assert doc.pages[0].metadata.get("file_name") == "sample.txt"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_text_parser_markdown():
    parser = TextParser()
    with tempfile.NamedTemporaryFile(
        suffix=".md", mode="w+", encoding="utf-8", delete=False
    ) as f:
        f.write("# Heading 1\n\n- Item 1\n- Item 2\n\n```py\ncode\n```")
        temp_path = f.name

    try:
        doc = await parser.parse(temp_path, "README.md")
        assert doc.file_name == "README.md"
        assert doc.total_pages == 1
        assert "# Heading 1" in doc.pages[0].text
        assert "Item 1" in doc.pages[0].text
        assert doc.pages[0].page_number == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_pdf_parser_multi_page():
    # Generate a valid 2-page PDF file in-memory using pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)

    with tempfile.NamedTemporaryFile(
        suffix=".pdf", mode="wb", delete=False
    ) as f:
        writer.write(f)
        temp_path = f.name

    try:
        parser = PDFParser()
        with patch.object(
            pypdf.PageObject,
            "extract_text",
            side_effect=["Page 1 Content", "Page 2 Content"],
        ):
            doc = await parser.parse(temp_path, "manual.pdf")
            assert doc.file_name == "manual.pdf"
            assert doc.total_pages == 2
            assert len(doc.pages) == 2
            assert doc.pages[0].page_number == 1
            assert doc.pages[0].text == "Page 1 Content"
            assert doc.pages[1].page_number == 2
            assert doc.pages[1].text == "Page 2 Content"
            assert doc.pages[0].metadata.get("page_number") == 1
            assert doc.pages[1].metadata.get("page_number") == 2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_docx_parser():
    parser = DocxParser()
    with tempfile.NamedTemporaryFile(
        suffix=".docx", mode="w+", delete=False
    ) as f:
        f.write("mock docx content")
        temp_path = f.name

    try:
        mock_output = "Extracted DOCX paragraph 1\n\nParagraph 2"
        with patch("docx2txt.process", return_value=mock_output):
            doc = await parser.parse(temp_path, "report.docx")
            assert doc.file_name == "report.docx"
            assert doc.total_pages == 1
            assert len(doc.pages) == 1
            assert "Extracted DOCX paragraph 1" in doc.pages[0].text
            assert doc.pages[0].page_number == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_parser_factory_dispatcher():
    assert isinstance(get_parser_for_file("test.pdf"), PDFParser)
    assert isinstance(get_parser_for_file("TEST.PDF"), PDFParser)
    assert isinstance(get_parser_for_file("report.docx"), DocxParser)
    assert isinstance(get_parser_for_file("legacy.doc"), DocxParser)
    assert isinstance(get_parser_for_file("notes.txt"), TextParser)
    assert isinstance(get_parser_for_file("guide.md"), TextParser)


def test_parser_factory_unsupported():
    with pytest.raises(ValueError, match="Unsupported file type"):
        get_parser_for_file("malicious.exe")

    with pytest.raises(ValueError, match="Unsupported file type"):
        get_parser_for_file("archive.zip")


@pytest.mark.asyncio
async def test_parser_missing_file():
    text_parser = TextParser()
    with pytest.raises(FileNotFoundError):
        await text_parser.parse("/non/existent/path/doc.txt", "doc.txt")

    pdf_parser = PDFParser()
    with pytest.raises(FileNotFoundError):
        await pdf_parser.parse("/non/existent/path/doc.pdf", "doc.pdf")

    docx_parser = DocxParser()
    with pytest.raises(FileNotFoundError):
        await docx_parser.parse("/non/existent/path/doc.docx", "doc.docx")


@pytest.mark.asyncio
async def test_parse_file_bytes_txt():
    raw_data = b"Line 1 from raw bytes\nLine 2 text"
    doc = await parse_file_bytes(raw_data, "bytes_test.txt")
    assert isinstance(doc, ParsedDocument)
    assert doc.file_name == "bytes_test.txt"
    assert doc.total_pages == 1
    assert "Line 1 from raw bytes" in doc.pages[0].text


@pytest.mark.asyncio
async def test_parse_file_bytes_unsupported():
    with pytest.raises(ValueError, match="Unsupported file type"):
        await parse_file_bytes(b"binary data", "file.unsupported")
