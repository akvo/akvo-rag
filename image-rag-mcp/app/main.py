from fastmcp import FastMCP

from typing import Optional
from app.core.config import settings

from app.tools.search import multimodal_search

mcp = FastMCP(name=settings.PROJECT_NAME)


@mcp.resource("resource://config")
def get_config() -> dict:
    """Provides the application's configuration."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@mcp.resource("resource://health")
def health_check():
    return {"status": "ok"}


@mcp.tool(
    "/search",
    title="Pest and Disease Search Tool",
    description=(
        "Search for pest and disease information using image and text queries."
    ),
)
def image_search_tool(
    image_file: Optional[bytes] = None,
    text_query: Optional[str] = None,
    top_k: int = 10,
) -> dict:
    return multimodal_search(
        image_file=image_file, text_query=text_query, top_k=top_k
    )


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8600,
        log_level="debug",
    )
