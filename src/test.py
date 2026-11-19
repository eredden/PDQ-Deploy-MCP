# test.py - A simple test client for the PDQ Deploy MCP server.

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["src/main.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List the registered MCP tools.
            tools = await session.list_tools()
            print("Registered tools:", [t.name for t in tools.tools])

            # Try calling the get_tables tool to see if the output shows all tables.
            result = await session.call_tool("get_tables", arguments={})
            print("Database tables:", result.content)

if __name__ == "__main__":
    asyncio.run(main())