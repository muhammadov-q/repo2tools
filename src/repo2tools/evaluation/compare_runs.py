"""Put a model's run with tools and its run without tools side by side.

    python3 -I `repo2tools compare-runs` out/runs/qwen3-8b-tools.jsonl out/runs/qwen3-8b-none.jsonl

Prints a Markdown table per exercise kind and writes it next to the first file as
<model>-comparison.md. "Used a tool" is the share of exercises with at least one tool call;
"used all needed tools" is the share where the model called every tool of the reference
solution (a tool-retrieval signal).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> dict[str, dict]:
    return {r["id"]: r for r in map(json.loads, open(path))}


def pct(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "-"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("with_tools", type=Path)
    parser.add_argument("without_tools", type=Path)
    args = parser.parse_args()

    tools, none = load(args.with_tools), load(args.without_tools)
    groups = defaultdict(list)
    for rid, r in tools.items():
        groups[(r["horizon"], r["kind"])].append((r, none.get(rid, {})))

    rows = ["| horizon | kind | n | with tools | without tools | used a tool | used all needed tools | tool calls (avg) | tool errors |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]

    def row(label_h, label_k, pairs):
        n = len(pairs)
        t = sum(r["passed"] for r, _ in pairs)
        o = sum(bool(x.get("passed")) for _, x in pairs)
        used = sum(r.get("tool_calls", 0) > 0 for r, _ in pairs)
        allref = sum(bool(r.get("used_all_reference_tools")) for r, _ in pairs)
        calls = sum(r.get("tool_calls", 0) for r, _ in pairs) / n
        errors = sum(r.get("tool_errors", 0) for r, _ in pairs)
        rows.append(f"| {label_h} | {label_k} | {n} | {pct(t, n)} | {pct(o, n)} | {pct(used, n)} | {pct(allref, n)} | "
                    f"{calls:.1f} | {errors} |")

    for (horizon, kind), pairs in sorted(groups.items()):
        row(horizon, kind, pairs)
    for horizon in ("short", "long"):
        pairs = [p for (h, _), ps in groups.items() if h == horizon for p in ps]
        row(f"**{horizon}**", "**all**", pairs)
    row("**all**", "**all**", [p for ps in groups.values() for p in ps])

    model = next(iter(tools.values()))["model"]
    table = "\n".join(rows)
    out = args.with_tools.with_name(f"{model}-comparison.md")
    out.write_text(f"# {model}: with tools vs without tools\n\n{table}\n")
    print(table)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
