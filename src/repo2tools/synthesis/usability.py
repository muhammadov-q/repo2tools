"""Check that a small model can pick and call each generated tool, and rewrite the names and descriptions it gets wrong.

    T=toolsets/generated/packaging-coder-60
    uv run repo2tools usability tasks  $T --base-url http://127.0.0.1:18000/v1 --model qwen3-32b
    uv run repo2tools usability check  $T --base-url http://127.0.0.1:18001/v1 --model qwen3-8b
    uv run repo2tools usability repair $T --base-url http://127.0.0.1:18001/v1 --model qwen3-8b \\
        --writer-url http://127.0.0.1:18000/v1 --writer-model qwen3-32b

A tool can give the same result as the library and still be of no use, because the model that
should call it does not understand its name and description. This script measures that, per tool.

tasks   For every sample call that passed the checks of `repo2tools generate`, an LLM writes a request in
        plain words that this call answers. It sees the library function, the inputs and the result,
        but never the tool's name or description. Every input value must appear in the request.
        Half of a tool's tasks are for repair ("dev"), the other half are held out ("test").
check   A small model gets each task three times: with only the tool the task was written for,
        with the whole tool set, and with no tools. A task counts as right when the model calls
        that tool with arguments that give the known result. Without tools we only learn which
        answers the model can guess.
repair  For every tool with a failed dev task, an LLM sees what the small model did and writes a new
        name and description. A rewrite is kept only if the small model then gets more of the tool's
        dev tasks right, and its final answer is the tool's result at least as often as before. The tool's code is not touched by the LLM: only the function name and the
        docstring are replaced, and the tool must pass the checks of `repo2tools generate` again. The result
        is a new tool set, <set>-usable, and it is measured again through its own server. The
        held-out tasks, which the rewriter never saw, show the effect.

Needs the report of `repo2tools generate` for the tool set, in out/generated/<set>/.
"""

import argparse
import ast
import asyncio
import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from repo2tools.evaluation import run_model
from repo2tools.evaluation.reference_calls import output_value
from repo2tools.synthesis import pipeline
from repo2tools.synthesis.pipeline import (
    LLM,
    TOOL_NAME,
    ToolResult,
    api_key_for,
    clone,
    end_to_end,
    extract_json,
    find_package,
    make_box,
    repo_name,
    run_worker,
    signature,
    static_problem,
    write_launchers,
)
from repo2tools.traces.format import write_traces

SYSTEM = {
    "tools": "You answer a request by using the tools you are given. Do not guess what a tool would return. When you are done, "
             "reply with only the final answer as a JSON value (true or false, a number, a string, a list or an object) and nothing else.",
    "none": "Answer the request. Reply with only the final answer as a JSON value (true or false, a number, a string, a list "
            "or an object) and nothing else.",
}
CONDITIONS = {"alone": "Tool alone", "set": "In the whole set", "none": "No tools"}
TASKS_PER_TOOL = 6
MAX_STEPS = 6
MAX_DESCRIPTION = 1200
JSON_NAMES = {str: "a JSON string", bool: "true or false", int: "a JSON number", float: "a JSON number", list: "a JSON list",
              dict: "a JSON object", type(None): "null"}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def out_dir(set_name: str) -> Path:
    return pipeline.ROOT / "out" / "generated" / set_name


# --- tasks -----------------------------------------------------------------------------------


def literals(value):
    """The strings and numbers inside a JSON value. true, false and null have no fixed wording."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (str, int, float)):
        yield value if isinstance(value, str) else json.dumps(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from literals(item)
    elif isinstance(value, list):
        for item in value:
            yield from literals(item)


def task_messages(callable_: dict, direct_call: str, arguments: dict, output) -> list[dict]:
    return [
        {"role": "system", "content": "You write short requests that test whether an AI model can use a tool. Reply with JSON only."},
        {"role": "user", "content": f"""A library was called like this:

{direct_call}
with {json.dumps(arguments)}
Result: {json.dumps(output)[:600]}

The function it calls:
{signature(callable_)}
{(callable_.get('docstring') or callable_.get('summary') or '')[:1500]}

Write the request of a user who needs exactly this result. Rules:
- Plain words, one or two sentences. Do not name the function.
- Give every input value exactly as written above, character for character. Leave out inputs that are null.
- Say what form the answer has if that is not obvious, for example "as a list" or "true or false".
- Do not give away the result.

Reply with one JSON object: {{"task": "..."}}"""},
    ]


def task_problem(text, tool: str, arguments: dict, output) -> str | None:
    if not isinstance(text, str) or len(text.strip()) < 10:
        return 'reply with {"task": "..."}'
    if tool in text:
        return "do not name the tool"
    missing = [v for v in literals(arguments) if v and v not in text]
    if missing:
        return f"these input values must appear exactly: {json.dumps(missing)}"
    if isinstance(output, str) and len(output) >= 4 and output not in json.dumps(arguments) and output in text:
        return "the request gives away the result"
    return None


async def make_tasks(toolset: Path, llm, per_tool: int = TASKS_PER_TOOL) -> list[dict]:
    """One task per checked sample call, split into dev and test. Written to out/generated/<set>/usability_tasks.jsonl."""
    manifest = json.loads((toolset / "manifest.json").read_text())
    out = out_dir(manifest["set"])
    report = json.loads((out / "report.json").read_text())
    api = json.loads((out / "api.json").read_text())
    callables = {f"{c['module']}.{c['qualname']}": c for c in api["callables"]}
    listed = {t["name"] for t in manifest["tools"]}

    async def write(tool: dict, number: int, row: dict) -> dict | None:
        chat = task_messages(callables[tool["wraps"]], tool["spec"]["direct_call"], row["arguments"], row["tool"])
        for _ in range(2):
            reply = await llm.chat("task", f"{tool['name']}-{number}", chat)
            try:
                text = extract_json(reply).get("task")
            except (ValueError, AttributeError):
                text = None
            problem = task_problem(text, tool["name"], row["arguments"], row["tool"])
            if not problem:
                return {"id": f"{tool['name']}-{number}", "tool": tool["name"], "split": "dev" if number % 2 == 0 else "test",
                        "task": text.strip(), "arguments": row["arguments"], "expected": row["tool"]}
            chat = chat + [{"role": "assistant", "content": reply}, {"role": "user", "content": f"Not acceptable: {problem}. Reply with the corrected JSON only."}]
        return None

    jobs = []
    for tool in report["tools"]:
        if not tool["accepted"] or tool["name"] not in listed:
            continue
        rows: dict[str, dict] = {}  # each different input once, in the order of the samples
        for row in tool["check"]["samples"]:
            if row["result"].startswith("same"):
                rows.setdefault(canonical(row["arguments"]), row)
        jobs += [write(tool, number, row) for number, row in enumerate(list(rows.values())[:per_tool])]
    written = await asyncio.gather(*jobs)
    tasks = [t for t in written if t]
    (out / "usability_tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks), encoding="utf-8")
    print(f"{len(tasks)} tasks for {len({t['tool'] for t in tasks})} tools ({len(written) - len(tasks)} sample calls gave no acceptable task) "
          f"-> {(out / 'usability_tasks.jsonl').relative_to(pipeline.ROOT)}")
    return tasks


def read_tasks(set_name: str) -> list[dict]:
    path = out_dir(set_name) / "usability_tasks.jsonl"
    if not path.is_file():
        raise SystemExit(f"missing {path}: run `repo2tools usability tasks` on this tool set first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- one model run, and its verdict --------------------------------------------------------------


def same_arguments(given: dict, wanted: dict, schema: dict) -> bool:
    """Equal after filling in the defaults and ignoring spaces inside strings (">=1, <2" is ">=1,<2")."""
    defaults = {name: p["default"] for name, p in (schema.get("properties") or {}).items() if "default" in p}

    def squeeze(value):
        if isinstance(value, str):
            return "".join(value.split())
        if isinstance(value, list):
            return [squeeze(v) for v in value]
        if isinstance(value, dict):
            return {k: squeeze(v) for k, v in value.items()}
        return value

    return canonical(squeeze({**defaults, **given})) == canonical(squeeze({**defaults, **wanted}))


def judge(task: dict, calls: list[dict], answer, schema: dict) -> dict:
    """What the model did with the tool the task was written for.

    right          it called that tool, with the task's arguments or with others that give the same result.
                   A true/false result needs the arguments themselves: half of all wrong calls would match it.
    no_call        it called no tool
    wrong_tool     it called only other tools
    bad_arguments  it called the tool, but never with arguments that give the known result
    """
    expected = task["expected"]
    target = [c for c in calls if c["tool"] == task["tool"]]

    def right(call: dict) -> bool:
        if not call["ok"] or not isinstance(call["arguments"], dict):
            return False
        return same_arguments(call["arguments"], task["arguments"], schema) or (
            not isinstance(expected, bool) and canonical(call["output"]) == canonical(expected))

    outcome = "right" if any(map(right, target)) else "no_call" if not calls else "wrong_tool" if not target else "bad_arguments"
    return {"outcome": outcome, "right_call": outcome == "right", "answer_right": canonical(answer) == canonical(expected)}


class Recorder:
    """Passes the model's calls to the real server, under the tools' real names, and keeps them."""

    def __init__(self, session, real_names: dict[str, str]):
        self.session, self.real_names, self.calls = session, real_names, []

    async def call_tool(self, name: str, arguments):
        call = {"shown": name, "tool": self.real_names.get(name), "arguments": arguments, "ok": False, "output": None}
        self.calls.append(call)
        if call["tool"] is None:
            raise ValueError(f"there is no tool named {name}")
        result = await self.session.call_tool(call["tool"], arguments)
        if result.isError:
            call["output"] = result.content[0].text[:300] if result.content else "error"
        else:
            call["ok"], call["output"] = True, output_value(result)
        return result


@dataclass
class Bench:
    """A tool set's running server, and the small model that tries its tools."""

    session: object
    specs: dict[str, dict]  # real tool name -> {"name", "description", "parameters"}
    client: object
    model: str
    limit: asyncio.Semaphore

    @classmethod
    async def start(cls, session, client, model: str, concurrency: int = 16) -> "Bench":
        specs = {t.name: {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}
                 for t in (await session.list_tools()).tools}
        return cls(session, specs, client, model, asyncio.Semaphore(concurrency))

    def offer(self, view: dict, only: set | None = None) -> list[dict]:
        """The tools in OpenAI format, under the names and descriptions in `view` (candidates not yet written to disk)."""
        return [{"type": "function", "function": {"name": view.get(real, spec)["name"], "description": view.get(real, spec)["description"],
                                                  "parameters": spec["parameters"]}}
                for real, spec in self.specs.items() if only is None or real in only]

    async def attempt(self, task: dict, condition: str, view: dict) -> dict:
        tools = [] if condition == "none" else self.offer(view, {task["tool"]} if condition == "alone" else None)
        recorder = Recorder(self.session, {view.get(real, spec)["name"]: real for real, spec in self.specs.items()
                                           if condition == "set" or (condition == "alone" and real == task["tool"])})
        mode = "none" if condition == "none" else "tools"
        exercise = {"id": task["id"], "kind": task["tool"], "horizon": "short", "task": task["task"], "answer": task["expected"],
                    "check": {"kind": "exact"}, "reference_calls": [{"tool": task["tool"], "arguments": task["arguments"]}], "reference_call_count": 1}
        args = SimpleNamespace(mode=mode, tool_choice="auto", model=self.model, thinking=False, tag=f"usability-{condition}",
                               max_steps=MAX_STEPS, system=SYSTEM[mode])
        record = {"task": task["id"], "tool": task["tool"], "split": task["split"], "condition": condition}
        async with self.limit:
            try:
                result = await run_model.solve(exercise, args, self.client, recorder, tools)
            except Exception as e:  # noqa: BLE001  (an endpoint failure is recorded, not fatal)
                return record | {"outcome": "error", "right_call": False, "answer_right": False, "answer": None, "calls": [], "error": repr(e)[:300]}
        return record | judge(task, recorder.calls, result["answer"], self.specs[task["tool"]]["parameters"]) | {
            "answer": result["answer"], "calls": recorder.calls, "tokens": result["tokens"], "full_trace": result["full_trace"]}

    async def run(self, tasks: list[dict], conditions=("alone", "set"), view: dict | None = None) -> list[dict]:
        known = [t for t in tasks if t["tool"] in self.specs]
        return list(await asyncio.gather(*(self.attempt(t, c, view or {}) for t in known for c in conditions)))


def right_count(records: list[dict], **where) -> tuple[int, int]:
    rows = [r for r in records if all(r[k] == v for k, v in where.items())]
    return sum(r["right_call"] for r in rows), len(rows)


def summarize(records: list[dict]) -> dict:
    conditions = [c for c in CONDITIONS if any(r["condition"] == c for r in records)]
    totals, per_tool = {}, defaultdict(dict)
    for c in conditions:
        rows = [r for r in records if r["condition"] == c]
        totals[c] = {"tasks": len(rows), "right": sum(r["right_call"] for r in rows), "answer_right": sum(r["answer_right"] for r in rows),
                     "outcomes": dict(Counter(r["outcome"] for r in rows)),
                     "splits": {s: list(right_count(rows, split=s)) for s in ("dev", "test")}}
        for tool in sorted({r["tool"] for r in rows}):
            mine = [r for r in rows if r["tool"] == tool]
            instead = Counter(call["tool"] for r in mine if r["outcome"] == "wrong_tool" for call in r["calls"][:1] if call["tool"])
            per_tool[tool][c] = {"tasks": len(mine), "right": sum(r["right_call"] for r in mine),
                                 "outcomes": dict(Counter(r["outcome"] for r in mine if r["outcome"] != "right")), "instead": dict(instead)}
    return {"totals": totals, "tools": dict(per_tool)}


def share(right: int, total: int) -> str:
    return f"{right} of {total}" + (f" ({right / total:.0%})" if total else "")


def write_check_report(path: Path, set_name: str, model: str, records: list[dict]) -> dict:
    summary = summarize(records) | {"set": set_name, "model": model}
    path.with_suffix(".json").write_text(json.dumps(summary | {"records": [{k: v for k, v in r.items() if k != "full_trace"} for r in records]},
                                                    indent=1, default=str), encoding="utf-8")
    totals = summary["totals"]
    shown = [c for c in ("alone", "set") if c in totals]
    lines = [f"# Usability of {set_name}", "",
             f"`{model}` gets one task per checked sample call: {totals[shown[0]]['tasks']} tasks for {len(summary['tools'])} tools. A task is right "
             "when the model calls the tool it was written for, with arguments that give the known result.", "",
             "| | " + " | ".join(CONDITIONS[c] for c in shown) + " |", "| --- |" + " --- |" * len(shown),
             "| **Right call** | " + " | ".join(f"**{share(totals[c]['right'], totals[c]['tasks'])}**" for c in shown) + " |",
             "| Right call, held-out tasks only | " + " | ".join(share(*totals[c]["splits"]["test"]) for c in shown) + " |"]
    for outcome, label in (("no_call", "No tool call"), ("wrong_tool", "Only other tools called"), ("bad_arguments", "Tool called, wrong arguments"), ("error", "Run failed")):
        if any(totals[c]["outcomes"].get(outcome) for c in shown):
            lines.append(f"| {label} | " + " | ".join(str(totals[c]["outcomes"].get(outcome, 0)) for c in shown) + " |")
    lines.append("| Final answer equals the known result | " + " | ".join(share(totals[c]["answer_right"], totals[c]["tasks"]) for c in shown) + " |")
    if "none" in totals:
        lines += ["", f"Without any tool, the model's answer is right on {share(totals['none']['answer_right'], totals['none']['tasks'])} tasks: these can be guessed."]
    lines += ["", "## Per tool", "", "| Tool | " + " | ".join(CONDITIONS[c] for c in shown) + " | Problems | Called instead |", "| --- |" + " --- |" * (len(shown) + 2)]
    for tool, by in summary["tools"].items():
        problems, instead = Counter(), Counter()
        for c in shown:
            problems.update(by[c]["outcomes"])
            instead.update(by[c]["instead"])
        lines.append(f"| `{tool}` | " + " | ".join(f"{by[c]['right']} of {by[c]['tasks']}" for c in shown) + " | "
                     + ", ".join(f"{k} {v}" for k, v in problems.most_common()) + " | " + ", ".join(f"`{k}` {v}" for k, v in instead.most_common(3)) + " |")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


# --- rewriting a name and description ------------------------------------------------------------


def describe_failure(record: dict, task: dict, bench: Bench, view: dict) -> str:
    where = "Only this tool was offered." if record["condition"] == "alone" else f"The tool was offered together with {len(bench.specs) - 1} others."
    if not record["calls"]:
        did = f"made no tool call and answered {json.dumps(record['answer'])[:120]}"
    else:
        parts = []
        for call in record["calls"][:3]:
            text = f"called `{call['shown']}` with {json.dumps(call['arguments'])[:200]}"
            if call["tool"] and call["tool"] != task["tool"]:
                text += f" (that tool's description: {view.get(call['tool'], bench.specs[call['tool']])['description'][:200]!r})"
            parts.append(text + (f" and got {json.dumps(call['output'])[:150]}" if call["ok"] else f" and got an error: {str(call['output'])[:150]}"))
        did = "; then ".join(parts)
    return f"Request: {task['task']!r}\n   {where} The model {did}.\n   A correct call: {json.dumps(task['arguments'])}"


def rewrite_messages(shown: dict, schema: dict, callable_: dict, direct_call: str, dev_tasks: list[dict], failures: list[str], taken: list[str]) -> list[dict]:
    parameters = "\n".join(f"- {name} ({p.get('type', 'any')}{', default ' + json.dumps(p['default']) if 'default' in p else ''})"
                           for name, p in (schema.get("properties") or {}).items()) or "- none"
    works = "\n".join(f"- {json.dumps(t['arguments'])} -> {json.dumps(t['expected'])[:200]}" for t in dev_tasks)
    returns = " or ".join(sorted({JSON_NAMES[type(t["expected"])] for t in dev_tasks}))
    wrong = "\n".join(f"{i}. {text}" for i, text in enumerate(failures, 1))
    return [
        {"role": "system", "content": "You improve the name and description of a tool, so that an AI model picks it and calls it correctly. Reply with JSON only."},
        {"role": "user", "content": f"""A small AI model got requests that this tool answers, and it did not use the tool correctly.

The tool now:
name: `{shown['name']}`
description: {shown['description']}
parameters (they cannot change):
{parameters}

What the tool computes: `{direct_call}`, with this library function:
{signature(callable_)}
{(callable_.get('docstring') or callable_.get('summary') or '')[:1500]}

Calls that are known to work, as input -> output:
{works}
The tool returns {returns}, exactly as shown in these calls. It never returns a library object, whatever the library function returns.

What went wrong:
{wrong}

Names of the other tools in the set, which are taken: {', '.join(taken)}

Write a better name and description. The model sees only the name, the description and the parameter names and types. So the description must say what the tool does, when to use it, what each parameter means and what form its value has, and what the output is. Describe the output as the JSON value in the working calls above, not as the library's type. State only what the library documentation and the working calls show. Do not mention the requests. At most 120 words. You may keep the name.

Reply with one JSON object: {{"name": "snake_case_name", "description": "..."}}"""},
    ]


def read_rewrite(reply: str, taken: set[str]) -> tuple[dict | None, str | None]:
    try:
        data = extract_json(reply)
    except ValueError as e:
        return None, str(e)
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not isinstance(data.get("description"), str):
        return None, 'reply with {"name": "...", "description": "..."}'
    name, description = data["name"].strip(), " ".join(data["description"].split())  # one line: exactly what the docstring will hold
    if not TOOL_NAME.match(name) or len(name) > 60:
        return None, "the name must be snake_case, at most 60 characters"
    if name in taken:
        return None, f"the name {name} is taken by another tool"
    if not 20 <= len(description) <= MAX_DESCRIPTION:
        return None, f"the description must have 20 to {MAX_DESCRIPTION} characters"
    return {"name": name, "description": description}, None


def apply_rewrite(code: str, old: str, new: str, description: str) -> str:
    """The tool's code with the function renamed and its docstring replaced. Nothing else changes."""
    function = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == old)
    first = function.body[0]
    if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)):
        raise ValueError(f"{old} has no docstring to replace")
    text = description.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    if text.endswith('"'):
        text = text[:-1] + '\\"'
    lines = code.splitlines()
    lines[first.lineno - 1:first.end_lineno] = [" " * first.col_offset + f'"""{text}"""']
    lines[function.lineno - 1] = re.sub(rf"\bdef {re.escape(old)}\b", f"def {new}", lines[function.lineno - 1], count=1)
    new_code = "\n".join(lines) + "\n"
    if ast.get_docstring(next(n for n in ast.parse(new_code).body if isinstance(n, ast.FunctionDef) and n.name == new), clean=False) != description:
        raise ValueError("the new docstring does not read back as the description")
    return new_code


async def rewrite_tool(tool: str, bench: Bench, view: dict, tasks: list[dict], before: list[dict], writer, callable_: dict, direct_call: str, rounds: int) -> dict:
    """Try up to `rounds` rewrites of one tool. Returns {"kept": {"name", "description"} | None, "attempts": [...], ...}."""
    dev = [t for t in tasks if t["tool"] == tool and t["split"] == "dev"]
    by_id = {t["id"]: t for t in dev}
    records = [r for r in before if r["tool"] == tool and r["split"] == "dev" and r["condition"] in ("alone", "set")]
    start = best = sum(r["right_call"] for r in records)
    answers = sum(r["answer_right"] for r in records)  # a rewrite may not make the model read the result worse
    result = {"tool": tool, "dev_runs": len(records), "dev_right_before": start, "dev_right_after": start, "kept": None, "attempts": []}
    shown = view.get(tool, bench.specs[tool])
    taken = sorted(view.get(real, spec)["name"] for real, spec in bench.specs.items() if real != tool)

    def failures(rows: list[dict], names: dict) -> list[str]:
        return [describe_failure(r, by_id[r["task"]], bench, names) for r in rows if not r["right_call"]][:4]

    chat = rewrite_messages(shown, bench.specs[tool]["parameters"], callable_, direct_call, dev, failures(records, view), taken)
    for _ in range(rounds):
        reply = await writer.chat("rewrite", tool, chat)
        rewrite, problem = read_rewrite(reply, set(taken))
        if problem:
            result["attempts"].append({"problem": problem})
            chat = chat + [{"role": "assistant", "content": reply}, {"role": "user", "content": f"Not acceptable: {problem}. Reply with the corrected JSON only."}]
            continue
        candidate = {**view, tool: rewrite}
        records = await bench.run(dev, ("alone", "set"), candidate)
        score, read = sum(r["right_call"] for r in records), sum(r["answer_right"] for r in records)
        result["attempts"].append({**rewrite, "dev_right": score, "dev_answers_right": read})
        if score > best and read >= answers:
            best, result["kept"], result["dev_right_after"] = score, rewrite, score
        if score == len(records) and read >= answers:
            break
        still = "\n".join(f"{i}. {text}" for i, text in enumerate(failures(records, candidate), 1)) or "(every call was right)"
        misread = (f"\nAlso, the model's final answer was the tool's result in only {read} runs (before: {answers}). The description must say "
                   "truthfully what the tool returns.") if read < answers else ""
        chat = chat + [{"role": "assistant", "content": reply},
                       {"role": "user", "content": f"With this name and description the model got {score} of {len(records)} runs right (before: {start}). Still wrong:\n{still}{misread}\n\n"
                                                   "Try again. Reply with one JSON object with \"name\" and \"description\"."}]
    return result


def write_repair_report(path: Path, source_set: str, new_set: str, model: str, writer_model: str, before: list[dict], after: list[dict],
                        rewrites: list[dict], renamed: dict, old_specs: dict, new_specs: dict) -> dict:
    back = {new: old for old, new in renamed.items()}
    for r in after:  # compare per tool under the old names
        r["tool"] = back.get(r["tool"], r["tool"])
    kept = [w for w in rewrites if w["kept"]]
    rows = []
    for label, where in (("Tool alone, held-out tasks", dict(condition="alone", split="test")), ("In the whole set, held-out tasks", dict(condition="set", split="test")),
                         ("Tool alone, tasks used for the repair", dict(condition="alone", split="dev")), ("In the whole set, tasks used for the repair", dict(condition="set", split="dev"))):
        rows.append({"measure": label, "before": list(right_count(before, **where)), "after": list(right_count(after, **where))})
    changed = {w["tool"] for w in kept}
    for label, tools in (("held-out tasks of the rewritten tools, both settings", changed), ("held-out tasks of the other tools, both settings", {r["tool"] for r in before} - changed)):
        held_out = [[r for r in records if r["tool"] in tools and r["split"] == "test" and r["condition"] in ("alone", "set")] for records in (before, after)]
        rows.append({"measure": label[0].upper() + label[1:], "before": list(right_count(held_out[0])), "after": list(right_count(held_out[1]))})
    per_tool = {}
    for tool in sorted({r["tool"] for r in before}):
        per_tool[tool] = {"before": list(right_count([r for r in before if r["condition"] in ("alone", "set")], tool=tool)),
                          "after": list(right_count([r for r in after if r["condition"] in ("alone", "set")], tool=tool))}
    worse = {t: v for t, v in per_tool.items() if v["after"][0] < v["before"][0]}
    summary = {"source_set": source_set, "set": new_set, "model": model, "writer_model": writer_model, "tools": len(old_specs),
               "tools_with_failed_dev_task": len(rewrites), "rewritten": len(kept), "renamed": renamed, "measures": rows,
               "per_tool": per_tool, "worse": sorted(worse), "rewrites": rewrites}
    path.with_suffix(".json").write_text(json.dumps(summary | {"after_records": [{k: v for k, v in r.items() if k != "full_trace"} for r in after]},
                                                    indent=1, default=str), encoding="utf-8")
    lines = [f"# Usability repair: {source_set} -> {new_set}", "",
             f"`{model}` uses the tools. `{writer_model}` writes new names and descriptions for tools with a failed task; it sees only the tasks "
             "marked for repair. A rewrite is kept if the small model then gets more of those right. The code of the tools is unchanged, "
             "and every rewritten tool passed the checks of `repo2tools generate` again. \"After\" is measured through the new tool set's own server.", "",
             f"**{len(kept)} of {len(rewrites)} tools with a failed task were rewritten** ({len(renamed)} renamed); the set has {len(old_specs)} tools.", "",
             "| Right calls | Before | After |", "| --- | --- | --- |"]
    lines += [f"| {r['measure']} | {share(*r['before'])} | {share(*r['after'])} |" for r in rows]
    lines += ["", "## Tools with a failed task", "", "| Tool | New name | Repair tasks right, before to after | All tasks right, before to after | Tries | Result |", "| --- | --- | --- | --- | --- | --- |"]
    for w in rewrites:
        tool, tries = w["tool"], len(w["attempts"])
        name = f"`{renamed[tool]}`" if tool in renamed else ""
        result = "rewritten" if w["kept"] else w.get("dropped") or "no rewrite was better"
        lines.append(f"| `{tool}` | {name} | {w['dev_right_before']} to {w['dev_right_after']} of {w['dev_runs']} | "
                     f"{per_tool[tool]['before'][0]} to {per_tool[tool]['after'][0]} of {per_tool[tool]['before'][1]} | {tries} | {result} |")
    if worse:
        lines += ["", "## Tools that got worse", ""] + [f"- `{t}`: {v['before'][0]} to {v['after'][0]} of {v['before'][1]}" + (" (not rewritten itself)" if t not in changed else "")
                                                        for t, v in worse.items()]
    lines += ["", "## New names and descriptions", ""]
    for w in kept:
        tool = w["tool"]
        new = renamed.get(tool, tool)
        lines += [f"### `{tool}`" + (f" is now `{new}`" if new != tool else ""), "", f"Before: {' '.join(old_specs[tool]['description'].split())}", "",
                  f"After: {new_specs[new]['description']}", ""]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


async def repair_set(toolset: Path, client, model: str, writer, rounds: int = 3, suffix: str = "usable", concurrency: int = 16) -> dict:
    root = pipeline.ROOT
    manifest = json.loads((toolset / "manifest.json").read_text())
    source_set = manifest["set"]
    out = out_dir(source_set)
    report = json.loads((out / "report.json").read_text())
    api = json.loads((out / "api.json").read_text())
    tool_reports = {t["name"]: t for t in report["tools"] if t["accepted"]}
    callables = {f"{c['module']}.{c['qualname']}": c for c in api["callables"]}
    tasks = read_tasks(source_set)

    # 1. measure, then try rewrites: candidates are only shown to the model, nothing is written yet
    view: dict[str, dict] = {}
    rewrites = []
    async with stdio_client(StdioServerParameters(command=str(toolset / "run_server.sh"), args=[])) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        bench = await Bench.start(session, client, model, concurrency)
        old_specs = bench.specs
        before = await bench.run(tasks, ("alone", "set", "none"))
        failing = sorted({r["tool"] for r in before if r["split"] == "dev" and r["condition"] != "none" and not r["right_call"]})
        for tool in failing:  # one at a time: a kept rewrite changes what the next tool is compared with
            entry = tool_reports[tool]
            result = await rewrite_tool(tool, bench, view, tasks, before, writer, callables[entry["wraps"]], entry["spec"]["direct_call"], rounds)
            rewrites.append(result)
            if result["kept"]:
                view[tool] = result["kept"]
            print(f"  {'ok ' if result['kept'] else 'NO '} {tool}: {result['dev_right_before']} to {result['dev_right_after']} of {result['dev_runs']} dev runs"
                  + (f", now {result['kept']['name']}" if result["kept"] and result["kept"]["name"] != tool else ""))

    # 2. write the new tool set, and run the checks of `repo2tools generate` on every rewritten tool
    new_set = f"{source_set}-{suffix}"
    dest = root / "toolsets" / "generated" / new_set
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(toolset, dest, ignore=shutil.ignore_patterns("__pycache__"))
    url, commit = manifest["url"], manifest["commit"]
    repo_root = pipeline.CACHE / "repos" / repo_name(url)
    clone(url, commit, repo_root)
    base, package = find_package(repo_root, manifest["package"])
    box = make_box(new_set, base, package, manifest.get("dependencies", []), dest)
    write_launchers(dest, new_set, new_set[len(repo_name(url)) + 1:], url, commit)
    done: dict[str, dict] = {}  # old name -> {"name", "code", "check"}
    for result in rewrites:
        if not result["kept"]:
            continue
        tool, new = result["tool"], result["kept"]["name"]
        entry = tool_reports[tool]
        try:
            code = apply_rewrite(entry["code"], tool, new, result["kept"]["description"])
            problem = static_problem(code, new, [p["name"] for p in entry["spec"]["parameters"]])
            check = None if problem else await asyncio.to_thread(run_worker, box, new, code, entry["spec"])
            if problem or not check["ok"]:
                raise ValueError(f"{(problem or (check['stage'], check.get('error')))}")
            old_rows = {canonical(r["arguments"]): canonical(r["tool"]) for r in entry["check"]["samples"]}
            if any(old_rows.get(canonical(r["arguments"])) != canonical(r["tool"]) for r in check["samples"]):
                raise ValueError("a sample call gives another result than before")
        except (ValueError, StopIteration) as e:
            result |= {"kept": None, "dev_right_after": result["dev_right_before"], "dropped": f"dropped, the checks failed: {str(e)[:150]}"}
            continue
        header = (f"# Generated by repo2tools from {url} at {commit[:12]}, model {manifest.get('model', 'unknown')}.\n"
                  f"# Wraps {entry['wraps']}. Name and description rewritten by `repo2tools usability`; the code is unchanged.\n")
        (dest / "tools" / f"{tool}.py").unlink()
        (dest / "tools" / f"{new}.py").write_text(header + code, encoding="utf-8")
        done[tool] = {"name": new, "code": code, "check": check}
    if done:
        problems = await end_to_end(dest / "run_server.sh", [ToolResult(d["name"], tool_reports[old]["wraps"], "", True, d["code"], tool_reports[old]["spec"], d["check"])
                                                             for old, d in done.items()])
        if problems:
            raise SystemExit(f"the rewritten tools fail over MCP: {problems}")
    renamed = {old: d["name"] for old, d in done.items() if d["name"] != old}

    manifest |= {"set": new_set, "toolset": str(dest.relative_to(root)), "usability_from": source_set, "renamed_tools": renamed, "rewritten_tools": sorted(done)}
    for entry in manifest["tools"]:
        if entry["name"] in done:
            d = done[entry["name"]]
            entry |= {"name": d["name"], "description": d["check"].get("description")}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    new_out = out_dir(new_set)
    new_out.mkdir(parents=True, exist_ok=True)
    for tool in report["tools"]:
        if tool["name"] in done:
            d = done[tool["name"]]
            tool |= {"name": d["name"], "code": d["code"], "check": d["check"], "description": d["check"].get("description")}
    report |= {"set": new_set, "toolset": manifest["toolset"]}
    (new_out / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    shutil.copy2(out / "api.json", new_out / "api.json")
    new_tasks = [t | {"tool": renamed.get(t["tool"], t["tool"])} for t in tasks]
    (new_out / "usability_tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in new_tasks), encoding="utf-8")

    # 3. measure the new set through its own server
    async with stdio_client(StdioServerParameters(command=str(dest / "run_server.sh"), args=[])) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        bench = await Bench.start(session, client, model, concurrency)
        new_specs = bench.specs
        for old, d in done.items():
            wanted = next(w["kept"]["description"] for w in rewrites if w["tool"] == old)
            if new_specs[d["name"]]["description"] != wanted:
                raise SystemExit(f"{d['name']}: the server shows another description than the one that was tested")
        after = await bench.run(new_tasks, ("alone", "set"))
    write_traces(root / "out" / "traces" / f"usability-{new_set}-{model}.jsonl.gz", [r.pop("full_trace") for r in before + after if "full_trace" in r])
    write_check_report(out / "usability", source_set, model, before)
    write_check_report(new_out / "usability", new_set, model, [dict(r) for r in after])
    summary = write_repair_report(new_out / "usability_repair", source_set, new_set, model, getattr(writer, "model", "unknown"), before, after,
                                  rewrites, renamed, old_specs, new_specs)
    for row in summary["measures"]:
        print(f"  {row['measure']}: {share(*row['before'])} -> {share(*row['after'])}")
    print(f"{summary['rewritten']} of {summary['tools_with_failed_dev_task']} tools rewritten -> {dest.relative_to(root)}, {(new_out / 'usability_repair.md').relative_to(root)}")
    return summary


async def check_set(toolset: Path, client, model: str, concurrency: int = 16) -> dict:
    set_name = json.loads((toolset / "manifest.json").read_text())["set"]
    tasks = read_tasks(set_name)
    async with stdio_client(StdioServerParameters(command=str(toolset / "run_server.sh"), args=[])) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        bench = await Bench.start(session, client, model, concurrency)
        records = await bench.run(tasks, ("alone", "set", "none"))
    write_traces(pipeline.ROOT / "out" / "traces" / f"usability-{set_name}-{model}.jsonl.gz", [r.pop("full_trace") for r in records if "full_trace" in r])
    summary = write_check_report(out_dir(set_name) / "usability", set_name, model, records)
    for c, total in summary["totals"].items():
        print(f"  {CONDITIONS[c]}: right call {share(total['right'], total['tasks'])}, answer right {share(total['answer_right'], total['tasks'])}, {total['outcomes']}")
    print(f"-> {(out_dir(set_name) / 'usability.md').relative_to(pipeline.ROOT)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("tasks", "check", "repair"))
    parser.add_argument("toolset", type=Path, help="a folder under toolsets/generated/")
    parser.add_argument("--base-url", required=True, help="tasks: the model that writes tasks. check, repair: the small model that uses the tools")
    parser.add_argument("--model", required=True)
    parser.add_argument("--writer-url", help="repair: the model that rewrites names and descriptions")
    parser.add_argument("--writer-model")
    parser.add_argument("--rounds", type=int, default=3, help="repair: rewrites to try per tool")
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()
    toolset = args.toolset.resolve()
    set_name = json.loads((toolset / "manifest.json").read_text())["set"]
    if args.command == "tasks":
        asyncio.run(make_tasks(toolset, LLM(args.base_url, args.model, False, 8, out_dir(set_name) / "usability_tasks_llm_log.jsonl")))
        return
    client = AsyncOpenAI(base_url=args.base_url, api_key=api_key_for(args.base_url), timeout=300, max_retries=2)
    if args.command == "check":
        asyncio.run(check_set(toolset, client, args.model, args.concurrency))
        return
    if not args.writer_url or not args.writer_model:
        parser.error("repair needs --writer-url and --writer-model")
    writer = LLM(args.writer_url, args.writer_model, False, 2, out_dir(f"{set_name}-usable") / "usability_repair_llm_log.jsonl")
    asyncio.run(repair_set(toolset, client, args.model, writer, args.rounds, concurrency=args.concurrency))


if __name__ == "__main__":
    main()
