from app.core.config import settings

DEFAULT_MCP_SERVERS = {
    "knowledge_bases_mcp": {
        "url": settings.KNOWLEDGE_BASES_MCP,
        "api_key": settings.KNOWLEDGE_BASES_API_KEY,
        "type": "fastmcp",
    },
    "weather_mcp": {
        "url": "http://host.docker.internal:8200",
        "type": "rest",
        "tools": [
            {
                "name": "get_current_weather",
                "description": "Get the current weather data for a given location.",
                "endpoint": "/weather/current",
                "method": "POST",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            },
            {
                "name": "get_forecast",
                "description": "Get weather forecast for given location and days.",
                "endpoint": "/weather/forecast",
                "method": "POST",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "days": {"type": "integer"},
                    },
                    "required": ["location"],
                },
            },
        ],
    },
}
