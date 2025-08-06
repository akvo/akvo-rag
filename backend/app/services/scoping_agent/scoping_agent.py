import asyncio
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager
from app.services.llm.llm_factory import LLMFactory
from .helper import make_structured_tool


async def scoping_agent():
    manager = MultiMCPClientManager(
        {
            "image_rag_mcp": "http://image-rag-mcp:8600/mcp",
            "knowledge_bases_mcp": "http://localhost:8700/mcp",
        }
    )

    # 🔹 Step 1
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

    # 🔹 Step 2
    all_resources_info = await manager.get_all_resources()
    resources_context = []

    for server_name, resource_list in all_resources_info.items():
        if isinstance(resource_list, list):
            for r in resource_list:
                kb_details = ""
                try:
                    # Baca isi resource
                    content = await manager.read_resource(
                        server_name=server_name, uri=r.uri
                    )
                    if content and hasattr(content[0], "text"):
                        try:
                            parsed = json.loads(content[0].text)
                            # Kalau isinya list KB
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

    # 🔹 Step 3
    system_prompt = (
        "You are a scoping agent.\n"
        "You have access ONLY to the tools listed below.\n"
        "NEVER call a tool that is not relevant to the user's query.\n"
        "If no tool is relevant, DO NOT call any tool — "
        "instead return ONLY a JSON object with:\n"
        "{\n"
        '  "resource_uri": "<uri from list above>",\n'
        '  "id": "<kb_id from list above or any relevant resource id>",\n'
        '  "reason": "<why it is relevant>"\n'
        "}\n\n"
        "Tools:\n"
        f"{[t.name for t in tools]}\n\n"
        "Resources:\n"
        f"{resources_text}\n"
    )

    # 🔹 Step 4
    llm = LLMFactory.create()
    agent_executor = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
        # debug=True,
    )

    return agent_executor


# Testing purpose from terminal
if __name__ == "__main__":

    async def main():
        agent = await scoping_agent()
        # await agent.ainvoke(
        #     {
        #         "messages": [
        #             HumanMessage(
        #                 content="How is cashew gumosis looks like?",
        #             )
        #         ]
        #     }
        # )

        result = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(content="Hi, what do you know about UNEP?")
                ]
            }
        )
        print(result)

    asyncio.run(main())


# python -m app.services.scoping_agent.scoping_agent
