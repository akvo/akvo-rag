from app.core.config import settings

DEFAULT_MCP_SERVERS = {
    "knowledge_bases_mcp": {
        "url": settings.KNOWLEDGE_BASES_MCP,
        "api_key": settings.KNOWLEDGE_BASES_API_KEY,
        "type": "fastmcp",
    },
    "weather_mcp": {
        "url": settings.WEATHER_MCP,
        "type": "rest",
        "tools": [
            {
                "name": "get_weather_forecast",
                "description": "Get multi-day weather forecasts for a given location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Uses open_meteo (free)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "days": {"type": "integer"},
                    },
                    "required": ["latitude", "longitude"],
                },
            },
            {
                "name": "get_current_weather",
                "description": "Fetch current weather conditions for a given location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Uses open_meteo (free)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "required": ["latitude", "longitude"],
                },
            },
            {
                "name": "get_historical_weather",
                "description": "Get historical weather data for a specific date and location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Uses open_meteo (free)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                    },
                    "required": [
                        "latitude", "longitude", "start_date", "end_date"
                    ],
                },
            },
            {
                "name": "analyze_weather_trends",
                "description": "Analyze weather trends over a specified period for a location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Uses open_meteo (free)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "period": {"type": "string"},
                    },
                    "required": [
                        "latitude", "longitude", "period"
                    ],
                },
            },
            {
                "name": "get_tomorrow_weather",
                "description": "Get weather forecast for tomorrow for a given location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses tomorrow_io API
                "api_key_name": "TOMORROW_IO_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": [
                        "location"
                    ],
                },
            },
            {
                "name": "get_weather_alerts",
                "description": "Fetch active weather alerts for a specified location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses tomorrow_io API
                "api_key_name": "TOMORROW_IO_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": [
                        "location"
                    ],
                },
            },
            {
                "name": "get_google_weather_current_conditions",
                "description": "Fetch current weather conditions from Google Weather for a given location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses Google Weather API
                "api_key_name": "GOOGLE_WEATHER_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "required": [
                        "latitude", "longitude"
                    ],
                },
            },
            {
                "name": "get_openweathermap_weather",
                "description": "Fetch current weather data from OpenWeatherMap for a given location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses OpenWeatherMap API
                "api_key_name": "OPENWEATHERMAP_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                    },
                    "required": [
                        "lat", "lon"
                    ],
                },
            },
            {
                "name": "get_accuweather_current_conditions",
                "description": "Fetch current weather conditions from AccuWeather for a given location key.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses AccuWeather API
                "api_key_name": "ACCUWEATHER_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location_key": {"type": "string"},
                    },
                    "required": [
                        "location_key"
                    ],
                },
            },
            {
                "name": "predict_weather_alert",
                "description": "Predict potential weather alerts based on location.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses OpenAI API
                "api_key_name": "OPENAI_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "required": [
                        "latitude", "longitude"
                    ],
                },
            },
            {
                "name": "list_villages",
                "description": "List villages in a specified state and/or district.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Geographic tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "district": {"type": "string"},
                    },
                    "required": [
                        "state"
                    ],
                },
            },
            {
                "name": "reverse_geocode",
                "description": "Get location details from latitude and longitude.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Geographic tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location_name": {"type": "string"},
                    },
                    "required": [
                        "location_name"
                    ],
                },
            },
            {
                "name": "get_administrative_bounds",
                "description": "Get administrative boundaries for a given village ID.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Geographic tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "village_id": {"type": "string"},
                    },
                    "required": [
                        "village_id"
                    ],
                },
            },
            {
                "name": "get_crop_calendar",
                "description": "Get crop calendar information for a specific region and/or crop type.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Crop calendar tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region": {"type": "string"},
                        "crop_type": {"type": "string"},
                    },
                    "required": [
                        "region"
                    ],
                },
            },
            {
                "name": "get_prominent_crops",
                "description": "Get prominent crops for a specific region and season.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Crop calendar tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region": {"type": "string"},
                        "season": {"type": "string"},
                    },
                    "required": [
                        "region", "season"
                    ],
                },
            },
            {
                "name": "estimate_crop_stage",
                "description": "Estimate the growth stage of a crop based on planting date and current date.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": False,  # Crop calendar tools (no API needed)
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "crop": {"type": "string"},
                        "plant_date": {"type": "string"},
                        "current_date": {"type": "string"},
                    },
                    "required": [
                        "crop", "plant_date", "current_date"
                    ],
                },
            },
            {
                "name": "generate_weather_alert",
                "description": "Generate weather alert based on crop and weather data.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses OpenAI API
                "api_key_name": "OPENAI_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "crop": {"type": "string"},
                        "weather_data": {"type": "dict"},
                        "growth_stage": {"type": "string"},
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "required": [
                        "crop", "weather_data", "growth_stage",
                        "latitude", "longitude"
                    ],
                },
            },
            {
                "name": "prioritize_alerts",
                "description": "Prioritize alerts based on urgency factors.",
                "endpoint": "/mcp",
                "method": "POST",
                "api_key_required": True,  # Uses OpenAI API
                "api_key_name": "OPENAI_API_KEY",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "alerts_list": {"type": "list"},
                        "urgency_factors": {"type": "dict"},
                    },
                    "required": [
                        "alerts_list", "urgency_factors"
                    ],
                },
            },
        ],
    },
}
