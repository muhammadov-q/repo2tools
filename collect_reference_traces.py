"""Replay the exercises' known-good solutions through an MCP server, and save them as traces.

    uv run python collect_reference_traces.py out/packaging/exercises.jsonl \\
        -o out/traces/reference-function.jsonl -- uv run python toolsets/pypa_packaging/server.py

No model is involved. The messages are the ones a model would see if it made exactly these calls,
one call per request, with run_model.py's system prompt. Our own generator wrote the long
solutions, so what repeats in them shows the method, not how agents behave.
"""

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from exercise_check import check, resolve
from run_model import SYSTEM, list_tools
from run_reference_calls import output_value
from traces import trace_from_calls, write_traces


async def collect(exercises: list[dict], command: list[str], tool_set: str) -> list[dict]:
    traces = []
    server = StdioServerParameters(command=command[0], args=command[1:])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await list_tools(session)
        for ex in exercises:
            outputs, calls = [], []
            for c in ex["reference_calls"]:
                arguments = resolve(c["arguments"], outputs)
                result = await session.call_tool(c["tool"], arguments)
                if result.isError:
                    raise SystemExit(f"{ex['id']}: {c['tool']} failed: {result.content[0].text}")
                value = output_value(result)
                outputs.append(value)
                calls.append({"tool": c["tool"], "arguments": arguments, "output": json.dumps(value)})
            answer = resolve(ex["reference_answer"], outputs)
            traces.append(trace_from_calls(
                "reference", ex["id"], ex["task"], SYSTEM["tools"], tools, calls, json.dumps(answer),
                kind=ex["kind"], horizon=ex["horizon"], tool_set=tool_set, meta={"thinking": False},
                outcome={"passed": check(ex, answer), "answer": answer, "finish": "answered",
                         "tool_calls": len(calls), "tool_errors": 0}))
    return traces


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exercises", type=Path)
    parser.add_argument("command", nargs="+", help="command that starts the MCP server on stdio (after --)")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--tool-set", default="function")
    parser.add_argument("--horizon", choices=("short", "long"))
    args = parser.parse_args()
    exercises = [ex for ex in map(json.loads, open(args.exercises)) if args.horizon in (None, ex["horizon"])]
    traces = asyncio.run(collect(exercises, args.command, args.tool_set))
    write_traces(args.output, traces)
    passed = sum(t["outcome"]["passed"] for t in traces)
    print(f"{passed}/{len(traces)} reference traces solve their task -> {args.output}")


if __name__ == "__main__":
    main()
