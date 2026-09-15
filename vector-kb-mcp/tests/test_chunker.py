from chunker.hashing import generate_chunk_id
from chunker.text_chunker import DocumentChunkDTO, TextChunker
from parser.base import ParsedDocument, ParsedPage


def test_generate_chunk_id_determinism():
    hash1, id1 = generate_chunk_id(
        kb_id=1,
        file_name="manual.pdf",
        chunk_content="This is sample content for testing determinism.",
    )
    hash2, id2 = generate_chunk_id(
        kb_id=1,
        file_name="manual.pdf",
        chunk_content="This is sample content for testing determinism.",
    )
    assert hash1 == hash2
    assert id1 == id2
    assert id1.startswith("kb_1_")
    assert len(hash1) == 64  # SHA256 hex length


def test_generate_chunk_id_variance():
    hash1, id1 = generate_chunk_id(
        kb_id=1, file_name="manual.pdf", chunk_content="Content A"
    )
    hash2, id2 = generate_chunk_id(
        kb_id=1, file_name="manual.pdf", chunk_content="Content B"
    )
    hash3, id3 = generate_chunk_id(
        kb_id=2, file_name="manual.pdf", chunk_content="Content A"
    )

    assert hash1 != hash2
    assert id1 != id2
    assert id1 != id3
    assert hash1 == hash3


def test_text_chunker_splits_document():
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    doc = ParsedDocument(
        file_name="guide.pdf",
        total_pages=2,
        pages=[
            ParsedPage(
                page_number=1,
                text="This is page one text with some sentences. "
                "It should be split into appropriate chunks.",
                metadata={"author": "Test"},
            ),
            ParsedPage(
                page_number=2,
                text="This is page two text with more content for "
                "testing multi-page document chunking.",
                metadata={"author": "Test"},
            ),
        ],
    )

    chunks = chunker.chunk_document(doc, kb_id=10)
    assert len(chunks) > 0
    for idx, c in enumerate(chunks):
        assert isinstance(c, DocumentChunkDTO)
        assert c.chunk_index == idx
        assert c.token_count > 0
        assert c.metadata["kb_id"] == 10
        assert c.metadata["file_name"] == "guide.pdf"
        assert c.metadata["page_number"] in (1, 2)
        assert c.metadata["author"] == "Test"
        assert c.chunk_id.startswith("kb_10_")


def test_text_chunker_empty_document():
    chunker = TextChunker()
    doc = ParsedDocument(
        file_name="empty.txt",
        total_pages=3,
        pages=[
            ParsedPage(page_number=1, text="   \n\n   "),
            ParsedPage(page_number=2, text=""),
            ParsedPage(page_number=3, text=None),
        ],
    )
    chunks = chunker.chunk_document(doc, kb_id=1)
    assert len(chunks) == 0


def test_text_chunker_chunk_size_and_overlap():
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)
    long_text = "Word " * 600  # ~3000 characters
    doc = ParsedDocument(
        file_name="long.txt",
        total_pages=1,
        pages=[ParsedPage(page_number=1, text=long_text)],
    )
    chunks = chunker.chunk_document(doc, kb_id=5)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.content) <= 500


def test_text_chunker_whitespace_splits():
    chunker = TextChunker(chunk_size=10, chunk_overlap=0)
    doc = ParsedDocument(
        file_name="spaces.txt",
        total_pages=1,
        pages=[ParsedPage(page_number=1, text="Content\n\n   \n\nMore")],
    )
    chunks = chunker.chunk_document(doc, kb_id=1)
    assert len(chunks) == 2
    assert chunks[0].content == "Content"
    assert chunks[1].content == "More"
