#!/bin/sh
# Start the hand-made packaging tools as an MCP server. No arguments: stdio. `--http PORT`: Streamable HTTP.
HERE=$(cd "$(dirname "$0")" && pwd)
exec uv run --quiet --project "$HERE/../.." python "$HERE/server.py" "$@"
