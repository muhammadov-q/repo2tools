"""Run a model on the exercises, with the MCP tools or without tools, and score its answers.

    uv run python run_model.py out/packaging/exercises.jsonl --mode tools \\
        --base-url http://127.0.0.1:8000/v1 --model qwen3-8b \\
        -- uv run python toolsets/pypa_packaging/server.py
    uv run python run_model.py out/packaging/exercises.jsonl --mode none --base-url ... --model ...

The endpoint is any OpenAI-compatible server with tool calling (e.g. vLLM). The API key is read
from $OPENAI_API_KEY. Writes one JSON line per exercise to out/runs/<model>-<mode>.jsonl and
prints success rates per kind and horizon.

Per exercise it records: passed, the parsed answer, tool calls and tool errors, which tools were
used, and whether they include every tool of the reference solution (a tool-retrieval signal).
"""

import argparse
import asyncio
import json
import re
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from exercise_check import check
from run_reference_calls import output_value

HERE = Path(__file__).parent
SYSTEM = {
    "tools": "You solve tasks about Python package versions and dependencies. Use the tools whenever they help; "
             "do not guess what a tool would return. When you are done, reply with only the final answer as a "
             "JSON value (true or false, a number, a string, a list or an object) and nothing else.",
    "none": "You solve tasks about Python package versions and dependencies. Reply with only the final answer as "
            "a JSON value (true or false, a number, a string, a list or an object) and nothing else.",
}


def parse_answer(text: str):
    """The model's final answer as a JSON value, or None if it is not one."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        # models sometimes wrap a plain answer, e.g. {"result": -1}; no exercise expects such an object
        if isinstance(value, dict) and len(value) == 1 and next(iter(value)) in ("result", "answer", "value"):
            return next(iter(value.values()))
        return value
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    # last resort: a bare string answer, e.g. 1.0rc1 without quotes
    return text if text and "\n" not in text and len(text) < 200 else None


async def solve(ex: dict, args, client: AsyncOpenAI, session: ClientSession | None, tools: list) -> dict:
    messages = [{"role": "system", "content": SYSTEM[args.mode]}, {"role": "user", "content": ex["task"]}]
    used, calls, errors, tokens, finish, raw, trace = [], 0, 0, 0, "max_steps", None, []
    for _ in range(args.max_steps):
        response = await client.chat.completions.create(
            model=args.model, messages=messages, tools=tools or None, temperature=0,
            max_tokens=4096 if args.thinking else 1024,
            extra_body={"chat_template_kwargs": {"enable_thinking": args.thinking}})
        tokens += response.usage.total_tokens if response.usage else 0
        msg = response.choices[0].message
        if not msg.tool_calls:
            # without a reasoning parser on the server, a thinking model's reasoning stays in the content
            final = re.sub(r"<think>.*?</think>", "", msg.content or "", flags=re.S).strip()
            raw = final[:500]
            answer = parse_answer(final)
            finish = "answered"
            break
        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            calls += 1
            used.append(tc.function.name)
            try:
                result = await session.call_tool(tc.function.name, json.loads(tc.function.arguments or "{}"))
                content = result.content[0].text if result.isError else json.dumps(output_value(result))
                errors += result.isError
            except Exception as e:  # noqa: BLE001  (bad JSON arguments or an unknown tool count as a tool error)
                content, errors = f"Error: {e}", errors + 1
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})
            trace.append({"tool": tc.function.name, "arguments": tc.function.arguments, "output": content[:500]})
    else:
        answer = None
    reference_tools = {c["tool"] for c in ex["reference_calls"]}
    return {"id": ex["id"], "kind": ex["kind"], "horizon": ex["horizon"], "mode": args.mode, "model": args.model,
            "passed": finish == "answered" and check(ex, answer), "answer": answer, "raw": raw, "finish": finish,
            "tool_calls": calls, "tool_errors": errors, "tools_used": sorted(set(used)),
            "used_all_reference_tools": reference_tools <= set(used), "reference_call_count": ex["reference_call_count"],
            "tokens": tokens, "trace": trace}


async def run(exercises: list[dict], args) -> list[dict]:
    client = AsyncOpenAI(base_url=args.base_url)
    async with AsyncExitStack() as stack:
        session, tools = None, []
        if args.mode == "tools":
            read, write = await stack.enter_async_context(
                stdio_client(StdioServerParameters(command=args.command[0], args=args.command[1:])))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}}
                     for t in (await session.list_tools()).tools]
        limit = asyncio.Semaphore(args.concurrency)

        async def one(ex):
            async with limit:
                try:
                    return await solve(ex, args, client, session, tools)
                except Exception as e:  # noqa: BLE001  (record endpoint failures instead of stopping the run)
                    return {"id": ex["id"], "kind": ex["kind"], "horizon": ex["horizon"], "mode": args.mode,
                            "model": args.model, "passed": False, "finish": f"error: {e!r}"[:300]}

        return await asyncio.gather(*(one(ex) for ex in exercises))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exercises", type=Path)
    parser.add_argument("command", nargs="*", help="command that starts the MCP server on stdio (after --), for --mode tools")
    parser.add_argument("--mode", choices=("tools", "none"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--limit", type=int, help="only the first N exercises (for a smoke test)")
    parser.add_argument("--horizon", choices=("short", "long"), help="only exercises of this horizon")
    parser.add_argument("--thinking", action="store_true", help="let Qwen3-style models think before answering")
    parser.add_argument("--tag", help="label for the output file name, e.g. the tool set's granularity")
    args = parser.parse_args()
    if args.mode == "tools" and not args.command:
        parser.error("--mode tools needs the MCP server command after --")

    exercises = [ex for ex in map(json.loads, open(args.exercises)) if args.horizon in (None, ex["horizon"])][: args.limit]
    results = asyncio.run(run(exercises, args))
    suffix = "".join(f"-{part}" for part in (args.tag, args.horizon, "thinking" if args.thinking else None) if part)
    out = HERE / "out" / "runs" / f"{args.model}-{args.mode}{suffix}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in results))

    groups = defaultdict(list)
    for r in results:
        groups[(r["horizon"], r["kind"])].append(r)
    print(f"{args.model}, mode={args.mode}")
    print(f"{'horizon':8} {'kind':24} {'passed':>8}")
    for (horizon, kind), rs in sorted(groups.items()):
        print(f"{horizon:8} {kind:24} {sum(r['passed'] for r in rs):3}/{len(rs):<4}")
    passed = sum(r["passed"] for r in results)
    print(f"total {passed}/{len(results)} ({passed / len(results):.0%}) -> {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
