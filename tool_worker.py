"""Check one generated tool against a direct library call. Stdlib and mcp only.

repo2tools.py runs this file inside the tool set's own environment and sandbox, because it imports
and calls generated code:

    <env>/bin/python -I tool_worker.py < request.json

Request: {"tool_file", "tool_name", "parameters": [{"name", ...}], "direct_call", "samples": [{...}]}
Result (one JSON object on stdout): {"ok", "stage", "error", "samples", "verified", "description",
"input_schema"}. `stage` is the first check that failed:

    loads         the file cannot be imported, or it has no such function
    fastmcp       FastMCP refuses the function, or its parameters are not the agreed ones
    spec          the test itself is wrong: the direct call never works, or a sample is unusable
    runs          the tool crashed with something other than ValueError, or its output is not JSON
    differential  the tool and the direct library call disagree

repo2tools.py imports the constants and direct_call_problem() from here, so this file imports mcp
only inside check().
"""

import ast
import asyncio
import builtins
import collections.abc
import contextlib
import copy
import datetime
import enum
import importlib
import importlib.util
import inspect
import io
import itertools
import json
import math
import os
import signal
import sys

# Not a security boundary: the sandbox is. This only tells the model early what not to use.
DANGEROUS_MODULES = {
    "asyncio", "builtins", "code", "ctypes", "ftplib", "glob", "http", "importlib", "marshal",
    "multiprocessing", "os", "pathlib", "pickle", "pty", "runpy", "shelve", "shutil", "signal",
    "smtplib", "socket", "socketserver", "ssl", "subprocess", "sys", "tempfile", "threading",
    "urllib.request", "webbrowser",
}
FORBIDDEN_NAMES = {"__import__", "breakpoint", "compile", "eval", "exec", "globals", "input", "locals",
                   "open", "print", "vars"}
SAFE_BUILTINS = ("abs", "bool", "bytes", "dict", "float", "frozenset", "int", "len", "list", "max", "min",
                 "repr", "set", "sorted", "str", "sum", "tuple")
DIRECT_CALL_NODES = (ast.Expression, ast.Call, ast.Attribute, ast.Name, ast.Load, ast.Constant, ast.keyword,
                     ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Subscript, ast.UnaryOp, ast.USub, ast.Not, ast.IfExp,
                     ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Is, ast.IsNot, ast.Eq, ast.NotEq)
SAMPLE_SECONDS = 5
# errors that mean the direct call itself is written wrongly, not that a sample is invalid
BROKEN_CALL_ERRORS = (NameError, AttributeError, ImportError, SyntaxError)


def direct_call_problem(expression: str, parameters: list[str], target: str) -> str | None:
    """Why a direct_call expression is not acceptable, or None. Runs before any code is executed."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        return f"direct_call is not a Python expression: {e.msg}"
    names, attributes = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, DIRECT_CALL_NODES):
            return f"direct_call may not use {type(node).__name__}: only calls, attributes, names, constants and simple conditions"
        if isinstance(node, ast.Name):
            if node.id.startswith("__"):
                return f"direct_call may not use {node.id}"
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return f"direct_call may not use {node.attr}"
            attributes.add(node.attr)
    if target not in names | attributes:
        return f"direct_call must use the library's {target}"
    missing = [p for p in parameters if p not in names]
    if missing:
        return f"direct_call must use every tool parameter; it does not use: {', '.join(missing)}"
    roots = names - set(parameters) - set(SAFE_BUILTINS)
    bad = roots & DANGEROUS_MODULES
    if bad:
        return f"direct_call may not use: {', '.join(sorted(bad))}"
    return None


class SampleTimeout(BaseException):
    """Derived from BaseException so that a tool's `except Exception` cannot swallow it."""


@contextlib.contextmanager
def time_limit(seconds: int):
    def on_alarm(signum, frame):
        raise SampleTimeout(f"took longer than {seconds} s")

    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def materialize(value):
    """Read out iterators, so a value can be compared more than once."""
    if isinstance(value, collections.abc.Iterator):
        return [materialize(v) for v in itertools.islice(value, 5000)]
    if isinstance(value, (list, tuple)):
        return type(value)(materialize(v) for v in value) if type(value) in (list, tuple) else list(value)
    if isinstance(value, collections.abc.Mapping):
        return {k: materialize(v) for k, v in value.items()}
    return value


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def to_json(value):
    """The JSON form of a library value. Objects without a JSON form become their str()."""
    if isinstance(value, enum.Enum):
        return to_json(value.value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, collections.abc.Mapping):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted((to_json(v) for v in value), key=canonical)
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return str(value)


def strictly_equal(a, b) -> bool:
    """JSON equality that keeps true and 1 apart and allows for float rounding."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(strictly_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(strictly_equal(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b or (isinstance(a, str) and isinstance(b, str) and a == b)


def same_shape_equal(tool_value, direct) -> bool:
    """Equal with the same structure. Order counts in lists, but not in the library's sets."""
    if isinstance(direct, (set, frozenset)):
        return isinstance(tool_value, list) and \
            sorted(map(canonical, tool_value)) == sorted(map(canonical, to_json(direct)))
    if isinstance(direct, (list, tuple)):
        return isinstance(tool_value, list) and len(tool_value) == len(direct) and \
            all(same_shape_equal(t, d) for t, d in zip(tool_value, direct))
    if isinstance(direct, collections.abc.Mapping):
        return isinstance(tool_value, dict) and tool_value.keys() == {str(k) for k in direct} and \
            all(same_shape_equal(tool_value[str(k)], v) for k, v in direct.items())
    return strictly_equal(tool_value, to_json(direct))


def leaves(value) -> list[str]:
    """All non-null scalars inside a JSON value, sorted. Ignores the structure around them."""
    if isinstance(value, dict):
        found = [leaf for v in value.values() for leaf in leaves(v)]
    elif isinstance(value, list):
        found = [leaf for v in value for leaf in leaves(v)]
    else:
        found = [] if value is None else [canonical(value)]
    return sorted(found)


def compare(tool_value, direct) -> str:
    """same, same_values (other shape, same content), same_attributes, opaque or mismatch."""
    expected = to_json(direct)
    if " at 0x" in canonical(expected):
        return "opaque"  # the library object has no readable form, so nothing can be compared
    if same_shape_equal(tool_value, direct):
        return "same"
    both_lists = isinstance(tool_value, list) and isinstance(direct, (list, tuple))
    if not both_lists and leaves(tool_value) == leaves(expected):
        return "same_values"
    if isinstance(tool_value, dict) and tool_value and not isinstance(direct, (collections.abc.Mapping, list, tuple)):
        shared = [k for k in tool_value if hasattr(direct, k)]
        if len(shared) * 2 >= len(tool_value) and \
                all(same_shape_equal(tool_value[k], materialize(getattr(direct, k))) for k in shared):
            return "same_attributes"
    return "mismatch"


def direct_namespace(expression: str, values: dict) -> dict:
    """Variables for evaluating a direct call: the arguments, safe builtins, imported modules."""
    namespace = {"__builtins__": {n: getattr(builtins, n) for n in SAFE_BUILTINS}, **copy.deepcopy(values)}
    for node in ast.walk(ast.parse(expression, mode="eval")):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            continue
        parts = []
        while isinstance(node, ast.Attribute):
            parts.insert(0, node.attr)
            node = node.value
        if not isinstance(node, ast.Name) or node.id in namespace["__builtins__"] or node.id in values:
            continue
        parts.insert(0, node.id)
        namespace.setdefault(node.id, importlib.import_module(node.id))
        for i in range(2, len(parts) + 1):  # packaging.version.Version: import packaging.version too
            try:
                importlib.import_module(".".join(parts[:i]))
            except ImportError:
                break
    return namespace


def run_direct(expression: str, values: dict) -> dict:
    try:
        with time_limit(SAMPLE_SECONDS):
            return {"value": materialize(eval(expression, direct_namespace(expression, values)))}  # noqa: S307
    except SampleTimeout as e:
        return {"error": str(e), "broken": False}
    except Exception as e:  # noqa: BLE001  (a library raising on a bad sample is normal)
        return {"error": f"{type(e).__name__}: {e}"[:300], "broken": isinstance(e, BROKEN_CALL_ERRORS),
                "type_error": isinstance(e, TypeError)}


def run_tool(mcp, name: str, arguments: dict) -> dict:
    """Call the tool the way a model would, through FastMCP's argument validation."""
    try:
        with time_limit(SAMPLE_SECONDS):
            result = asyncio.run(mcp.call_tool(name, copy.deepcopy(arguments)))
    except SampleTimeout as e:
        return {"error": str(e), "crash": True}
    except Exception as e:  # noqa: BLE001  (FastMCP wraps the tool's exception in a ToolError)
        cause = e.__cause__ or e
        return {"error": f"{type(cause).__name__}: {cause}"[:300], "crash": not isinstance(cause, ValueError)}
    structured = result[1] if isinstance(result, tuple) else None
    if structured is not None:
        return {"value": structured["result"] if set(structured) == {"result"} else structured}
    blocks = result[0] if isinstance(result, tuple) else result
    text = "".join(b.text for b in blocks if b.type == "text")
    try:
        return {"value": json.loads(text)}
    except json.JSONDecodeError:
        return {"error": f"output is not JSON: {text[:200]}", "crash": True}


def check(request: dict) -> dict:
    name = request["tool_name"]
    report = {"ok": False, "stage": None, "error": None, "samples": [], "verified": False}

    def failed(stage: str, error: str) -> dict:
        return report | {"stage": stage, "error": error[:1500]}

    try:
        spec = importlib.util.spec_from_file_location(f"generated_{name}", request["tool_file"])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module  # pydantic looks up TypedDicts through sys.modules
        spec.loader.exec_module(module)
        function = getattr(module, name)
    except BaseException as e:  # noqa: BLE001  (generated code may raise anything, even SystemExit)
        return failed("loads", f"{type(e).__name__}: {e}")

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("check", log_level="ERROR")
    try:
        mcp.add_tool(function)
        listed = asyncio.run(mcp.list_tools())[0]
    except Exception as e:  # noqa: BLE001
        return failed("fastmcp", f"{type(e).__name__}: {e}")
    report |= {"description": listed.description, "input_schema": listed.inputSchema}
    agreed = [p["name"] for p in request["parameters"]]
    have = list(listed.inputSchema.get("properties", {}))
    if sorted(agreed) != sorted(have):
        return failed("fastmcp", f"the function's parameters must be {agreed}, but they are {have}")
    if not (listed.description or "").strip():
        return failed("fastmcp", "the function needs a docstring: a model reads it as the description")

    signature = inspect.signature(function)
    for sample in request["samples"]:
        try:
            bound = signature.bind(**sample)
        except TypeError as e:
            return failed("spec", f"sample {canonical(sample)} does not fit the parameters: {e}")
        bound.apply_defaults()
        values = dict(bound.arguments)
        direct = run_direct(request["direct_call"], values)
        again = run_direct(request["direct_call"], values)
        tool = run_tool(mcp, name, sample)
        row = {"arguments": sample, "tool": tool.get("value", tool.get("error")),
               "direct": canonical(to_json(direct["value"])) if "value" in direct else direct["error"]}
        if "error" in direct and "error" in tool:
            row["result"] = "both_error"
        elif "error" in direct:
            row["result"] = "mismatch"
            row["why"] = f"the direct library call raised {direct['error']}, but the tool returned {canonical(tool['value'])[:300]}"
        elif "error" in tool:
            row["result"] = "crash" if tool["crash"] else "mismatch"
            row["why"] = f"the tool raised {tool['error']}, but the direct library call returned {row['direct'][:300]}"
        elif "error" not in again and canonical(to_json(again["value"])) != canonical(to_json(direct["value"])):
            row["result"] = "unstable"  # e.g. the current time: two direct calls already differ
        else:
            row["result"] = compare(tool["value"], direct["value"])
            if row["result"] == "mismatch":
                row["why"] = f"the tool returned {canonical(tool['value'])[:300]}, but the direct library call returned {row['direct'][:300]}"
        row["direct_error"] = direct if "error" in direct else None
        report["samples"].append(row)

    rows = report["samples"]
    broken = [r for r in rows if r["direct_error"] and r["direct_error"].get("broken")]
    worked = [r for r in rows if not r["direct_error"]]
    if broken:
        return failed("spec", f"the direct_call expression is wrong: {broken[0]['direct_error']['error']}")
    if not worked:
        errors = {r["direct_error"]["error"] for r in rows}
        return failed("spec", "the direct call failed on every sample, so nothing can be compared. "
                              f"Errors: {sorted(errors)[:3]}. Use samples that are valid for the library.")
    for r in rows:
        r.pop("direct_error")
    crashes = [r for r in rows if r["result"] == "crash"]
    if crashes:
        return failed("runs", "\n".join(f"Input {canonical(r['arguments'])}: {r['why']}" for r in crashes[:3]))
    mismatches = [r for r in rows if r["result"] == "mismatch"]
    if mismatches:
        return failed("differential", "\n".join(f"Input {canonical(r['arguments'])}: {r['why']}" for r in mismatches[:3]))
    same = [r for r in rows if r["result"].startswith("same")]
    needed = 2 if agreed else 1
    unverifiable = [r for r in rows if r["result"] in ("unstable", "opaque")]
    if len(same) < needed and not unverifiable:
        return failed("spec", f"only {len(same)} samples gave a result to compare; {needed} are needed. "
                              "Add valid samples with different inputs.")
    return report | {"ok": True, "stage": "ok", "verified": len(same) >= needed}


def main() -> None:
    request = json.load(sys.stdin)
    real_stdout = sys.stdout
    # generated code must not be able to write into our result
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        report = check(request)
    real_stdout.write(json.dumps(report, default=str))
    real_stdout.flush()
    os._exit(0)  # a leftover thread from generated code must not keep the process alive


if __name__ == "__main__":
    main()
