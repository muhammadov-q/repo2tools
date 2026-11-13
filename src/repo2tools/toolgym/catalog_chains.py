"""Summarise ToolGym's catalog check and chain_check dry-run output (stdlib only).

    uv run repo2tools toolgym-chains out/baseline/check.txt out/baseline/chains.txt
"""

import re
import sys
from collections import Counter, defaultdict


def main() -> None:
    check_txt, chains_txt = open(sys.argv[1]).read(), open(sys.argv[2]).read()

    # tools per server from the check report
    tools, server = {}, None
    for line in check_txt.splitlines():
        m = re.match(r"\s+\[OK\] (\S+): \d+ tools", line)
        if m:
            server = m.group(1)
            continue
        m = re.match(r"\s{4}(\w+)\((.*)\) -> (\S+)", line)
        if m and server:
            tools[f"{server}/{m.group(1)}"] = (m.group(2), m.group(3))

    edges, kinds, kinds_cross = set(), Counter(), Counter()
    for m in re.finditer(r"\d+\. (\S+) -> (\S+) \[(\w+)\]", chains_txt):
        a, b, k = m.groups()
        edges.add((a, b))
        kinds[k] += 1
        if a.split("/")[0] != b.split("/")[0]:
            kinds_cross[k] += 1

    def srv(t):
        return t.split("/")[0]

    out_n, in_n = defaultdict(set), defaultdict(set)
    for a, b in edges:
        out_n[a].add(b)
        in_n[b].add(a)
    same = sum(1 for a, b in edges if srv(a) == srv(b))
    print(f"servers={len({srv(t) for t in tools})} tools={len(tools)}")
    print(f"chain lines={sum(kinds.values())} kinds={dict(kinds)} cross-server lines by kind={dict(kinds_cross)}")
    print(f"unique tool->tool edges={len(edges)} same-server={same} cross-server={len(edges)-same}")

    isolated = [t for t in tools if not out_n[t] and not in_n[t]]
    sources_only = [t for t in tools if out_n[t] and not in_n[t]]
    sinks_only = [t for t in tools if in_n[t] and not out_n[t]]
    print(f"\nno chain in or out ({len(isolated)}):", ", ".join(sorted(isolated)))
    print(f"only start a chain ({len(sources_only)}):", ", ".join(sorted(sources_only)))
    print(f"only end a chain ({len(sinks_only)}):", ", ".join(sorted(sinks_only)))

    # servers that connect to another server at all
    links = Counter((srv(a), srv(b)) for a, b in edges if srv(a) != srv(b))
    print("\ncross-server links (server -> server: tool pairs):")
    for (x, y), n in sorted(links.items(), key=lambda kv: (-kv[1], kv[0])):  # ties in a fixed order
        print(f"  {x} -> {y}: {n}")

    # strongly connected components (Tarjan) and longest path in the condensation
    idx, low, stack, on, comps, counter = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(10000)
    def strong(v):
        idx[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in out_n[v]:
            if w not in idx:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            comps.append(comp)
    for t in tools:
        if t not in idx:
            strong(t)
    cid = {t: i for i, c in enumerate(comps) for t in c}
    cedges = defaultdict(set)
    for a, b in edges:
        if cid[a] != cid[b]:
            cedges[cid[a]].add(cid[b])
    memo = {}
    def longest(c):  # number of distinct tools on the best path, counting a cyclic group by its size
        if c not in memo:
            memo[c] = len(comps[c]) + max((longest(d) for d in cedges[c]), default=0)
        return memo[c]
    big = sorted(comps, key=len, reverse=True)
    print(f"\ngroups of tools that can reach each other (cycles): {[len(c) for c in big if len(c) > 1]}")
    for c in big[:2]:
        if len(c) > 1:
            print(f"  size {len(c)}: servers {sorted({srv(t) for t in c})}")
    best = max(range(len(comps)), key=longest)
    print(f"upper bound on distinct tools in one chain: {longest(best)} (starting from group of size {len(comps[best])})")
    # longest chain that never repeats a server
    def longest_servers(t, seen):
        best = 1
        for w in out_n[t]:
            if srv(w) not in seen:
                best = max(best, 1 + longest_servers(w, seen | {srv(w)}))
        return best
    print(f"longest chain where every step uses a different server: {max(longest_servers(t, frozenset({srv(t)})) for t in tools)} tools")


if __name__ == "__main__":
    main()
