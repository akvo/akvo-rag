import asyncio

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

    all_resources_info = await manager.get_all_resources()
    resources_context = []
    for server_name, resource_list in all_resources_info.items():
        if isinstance(resource_list, list):
            for r in resource_list:
                content = await manager.read_resource(
                    server_name=server_name, uri=r.uri
                )
                if content:
                    print(content, "=====")
                resources_context.append(
                    f"[{server_name}] {r.uri} - {r.name} ({r.description})"
                )
    resources_text = "\n".join(resources_context)
    system_prompt = (
        "You are a scoping agent. "
        "You have access to these tools and resources:\n"
        f"{resources_text}\n"
        "Select the most relevant tool or resource based on the user query."
    )

    llm = LLMFactory.create()

    agent_executor = create_react_agent(
        model=llm, tools=tools, prompt=system_prompt, debug=True
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

        await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(content="Hi, what do you know about UNEP?")
                ]
            }
        )

    asyncio.run(main())


# python -m app.services.scoping_agent.scoping_agent
