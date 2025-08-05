from fastmcp import FastMCP

from app.core.config import settings

mcp = FastMCP(name=settings.PROJECT_NAME)


@mcp.resource("resource://config")
def get_config() -> dict:
    """Provides the application's configuration."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@mcp.tool("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8600,
        log_level="debug",
    )
