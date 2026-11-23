# test_server.py - A simple test client for the PDQ Deploy MCP server.

from argparse import ArgumentParser
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    parser = ArgumentParser(description="Test the PDQ Deploy MCP server.")

    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to the SQLite database used by the server.",
    )
    args = parser.parse_args()

    server_params = StdioServerParameters(
        command="pdq-deploy-mcp",
        args=[
            "--db-path",
            args.db_path,
        ],
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