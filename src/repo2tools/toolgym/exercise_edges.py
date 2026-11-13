"""Compare ToolGym's 2-step chains for one server with the data flow our exercises need.

    python3 -I `repo2tools toolgym-edges` out/packaging_toolgym/chains_packaging.txt \\
        out/packaging/exercises.jsonl ../tool-gym/gym/tools/mcp_servers/catalog/kobiljon_pypa_packaging_tools/mcp_server.json

The chains file is the output of `chain_check --dry-run <server>`. Every {"$ref": [i, ...]}
argument in a reference solution is one data-flow link (tool of call i -> this tool, parameter);
the script reports how many of those links ToolGym's signature graph also has. It also splits
ToolGym's links into useful ones and noise: casts, and booleans fed into on/off flags.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

CHAIN = re.compile(r"\d+\. \S+?/(\S+) -> \S+?/(\S+) \[(\w+)\] param=(\w+)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chains", type=Path)
    parser.add_argument("exercises", type=Path)
    parser.add_argument("mcp_server", type=Path)
    args = parser.parse_args()

    spec = json.loads(args.mcp_server.read_text())
    param_types = {t["mcp_spec"]["name"]: t["gym_types"]["parameters"] for t in spec["tools"]}
    edges = {}
    for src, dst, kind, param in CHAIN.findall(args.chains.read_text()):
        edges[(src, dst, param)] = kind

    def label(src, dst, param):
        kind = edges[(src, dst, param)]
        if kind == "cast":
            return "noise: cast"
        if param_types[dst][param] == "boolean":
            return "noise: boolean into a flag"
        return f"useful: {kind}"

    counts = Counter(label(*e) for e in edges)
    tools = set(param_types)
    linked = {t for src, dst, _ in edges for t in (src, dst)}
    useful = [e for e in edges if label(*e).startswith("useful")]
    useful_linked = {t for src, dst, _ in useful for t in (src, dst)}
    print(f"ToolGym links between {len(tools)} tools: {len(edges)}")
    for key in sorted(counts):
        print(f"  {key:28} {counts[key]}")
    print(f"tools with no link at all: {sorted(tools - linked) or 'none'}")
    print(f"tools with no useful link: {sorted(tools - useful_linked) or 'none'}")

    needed, found, missing = Counter(), Counter(), Counter()
    for line in open(args.exercises):
        ex = json.loads(line)
        calls = ex["reference_calls"]
        for call in calls:
            for param, value in call["arguments"].items():
                if isinstance(value, dict) and set(value) == {"$ref"}:
                    link = (calls[value["$ref"][0]]["tool"], call["tool"], param)
                    needed[link] += 1
                    (found if link in edges else missing)[link] += 1
    print(f"\ndata-flow links used by the exercises' reference solutions: {len(needed)} distinct, "
          f"{sum(needed.values())} uses")
    for link, n in sorted(needed.items(), key=lambda kv: -kv[1]):
        status = f"in ToolGym [{edges[link]}]" if link in edges else "MISSING in ToolGym"
        print(f"  {link[0]} -> {link[1]} ({link[2]}): {n} uses, {status}")
    print(f"covered: {len(needed) - len(missing)}/{len(needed)} distinct links")


if __name__ == "__main__":
    main()
