"""Turn the entries of a ToolGym pipeline run into exercises that `repo2tools run-model` can score.

    uv run repo2tools toolgym-exercises ../tool-gym/results/gym/repo2tools/<run> -o out/toolgym_exercises/<name>.jsonl

ToolGym validates its synthetic tasks with an LLM judge and an LLM challenger. This gives a check
that needs no LLM: the task asks for the result of a chain of tool calls, and the chain was really
run, so the correct answer is the last call's output. A model that is given the task, with or
without the tools, either returns that value or not.

It is a strict check. A task whose text does not pin down the inputs cannot be solved by anyone, and
that is part of what it measures. `toolgym_passed` keeps ToolGym's own verdict for comparison.
"""

import argparse
import json
import random
from pathlib import Path

from repo2tools.toolgym.traces import user_task


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


def compose(parts: list[dict], number: int) -> dict:
    """One long exercise from several short ones: solve them all, answer with the list of results.

    A tool set's type graph allows only short chains of different tools (4 calls for the generated
    packaging tools). Long tasks in practice repeat short patterns over several items, so this builds
    them the same way. The parts are independent: a model may solve them in any order.
    """
    calls, offsets = [], []
    for part in parts:
        offsets.append(len(calls))
        calls += part["reference_calls"]
    task = (f"Solve these {len(parts)} tasks. Answer with one JSON list that holds the {len(parts)} results in the same order.\n\n"
            + "\n\n".join(f"Task {i + 1}: {part['task'].rsplit(chr(10), 1)[0]}" for i, part in enumerate(parts)))
    return {"id": f"toolgym-composed-{number:03d}", "kind": "toolgym_composed", "horizon": "long" if len(calls) >= 8 else "short",
            "task": task, "answer": [part["answer"] for part in parts], "check": {"kind": "exact"}, "reference_calls": calls,
            "reference_answer": [{"$ref": [offset + part["reference_call_count"] - 1]} for offset, part in zip(offsets, parts)],
            "reference_call_count": len(calls), "toolgym_passed": all(part["toolgym_passed"] for part in parts),
            "provenance": {"composed_from": [part["id"] for part in parts], "answer_from": "outputs of each chain's last call, as executed by ToolGym"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--only-passed", action="store_true", help="only entries that ToolGym's validation accepted")
    parser.add_argument("--compose", type=int, default=0, help="combine this many chains into one long exercise")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    exercises, skipped = [], 0
    for run in args.runs:
        for path in sorted((run / "entries").glob("entry_*.json")):
            ex = exercise(json.loads(path.read_text()), run.name)
            if ex is None:
                skipped += 1
            elif ex["toolgym_passed"] or not args.only_passed:
                exercises.append(ex)
    if args.compose:
        rng = random.Random(args.seed)
        rng.shuffle(exercises)
        groups = [exercises[i:i + args.compose] for i in range(0, len(exercises) - args.compose + 1, args.compose)]
        exercises = [compose(group, number) for number, group in enumerate(groups, 1)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(ex) + "\n" for ex in exercises), encoding="utf-8")
    print(f"{len(exercises)} exercises ({sum(e['toolgym_passed'] for e in exercises)} accepted by ToolGym), "
          f"{skipped} chains skipped because they end in an error -> {args.output}")


if __name__ == "__main__":
    main()
