"""Tests for `repo2tools usability`: a real generated tool set, a scripted task writer and rewriter, and a scripted small model."""

import ast
import asyncio
import json
import re
import subprocess
from types import SimpleNamespace

import pytest

from helpers import ScriptedLLM, options
from repo2tools.synthesis import pipeline, usability
from test_traces import completion

LIBRARY = '''"""Product codes such as AB-12."""
import re


def normalize(code: str) -> str:
    """Upper-case a product code. Raises ValueError if it is not one."""
    if not re.fullmatch(r"[A-Za-z]{2}-[0-9]+", code):
        raise ValueError(f"not a product code: {code!r}")
    return code.upper()


def label(code: str) -> str:
    """The text printed for a product code."""
    return f"[{normalize(code)}]"


def describe(code: str) -> str:
    """A sentence about a product code."""
    return f"Product {normalize(code)} is in stock."
'''
# what each tool's docstring says, and the word the scripted model looks for in a request
DOCS = {"normalize_code": "Tidy a product code. code: a product code.",
        "label_code": "Label maker tool. code: a product code.",
        "describe_code": "A sentence about a product code, for example for a sticker. code: a product code."}
SAMPLES = {"normalize_code": ["ab-12", "Cd-7", "zz-100", "ef-9"], "label_code": ["qq-5", "RS-88", "tu-3", "vw-41"],
           "describe_code": ["gh-6", "ij-11", "kl-2", "mn-77"]}
REQUESTS = {"normalize_code": "Please tidy the product code {}.", "label_code": "Print a sticker for {}.", "describe_code": "Write a sentence about {}."}
WORDS = ("tidy", "sticker", "sentence")


class SmallModel:
    """Calls the offered tool whose name has the request's key word, else the first whose description has it, else no tool."""

    def __init__(self):
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        last = kwargs["messages"][-1]
        if last["role"] == "tool":
            return completion(content=last["content"])
        word = next(w for w in WORDS if w in last["content"])
        value = re.search(r"[A-Za-z]{2}-[0-9]+", last["content"]).group(0)
        offered = [t["function"] for t in kwargs.get("tools") or []]
        for tool in [t for t in offered if word in t["name"]] + [t for t in offered if word in t["description"].lower()]:
            return completion(calls=[(tool["name"], {"code": value})])
        return completion(content='"unknown"')


def task_script(overrides=None):
    script = {("task", f"{tool}-{i}"): [json.dumps({"task": REQUESTS[tool].format(value)})] for tool, values in SAMPLES.items() for i, value in enumerate(values)}
    return script | (overrides or {})


@pytest.fixture
def toolset(tmp_path, monkeypatch):
    """Three generated tools over a tiny library. The scripted model cannot find label_code: nothing in it says "sticker"."""
    root = tmp_path / "root"
    monkeypatch.setattr(pipeline, "ROOT", root)
    monkeypatch.setattr(pipeline, "CACHE", root / ".cache")
    root.mkdir()
    repo = tmp_path / "repo" / "codes"
    (repo / "codes").mkdir(parents=True)
    (repo / "codes" / "__init__.py").write_text(LIBRARY)
    (repo / "pyproject.toml").write_text('[project]\nname = "codes"\ndependencies = []\n')
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo)]
    for command in (["init", "--quiet"], ["add", "."], ["commit", "--quiet", "-m", "init"]):
        subprocess.run([*git, *command], check=True)
    script = {("propose", "codes"): [json.dumps([{"function": f"codes.{name.split('_')[0]}", "name": name, "description": DOCS[name]} for name in DOCS])]}
    for name, values in SAMPLES.items():
        function = name.split("_")[0]
        script[("spec", name)] = [json.dumps({"parameters": [{"name": "code", "type": "string", "description": "a product code", "required": True}],
                                              "direct_call": f"codes.{function}(code)", "samples": [{"code": v} for v in values]})]
        script[("code", name)] = [f'```python\nimport codes\n\n\ndef {name}(code: str) -> str:\n    """{DOCS[name]}"""\n    return codes.{function}(code)\n```']
    report = asyncio.run(pipeline.generate(options(repo), llm=ScriptedLLM(script)))
    assert report["accepted"] == 3, [(t["name"], t["attempts"]) for t in report["tools"]]
    return root / "toolsets" / "generated" / "codes-test", root


def make_tasks(toolset, overrides=None):
    folder, _ = toolset
    writer = ScriptedLLM(task_script(overrides))
    return asyncio.run(usability.make_tasks(folder, writer)), writer


def repair(toolset, replies, rounds=3):
    folder, root = toolset
    make_tasks(toolset)
    writer, model = ScriptedLLM({("rewrite", "label_code"): replies}), SmallModel()
    summary = asyncio.run(usability.repair_set(folder, model, "small", writer, rounds=rounds))
    return summary, writer, root / "toolsets" / "generated" / "codes-test-usable"


GOOD = json.dumps({"name": "make_sticker_text", "description": "Return the text of the sticker for a product code.\n code: the product code, e.g. ab-12."})


# --- tasks -----------------------------------------------------------------------------------


def test_tasks_are_written_from_the_library_not_from_the_tool(toolset):
    tasks, writer = make_tasks(toolset)
    assert len(tasks) == 12 and {t["tool"] for t in tasks} == set(DOCS)
    assert [t["split"] for t in tasks if t["tool"] == "label_code"] == ["dev", "test", "dev", "test"]
    first = next(t for t in tasks if t["id"] == "label_code-0")
    assert first["arguments"] == {"code": "qq-5"} and first["expected"] == "[QQ-5]" and first["task"] == "Print a sticker for qq-5."
    prompts = json.dumps([m for _, _, m in writer.chats])
    assert "codes.label(code)" in prompts and "The text printed for a product code." in prompts  # the library side
    assert "label_code" not in prompts and "Label maker tool" not in prompts  # never the tool's name or description


def test_a_task_must_contain_every_input_and_not_the_result(toolset):
    bad = {("task", "label_code-1"): [json.dumps({"task": "Print a sticker for the code."}), json.dumps({"task": "Print a sticker for RS-88."})],
           ("task", "label_code-2"): [json.dumps({"task": "Print a sticker for tu-3, it is [TU-3]."})],
           ("task", "label_code-3"): [json.dumps({"task": "Call label_code on vw-41."})]}
    tasks, writer = make_tasks(toolset, bad)
    assert [t["id"] for t in tasks if t["tool"] == "label_code"] == ["label_code-0", "label_code-1"]  # one corrected, two dropped
    retry = next(m for stage, subject, m in writer.chats if subject == "label_code-1" and len(m) > 2)
    assert "RS-88" in retry[-1]["content"] and "must appear exactly" in retry[-1]["content"]


def test_task_problem():
    assert usability.task_problem("Is 1.5 allowed by >=1.0,<2.0? Answer true or false.", "check", {"spec": ">=1.0,<2.0", "version": "1.5", "pre": None}, True) is None
    assert "must appear exactly" in usability.task_problem("Is 1.5 allowed by >=1.0, <2.0?", "check", {"spec": ">=1.0,<2.0", "version": "1.5"}, True)
    assert usability.task_problem("Which tags fit Python 3 9 with cp39?", "list_wheel_tags", {"python_version": [3, 9], "interpreter": "cp39"}, []) is None
    assert "gives away" in usability.task_problem("Normalize Django_App to django-app.", "canon", {"name": "Django_App"}, "django-app")
    assert usability.task_problem("Normalize the version 1.0.1 please.", "canon", {"version": "1.0.1"}, "1.0.1") is None  # the result is the input


# --- judging a run ---------------------------------------------------------------------------


SCHEMA = {"properties": {"spec": {"type": "string"}, "version": {"type": "string"}, "prereleases": {"default": None}}}
TASK = {"tool": "contains", "arguments": {"spec": ">=1.0,<2.0", "version": "1.5", "prereleases": None}, "expected": True}


def call(tool, arguments, output, ok=True):
    return {"shown": tool, "tool": tool, "arguments": arguments, "ok": ok, "output": output}


def test_same_arguments_fills_defaults_and_ignores_spaces():
    assert usability.same_arguments({"spec": ">=1.0, <2.0", "version": "1.5"}, TASK["arguments"], SCHEMA)
    assert not usability.same_arguments({"spec": ">=1.0", "version": "1.5"}, TASK["arguments"], SCHEMA)
    assert not usability.same_arguments({"spec": ">=1.0,<2.0", "version": "1.5", "prereleases": True}, TASK["arguments"], SCHEMA)


def test_judge_names_what_went_wrong():
    judge = lambda calls, answer=True, task=TASK: usability.judge(task, calls, answer, SCHEMA)["outcome"]  # noqa: E731
    assert judge([call("contains", {"spec": ">=1.0,<2.0", "version": "1.5"}, True)]) == "right"
    assert judge([]) == "no_call"
    assert judge([call("other", {"x": 1}, True)]) == "wrong_tool"
    assert judge([call("contains", {"spec": ">=1.0,<2.0"}, "missing version", ok=False)]) == "bad_arguments"
    # a true/false result that matches by luck is not a right call
    assert judge([call("contains", {"spec": ">=0.1", "version": "1.5"}, True)]) == "bad_arguments"
    # any other result may be reached with other arguments
    text = TASK | {"expected": "1.5"}
    assert judge([call("contains", {"spec": ">=1", "version": "1.5"}, "1.5")], task=text) == "right"
    assert judge([call("contains", {"spec": ">=1", "version": "1.5"}, "1.6")], task=text) == "bad_arguments"
    verdict = usability.judge(TASK, [], True, SCHEMA)
    assert verdict["answer_right"] and not verdict["right_call"]  # a guessed answer is not a use of the tool


def test_apply_rewrite_changes_only_name_and_docstring():
    code = 'import codes\n\n\ndef label_code(code: str) -> str:\n    """Old text.\n\n    code: a code.\n    """\n    return codes.label(code)\n'
    description = 'Sticker text, e.g. "ab-12" gives "[AB-12]". A backslash \\ and """ stay. Ends with "x"'
    new = usability.apply_rewrite(code, "label_code", "make_sticker_text", description)
    function = ast.parse(new).body[1]
    assert function.name == "make_sticker_text" and ast.get_docstring(function, clean=False) == description
    assert new.startswith("import codes\n\n\ndef make_sticker_text(code: str) -> str:\n") and new.endswith("    return codes.label(code)\n")
    assert "Old text" not in new
    with pytest.raises(ValueError):
        usability.apply_rewrite("def f(x: int) -> int:\n    return x\n", "f", "g", "A description of twenty chars.")


def test_read_rewrite():
    taken = {"normalize_code"}
    assert usability.read_rewrite(GOOD, taken)[0] == {"name": "make_sticker_text", "description": "Return the text of the sticker for a product code. code: the product code, e.g. ab-12."}
    assert "taken" in usability.read_rewrite(json.dumps({"name": "normalize_code", "description": "x" * 30}), taken)[1]
    assert "snake_case" in usability.read_rewrite(json.dumps({"name": "MakeSticker", "description": "x" * 30}), taken)[1]
    assert "characters" in usability.read_rewrite(json.dumps({"name": "ok_name", "description": "short"}), taken)[1]
    assert usability.read_rewrite("no json here", taken)[0] is None


# --- check and repair, end to end --------------------------------------------------------------


def test_check_finds_the_tool_the_model_cannot_use(toolset):
    folder, root = toolset
    make_tasks(toolset)
    summary = asyncio.run(usability.check_set(folder, SmallModel(), "small"))
    tools = summary["tools"]
    assert tools["normalize_code"]["alone"]["right"] == 4 and tools["normalize_code"]["set"]["right"] == 4
    assert tools["label_code"]["alone"] == {"tasks": 4, "right": 0, "outcomes": {"no_call": 4}, "instead": {}}
    assert tools["label_code"]["set"]["outcomes"] == {"wrong_tool": 4} and tools["label_code"]["set"]["instead"] == {"describe_code": 4}
    assert summary["totals"]["set"]["right"] == 8 and summary["totals"]["none"]["answer_right"] == 0
    text = (root / "out" / "generated" / "codes-test" / "usability.md").read_text()
    assert "| `label_code` | 0 of 4 | 0 of 4 |" in text and "`describe_code` 4" in text


def test_repair_renames_the_tool_and_measures_through_the_new_server(toolset):
    folder, root = toolset
    summary, writer, new = repair(toolset, [GOOD])
    assert summary["rewritten"] == 1 and summary["tools_with_failed_dev_task"] == 1 and summary["renamed"] == {"label_code": "make_sticker_text"}
    measures = {m["measure"]: (m["before"], m["after"]) for m in summary["measures"]}
    assert measures["Tool alone, held-out tasks"] == ([4, 6], [6, 6]) and measures["In the whole set, held-out tasks"] == ([4, 6], [6, 6])
    assert summary["per_tool"]["label_code"] == {"before": [0, 8], "after": [8, 8]} and summary["worse"] == []
    # the new set: the file is renamed, only name and docstring differ, and the old set is untouched
    code = (new / "tools" / "make_sticker_text.py").read_text()
    assert "def make_sticker_text(code: str) -> str:" in code and "return codes.label(code)" in code and "sticker for a product code" in code
    assert not (new / "tools" / "label_code.py").exists() and (folder / "tools" / "label_code.py").exists()
    manifest = json.loads((new / "manifest.json").read_text())
    assert manifest["set"] == "codes-test-usable" and manifest["renamed_tools"] == {"label_code": "make_sticker_text"}
    assert sorted(t["name"] for t in manifest["tools"]) == ["describe_code", "make_sticker_text", "normalize_code"]
    report = json.loads((root / "out" / "generated" / "codes-test-usable" / "report.json").read_text())
    renamed = next(t for t in report["tools"] if t["name"] == "make_sticker_text")
    assert renamed["check"]["ok"] and all(r["result"] == "same" for r in renamed["check"]["samples"])  # checked against the library again
    # the rewriter saw what the model did on the repair tasks, and never a held-out task
    prompt = writer.chats[0][2][-1]["content"]
    assert "Print a sticker for qq-5." in prompt and "made no tool call" in prompt and "called `describe_code`" in prompt
    assert "RS-88" not in json.dumps([m for _, _, m in writer.chats]) and "vw-41" not in json.dumps([m for _, _, m in writer.chats])
    text = (root / "out" / "generated" / "codes-test-usable" / "usability_repair.md").read_text()
    assert "`label_code` is now `make_sticker_text`" in text and "**1 of 1 tools with a failed task were rewritten**" in text


def test_a_rewrite_that_does_not_help_is_not_kept(toolset):
    folder, root = toolset
    useless = json.dumps({"name": "label_text", "description": "Return the label text for a product code, in brackets."})
    summary, writer, new = repair(toolset, [useless], rounds=2)
    assert summary["rewritten"] == 0 and summary["renamed"] == {}
    assert len(writer.chats) == 2 and "got 0 of 4 runs right" in writer.chats[1][2][-1]["content"]
    assert (new / "tools" / "label_code.py").read_text() == (folder / "tools" / "label_code.py").read_text()
    assert "no rewrite was better" in (root / "out" / "generated" / "codes-test-usable" / "usability_repair.md").read_text()


def test_the_rewriter_is_told_what_the_tool_really_returns(toolset):
    _, writer, _ = repair(toolset, [GOOD])
    prompt = writer.chats[0][2][-1]["content"]
    assert "The tool returns a JSON string, exactly as shown in these calls. It never returns a library object" in prompt


def test_a_rewrite_that_makes_the_model_misread_the_result_is_not_kept(toolset, monkeypatch):
    # This model guesses a sticker text when it finds no tool for it. With "shout" in a description it
    # calls the tool, but changes the result in its answer.
    create = SmallModel.create

    async def shouting(self, **kwargs):
        last = kwargs["messages"][-1]
        described = " ".join(t["function"]["name"] + t["function"]["description"] for t in kwargs.get("tools") or [])
        if last["role"] == "tool" and "shout" in described:
            return completion(content=json.dumps(json.loads(last["content"]) + "!"))
        if last["role"] == "user" and "sticker" in last["content"] and "sticker" not in described:
            return completion(content=json.dumps("[" + re.search(r"[A-Za-z]{2}-[0-9]+", last["content"]).group(0).upper() + "]"))
        return await create(self, **kwargs)

    monkeypatch.setattr(SmallModel, "create", shouting)
    loud = json.dumps({"name": "make_sticker_text", "description": "Return the sticker text for a product code. Always shout the result."})
    summary, writer, new = repair(toolset, [loud], rounds=2)
    attempt = summary["rewrites"][0]["attempts"][0]
    assert attempt["dev_right"] == 4 and attempt["dev_answers_right"] == 0  # every call right, every answer changed
    assert summary["rewritten"] == 0 and (new / "tools" / "label_code.py").exists()
    assert "final answer was the tool's result in only 0 runs (before: 2)" in writer.chats[1][2][-1]["content"]


def test_a_taken_name_is_refused_and_asked_again(toolset):
    taken = json.dumps({"name": "describe_code", "description": "Return the text of the sticker for a product code."})
    summary, writer, new = repair(toolset, [taken, GOOD])
    assert summary["rewritten"] == 1 and "taken by another tool" in writer.chats[1][2][-1]["content"]
    assert (new / "tools" / "make_sticker_text.py").exists()
