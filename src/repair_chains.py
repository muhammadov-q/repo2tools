"""Repair generated tools whose output no other tool can take.

    uv run python src/repair_chains.py toolsets/generated/packaging-coder-60 --base-url http://127.0.0.1:18000/v1 --model qwen3-32b

A tool can pass every check of repo2tools.py and still be a dead end in a chain. Example: a tool
takes a version constraint such as ">=1.0" and returns "<VersionRange '[1.0, 2.0.dev0)'>", the
library object's printed form, which no tool accepts. generated_to_toolgym.py finds these: the LLM
gives the output a type, and feeding the output into the tools that take this type fails.

For each such tool this script asks the LLM for a new test (a direct library call whose result has
the form other tools take), then, in a separate request that cannot see the test, for new code. A
repaired tool is kept only if all of these hold:
  1. it passes all checks of repo2tools.py again (same result as the direct library call),
  2. inputs that gave different results before still give different results, and
  3. the tools that take its type accept its outputs when they are run.

The result is a new tool set, <set>-chained, with the repaired tools swapped in and the others
unchanged. Run generated_to_toolgym.py on it to see the links it now has.

Needs the reports of repo2tools.py and generated_to_toolgym.py for the tool set, in out/generated/<set>/.
"""

import argparse
import asyncio
import json
import random
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import repo2tools
from generated_to_toolgym import KEEP_RATE, Server, unique
from repo2tools import (LLM, ToolResult, clone, code_messages, end_to_end, extract_code, find_package, make_box, parse_spec,
                        repo_name, run_worker, signature, spec_messages, static_problem, write_launchers)


@dataclass
class DeadEnd:
    """A tool whose typed output was rejected by the tools that take that type."""

    tool: str
    type_name: str
    examples: list  # values of this type that tools accept as input
    consumers: list[tuple[str, str]]  # (tool, parameter) that take this type
    old_outputs: list
    repaired: bool = False
    new_outputs: list = field(default_factory=list)
    tried: int = 0
    worked: int = 0
    attempts: list[dict] = field(default_factory=list)  # one {"stage", "error"} per try
    spec: dict | None = None
    code: str | None = None
    check: dict | None = None


def find_dead_ends(types_report: dict, catalog: dict, tool_reports: dict) -> list[DeadEnd]:
    """Output claims that were tested by running and failed. Only single values for now, not lists or fields."""
    consumers: dict[str, list] = {}
    for entry in catalog["mcp_server"]["tools"]:
        for param, type_name in entry["gym_types"]["parameters"].items():
            consumers.setdefault(type_name, []).append((entry["mcp_spec"]["name"], param))
    found = []
    for check in types_report["output_checks"]:
        claim = check["output"]
        if check["kept"] or not check["tried"] or claim.startswith(("field ", "list[")):
            continue
        type_name = check.get("type", claim)
        examples = catalog["types"]["pools"].get(type_name, [])
        takers = [c for c in consumers.get(type_name, []) if c[0] != check["tool"]] or consumers.get(type_name, [])
        report = tool_reports.get(check["tool"])
        if not report or not examples or not takers:
            continue
        outputs = unique([row["tool"] for row in report["check"]["samples"] if row["result"].startswith("same")])
        found.append(DeadEnd(check["tool"], type_name, examples[:6], takers, outputs[:4]))
    return found


def returned_class_api(callable_: dict, api: dict) -> str:
    """Public methods and properties of the class the wrapped function returns, as text for the prompt."""
    names = {c["qualname"].split(".")[0] for c in api["callables"] if "." in c["qualname"]}
    mentioned = [n for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", callable_.get("returns") or "") if n in names]
    owner = callable_["qualname"].split(".")[0] if "." in callable_["qualname"] else None
    classes = unique(mentioned + ([owner] if owner in names else []))
    lines = [f"- {c['kind']} {signature(c)} | {c['summary'][:90]}" for name in classes for c in api["callables"]
             if c["qualname"].startswith(name + ".")]
    return "\n".join(lines[:40])


def repair_request(dead: DeadEnd, callable_: dict, api: dict) -> str:
    takers = ", ".join(f"`{tool}` (parameter `{param}`)" for tool, param in dead.consumers[:4])
    methods = returned_class_api(callable_, api)
    return f"""This tool passes its test, but it is a dead end: its output cannot be used as the input of any other tool.

Its output is a {dead.type_name}, for example: {', '.join(json.dumps(v) for v in dead.old_outputs[:3])}
Tools that take a {dead.type_name}: {takers}
They accept values like: {', '.join(json.dumps(v) for v in dead.examples[:5])}
They reject this tool's output.

Change "direct_call" so that its result has the form those tools accept. Still call the same library function, then convert its result with the library, not by cutting up text.{' The library offers:' + chr(10) + methods if methods else ''}

Keep the same parameters and samples. Reply with the corrected JSON only."""


def merged_results(old_rows: list[dict], new_rows: list[dict]) -> str | None:
    """Two inputs that used to give different results and now give the same one, as text, or None.

    A repair may change the form of an output, not lose information. Seen with a real model: a union
    of version ranges that the library cannot write as one constraint was returned as "", which means
    "all versions". The test and the tool agreed on that, and every consumer accepted "".
    """
    old = {json.dumps(r["arguments"], sort_keys=True): r["tool"] for r in old_rows if r["result"].startswith("same")}
    seen: dict[str, tuple[str, object]] = {}
    for row in new_rows:
        key = json.dumps(row["arguments"], sort_keys=True)
        if not row["result"].startswith("same") or key not in old:
            continue
        new_value = json.dumps(row["tool"], sort_keys=True)
        if new_value in seen and json.dumps(seen[new_value][1], sort_keys=True) != json.dumps(old[key], sort_keys=True):
            return (f"inputs {seen[new_value][0]} and {key} gave different results before ({json.dumps(seen[new_value][1])} and "
                    f"{json.dumps(old[key])}) and now both give {new_value}")
        seen.setdefault(new_value, (key, old[key]))
    return None


async def consumers_accept(server: Server, dead: DeadEnd, base_arguments: dict, values: list, rng: random.Random) -> tuple[int, int, str | None]:
    """(tried, worked, first rejected call) when the new outputs are fed into the tools that take the type."""
    tried, worked, rejected = 0, 0, None
    for tool, param in rng.sample(dead.consumers, min(3, len(dead.consumers))):
        for value in values[:4]:
            ok, _ = await server.call(tool, {**base_arguments[tool], param: value})
            tried, worked = tried + 1, worked + ok
            if not ok and rejected is None:
                rejected = f"`{tool}` rejected {json.dumps(value)} for its parameter `{param}`"
    return tried, worked, rejected


async def repair(dead: DeadEnd, report: dict, callable_: dict, api: dict, llm, box, base: Path, server: Server,
                 base_arguments: dict, rounds: int, rng: random.Random) -> DeadEnd:
    name = dead.tool
    pick = {"callable": callable_, "name": name, "description": report["description"]}
    old_parameters = sorted(p["name"] for p in report["spec"]["parameters"])
    spec_chat = spec_messages(pick, base, api["classes"]) + [
        {"role": "assistant", "content": json.dumps(report["spec"])},
        {"role": "user", "content": repair_request(dead, callable_, api)}]
    # the code writer learns what form the output must have, but never sees the test
    hint = (f" Return the result as a {dead.type_name}, in the form other tools take as input, for example "
            f"{', '.join(json.dumps(v) for v in dead.examples[:3])}. Do not return the printed form of a library object.")
    methods = returned_class_api(callable_, api)
    if methods:  # library documentation, not the test: without it the code writer invents conversion methods
        hint += " Convert with the library, using only functions that exist. The class offers:\n" + methods
    code_pick = {**pick, "description": report["description"].rstrip(".") + "." + hint}

    def note(stage: str, error: str, chat: list, reply: str, request: str) -> None:
        dead.attempts.append({"stage": stage, "error": error})
        chat += [{"role": "assistant", "content": reply}, {"role": "user", "content": request}]

    for _ in range(rounds + 1):
        reply = await llm.chat("repair_spec", name, spec_chat)
        spec, problem = parse_spec(reply, pick)
        if not problem and sorted(p["name"] for p in spec["parameters"]) != old_parameters:
            problem = f"keep exactly these parameters: {old_parameters}"
        if problem:
            note("spec", problem, spec_chat, reply, f"This is not acceptable: {problem}\nReply with the corrected JSON only.")
            continue
        code_chat = code_messages(code_pick, spec, base, api["classes"])
        check = None
        for _ in range(3):
            code_reply = await llm.chat("repair_code", name, code_chat)
            code = extract_code(code_reply)
            static = static_problem(code, name, [p["name"] for p in spec["parameters"]])
            check = None if static else await asyncio.to_thread(run_worker, box, name, code, spec)
            stage, error = static or (check["stage"], check.get("error"))
            if stage == "ok" or stage == "spec":
                break
            note(stage, error, code_chat, f"```python\n{code}```", f"This code failed the check `{stage}`:\n{error}\n\nFix it. Reply with one Python code block and nothing else.")
        if not check or not check["ok"]:
            if check and check["stage"] == "spec":
                note("spec", check["error"], spec_chat, json.dumps(spec), f"Running this plan failed: {check['error']}\nReply with the corrected JSON only.")
            else:
                spec_chat += [{"role": "assistant", "content": json.dumps(spec)},
                              {"role": "user", "content": "No tool could be written for this plan. Try another direct_call. Reply with the corrected JSON only."}]
            continue
        merged = merged_results(report["check"]["samples"], check["samples"])
        if merged:
            note("merged", merged, spec_chat, json.dumps(spec),
                 f"This loses information: {merged}. A repair may change the form of the output, but different results must stay different. "
                 "If the library cannot express a result in the new form, do not replace it with a made-up value.\nReply with the corrected JSON only.")
            continue
        outputs = unique([row["tool"] for row in check["samples"] if row["result"].startswith("same")])
        dead.tried, dead.worked, rejected = await consumers_accept(server, dead, base_arguments, outputs, rng)
        dead.new_outputs = outputs[:4]
        if dead.tried and dead.worked / dead.tried >= KEEP_RATE:
            dead.attempts.append({"stage": "ok", "error": None})
            dead.repaired, dead.spec, dead.code, dead.check = True, spec, code, check
            return dead
        note("chain", f"{dead.worked} of {dead.tried} consumer calls worked; {rejected}", spec_chat, json.dumps(spec),
             f"The new output is still rejected: {rejected}. Only {dead.worked} of {dead.tried} calls worked.\n"
             f"Accepted values look like: {', '.join(json.dumps(v) for v in dead.examples[:5])}\nReply with the corrected JSON only.")
    return dead


def write_report(path: Path, source_set: str, new_set: str, model: str, dead_ends: list[DeadEnd]) -> dict:
    repaired = [d for d in dead_ends if d.repaired]
    summary = {"source_set": source_set, "set": new_set, "model": model, "dead_ends": len(dead_ends), "repaired": len(repaired),
               "tools": [{k: v for k, v in asdict(d).items() if k not in ("check",)} for d in dead_ends]}
    path.with_suffix(".json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    lines = [f"# Chain repair: {source_set} -> {new_set}", "",
             f"Model `{model}`. A dead end is a tool whose output the tools of its type reject. A repair is kept only if the tool "
             f"passes all checks of repo2tools.py again and at least {KEEP_RATE:.0%} of the consumer calls work.", "",
             f"**{len(repaired)} of {len(dead_ends)} dead ends repaired.**", "",
             "| Tool | Type | Output before | Output after | Consumer calls that work | Tries | Result |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in dead_ends:
        before = json.dumps(d.old_outputs[0])[:60] if d.old_outputs else ""
        after = json.dumps(d.new_outputs[0])[:60] if d.new_outputs else ""
        last = d.attempts[-1] if d.attempts else {"stage": "none", "error": ""}
        error = re.sub(r"[|\s]+", " ", str(last["error"]))[:120]
        result = "repaired" if d.repaired else f"not repaired: {last['stage']}: {error}"
        lines.append(f"| `{d.tool}` | `{d.type_name}` | `{before}` | `{after}` | {d.worked} of {d.tried} | {len(d.attempts)} | {result} |")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


async def repair_set(toolset: Path, llm, rounds: int = 3, seed: int = 0, suffix: str = "chained") -> dict:
    root = repo2tools.ROOT
    manifest = json.loads((toolset / "manifest.json").read_text())
    source_set = manifest["set"]
    out = root / "out" / "generated" / source_set
    for needed in ("report.json", "api.json", "toolgym_types.json", "toolgym_catalog.json"):
        if not (out / needed).is_file():
            raise SystemExit(f"missing {out / needed}: run repo2tools.py and generated_to_toolgym.py on this tool set first")
    report = json.loads((out / "report.json").read_text())
    api = json.loads((out / "api.json").read_text())
    tool_reports = {t["name"]: t for t in report["tools"] if t["accepted"]}
    dead_ends = find_dead_ends(json.loads((out / "toolgym_types.json").read_text()), json.loads((out / "toolgym_catalog.json").read_text()), tool_reports)
    callables = {f"{c['module']}.{c['qualname']}": c for c in api["callables"]}

    new_set = f"{source_set}-{suffix}"
    dest = root / "toolsets" / "generated" / new_set
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(toolset, dest, ignore=shutil.ignore_patterns("__pycache__"))
    url, commit = manifest["url"], manifest["commit"]
    repo_root = repo2tools.CACHE / "repos" / repo_name(url)
    clone(url, commit, repo_root)
    base, package = find_package(repo_root, manifest["package"])
    box = make_box(new_set, base, package, manifest.get("dependencies", []), dest)
    write_launchers(dest, new_set, new_set[len(repo_name(url)) + 1:], url, commit)

    # a working call of every tool, to change one argument at a time when testing consumers
    base_arguments = {name: next(row["arguments"] for row in t["check"]["samples"] if row["result"].startswith("same"))
                      for name, t in tool_reports.items() if any(row["result"].startswith("same") for row in t["check"]["samples"])}
    for dead in dead_ends:
        dead.consumers = [c for c in dead.consumers if c[0] in base_arguments]
    dead_ends = [d for d in dead_ends if d.consumers]
    rng = random.Random(seed)
    if dead_ends:
        async with stdio_client(StdioServerParameters(command=str(toolset / "run_server.sh"), args=[])) as (read, write), \
                ClientSession(read, write) as session:
            await session.initialize()
            server = Server(session)
            for dead in dead_ends:  # one at a time: they share the server session
                await repair(dead, tool_reports[dead.tool], callables[tool_reports[dead.tool]["wraps"]], api, llm, box, base, server,
                             base_arguments, rounds, rng)
                print(f"  {'ok ' if dead.repaired else 'NO '} {dead.tool} ({' > '.join(a['stage'] for a in dead.attempts)})")

    # swap the repaired tools in, then call them through the finished server
    def install(dead: DeadEnd) -> None:
        header = (f"# Generated by repo2tools from {url} at {commit[:12]}, model {getattr(llm, 'model', 'unknown')}.\n"
                  f"# Wraps {tool_reports[dead.tool]['wraps']}. Rewritten by repair_chains.py so that its output can feed other tools.\n")
        (dest / "tools" / f"{dead.tool}.py").write_text(header + dead.code, encoding="utf-8")

    for dead in dead_ends:
        if dead.repaired:
            install(dead)
    repaired = [d for d in dead_ends if d.repaired]
    if repaired:
        problems = await end_to_end(dest / "run_server.sh", [ToolResult(d.tool, tool_reports[d.tool]["wraps"], "", True, d.code, d.spec, d.check) for d in repaired])
        for dead in repaired:
            if dead.tool in problems:
                dead.repaired = False
                dead.attempts.append({"stage": "end_to_end", "error": problems[dead.tool]})
                shutil.copy2(toolset / "tools" / f"{dead.tool}.py", dest / "tools" / f"{dead.tool}.py")

    kept = {d.tool: d for d in dead_ends if d.repaired}
    manifest |= {"set": new_set, "toolset": str(dest.relative_to(root)), "repaired_from": source_set, "repaired_tools": sorted(kept)}
    for entry in manifest["tools"]:
        if entry["name"] in kept:
            d = kept[entry["name"]]
            entry |= {"description": d.check.get("description"), "verified": d.check["verified"], "direct_call": d.spec["direct_call"], "samples": d.spec["samples"]}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    new_out = root / "out" / "generated" / new_set
    new_out.mkdir(parents=True, exist_ok=True)
    for tool in report["tools"]:
        if tool["name"] in kept:
            d = kept[tool["name"]]
            tool |= {"code": d.code, "spec": d.spec, "check": d.check}
    report |= {"set": new_set, "toolset": manifest["toolset"]}
    (new_out / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    shutil.copy2(out / "api.json", new_out / "api.json")
    summary = write_report(new_out / "chain_repair", source_set, new_set, getattr(llm, "model", "unknown"), dead_ends)
    print(f"{summary['repaired']} of {summary['dead_ends']} dead ends repaired -> {dest.relative_to(root)}, {(new_out / 'chain_repair.md').relative_to(root)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("toolset", type=Path, help="a folder under toolsets/generated/")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--rounds", type=int, default=3, help="repair rounds per tool")
    parser.add_argument("--thinking", action="store_true")
    args = parser.parse_args()
    toolset = args.toolset.resolve()
    source_set = json.loads((toolset / "manifest.json").read_text())["set"]
    llm = LLM(args.base_url, args.model, args.thinking, 2, repo2tools.ROOT / "out" / "generated" / f"{source_set}-chained" / "chain_repair_llm_log.jsonl")
    asyncio.run(repair_set(toolset, llm, args.rounds))


if __name__ == "__main__":
    main()
