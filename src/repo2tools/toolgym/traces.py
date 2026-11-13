"""Turn the entries of a ToolGym pipeline run into our trace format (see `traces/format.py`).

    uv run repo2tools toolgym-traces ../tool-gym/results/gym/repo2tools/<run> -o out/traces/toolgym-<name>.jsonl.gz

Needs a run made with `repo2tools toolgym-local generate`, which saves each entry as JSON. One entry is one
synthetic task: ToolGym sampled a chain of tools, ran it, and had an LLM write the task and the final
answer. The trace shows what a model would see if it made exactly these calls, one per request, with
`repo2tools run-model`'s system prompt, so it can be compared with our other traces in `repo2tools analyze-traces`.

`passed` is ToolGym's own validation verdict (LLM judge and challenger), not a check against a known
answer.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from repo2tools.evaluation.run_model import SYSTEM
from repo2tools.traces.format import trace_from_calls, write_traces


def user_task(record: dict) -> str:
    """The first user message of an Apertus record."""
    for message in record["conversation"]["messages"]:
        if message.get("role") == "user":
            return message["content"]
    raise ValueError("the record has no user message")


def openai_tools(record: dict) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
            for t in record["tools"]]


def convert(entry: dict, tool_set: str) -> dict:
    calls = [{"tool": s["tool"], "arguments": s["arguments"], "output": s["output"] if isinstance(s["output"], str) else json.dumps(s["output"])}
             for s in entry["steps"]]
    horizon = "long" if len(calls) >= 8 else "short"  # long = 8+ calls, as in the exercises
    return trace_from_calls("toolgym", entry["uuid"], user_task(entry["record"]), SYSTEM["tools"], openai_tools(entry["record"]), calls,
                            entry["answer"], kind="toolgym_chain", horizon=horizon, tool_set=tool_set, meta={"thinking": False, "distractors": entry.get("distractors")},
                            outcome={"passed": bool(entry["passed"]), "answer": entry["answer"], "finish": "answered", "tool_calls": len(calls), "tool_errors": 0})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path, help="run folders under results/gym/repo2tools/ in the ToolGym checkout")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--tool-set", default="toolgym")
    parser.add_argument("--only-passed", action="store_true", help="leave out entries that ToolGym's validation rejected")
    args = parser.parse_args()
    traces = []
    for run in args.runs:
        for path in sorted((run / "entries").glob("entry_*.json")):
            trace = convert(json.loads(path.read_text()), args.tool_set)
            if trace["outcome"]["passed"] or not args.only_passed:
                traces.append(trace)
    write_traces(args.output, traces)
    lengths = Counter(t["outcome"]["tool_calls"] for t in traces)
    print(f"{len(traces)} traces, {sum(t['outcome']['passed'] for t in traces)} passed ToolGym's validation; "
          f"calls per trace: {dict(sorted(lengths.items()))} -> {args.output}")


if __name__ == "__main__":
    main()
