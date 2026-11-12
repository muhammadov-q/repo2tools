"""Tests for repair_chains.py: a real generated tool set with one dead-end tool, and a scripted LLM."""

import asyncio
import json
import subprocess

import pytest

import generated_to_toolgym
import repair_chains
import repo2tools
from generated_to_toolgym import links
from test_repo2tools import ScriptedLLM, options

LIBRARY = '''"""Product codes such as AB-12."""
import re


class Label:
    """A printed label for a product code."""

    def __init__(self, code: str) -> None:
        self._code = code

    def text(self) -> str:
        """The code on the label."""
        return self._code

    def __str__(self) -> str:
        return f"<Label {self._code}>"


def normalize(code: str) -> str:
    """Upper-case a product code. Raises ValueError if it is not one."""
    if not re.fullmatch(r"[A-Za-z]{2}-[0-9]+", code):
        raise ValueError(f"not a product code: {code!r}")
    return code.upper()


def label(code: str) -> Label:
    """Make a label for a product code."""
    return Label(normalize(code))


def describe(code: str) -> str:
    """A sentence about a product code."""
    return f"Product {normalize(code)} is in stock."
'''


def spec(direct_call, samples):
    return json.dumps({"parameters": [{"name": "code", "type": "string", "description": "a product code", "required": True}],
                       "direct_call": direct_call, "samples": samples})


def code(name, expression):
    return f'```python\nimport codes\n\n\ndef {name}(code: str) -> str:\n    """Tool {name}. code: a product code, e.g. ab-12."""\n    return {expression}\n```'


SAMPLES = {"normalize_code": [{"code": "ab-12"}, {"code": "Cd-7"}, {"code": "zz-100"}],
           "label_code": [{"code": "qq-5"}, {"code": "RS-88"}, {"code": "tu-3"}],
           "describe_code": [{"code": "gh-6"}, {"code": "ij-11"}, {"code": "kl-2"}]}
TYPES = {"normalize_code": {"parameters": {"code": "ProductCode"}, "output": "ProductCode"},
         "label_code": {"parameters": {"code": "ProductCode"}, "output": "ProductCode"},
         "describe_code": {"parameters": {"code": "ProductCode"}, "output": "string"}}
GOOD_SPEC = spec("codes.label(code).text()", SAMPLES["label_code"])
GOOD_CODE = code("label_code", "codes.label(code).text()")


@pytest.fixture
def toolset(tmp_path, monkeypatch):
    """A generated tool set where label_code returns '<Label AB-12>', which no tool accepts, typed and checked."""
    root = tmp_path / "root"
    monkeypatch.setattr(repo2tools, "ROOT", root)
    monkeypatch.setattr(repo2tools, "CACHE", root / ".cache")
    monkeypatch.setattr(generated_to_toolgym, "OUT", root / "out" / "generated")
    root.mkdir()
    repo = tmp_path / "repo" / "codes"
    (repo / "codes").mkdir(parents=True)
    (repo / "codes" / "__init__.py").write_text(LIBRARY)
    (repo / "pyproject.toml").write_text('[project]\nname = "codes"\ndependencies = []\n')
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo)]
    for command in (["init", "--quiet"], ["add", "."], ["commit", "--quiet", "-m", "init"]):
        subprocess.run([*git, *command], check=True)
    script = {("propose", "codes"): [json.dumps([{"function": f"codes.{f}", "name": f"{f}_code", "description": f"Use {f} on a product code."}
                                                 for f in ("normalize", "label", "describe")])],
              ("spec", "normalize_code"): [spec("codes.normalize(code)", SAMPLES["normalize_code"])],
              ("code", "normalize_code"): [code("normalize_code", "codes.normalize(code)")],
              ("spec", "label_code"): [spec("codes.label(code)", SAMPLES["label_code"])],
              ("code", "label_code"): [code("label_code", "str(codes.label(code))")],
              ("spec", "describe_code"): [spec("codes.describe(code)", SAMPLES["describe_code"])],
              ("code", "describe_code"): [code("describe_code", "codes.describe(code)")]}
    report = asyncio.run(repo2tools.generate(options(repo), llm=ScriptedLLM(script)))
    assert report["accepted"] == 3, [(t["name"], t["attempts"]) for t in report["tools"]]
    folder = root / "toolsets" / "generated" / "codes-test"
    dest = tmp_path / "toolgym" / "gym" / "tools" / "mcp_servers" / "catalog"
    dest.mkdir(parents=True)
    summary = asyncio.run(generated_to_toolgym.export(folder, dest, ScriptedLLM({("types", "codes-test"): [json.dumps({"tools": TYPES})]})))
    assert not next(e for e in summary["output_checks"] if e["tool"] == "label_code")["kept"]
    return folder, dest, root


def run_repair(toolset, replies, rounds=2):
    folder, dest, root = toolset
    llm = ScriptedLLM(replies)
    return asyncio.run(repair_chains.repair_set(folder, llm, rounds=rounds)), llm, root / "toolsets" / "generated" / "codes-test-chained"


def test_dead_end_is_found(toolset):
    folder, _, root = toolset
    out = root / "out" / "generated" / "codes-test"
    reports = {t["name"]: t for t in json.loads((out / "report.json").read_text())["tools"]}
    found = repair_chains.find_dead_ends(json.loads((out / "toolgym_types.json").read_text()), json.loads((out / "toolgym_catalog.json").read_text()), reports)
    assert [d.tool for d in found] == ["label_code"]  # describe_code claimed no type, so it is not a dead end
    dead = found[0]
    assert dead.type_name == "ProductCode" and dead.old_outputs[0].startswith("<Label ")
    assert ("normalize_code", "code") in dead.consumers and ("label_code", "code") not in dead.consumers
    assert "ab-12" in dead.examples


def test_repaired_tool_is_checked_again_and_chains(toolset):
    summary, llm, new = run_repair(toolset, {("repair_spec", "label_code"): [GOOD_SPEC], ("repair_code", "label_code"): [GOOD_CODE]})
    folder, dest, root = toolset
    assert summary["repaired"] == 1 and summary["dead_ends"] == 1
    assert "codes.label(code).text()" in (new / "tools" / "label_code.py").read_text()
    assert "str(codes.label(code))" in (folder / "tools" / "label_code.py").read_text()  # the original set is untouched
    manifest = json.loads((new / "manifest.json").read_text())
    assert manifest["set"] == "codes-test-chained" and manifest["repaired_tools"] == ["label_code"]
    assert next(t for t in manifest["tools"] if t["name"] == "label_code")["direct_call"] == "codes.label(code).text()"
    # the request tells the model what is wrong and what the library offers
    request = next(m for stage, _, m in llm.chats if stage == "repair_spec")[-1]["content"]
    assert "<Label " in request and "normalize_code" in request and "Label.text" in request
    # the code writer is told the output form, but never sees the test
    code_prompt = json.dumps(next(m for stage, _, m in llm.chats if stage == "repair_code"))
    assert "ProductCode" in code_prompt and ".text()" not in code_prompt
    # typed again, the repaired set has the link that was missing
    again = asyncio.run(generated_to_toolgym.export(new, dest, ScriptedLLM({("types", "codes-test-chained"): [json.dumps({"tools": TYPES})]})))
    assert next(e for e in again["output_checks"] if e["tool"] == "label_code")["kept"]
    catalog = dest / "repo2tools_codes_test_chained"
    pairs = {(a, b) for a, b, _ in links(json.loads((catalog / "mcp_server.json").read_text()), json.loads((catalog / "types.json").read_text()))}
    assert ("label_code", "normalize_code") in pairs


def test_a_repair_that_is_still_a_dead_end_is_not_kept(toolset):
    same = spec("codes.label(code)", SAMPLES["label_code"])
    summary, llm, new = run_repair(toolset, {("repair_spec", "label_code"): [same], ("repair_code", "label_code"): [code("label_code", "str(codes.label(code))")]})
    folder = toolset[0]
    assert summary["repaired"] == 0
    tool = summary["tools"][0]
    assert [a["stage"] for a in tool["attempts"]] == ["chain"] * 3 and tool["worked"] == 0
    assert (new / "tools" / "label_code.py").read_text() == (folder / "tools" / "label_code.py").read_text()
    feedback = [m for stage, _, m in llm.chats if stage == "repair_spec"][1][-1]["content"]
    assert "still rejected" in feedback and "<Label " in feedback and "Only 0 of" in feedback


def test_a_repair_that_disagrees_with_the_library_is_not_kept(toolset):
    # the output looks like a code and consumers would take it, but it is not what the library returns
    wrong = code("label_code", "'XX-1'")
    summary, _, new = run_repair(toolset, {("repair_spec", "label_code"): [GOOD_SPEC], ("repair_code", "label_code"): [wrong]}, rounds=1)
    assert summary["repaired"] == 0
    assert "differential" in [a["stage"] for a in summary["tools"][0]["attempts"]]
    assert "XX-1" not in (new / "tools" / "label_code.py").read_text()


def test_wrong_code_is_repaired_before_the_chain_check(toolset):
    wrong = code("label_code", "codes.label(code).text().lower()")
    summary, _, _ = run_repair(toolset, {("repair_spec", "label_code"): [GOOD_SPEC], ("repair_code", "label_code"): [wrong, GOOD_CODE]})
    assert summary["repaired"] == 1
    assert [a["stage"] for a in summary["tools"][0]["attempts"]] == ["differential", "ok"]


def test_changing_the_parameters_is_refused(toolset):
    renamed = json.dumps({"parameters": [{"name": "product", "type": "string", "description": "x", "required": True}],
                          "direct_call": "codes.label(product).text()", "samples": [{"product": "qq-5"}, {"product": "RS-88"}, {"product": "tu-3"}]})
    summary, _, _ = run_repair(toolset, {("repair_spec", "label_code"): [renamed, GOOD_SPEC], ("repair_code", "label_code"): [GOOD_CODE]})
    assert summary["repaired"] == 1
    assert summary["tools"][0]["attempts"][0] == {"stage": "spec", "error": "keep exactly these parameters: ['code']"}
