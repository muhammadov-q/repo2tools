"""Turn the entries of a ToolGym pipeline run into exercises that run_model.py can score.

    uv run python toolgym_exercises.py ../tool-gym/results/gym/repo2tools/<run> -o out/toolgym_exercises/<name>.jsonl

ToolGym validates its synthetic tasks with an LLM judge and an LLM challenger. This gives a check
that needs no LLM: the task asks for the result of a chain of tool calls, and the chain was really
run, so the correct answer is the last call's output. A model that is given the task, with or
without the tools, either returns that value or not.

It is a strict check. A task whose text does not pin down the inputs cannot be solved by anyone, and
that is part of what it measures. `toolgym_passed` keeps ToolGym's own verdict for comparison.
"""

import argparse
import json
from pathlib import Path

from toolgym_traces import user_task


def exercise(entry: dict, run: str) -> dict | None:
    steps = entry["steps"]
    if not steps or isinstance(steps[-1]["output"], str) and steps[-1]["output"].startswith("Error executing tool"):
        return None  # a chain that ends in an error has no answer to ask for
    calls = [{"tool": s["tool"], "arguments": s["arguments"]} for s in steps]
    return {"id": f"toolgym-{entry['uuid'][:8]}", "kind": "toolgym_chain", "horizon": "long" if len(calls) >= 8 else "short",
            "task": user_task(entry["record"]) + "\nAnswer with the final result as a JSON value.",
            "answer": steps[-1]["output"], "check": {"kind": "exact"}, "reference_calls": calls,
            "reference_answer": {"$ref": [len(calls) - 1]}, "reference_call_count": len(calls),
            "toolgym_passed": bool(entry["passed"]), "provenance": {"toolgym_run": run, "uuid": entry["uuid"],
                                                                     "answer_from": "output of the chain's last call, as executed by ToolGym"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--only-passed", action="store_true", help="only entries that ToolGym's validation accepted")
    args = parser.parse_args()
    exercises, skipped = [], 0
    for run in args.runs:
        for path in sorted((run / "entries").glob("entry_*.json")):
            ex = exercise(json.loads(path.read_text()), run.name)
            if ex is None:
                skipped += 1
            elif ex["toolgym_passed"] or not args.only_passed:
                exercises.append(ex)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(ex) + "\n" for ex in exercises), encoding="utf-8")
    print(f"{len(exercises)} exercises ({sum(e['toolgym_passed'] for e in exercises)} accepted by ToolGym), "
          f"{skipped} chains skipped because they end in an error -> {args.output}")


if __name__ == "__main__":
    main()
