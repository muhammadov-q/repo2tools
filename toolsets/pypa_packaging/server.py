"""Serve the pypa/packaging tools as an MCP server.

    uv run python toolsets/pypa_packaging/server.py            # stdio
    uv run python toolsets/pypa_packaging/server.py --http 8765  # Streamable HTTP at /mcp
    uv run python toolsets/pypa_packaging/server.py --level workflow  # a coarser tool set

--level picks the granularity: function (default, the 21 tools in tools.py), feature or workflow
(coarse_tools.py), or all of them together.
"""

import argparse

from mcp.server.fastmcp import FastMCP

from tools import TOOLS

mcp = FastMCP("pypa_packaging_tools", log_level="WARNING")


def add_tools(level: str) -> None:
    tools = list(TOOLS) if level in ("function", "all") else []
    if level != "function":
        from coarse_tools import FEATURE_TOOLS, WORKFLOW_TOOLS

        tools += {"feature": FEATURE_TOOLS, "workflow": WORKFLOW_TOOLS, "all": FEATURE_TOOLS + WORKFLOW_TOOLS}[level]
    for tool in tools:
        mcp.add_tool(tool)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--http", type=int, metavar="PORT", help="serve Streamable HTTP on this port")
    parser.add_argument("--level", choices=("function", "feature", "workflow", "all"), default="function")
    args = parser.parse_args()
    add_tools(args.level)
    if args.http:
        mcp.settings.port = args.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
