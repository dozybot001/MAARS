"""MCP server connections for ADK agents.

Uses community MCP servers instead of custom tool implementations.
Each function returns a McpToolset that ADK agents can use directly.
Returns None if the MCP server is unavailable — callers should filter.
"""

import logging

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

log = logging.getLogger(__name__)


def create_arxiv_toolset() -> McpToolset | None:
    """arXiv MCP server — search, download, read full papers.

    Returns None if the server package is not installed.
    """
    try:
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=["-m", "arxiv_mcp_server"],
                ),
                timeout=60.0,
            ),
        )
    except Exception as e:
        log.warning("arXiv MCP server unavailable: %s", e)
        return None


def create_fetch_toolset() -> McpToolset | None:
    """Web fetch MCP server — retrieve content from any URL.

    Returns None if the server package is not installed.
    """
    try:
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=["-m", "mcp_server_fetch"],
                ),
                timeout=60.0,
            ),
        )
    except Exception as e:
        log.warning("Fetch MCP server unavailable: %s", e)
        return None
