from typing import Any, Awaitable, Callable, Dict, Optional

from retriever.chroma_retriever import ChromaRetriever
from handlers.kb_handlers import (
    handle_list_kbs,
    handle_get_kb,
    handle_create_kb,
    handle_update_kb,
    handle_delete_kb,
)
from handlers.doc_handlers import (
    handle_list_docs,
    handle_get_doc,
    handle_get_tasks,
)
from handlers.query_handlers import handle_query_kb
from handlers.serializers import serialize_kb, serialize_doc, serialize_task


def build_tool_handlers(
    retriever_getter: Callable[[], Optional[ChromaRetriever]],
) -> Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]]:
    """
    Build and return the complete tool handler registry map for the worker.
    """
    async def _query_handler_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await handle_query_kb(args, retriever=retriever_getter())

    return {
        "query_knowledge_base": _query_handler_wrapper,
        "list_knowledge_bases": handle_list_kbs,
        "get_knowledge_base": handle_get_kb,
        "create_knowledge_base": handle_create_kb,
        "update_knowledge_base": handle_update_kb,
        "delete_knowledge_base": handle_delete_kb,
        "list_documents": handle_list_docs,
        "get_document": handle_get_doc,
        "get_processing_tasks": handle_get_tasks,
    }


__all__ = [
    "build_tool_handlers",
    "handle_query_kb",
    "handle_list_kbs",
    "handle_get_kb",
    "handle_create_kb",
    "handle_update_kb",
    "handle_delete_kb",
    "handle_list_docs",
    "handle_get_doc",
    "handle_get_tasks",
    "serialize_kb",
    "serialize_doc",
    "serialize_task",
]
