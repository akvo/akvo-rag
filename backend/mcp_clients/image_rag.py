import asyncio
from fastmcp import Client


client = Client("http://host.docker.internal:8600/mcp")


async def main():
    async with client:
        await client.ping()

        tools = await client.list_tools()
        print(tools)


asyncio.run(main())
