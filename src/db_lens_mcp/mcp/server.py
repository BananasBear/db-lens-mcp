"""MCP server construction and stdio runner."""

from __future__ import annotations

from db_lens_mcp.mcp.tools import register_tools


def create_server():
    """Create a configured MCP server instance."""

    from mcp.server.fastmcp import FastMCP

    server = FastMCP("db-lens-mcp")
    register_tools(server)
    return server


def run_stdio_server() -> None:
    """Run the local MCP stdio server."""

    server = create_server()
    server.run(transport="stdio")
