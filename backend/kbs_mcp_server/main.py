import json

from fastmcp import FastMCP
from mcp.types import TextResourceContents
from typing import List

from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeBase, Document
from .query import query_kbs


mcp = FastMCP(name="Kowledge Bases MCP Server")


@mcp.custom_route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}


@mcp.resource(
    uri="resource://knowledge_bases",
    name="List of all Knowledge Bases",
    description="List of all available knowledge bases in the system.",
)
def list_all_knowledge_bases():
    """
    List all knowledge bases.
    """
    db = SessionLocal()
    try:
        # embeddings = EmbeddingsFactory.create()

        kbs = (
            db.query(KnowledgeBase)
            .join(Document, Document.knowledge_base_id == KnowledgeBase.id)
            .group_by(KnowledgeBase.id)
            .all()
        )

        print(f"Found {len(kbs)} KBs in DB")
        available_kbs = []
        for kb in kbs:
            print(f"KB: {kb.name} has {len(kb.documents)} docs")
            available_kbs.append(
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                }
            )
        return TextResourceContents(
            uri="resource://knowledge_bases",
            mimeType="application/json",
            text=json.dumps(available_kbs),
        )
    finally:
        db.close()


@mcp.tool(
    name="query_knowledge_base",
    description="Query a specific knowledge base return answer with context.",
)
async def query_knowledge_base(query: str, knowledge_base_ids: List[int]):
    return await query_kbs(query=query, knowledge_base_ids=knowledge_base_ids)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8700,
        log_level="debug",
    )
