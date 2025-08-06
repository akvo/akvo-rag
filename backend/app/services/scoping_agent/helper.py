import re

from pydantic import create_model
from typing import Any
from langchain.tools import StructuredTool


def sanitize_tool_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def json_schema_to_pydantic(name: str, schema: dict):
    """
    Convert MCP tool's inputSchema to a Pydantic model dynamically.
    """
    fields = {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    for field_name, field_info in props.items():
        field_type = Any
        if field_info.get("type") == "string":
            field_type = str
        elif field_info.get("type") == "integer":
            field_type = int
        elif field_info.get("type") == "number":
            field_type = float
        elif field_info.get("type") == "boolean":
            field_type = bool
        elif field_info.get("type") == "object":
            field_type = dict
        elif field_info.get("type") == "array":
            field_type = list

        # Default value
        default = field_info.get("default", None)
        if field_name not in required:
            field_type = field_type | None

        fields[field_name] = (field_type, default)

    return create_model(name, **fields)


def make_structured_tool(
    manager,
    server_name: str,
    tool_name: str,
    input_schema: dict,
    description: str,
):
    """
    Create a structured tool for the MCP client.
    """
    model = json_schema_to_pydantic(
        name=f"{server_name}_{tool_name}_Input", schema=input_schema
    )

    async def async_executor(**kwargs):
        args = model(**kwargs)  # validasi & parsing
        return await manager.run_tool(
            server_name=server_name,
            tool_name=tool_name,
            param=args.model_dump(),
        )

    return StructuredTool.from_function(
        coroutine=async_executor,
        name=sanitize_tool_name(f"{server_name}_{tool_name}"),
        description=description,
        args_schema=model,
        metadata={"original_name": tool_name, "server_name": server_name},
    )
