"""
Utility script to ensure ChromaDB collections are populated with chunk
embeddings from vkb_document_chunks in PostgreSQL.
"""

import argparse
import asyncio
import logging
from typing import List

import chromadb
from openai import AsyncOpenAI
from sqlalchemy import select

from core.config import settings
from db.session import get_db_session
from models import DocumentChunk
from retriever.chroma_retriever import ChromaRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [seed_chroma] %(message)s",
)
logger = logging.getLogger("seed_chroma")


async def seed_kb(
    kb_id: int, limit: int = None, batch_size: int = 200, force: bool = False
):
    """Seed ChromaDB collection for a given knowledge base ID."""
    collection_name = f"kb_{kb_id}"

    # Initialize Chroma client
    if settings.CHROMA_HOST and settings.CHROMA_PORT:
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST, port=int(settings.CHROMA_PORT)
        )
    else:
        chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY
        )

    # Check if collection already has documents
    try:
        coll = chroma_client.get_collection(name=collection_name)
        count = coll.count()
        if count > 0 and not force and not limit:
            logger.info(
                "Collection '%s' already has %d documents. Skipping (use --force to re-seed/append).",  # noqa
                collection_name,
                count,
            )
            return count
    except Exception:
        pass

    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    retriever = ChromaRetriever(
        chroma_client=chroma_client,
        openai_client=openai_client,
        embedding_model="text-embedding-3-small",
        expected_dim=1536,
    )

    # Fetch chunks from PostgreSQL
    async with get_db_session() as session:
        query = (
            select(DocumentChunk)
            .where(DocumentChunk.kb_id == kb_id)
            .order_by(DocumentChunk.id)
        )
        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        chunks: List[DocumentChunk] = result.scalars().all()

    if not chunks:
        logger.warning(
            "No document chunks found in PostgreSQL for KB %d", kb_id
        )
        return 0

    logger.info(
        "Seeding Chroma collection '%s' with %d chunks...",
        collection_name,
        len(chunks),
    )

    total_synced = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]  # noqa
        ids = []
        texts = []
        metadatas = []

        for c in batch:
            page_content = ""
            meta = {}
            if c.chunk_metadata and isinstance(c.chunk_metadata, dict):
                page_content = c.chunk_metadata.get("page_content", "")
                meta = {
                    k: str(v) if isinstance(v, (dict, list)) else v
                    for k, v in c.chunk_metadata.items()
                    if k != "page_content"
                }

            if not page_content:
                continue

            ids.append(c.id)
            texts.append(page_content)
            meta["document_id"] = c.document_id
            meta["chunk_id"] = c.id
            meta["kb_id"] = c.kb_id
            meta["file_name"] = c.file_name
            metadatas.append(meta)

        if not texts:
            continue

        embeddings = await retriever.embed_texts(texts)
        await retriever.upsert_collection_chunks(
            collection_name=collection_name,
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        total_synced += len(ids)
        logger.info(
            "Synced %d / %d chunks to '%s'",
            total_synced,
            len(chunks),
            collection_name,
        )

    logger.info(
        "Successfully seeded %d chunks to collection '%s'",
        total_synced,
        collection_name,
    )
    return total_synced


async def main():
    parser = argparse.ArgumentParser(
        description="Seed ChromaDB from PostgreSQL document chunks"
    )
    parser.add_argument(
        "--kb-id", type=int, default=115, help="Knowledge Base ID to seed"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max chunks to seed"
    )
    parser.add_argument(
        "--batch-size", type=int, default=200, help="Embedding batch size"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-seeding even if collection exists",
    )
    args = parser.parse_args()

    await seed_kb(
        kb_id=args.kb_id,
        limit=args.limit,
        batch_size=args.batch_size,
        force=args.force,
    )


if __name__ == "__main__":
    asyncio.run(main())
