import asyncio
import logging
from typing import Any, List, Optional
from openai import AsyncOpenAI

from core.guards import validate_embedding_dimension
from .models import RetrievedChunk

logger = logging.getLogger("vector-kb-mcp.retriever")


class ChromaRetriever:
    def __init__(
        self,
        chroma_client: Any,
        openai_client: AsyncOpenAI,
        embedding_model: str = "text-embedding-3-small",
        expected_dim: int = 1536,
    ):
        """
        Direct ChromaDB retriever for parallel multi-KB search.

        Args:
            chroma_client: Initialized chromadb ClientAPI instance.
            openai_client: AsyncOpenAI client instance.
            embedding_model: OpenAI embedding model name.
            expected_dim: Expected embedding vector dimension (default: 1536).
        """
        self.chroma = chroma_client
        self.openai = openai_client
        self.embedding_model = embedding_model
        self.expected_dim = expected_dim

    async def _embed_query(self, query: str) -> List[float]:
        """
        Generate normalized embedding vector for the search query and
        validate its dimensionality against the expected dimension guard.
        """
        response = await self.openai.embeddings.create(
            input=[query],
            model=self.embedding_model,
        )
        raw_vector = response.data[0].embedding
        return validate_embedding_dimension(
            embedding=raw_vector,
            expected_dim=self.expected_dim,
            kb_id=0,
            model=self.embedding_model,
        )

    async def _query_single_collection(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int,
    ) -> List[RetrievedChunk]:
        """
        Query a single ChromaDB collection asynchronously.

        Args:
            collection_name: Target Chroma collection name (e.g. 'kb_1').
            query_vector: 1536-dimensional query embedding vector.
            top_k: Maximum chunk count to retrieve.

        Returns:
            List of RetrievedChunk DTOs with calculated cosine scores.
        """
        try:
            collection = await asyncio.to_thread(
                self.chroma.get_collection, name=collection_name
            )
            results = await asyncio.to_thread(
                collection.query,
                query_embeddings=[query_vector],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            if (
                not results
                or not results.get("documents")
                or not results["documents"][0]
            ):
                return []

            docs = results["documents"][0]
            metas = (
                results["metadatas"][0]
                if results.get("metadatas")
                else [{}] * len(docs)
            )
            distances = (
                results["distances"][0]
                if results.get("distances")
                else [0.0] * len(docs)
            )
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            coll_meta = getattr(collection, "metadata", None) or {}
            if not isinstance(coll_meta, dict):
                coll_meta = {}
            space = coll_meta.get("hnsw:space", "l2")

            chunks: List[RetrievedChunk] = []
            for doc_text, meta, dist, cid in zip(docs, metas, distances, ids):
                d = float(dist)
                if space == "cosine":
                    similarity_score = round(max(0.0, min(1.0, 1.0 - d)), 4)
                elif space == "ip":
                    similarity_score = round(max(0.0, min(1.0, d)), 4)
                else:
                    # L2 metric: d = 2 - 2*cos(theta) => cos(theta) = 1 - d/2
                    similarity_score = round(
                        max(0.0, min(1.0, 1.0 - (d / 2.0))), 4
                    )

                meta_dict = meta if isinstance(meta, dict) else {}

                chunks.append(
                    RetrievedChunk(
                        chunk_id=str(cid),
                        kb_id=int(meta_dict.get("kb_id", 0)),
                        document_id=str(meta_dict.get("document_id", "")),
                        content=str(doc_text),
                        score=similarity_score,
                        metadata=meta_dict,
                    )
                )

            return chunks
        except Exception as e:
            logger.debug(
                "Failed querying collection %s: %s", collection_name, e
            )
            return []

    async def search(
        self,
        query: str,
        kb_ids: List[int],
        top_k: int = 4,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Perform parallel multi-KB vector similarity search.

        Args:
            query: The user search query string.
            kb_ids: List of knowledge base IDs to query in parallel.
            top_k: Maximum total chunks to return across all KBs.
            score_threshold: Minimum similarity score cutoff (optional).

        Returns:
            Ranked list of RetrievedChunk objects ordered by similarity.
        """
        if not kb_ids or not query or not query.strip():
            return []

        # 1. Generate query embedding
        query_vector = await self._embed_query(query.strip())

        # 2. Query all target KB collections in parallel
        tasks = [
            self._query_single_collection(f"kb_{kbid}", query_vector, top_k)
            for kbid in kb_ids
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=False)

        # 3. Flatten results
        all_chunks: List[RetrievedChunk] = []
        for res in results_nested:
            all_chunks.extend(res)

        # 4. Sort descending by similarity score
        all_chunks.sort(key=lambda c: c.score, reverse=True)

        # 5. Apply score threshold filter if configured
        if score_threshold is not None:
            all_chunks = [c for c in all_chunks if c.score >= score_threshold]

        # 6. Return top_k highest scoring chunks
        return all_chunks[:top_k]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a batch of text chunks.
        """
        if not texts:
            return []
        response = await self.openai.embeddings.create(
            input=texts,
            model=self.embedding_model,
        )
        return [
            validate_embedding_dimension(
                embedding=item.embedding,
                expected_dim=self.expected_dim,
                kb_id=0,
                model=self.embedding_model,
            )
            for item in response.data
        ]

    async def upsert_collection_chunks(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[dict],
    ) -> None:
        """
        Upsert chunk embeddings and metadata into a ChromaDB collection.
        """
        if not ids:
            return

        def _sync_upsert():
            coll = self.chroma.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            coll.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        await asyncio.to_thread(_sync_upsert)

    async def delete_document_chunks(
        self,
        collection_name: str,
        document_id: int,
    ) -> None:
        """
        Delete all vector chunks belonging to
        a document from a Chroma collection.
        """

        def _sync_delete():
            try:
                coll = self.chroma.get_collection(name=collection_name)
                coll.delete(where={"document_id": document_id})
            except Exception as e:
                logger.debug(
                    "Collection %s delete ignored: %s", collection_name, e
                )

        await asyncio.to_thread(_sync_delete)
