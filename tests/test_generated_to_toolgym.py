"""Tests for generated_to_toolgym.py: types proposed by a scripted LLM, checked by running real generated tools."""

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

import generated_to_toolgym
import repo2tools
from generated_to_toolgym import links, parse_type
from test_repo2tools import ScriptedLLM, options

LIBRARY = '''"""Product codes such as AB-12."""
import re


def normalize(code: str) -> str:
    """Upper-case a product code. Raises ValueError if it is not one."""
    if not re.fullmatch(r"[A-Za-z]{2}-[0-9]+", code):
        raise ValueError(f"not a product code: {code!r}")
    return code.upper()


def split(code: str) -> dict:
    """Split a product code into prefix and number."""
    code = normalize(code)
    return {"prefix": code[:2], "number": int(code[3:]), "related": [code, code[:2] + "-0"]}


def newest(codes: list) -> str:
    """The code with the highest number."""
    return max((normalize(c) for c in codes), key=lambda c: int(c[3:]))


def shout(text: str, twice: bool = False) -> str:
    """Upper-case any text."""
    return text.upper() * (2 if twice else 1)


def describe(code: str) -> str:
    """A sentence about a product code."""
    return f"Product {normalize(code)} is in stock."
'''


def tool(name, library_call, parameters, hints, returns, samples):
    spec = {"parameters": [{"name": p, "type": "string", "description": p, "required": True} for p in parameters],
            "direct_call": library_call, "samples": samples}
    arguments = ", ".join(f"{p}: {h}" for p, h in zip(parameters, hints))
    code = (f"```python\nimport codes\n\n\ndef {name}({arguments}) -> {returns}:\n"
            f'    """Tool {name}. Example: see the library."""\n    return {library_call}\n```')
    return {("spec", name): [json.dumps(spec)], ("code", name): [code]}


@pytest.fixture
def toolset(tmp_path, monkeypatch):
    """A real generated tool set over the codes library, built with a scripted LLM."""
    monkeypatch.setattr(repo2tools, "ROOT", tmp_path / "root")
    monkeypatch.setattr(repo2tools, "CACHE", tmp_path / "root" / ".cache")
    monkeypatch.setattr(generated_to_toolgym, "OUT", tmp_path / "root" / "out" / "generated")
    (tmp_path / "root").mkdir()
    repo = tmp_path / "repo" / "codes"
    (repo / "codes").mkdir(parents=True)
    (repo / "codes" / "__init__.py").write_text(LIBRARY)
    (repo / "pyproject.toml").write_text('[project]\nname = "codes"\ndependencies = []\n')
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(repo)]
    for command in (["init", "--quiet"], ["add", "."], ["commit", "--quiet", "-m", "init"]):
        subprocess.run([*git, *command], check=True)
    names = ["normalize_code", "split_code", "newest_code", "shout_text", "describe_code"]
    functions = ["normalize", "split", "newest", "shout", "describe"]
    script = {("propose", "codes"): [json.dumps([{"function": f"codes.{f}", "name": n, "description": f"Use {f}."}
                                                 for n, f in zip(names, functions)])]}
    script |= tool("normalize_code", "codes.normalize(code)", ["code"], ["str"], "str", [{"code": "ab-12"}, {"code": "Cd-7"}, {"code": "zz-100"}, {"code": "bad"}])
    script |= tool("split_code", "codes.split(code)", ["code"], ["str"], "dict", [{"code": "qq-5"}, {"code": "RS-88"}, {"code": "tu-3"}])
    script |= tool("newest_code", "codes.newest(items)", ["items"], ["list[str]"], "str", [{"items": ["aa-1", "bb-9"]}, {"items": ["cc-4"]}, {"items": ["dd-2", "ee-3", "ff-1"]}])
    script |= tool("shout_text", "codes.shout(text, twice)", ["text", "twice"], ["str", "bool = False"], "str",
                   [{"text": "hello there"}, {"text": "good morning", "twice": True}, {"text": "what a day"}])
    script |= tool("describe_code", "codes.describe(code)", ["code"], ["str"], "str", [{"code": "gh-6"}, {"code": "ij-11"}, {"code": "kl-2"}])
    report = asyncio.run(repo2tools.generate(options(repo), llm=ScriptedLLM(script)))
    assert report["accepted"] == 5, [(t["name"], t["attempts"]) for t in report["tools"]]
    dest = tmp_path / "toolgym" / "gym" / "tools" / "mcp_servers" / "catalog"
    dest.mkdir(parents=True)
    return tmp_path / "root" / "toolsets" / "generated" / "codes-test", dest


def run_export(toolset, proposal):
    folder, dest = toolset
    summary = asyncio.run(generated_to_toolgym.export(folder, dest, ScriptedLLM({("types", "codes-test"): [json.dumps({"tools": proposal})]})))
    catalog = dest / "repo2tools_codes_test"
    return summary, json.loads((catalog / "mcp_server.json").read_text()), json.loads((catalog / "types.json").read_text()), catalog


GOOD = {
    "normalize_code": {"parameters": {"code": "ProductCode"}, "output": "ProductCode"},
    "split_code": {"parameters": {"code": "ProductCode"}, "output": {"fields": {"prefix": "ProductCode", "related": "list[ProductCode]", "number": "integer"}}},
    "newest_code": {"parameters": {"items": "list[ProductCode]"}, "output": "ProductCode"},
    "shout_text": {"parameters": {"text": "string", "twice": "boolean"}, "output": "string"},
    "describe_code": {"parameters": {"code": "ProductCode"}, "output": "ProductCode"},
}


def gym_types(server):
    return {t["mcp_spec"]["name"]: t["gym_types"] for t in server["tools"]}


def test_parse_type():
    assert parse_type("ProductCode") == ("one", "ProductCode")
    assert parse_type("list[ProductCode]") == ("list", "ProductCode")
    assert parse_type("ProductCode[]") == ("list", "ProductCode")
    assert parse_type({"list_of": "ProductCode"}) == ("list", "ProductCode")
    for plain in ("string", "boolean", "String", "list[string]", "not a name", None, 3):
        assert parse_type(plain) is None


def test_true_claims_are_kept_and_false_ones_withdrawn(toolset):
    summary, server, types, catalog = run_export(toolset, GOOD)
    t = gym_types(server)
    # the three code parameters share one type, and the list parameter is a list of it
    assert t["normalize_code"]["parameters"] == {"code": "ProductCode"}
    assert t["split_code"]["parameters"] == {"code": "ProductCode"}
    assert t["newest_code"]["parameters"] == {"items": "ProductCodeList"}
    assert types["lists"]["ProductCodeList"]["element"] == "ProductCode"
    # outputs: a code is a code; a sentence about a code is not, although the LLM said so
    assert t["normalize_code"]["output_type"] == "ProductCode"
    assert t["newest_code"]["output_type"] == "ProductCode"
    assert t["describe_code"]["output_type"] == "string"
    # object output: the prefix is not a code, the related list is
    assert t["split_code"]["output_type"] == "SplitCodeOutput"
    assert types["objects"]["SplitCodeOutput"]["fields"] == {"related": "ProductCodeList"}
    # free text and flags
    assert t["shout_text"]["parameters"]["twice"] == "ShoutTextTwice"  # a flag gets its own type
    assert types["pools"]["ShoutTextTwice"] == [False, True]
    assert t["shout_text"]["parameters"]["text"] == "ShoutTextText"
    assert types["pools"]["ShoutTextText"] == ["hello there", "good morning", "what a day"]
    # the pool holds only inputs that worked: "bad" raised
    assert "bad" not in types["pools"]["ProductCode"] and "ab-12" in types["pools"]["ProductCode"]
    assert "aa-1" in types["pools"]["ProductCode"]  # elements of the list parameter count too
    assert summary["output_claims"] == 5 and summary["output_claims_kept"] == 3
    for name in ("types.py", "contribution.py", "__init__.py"):
        assert (catalog / name).is_file()


def test_a_parameter_that_cannot_take_the_types_values_is_withdrawn(toolset):
    wrong = json.loads(json.dumps(GOOD))
    wrong["shout_text"]["parameters"]["text"] = "ProductCode"  # text is not a code: codes work as text, but not the other way
    summary, server, types, _ = run_export(toolset, wrong)
    t = gym_types(server)
    withdrawn = {(e["tool"], e["parameter"]) for e in summary["parameter_checks"] if not e["kept"]}
    # only the text parameter leaves: its values fail on every code parameter
    assert withdrawn == {("shout_text", "text")}
    assert "hello there" not in types["pools"]["ProductCode"]
    assert t["shout_text"]["parameters"]["text"] == "ShoutTextText"
    assert t["normalize_code"]["parameters"]["code"] == t["describe_code"]["parameters"]["code"] == "ProductCode"


def test_an_output_with_a_narrower_name_falls_back_to_the_parameter_type(toolset):
    narrower = json.loads(json.dumps(GOOD))
    narrower["normalize_code"]["output"] = "NormalizedProductCode"  # no parameter has this type
    narrower["describe_code"]["output"] = "ProductSentence"  # shares a word, but a sentence is not a code
    summary, server, _, _ = run_export(toolset, narrower)
    t = gym_types(server)
    assert t["normalize_code"]["output_type"] == "ProductCode"
    assert t["describe_code"]["output_type"] == "string"
    check = next(e for e in summary["output_checks"] if e["tool"] == "normalize_code")
    assert check["kept"] and "works as ProductCode" in check["why"]


def test_object_fields_are_asked_about_and_checked(toolset):
    folder, dest = toolset
    whole = json.loads(json.dumps(GOOD))
    whole["split_code"]["output"] = "SplitResult"  # the LLM names the whole object; no parameter takes that
    llm = ScriptedLLM({("types", "codes-test"): [json.dumps({"tools": whole})],
                       ("fields", "codes-test"): [json.dumps({"split_code": {"related": "list[ProductCode]", "prefix": "ProductCode", "number": "integer"}})]})
    summary = asyncio.run(generated_to_toolgym.export(folder, dest, llm))
    catalog = dest / "repo2tools_codes_test"
    server, types = json.loads((catalog / "mcp_server.json").read_text()), json.loads((catalog / "types.json").read_text())
    assert gym_types(server)["split_code"]["output_type"] == "SplitCodeOutput"
    assert types["objects"]["SplitCodeOutput"]["fields"] == {"related": "ProductCodeList"}  # the prefix is not a code: checked by running
    question = next(m for stage, _, m in llm.chats if stage == "fields")[-1]["content"]
    assert "`ProductCode`" in question and '"prefix"' in question and "### split_code" in question
    assert "### normalize_code" not in question  # only tools that return objects are asked about
    assert ("split_code", "normalize_code") in {(a, b) for a, b, _ in links(server, types)}


def test_links_follow_the_kept_types(toolset):
    _, server, types, _ = run_export(toolset, GOOD)
    found = links(server, types)
    pairs = {(a, b) for a, b, _ in found}
    assert ("normalize_code", "split_code") in pairs  # direct
    assert ("newest_code", "describe_code") in pairs
    assert ("split_code", "newest_code") in pairs  # the related field is a list of codes
    assert ("split_code", "normalize_code") in pairs  # ... and its first element is a code
    assert not any(a == "describe_code" for a, _ in pairs)  # its output type was withdrawn
    assert not any("shout_text" in pair for pair in pairs)


def test_type_names_do_not_clash_with_other_servers(toolset):
    folder, dest = toolset
    other = dest / "someone_else"
    other.mkdir()
    (other / "types.py").write_text('X = make(name="ProductCode")\n')
    _, server, types, _ = run_export(toolset, GOOD)
    assert "ProductCode" not in types["pools"] and "ProductCodeX" in types["pools"]
    assert gym_types(server)["normalize_code"]["parameters"] == {"code": "ProductCodeX"}
    assert types["lists"]["ProductCodeList"]["element"] == "ProductCodeX"


def test_unused_optional_parameters_are_left_out(toolset):
    folder, dest = toolset
    manifest = json.loads((folder / "manifest.json").read_text())
    for entry in manifest["tools"]:
        if entry["name"] == "shout_text":
            entry["samples"] = [{"text": "hello there"}, {"text": "what a day"}]  # nobody sets `twice`
    (folder / "manifest.json").write_text(json.dumps(manifest))
    _, server, _, _ = run_export(toolset, GOOD)
    shout = next(t for t in server["tools"] if t["mcp_spec"]["name"] == "shout_text")
    assert list(shout["gym_types"]["parameters"]) == ["text"]
    assert list(shout["mcp_spec"]["inputSchema"]["properties"]) == ["text"]
