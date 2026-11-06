"""Serve the generated tools in tools/ over MCP on stdio. One file per tool."""

import importlib.util
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("packaging-coder-60", log_level="WARNING")
for path in sorted((Path(__file__).resolve().parent / "tools").glob("*.py")):
    spec = importlib.util.spec_from_file_location(f"generated_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    mcp.add_tool(getattr(module, path.stem))
mcp.run()
