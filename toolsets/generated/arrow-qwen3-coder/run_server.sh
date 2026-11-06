#!/bin/sh
# Start these generated tools as an MCP server on stdio, in their own environment and sandbox.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
ENV_DIR="$ROOT/.cache/envs/arrow-qwen3-coder"
if [ ! -x "$ENV_DIR/bin/python" ]; then
    echo "No environment yet. Run: uv run python repo2tools.py https://github.com/arrow-py/arrow --commit 2224255c4acc594d734cef0bbc83360452a67983 --tag qwen3-coder --env-only" >&2
    exit 1
fi
PROFILE="$ROOT/.cache/envs/arrow-qwen3-coder.sb"
PREFIX=""
if [ -f "$PROFILE" ] && command -v sandbox-exec >/dev/null 2>&1; then
    exec env -i PATH=/usr/bin:/bin HOME="$ENV_DIR.tmp" TMPDIR="$ENV_DIR.tmp" PYTHONDONTWRITEBYTECODE=1 LANG=C.UTF-8 \
        sandbox-exec -f "$PROFILE" "$ENV_DIR/bin/python" -I "$HERE/server.py"
fi
echo "WARNING: running generated code without a sandbox" >&2
exec env -i PATH=/usr/bin:/bin HOME="$ENV_DIR.tmp" TMPDIR="$ENV_DIR.tmp" PYTHONDONTWRITEBYTECODE=1 LANG=C.UTF-8 \
    "$ENV_DIR/bin/python" -I "$HERE/server.py"
