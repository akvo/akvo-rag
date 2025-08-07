import asyncio
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager


# Testing purpose from terminal
# can handle more that one MCP server
# e.g. image_rag, text_analysis, etc.
async def main():
    manager = MultiMCPClientManager()
    print("\n🔍 Ping servers:")
    print(await manager.ping_all())

    print("\n📋 Resources available:")
    resources = await manager.get_all_resources()
    for server, t in resources.items():
        print(f"{server}: {t}")

    print("\n📋 Tools available:")
    tools = await manager.get_all_tools()
    for server, t in tools.items():
        print(f"{server}: {t}")

    # print("\n⚡ Call tool '/search' image_rag:")
    # result = await manager.run_tool(
    #     "image_rag", "/search", {"text_query": "What is cashew gumosis?"}
    # )
    # print(f"Call result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
