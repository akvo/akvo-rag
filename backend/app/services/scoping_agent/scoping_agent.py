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

    llm = LLMFactory.create()

    agent_executor = create_react_agent(model=llm, tools=tools, debug=True)

    return agent_executor


# Testing purpose from terminal
if __name__ == "__main__":

    async def main():
        agent = await scoping_agent()
        result = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="How is cashew gumosis looks like?",
                    )
                ]
            }
        )
        print(result)

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content="Where is Indonesia located?")]}
        )
        print(result)

    asyncio.run(main())
