import json

from langgraph.prebuilt import create_react_agent
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager
from app.services.llm.llm_factory import LLMFactory
from .helper import make_structured_tool


async def scoping_agent():
    manager = MultiMCPClientManager()

    # Step 1: Ambil semua tools
    all_tools_info = await manager.get_all_tools()
    tools = []
    for server_name, tool_list in all_tools_info.items():
        if isinstance(tool_list, list):
            for tool in tool_list:
                tools.append(
                    make_structured_tool(
                        manager=manager,
                        server_name=server_name,
                        tool_name=tool.name,
                        input_schema=tool.inputSchema,
                        description=tool.description,
                    )
                )
    tool_list = [
        {
            "server_name": t.metadata.get("server_name"),
            "tool_name": t.metadata.get("original_name", t.name),
            "description": t.description,
        }
        for t in tools
    ]

    # Step 2: Ambil semua resources
    all_resources_info = await manager.get_all_resources()
    resources_context = []
    for server_name, resource_list in all_resources_info.items():
        if isinstance(resource_list, list):
            for r in resource_list:
                kb_details = ""
                try:
                    content = await manager.read_resource(
                        server_name=server_name, uri=r.uri
                    )
                    if content and hasattr(content[0], "text"):
                        try:
                            parsed = json.loads(content[0].text)
                            if (
                                isinstance(parsed, list)
                                and parsed
                                and "id" in parsed[0]
                            ):
                                kb_details = "\n".join(
                                    [
                                        f"  - ({kb['id']}) {kb['name']}: {kb.get('description', '')}"
                                        for kb in parsed
                                    ]
                                )
                            else:
                                kb_details = content[0].text
                        except json.JSONDecodeError:
                            kb_details = content[0].text
                except Exception as e:
                    kb_details = f"[Error reading resource: {e}]"

                resources_context.append(
                    f"[{server_name}] {r.uri} - {r.name} ({r.description})\nKBs:\n{kb_details}"
                )

    resources_text = "\n\n".join(resources_context)

    # Step 3: Prompt khusus supaya LLM return JSON siap dispatch
    system_prompt = (
        "You are a scoping agent.\n"
        "You have access ONLY to the tools listed below.\n"
        "Your job: Pick the most relevant tool, "
        "and return ONLY a JSON object in this format:\n"
        "{\n"
        '  "server_name": "<server name from the list>",\n'
        '  "tool_name": "<tool name from the list>",\n'
        '  "input": { <valid JSON matching the tool input schema> }\n'
        "}\n\n"
        "If no tool is relevant, return:\n"
        "{\n"
        '  "server_name": null,\n'
        '  "tool_name": null,\n'
        '  "input": {}\n'
        "}\n\n"
        f"Tools: {tool_list}\n\n"
        f"Resources:\n{resources_text}\n"
    )

    llm = LLMFactory.create()
    agent_executor = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    return agent_executor
