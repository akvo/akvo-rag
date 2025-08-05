import asyncio
from fastmcp import Client


client = Client("http://image-rag-mcp:8600/mcp")


async def main():
    async with client:
        await client.ping()

        tools = await client.list_tools()
        print(tools)


if __name__ == "__main__":
    asyncio.run(main())
