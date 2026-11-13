"""Play every exercise's reference solution through an MCP tool server and check the answers.

This tests the tools, not a model: every reference call must succeed over MCP, and the answer
built from the outputs must match the exercise's answer, which comes from the library's own
tests or from direct library calls.

Usage:
    uv run repo2tools check-tools out/packaging/exercises.jsonl \\
        -- uv run python toolsets/pypa_packaging/server.py
Writes <exercises>.reference_run.json next to the exercises file.
"""

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repo2tools.evaluation.exercise_check import check, resolve


def output_value(result):
    """The JSON value a tool returned. FastMCP wraps non-object results as {"result": ...}."""
    if result.structuredContent is not None:
        content = result.structuredContent
        return content["result"] if set(content) == {"result"} else content
    return json.loads("".join(c.text for c in result.content if c.type == "text"))


async def run(exercises: list[dict], command: list[str]) -> dict:
    per_tool, per_kind, failures = defaultdict(Counter), defaultdict(Counter), []
    server = StdioServerParameters(command=command[0], args=command[1:])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for ex in exercises:
            outputs, error, answer = [], None, None
            for c in ex["reference_calls"]:
                result = await session.call_tool(c["tool"], resolve(c["arguments"], outputs))
                per_tool[c["tool"]]["calls"] += 1
                if result.isError:
                    per_tool[c["tool"]]["errors"] += 1
                    error = f"{c['tool']}: {result.content[0].text}"
                    break
                outputs.append(output_value(result))
            if error is None:
                try:
                    answer = resolve(ex["reference_answer"], outputs)
                except (KeyError, IndexError, TypeError) as e:
                    error = f"reference_answer: {e!r}"
            passed = error is None and check(ex, answer)
            per_kind[ex["kind"]]["passed" if passed else "failed"] += 1
            if not passed:
                failures.append({"id": ex["id"], "error": error, "got": answer, "expected": ex["answer"]})
    return {"per_kind": per_kind, "per_tool": per_tool, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exercises", type=Path)
    parser.add_argument("command", nargs="+", help="command that starts the MCP server on stdio (after --)")
    args = parser.parse_args()

    exercises = [json.loads(line) for line in open(args.exercises)]
    report = asyncio.run(run(exercises, args.command))
    args.exercises.with_suffix(".reference_run.json").write_text(json.dumps(report, indent=1))

    print(f"{'kind':24} passed failed")
    for kind, counts in sorted(report["per_kind"].items()):
        print(f"{kind:24} {counts['passed']:6} {counts['failed']:6}")
    print(f"\n{'tool':22} calls errors")
    for tool, counts in sorted(report["per_tool"].items()):
        print(f"{tool:22} {counts['calls']:5} {counts['errors']:6}")
    total = sum(c["passed"] for c in report["per_kind"].values())
    print(f"\n{total}/{len(exercises)} exercises solved by their reference calls; "
          f"{len(report['per_tool'])} of the server's tools were exercised")
    for failure in report["failures"][:10]:
        print("FAILED", json.dumps(failure)[:300])


if __name__ == "__main__":
    main()
