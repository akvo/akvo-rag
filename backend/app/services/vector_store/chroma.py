from typing import List, Any
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
import chromadb 
import logging
from app.core.config import settings

from .base import BaseVectorStore

logger = logging.getLogger(__name__)

class ChromaVectorStore(BaseVectorStore):
    """Chroma vector store implementation"""
    
    def __init__(self, collection_name: str, embedding_function: Embeddings, **kwargs):
        """Initialize Chroma vector store"""
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_DB_HOST,
            port=settings.CHROMA_DB_PORT,
        )
        
        self._store = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embedding_function,
        )
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to Chroma in batches to avoid payload size limits"""
        if not documents:
            return
        
        batch_size = settings.VECTOR_STORE_BATCH_SIZE
        total_documents = len(documents)
        
        logger.info(f"Adding {total_documents} documents to vector store in batches of {batch_size}")
        
        for i in range(0, total_documents, batch_size):
            batch = documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_documents + batch_size - 1) // batch_size
            
            logger.info(f"Adding batch {batch_num}/{total_batches} ({len(batch)} documents)")
            self._store.add_documents(batch)
            
        logger.info(f"Successfully added all {total_documents} documents to vector store")
    
    def delete(self, ids: List[str]) -> None:
        """Delete documents from Chroma"""
        self._store.delete(ids)
    
    def as_retriever(self, **kwargs: Any):
        """Return a retriever interface"""
        return self._store.as_retriever(**kwargs)
    
    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents in Chroma"""
        return self._store.similarity_search(query, k=k, **kwargs)
    
    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        """Search for similar documents in Chroma with score"""
        return self._store.similarity_search_with_score(query, k=k, **kwargs)

    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self._store._client.delete_collection(self._store._collection.name) 