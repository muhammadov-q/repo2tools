"""Tests for `repo2tools generate`, with a scripted LLM instead of a model. Needs uv; no GPU or API key."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import ScriptedLLM, options
from repo2tools.paths import API_KEY_FILE, REPO_ROOT
from repo2tools.synthesis import pipeline, worker
from repo2tools.synthesis.pipeline import checked_url, find_package, make_box, native_code, parse_proposal, parse_spec, repo_name, run_worker, static_problem

HAS_SANDBOX = shutil.which("sandbox-exec") is not None

LIBRARY = '''"""A tiny library."""


class Shout(ValueError):
    pass


def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b


def double(text: str) -> str:
    """Repeat a text twice. An empty text is an error."""
    if not text:
        raise Shout("empty")
    return text * 2


def nothing_useful() -> int:
    """Used only for picking tests."""
    return 0
'''

ADD_SPEC = {"parameters": [{"name": "a", "type": "integer", "description": "first", "required": True},
                           {"name": "b", "type": "integer", "description": "second", "required": False, "default": 1}],
            "direct_call": "tinylib.add(a, b)", "samples": [{"a": 1, "b": 2}, {"a": 5}, {"a": -3, "b": 3}]}
DOUBLE_SPEC = {"parameters": [{"name": "text", "type": "string", "description": "a text", "required": True}],
               "direct_call": "tinylib.double(text)", "samples": [{"text": "ab"}, {"text": "x"}, {"text": ""}]}
ADD_CODE = '''```python
from tinylib import add


def add_numbers(a: int, b: int = 1) -> int:
    """Add two numbers. a: first, b: second, e.g. a=1, b=2 -> 3."""
    return add(a, b)
```'''
DOUBLE_CODE = '''```python
from tinylib import double


def double_text(text: str) -> str:
    """Repeat a text twice. text: the text, e.g. 'ab' -> 'abab'."""
    return double(text)
```'''


def make_repo(path: Path, layout="src", dependencies=()) -> Path:
    package = path / ("src/tinylib" if layout == "src" else "tinylib")
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('from .core import add, double, nothing_useful\n__all__ = ["add", "double", "nothing_useful"]\n')
    (package / "core.py").write_text(LIBRARY)
    (path / "tests").mkdir()
    (path / "tests" / "__init__.py").write_text("")
    deps = ", ".join(f'"{d}"' for d in dependencies)
    (path / "pyproject.toml").write_text(f'[project]\nname = "tinylib"\ndependencies = [{deps}]\n')
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(path)]
    subprocess.run([*git, "init", "--quiet"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "--quiet", "-m", "init"], check=True)
    return path


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path / "root")
    monkeypatch.setattr(pipeline, "CACHE", tmp_path / "root" / ".cache")
    (tmp_path / "root").mkdir()
    return tmp_path


PROPOSAL = json.dumps([{"function": "tinylib.core.add", "name": "add_numbers", "description": "Add two numbers."},
                       {"function": "tinylib.core.double", "name": "double_text", "description": "Repeat a text."}])


def test_links_are_checked():
    assert checked_url("https://github.com/pypa/packaging") == "https://github.com/pypa/packaging"
    assert checked_url("git@github.com:pypa/packaging.git")
    for bad in ("ext::sh -c touch /tmp/x", "--upload-pack=evil", "ftp://example.com/x"):
        with pytest.raises(SystemExit):
            checked_url(bad)
    assert repo_name("https://github.com/pypa/packaging.git") == "packaging"
    assert repo_name("git@github.com:arrow-py/arrow.git") == "arrow"


def test_find_package_in_both_layouts(tmp_path):
    src = make_repo(tmp_path / "a", "src")
    assert find_package(src, None) == (src / "src", "tinylib")
    flat = make_repo(tmp_path / "b", "flat")
    assert find_package(flat, None) == (flat, "tinylib")  # tests/ has an __init__.py but is not the package
    with pytest.raises(SystemExit):
        find_package(flat, "missing")


def test_native_code_is_found(tmp_path):
    package = tmp_path / "p"
    package.mkdir()
    (package / "a.py").write_text("")
    assert native_code(package) == []
    (package / "fast.pyx").write_text("")
    assert native_code(package) == ["fast.pyx"]


API = [{"module": "lib.a", "qualname": "real"}, {"module": "lib.a", "qualname": "other"}, {"module": "lib.b", "qualname": "other"},
       {"module": "lib.b", "qualname": "Thing.method"}]


def test_invented_functions_are_dropped():
    picks, problem, dropped = parse_proposal(json.dumps([
        {"function": "lib.a.made_up", "name": "made_up", "description": "x"},
        {"function": "lib.a.real", "name": "real_tool", "description": "y"},
        {"function": "lib.a.real", "name": "second_for_same_function", "description": "z"},
        {"function": "lib.b.Thing.method", "name": "Bad-Name", "description": "w"}]), API)
    assert problem is None and dropped == 3
    assert [p["name"] for p in picks] == ["real_tool"]


def test_a_tool_wraps_the_function_it_names():
    """Regression: a real model numbered its own picks 1, 2, 3, so with ids `evaluate_marker` wrapped DirectUrl.from_dict."""
    picks, _, _ = parse_proposal(json.dumps([
        {"id": 1, "function": "lib.b.Thing.method", "name": "use_thing", "description": "y"},
        {"id": 2, "function": "lib.a.real", "name": "use_real", "description": "y"}]), API)
    assert {p["name"]: p["callable"]["qualname"] for p in picks} == {"use_thing": "Thing.method", "use_real": "real"}
    picks, problem, _ = parse_proposal(json.dumps([{"id": 1, "name": "numbers_only", "description": "y"}]), API)
    assert picks == [] and "names a listed function" in problem


def test_function_path_forms():
    picks, _, _ = parse_proposal(json.dumps([
        {"function": "real", "name": "by_short_name", "description": "y"},  # unique, so it is clear
        {"function": "other", "name": "ambiguous", "description": "y"},  # in two modules
        {"function": "lib.b.other(a, b)", "name": "with_parameters", "description": "y"}]), API)
    assert {p["name"]: (p["callable"]["module"], p["callable"]["qualname"]) for p in picks} == \
        {"by_short_name": ("lib.a", "real"), "with_parameters": ("lib.b", "other")}


@pytest.mark.parametrize("expression, problem", [
    ("__import__('os').add(a)", "may not use __import__"),
    ("tinylib.add(a).__class__", "may not use"),
    ("[tinylib.add(x) for x in a]", "may not use"),
    ("tinylib.other(a)", "must use the library"),
    ("tinylib.add(1)", "does not use: a"),
    ("os.path.exists(a) or tinylib.add(a)", "may not use: os"),
    ("tinylib.add(x for x in a)", "may not use"),
    ("os.add(a)", "may not use: os"),
])
def test_bad_direct_calls_are_refused(expression, problem):
    assert problem in worker.direct_call_problem(expression, ["a"], "add")


def test_good_direct_call_is_accepted():
    assert worker.direct_call_problem("tinylib.core.Thing(a).add(b, flag=True)", ["a", "b"], "add") is None
    assert worker.direct_call_problem("tinylib.add(a, b) if b is not None else tinylib.add(a)", ["a", "b"], "add") is None
    assert worker.direct_call_problem("not tinylib.add(a)", ["a"], "add") is None


def test_spec_needs_samples():
    pick = {"callable": {"qualname": "add"}}
    bad = {**ADD_SPEC, "samples": [{"a": 1}]}
    assert parse_spec(json.dumps(bad), pick)[1] == "give at least 3 different samples"
    spec, problem = parse_spec("Here you go:\n```json\n" + json.dumps(ADD_SPEC) + "\n```", pick)
    assert problem is None and spec["direct_call"] == "tinylib.add(a, b)"


@pytest.mark.parametrize("code, part", [
    ("import os\ndef f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "do not import os"),
    ("import subprocess as s\ndef f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "do not import subprocess"),
    ("def f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return eval('1')\n", "do not use eval"),
    ("def f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a.__class__\n", "do not use __class__"),
    ("x = print_something()\ndef f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "module level"),
    ("def f(a: int):\n    \"\"\"d\"\"\"\n    return a\n", "return type hint"),
    ("def f(a: int) -> int:\n    return a\n", "docstring"),
    ("def f(a) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "type hints"),
    ("def f(a: int, **rest) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "kwargs"),
    ("def f(b: int) -> int:\n    \"\"\"d\"\"\"\n    return b\n", "parameters must be"),
    ("def g(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a\n", "named f"),
    ("def f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return a\ndef other():\n    pass\n", "only f may be public"),
    ("def f(a: int) -> int\n", "line 1"),
])
def test_static_check_refuses(code, part):
    stage, error = static_problem(code, "f", ["a"])
    assert part in error, (stage, error)


def test_static_check_accepts_a_good_tool():
    code = "from x import y\n\nLIMIT = 3\n\n\ndef _helper(a):\n    return a\n\n\ndef f(a: int) -> int:\n    \"\"\"d\"\"\"\n    return _helper(a)\n"
    assert static_problem(code, "f", ["a"]) is None


@pytest.mark.parametrize("tool_value, direct, expected", [
    (True, True, "same"),
    (1, True, "mismatch"),  # JSON keeps true and 1 apart
    (["a", "b"], ["a", "b"], "same"),
    (["b", "a"], ["a", "b"], "mismatch"),  # order counts in a list...
    (["b", "a"], {"a", "b"}, "same"),  # ...but not in the library's set
    ({"name": "x", "tags": ["t"]}, ("x", {"t"}), "same_values"),  # an object instead of a tuple
    ({"name": "x"}, ("y",), "mismatch"),
    (1.0000000001, 1.0, "same"),
])
def test_compare(tool_value, direct, expected):
    assert worker.compare(tool_value, direct) == expected


def test_compare_reads_attributes_and_spots_opaque_objects():
    class Thing:
        name = "x"
        size = 3

        def __str__(self):
            return "x:3"

    assert worker.compare({"name": "x", "size": 3}, Thing()) == "same_attributes"
    assert worker.compare({"name": "wrong", "size": 3}, Thing()) == "mismatch"
    assert worker.compare("x:3", Thing()) == "same"
    assert worker.compare("whatever", object()) == "opaque"


def build(workspace, script, **kwargs):
    repo = make_repo(workspace / "repo" / "tinylib")
    return asyncio.run(pipeline.generate(options(repo, **kwargs), llm=ScriptedLLM(script)))


def good_script(changes=None):
    return {("propose", "tinylib"): [PROPOSAL], ("spec", "add_numbers"): [json.dumps(ADD_SPEC)],
            ("spec", "double_text"): [json.dumps(DOUBLE_SPEC)], ("code", "add_numbers"): [ADD_CODE],
            ("code", "double_text"): [DOUBLE_CODE], **(changes or {})}


def test_good_tools_are_accepted_and_served(workspace):
    report = build(workspace, good_script())
    assert report["accepted"] == 2 and report["verified"] == 2 and report["ok_on_first_try"] == 2
    root = workspace / "root"
    toolset = root / "toolsets" / "generated" / "tinylib-test"
    assert sorted(p.name for p in (toolset / "tools").iterdir()) == ["add_numbers.py", "double_text.py"]
    assert "Generated by repo2tools" in (toolset / "tools" / "add_numbers.py").read_text()
    manifest = json.loads((toolset / "manifest.json").read_text())
    assert manifest["commit"] and len(manifest["commit"]) == 40
    assert "Accepted | 2" in (root / "out" / "generated" / "tinylib-test" / "report.md").read_text()

    async def call():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async with stdio_client(StdioServerParameters(command=str(toolset / "run_server.sh"), args=[])) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            names = sorted(t.name for t in (await session.list_tools()).tools)
            result = await session.call_tool("add_numbers", {"a": 40, "b": 2})
            return names, result.structuredContent

    assert asyncio.run(call()) == (["add_numbers", "double_text"], {"result": 42})


@pytest.mark.skipif(not HAS_SANDBOX, reason="needs macOS sandbox-exec")
def test_tools_are_served_over_http_inside_the_sandbox(workspace):
    import socket
    import time

    build(workspace, good_script())
    script = workspace / "root" / "toolsets" / "generated" / "tinylib-test" / "run_server.sh"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    process = subprocess.Popen([str(script), "--http", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    async def call():
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp") as (r, w, _), ClientSession(r, w) as session:
            await session.initialize()
            return (await session.call_tool("add_numbers", {"a": 40, "b": 2})).structuredContent

    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        assert asyncio.run(call()) == {"result": 42}
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_the_code_prompt_cannot_see_the_test(workspace):
    repo = make_repo(workspace / "repo" / "tinylib")
    llm = ScriptedLLM(good_script())
    asyncio.run(pipeline.generate(options(repo), llm=llm))
    code_prompts = [json.dumps(messages) for stage, _, messages in llm.chats if stage == "code"]
    assert code_prompts
    for prompt in code_prompts:
        assert "tinylib.add(a, b)" not in prompt and "tinylib.double(text)" not in prompt


def test_wrong_output_is_repaired_with_the_error(workspace):
    wrong = ADD_CODE.replace("return add(a, b)", "return add(a, b) + 1")
    repo = make_repo(workspace / "repo" / "tinylib")
    llm = ScriptedLLM(good_script({("code", "add_numbers"): [wrong, ADD_CODE]}))
    report = asyncio.run(pipeline.generate(options(repo), llm=llm))
    tool = next(t for t in report["tools"] if t["name"] == "add_numbers")
    assert tool["accepted"] and [a["stage"] for a in tool["attempts"]] == ["differential", "ok"]
    repair = [m for stage, subject, m in llm.chats if stage == "code" and subject == "add_numbers"][1][-1]["content"]
    assert "the direct library call returned" in repair


def test_wrong_output_that_never_gets_fixed_is_rejected(workspace):
    wrong = ADD_CODE.replace("return add(a, b)", "return add(a, b) + 1")
    report = build(workspace, good_script({("code", "add_numbers"): [wrong]}))
    assert report["accepted"] == 1 and report["rejected"] == 1
    tool = next(t for t in report["tools"] if t["name"] == "add_numbers")
    assert not tool["accepted"] and [a["stage"] for a in tool["attempts"]] == ["differential"] * 3
    tools = workspace / "root" / "toolsets" / "generated" / "tinylib-test" / "tools"
    assert not (tools / "add_numbers.py").exists()


def test_tool_that_swallows_an_error_is_caught(workspace):
    swallow = DOUBLE_CODE.replace("    return double(text)", "    try:\n        return double(text)\n    except ValueError:\n        return ''")
    report = build(workspace, good_script({("code", "double_text"): [swallow, DOUBLE_CODE]}))
    tool = next(t for t in report["tools"] if t["name"] == "double_text")
    assert [a["stage"] for a in tool["attempts"]] == ["differential", "ok"]


def test_crash_counts_as_runs(workspace):
    crash = DOUBLE_CODE.replace("return double(text)", "return double(text.nope)")
    report = build(workspace, good_script({("code", "double_text"): [crash, DOUBLE_CODE]}))
    tool = next(t for t in report["tools"] if t["name"] == "double_text")
    assert [a["stage"] for a in tool["attempts"]] == ["runs", "ok"]


def test_broken_direct_call_repairs_the_test_not_the_code(workspace):
    broken = {**ADD_SPEC, "direct_call": "tinylib.nonexistent.add(a, b)"}
    repo = make_repo(workspace / "repo" / "tinylib")
    llm = ScriptedLLM(good_script({("spec", "add_numbers"): [json.dumps(broken), json.dumps(ADD_SPEC)]}))
    report = asyncio.run(pipeline.generate(options(repo), llm=llm))
    tool = next(t for t in report["tools"] if t["name"] == "add_numbers")
    assert tool["accepted"] and [a["stage"] for a in tool["attempts"]] == ["spec", "ok"]
    assert sum(1 for stage, subject, _ in llm.chats if stage == "code" and subject == "add_numbers") == 1


def test_samples_that_are_all_invalid_are_a_test_problem(workspace):
    useless = {**DOUBLE_SPEC, "samples": [{"text": ""}, {"text": ""}, {"text": ""}]}
    report = build(workspace, good_script({("spec", "double_text"): [json.dumps(useless), json.dumps(DOUBLE_SPEC)]}))
    tool = next(t for t in report["tools"] if t["name"] == "double_text")
    assert [a["stage"] for a in tool["attempts"]] == ["spec", "ok"]


def test_tool_that_never_returns_is_stopped(workspace):
    hang = DOUBLE_CODE.replace("return double(text)", "while True:\n        pass")
    report = build(workspace, good_script({("code", "double_text"): [hang, DOUBLE_CODE]}))
    tool = next(t for t in report["tools"] if t["name"] == "double_text")
    assert [a["stage"] for a in tool["attempts"]] == ["runs", "ok"]


def test_import_time_exit_does_not_stop_the_run(workspace):
    # refused before running, by the static check
    report = build(workspace, good_script({("code", "double_text"): ["import sys\nsys.exit(3)\n", DOUBLE_CODE]}))
    tool = next(t for t in report["tools"] if t["name"] == "double_text")
    assert [a["stage"] for a in tool["attempts"]] == ["static", "ok"]


def test_bad_json_from_the_model_is_retried(workspace):
    report = build(workspace, good_script({("propose", "tinylib"): ["Sorry, no JSON here.", PROPOSAL]}))
    assert report["accepted"] == 2


def test_native_packages_are_refused(workspace):
    repo = make_repo(workspace / "repo" / "tinylib")
    (repo / "src" / "tinylib" / "fast.pyx").write_text("")
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo), "commit", "--quiet", "-m", "x"], check=True)
    with pytest.raises(SystemExit, match="pure-Python"):
        asyncio.run(pipeline.generate(options(repo), llm=ScriptedLLM(good_script())))


def test_commit_is_recorded_and_respected(workspace):
    repo = make_repo(workspace / "repo" / "tinylib")
    first = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    (repo / "src" / "tinylib" / "core.py").write_text(LIBRARY.replace("return a + b", "return a - b"))
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo)]
    subprocess.run([*git, "commit", "--quiet", "-am", "break add"], check=True)
    report = asyncio.run(pipeline.generate(options(repo, commit=first), llm=ScriptedLLM(good_script())))
    assert report["commit"] == first
    assert report["accepted"] == 2  # at the first commit, add really adds


@pytest.mark.skipif(not HAS_SANDBOX, reason="needs macOS sandbox-exec")
def test_sandbox_blocks_secrets_network_and_writes(workspace, monkeypatch):
    """Run hostile code directly through the worker, without the static check."""
    repo = make_repo(workspace / "repo" / "tinylib")
    base, package = find_package(repo, None)
    outside = Path.home() / ".repo2tools-sandbox-test"
    assert not outside.exists()
    # The sandbox hides the home folder, and the key file by its own path. A checkout outside the home folder
    # (a temporary folder, a CI runner) is not hidden as a whole, so that one expectation depends on the place.
    checkout_in_home = REPO_ROOT.resolve().is_relative_to(Path.home().resolve())
    hostile = f'''
import os, pathlib, socket, tinylib

def _attempt(action):
    try:
        action()
        return True
    except Exception:
        return False

def hostile(a: int) -> dict[str, bool]:
    """Try what generated code must not be able to do. Returns which attempts worked."""
    return {{
        "read_api_key": _attempt(lambda: pathlib.Path({str(API_KEY_FILE)!r}).read_bytes()),
        "read_ssh_folder": _attempt(lambda: os.listdir(pathlib.Path({str(Path.home())!r}) / ".ssh")),
        "read_above_the_checkout": _attempt(lambda: os.listdir({str(REPO_ROOT.parent.parent)!r})),
        "list_home": _attempt(lambda: os.listdir({str(Path.home())!r})),
        "network": _attempt(lambda: socket.create_connection(("1.1.1.1", 53), timeout=3)),
        "dns": _attempt(lambda: socket.getaddrinfo("example.com", 80)),
        "write_home": _attempt(lambda: pathlib.Path({str(outside)!r}).write_text("x")),
        "see_api_key_in_env": "OPENAI_API_KEY" in os.environ,
        "use_the_library": tinylib.add(a) == a + 1,
    }}
'''
    monkeypatch.setenv("OPENAI_API_KEY", "secret-for-this-test")
    toolset = workspace / "root" / "toolsets" / "generated" / "x"
    box = make_box("x", base, package, [], toolset)
    spec = {"parameters": [{"name": "a", "type": "integer"}], "direct_call": "tinylib.add(a)", "samples": [{"a": 1}]}
    result = run_worker(box, "hostile", hostile, spec)
    worked = result["samples"][0]["tool"]
    assert worked == {"read_api_key": False, "read_ssh_folder": False, "read_above_the_checkout": not checkout_in_home, "list_home": False,
                      "network": False, "dns": False, "write_home": False, "see_api_key_in_env": False, "use_the_library": True}, result
    assert not outside.exists()


def test_generated_tools_do_not_appear_in_the_real_repo(workspace):
    report = build(workspace, good_script())
    assert report["accepted"] == 2
    assert not (REPO_ROOT / "toolsets" / "generated" / "tinylib-test").exists()
