"""Turn a repository link into checked MCP tools.

    uv run repo2tools generate https://github.com/pypa/packaging --commit c1d2a9d \\
        --base-url http://127.0.0.1:18000/v1 --model qwen3-8b

Steps:
  1. Clone the repo at a recorded commit into .cache/repos/ (ignored by git).
  2. Find the package (src layout or top level) and scrape its public API. No repo code runs.
  3. An LLM picks which functions become tools: one tool per library function.
  4. For each tool, an LLM writes a test (a direct library call and sample inputs), then, in a
     separate request that cannot see the test, the code.
  5. Automatic checks: the code loads, FastMCP accepts it, it runs on the samples, and it gives the
     same result as the direct library call. Errors go back to the LLM for a few repair rounds.
  6. Write the tool set to toolsets/generated/<name>/ and a report to out/generated/<name>/.

First version: pure-Python libraries, one tool per function.

Repo code and generated code are untrusted:
  - Only repos you name on the command line are cloned.
  - The repo is never built or installed: dependencies come as wheels (--no-build), and the package
    is copied into its own environment. So no setup.py or build backend runs.
  - Generated code and library code run only in that environment, with an empty environment
    (no API keys), and on macOS inside sandbox-exec: no network, no reading the home folder
    (SSH keys, the API key, these notes), and writing only to one scratch folder.
  - On other systems there is no such sandbox. The tool warns about it and says so in the report.

The API key comes from $OPENAI_API_KEY, or from .vllm_api_key if the endpoint is on this computer.
"""

import argparse
import ast
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from repo2tools.evaluation.reference_calls import output_value
from repo2tools.paths import API_KEY_FILE, REPO_ROOT
from repo2tools.synthesis.scrape import constructors, scrape_package
from repo2tools.synthesis.usage import count_usage
from repo2tools.synthesis.worker import DANGEROUS_MODULES, FORBIDDEN_NAMES, direct_call_problem

WORKER = Path(__file__).resolve().parent / "worker.py"  # run by path inside each tool set's own environment
ROOT = REPO_ROOT  # toolsets/ and out/ go here; tests point this at a temporary folder
CACHE = ROOT / ".cache"
MCP_REQUIREMENT = "mcp>=1.26,<2"
NOT_A_PACKAGE = {"benchmarks", "build", "ci", "dist", "doc", "docs", "example", "examples", "scripts", "site",
                 "tasks", "test", "tests", "tools"}
NATIVE_SUFFIXES = {".c", ".cc", ".cpp", ".f90", ".pxd", ".pyd", ".pyx", ".rs", ".so"}
JSON_TYPES = {"string", "integer", "number", "boolean", "array", "object", "null"}
TOOL_NAME = re.compile(r"[a-z][a-z0-9_]*$")
LISTING_CHUNK = 150
MAX_PER_CLASS = 6  # tools one class may give when classes can be picked (--classes)
WORKER_SECONDS = 90


# --- repository ------------------------------------------------------------------------------


def checked_url(url: str) -> str:
    """Accept https, ssh and local folders. Refuse git's command transports such as ext::."""
    if url.startswith("-") or "::" in url:
        raise SystemExit(f"refusing this repo link: {url}")
    if re.match(r"(https|ssh)://", url) or re.match(r"[\w.-]+@[\w.-]+:", url) or Path(url).is_dir():
        return url
    raise SystemExit(f"not a repo link or a local folder: {url}")


def repo_name(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1].removesuffix(".git")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).lower()


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True, **kwargs)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"failed: {' '.join(command)}\n{e.stderr[-1500:]}") from e


def clone(url: str, commit: str | None, dest: Path) -> str:
    """Clone or update `dest` and check out `commit` (default: the remote's HEAD). Returns the full hash."""
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.ext.allow=never"]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
    if dest.exists():
        origin = run([*git, "-C", str(dest), "remote", "get-url", "origin"]).stdout.strip()
        if origin != url:  # another repo with the same folder name
            shutil.rmtree(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        run([*git, "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--", url, str(dest)], env=env)
    else:
        run([*git, "-C", str(dest), "fetch", "--quiet", "origin"], env=env)
    run([*git, "-C", str(dest), "checkout", "--quiet", "--force", "--detach", commit or "origin/HEAD"], env=env)
    return run([*git, "-C", str(dest), "rev-parse", "HEAD"]).stdout.strip()


def project_metadata(root: Path) -> tuple[str | None, list[str]]:
    """Project name and dependencies from pyproject.toml, read as data. Nothing is executed."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return None, []
    project = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {})
    return project.get("name"), list(project.get("dependencies", []))


def find_package(root: Path, wanted: str | None) -> tuple[Path, str]:
    """(folder that contains the package, package name): src layout first, then top level."""
    normal = lambda s: re.sub(r"[-_.]+", "_", s).lower()  # noqa: E731
    names = {normal(n) for n in (project_metadata(root)[0], root.name) if n}
    for base in (root / "src", root):
        if not base.is_dir():
            continue
        found = sorted(d.name for d in base.iterdir() if (d / "__init__.py").is_file()
                       and d.name not in NOT_A_PACKAGE and not d.name.startswith((".", "_")))
        if wanted and wanted in found:
            return base, wanted
        if wanted or not found:
            continue
        named = [n for n in found if normal(n) in names]
        if named:
            return base, named[0]
        if len(found) == 1:
            return base, found[0]
        return base, max(found, key=lambda n: sum(p.stat().st_size for p in (base / n).rglob("*.py")))
    raise SystemExit(f"no Python package {'named ' + wanted if wanted else ''} found in {root} (looked in src/ and the top level)")


def native_code(package_dir: Path) -> list[str]:
    return sorted(str(p.relative_to(package_dir)) for p in package_dir.rglob("*") if p.suffix in NATIVE_SUFFIXES)


# --- own environment and sandbox -------------------------------------------------------------


@dataclass
class Box:
    """Where a tool set's untrusted code runs."""

    env_dir: Path
    scratch: Path
    profile: Path | None

    @property
    def python(self) -> Path:
        return self.env_dir / "bin" / "python"

    @property
    def clean_env(self) -> dict:
        return {"PATH": "/usr/bin:/bin", "HOME": str(self.scratch), "TMPDIR": str(self.scratch),
                "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}

    def command(self, *arguments: str) -> list[str]:
        prefix = ["sandbox-exec", "-f", str(self.profile)] if self.profile else []
        return [*prefix, str(self.python), "-I", *arguments]


def sandbox_profile(readable: list[Path], writable: Path, secret: Path) -> str:
    """A macOS sandbox profile: no network, the home folder unreadable, one writable folder."""
    quoted = lambda p: '"' + str(p.resolve()).replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
    # generated code may serve MCP on this computer's own address, and nothing else on the network
    lines = ["(version 1)", "(allow default)", "(deny network*)",
             '(allow network-bind network-inbound (local ip "localhost:*"))', "(deny file-write*)",
             f"(deny file-read* (subpath {quoted(Path.home())}))", "(allow file-read-metadata)"]
    lines += [f"(allow file-read* (subpath {quoted(p)}))" for p in readable]
    lines += [f"(allow file-read* file-write* (subpath {quoted(writable)}))",
              '(allow file-write* (literal "/dev/null") (literal "/dev/stdout") (literal "/dev/stderr"))',
              f"(deny file-read* (literal {quoted(secret)}))"]
    return "\n".join(lines) + "\n"


def make_box(set_name: str, base: Path, package: str, dependencies: list[str], toolset_dir: Path) -> Box:
    envs = CACHE / "envs"
    envs.mkdir(parents=True, exist_ok=True)
    box = Box(envs / set_name, envs / f"{set_name}.tmp", None)
    run(["uv", "venv", "--quiet", "--clear", "--python", "3.12", str(box.env_dir)])
    # --no-build: wheels only, so no dependency's setup.py can run
    run(["uv", "pip", "install", "--quiet", "--python", str(box.python), "--no-build", MCP_REQUIREMENT, *dependencies])
    site_packages = next((box.env_dir / "lib").glob("python*/site-packages"))
    shutil.rmtree(site_packages / package, ignore_errors=True)
    shutil.copytree(base / package, site_packages / package, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.rmtree(box.scratch, ignore_errors=True)
    box.scratch.mkdir()
    if shutil.which("sandbox-exec"):
        config = dict(line.split(" = ", 1) for line in (box.env_dir / "pyvenv.cfg").read_text().splitlines() if " = " in line)
        interpreter_root = Path(config["home"]).resolve().parent
        box.profile = envs / f"{set_name}.sb"
        box.profile.write_text(sandbox_profile([box.env_dir, interpreter_root, WORKER, toolset_dir],
                                               box.scratch, API_KEY_FILE))
    else:
        print("WARNING: no sandbox on this system. Generated code runs without network or file limits.", file=sys.stderr)
    return box


# --- LLM -------------------------------------------------------------------------------------


def api_key_for(base_url: str) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    keyfile = API_KEY_FILE
    if urlparse(base_url).hostname in ("127.0.0.1", "localhost") and keyfile.is_file():
        return keyfile.read_text().strip()
    raise SystemExit("set OPENAI_API_KEY")


class LLM:
    """Keeps every request and answer in a log, with its token counts."""

    def __init__(self, base_url: str, model: str, thinking: bool, concurrency: int, log_path: Path):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key_for(base_url), timeout=900, max_retries=2)
        self.model, self.thinking = model, thinking
        self.limit = asyncio.Semaphore(concurrency)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = open(log_path, "w", encoding="utf-8")
        self.tokens: Counter = Counter()
        self.requests: Counter = Counter()

    async def chat(self, stage: str, subject: str, messages: list[dict], max_tokens: int = 2048) -> str:
        started = time.monotonic()
        async with self.limit:
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0,
                max_tokens=max_tokens * 2 if self.thinking else max_tokens,
                extra_body={"chat_template_kwargs": {"enable_thinking": self.thinking}})
        text = response.choices[0].message.content or ""
        usage = response.usage.model_dump() if response.usage else {}
        self.tokens[stage] += usage.get("total_tokens", 0)
        self.requests[stage] += 1
        self.log.write(json.dumps({"stage": stage, "subject": subject, "messages": messages, "response": text,
                                   "finish_reason": response.choices[0].finish_reason, "usage": usage,
                                   "seconds": round(time.monotonic() - started, 1)}) + "\n")
        self.log.flush()
        # without a reasoning parser on the server, a thinking model's reasoning stays in the content
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str):
    """The first JSON list or object in a reply. Raises ValueError if there is none."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\[{]", text):
        try:
            return decoder.raw_decode(text, match.start())[0]
        except json.JSONDecodeError:
            continue
    raise ValueError("the reply has no valid JSON")


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return (max(blocks, key=len) if blocks else text).strip() + "\n"


# --- prompts ---------------------------------------------------------------------------------
# The examples use the standard library, not the target repo: on packaging, version-0 tools as
# examples would hand the model the answers we want to measure.


def format_param(p: dict) -> str:
    stars = {"var_positional": "*", "var_keyword": "**"}.get(p["kind"], "")
    annotation = f": {p['annotation'][:60]}" if p.get("annotation") else ""
    default = f" = {p['default'][:30]}" if p.get("default") is not None else ""
    return f"{stars}{p['name']}{annotation}{default}"


def signature(c: dict) -> str:
    if c.get("operator"):
        return f"{c['module']}.{c['qualname']} (written `{c['operator']}`)"
    return f"{c['module']}.{c['qualname']}({', '.join(map(format_param, c['params']))}) -> {c['returns']}"


def function_path(c: dict) -> str:
    return f"{c['module']}.{c['qualname']}"


def class_callables(classes: dict) -> list[dict]:
    """Classes as entries the LLM can pick, for uses that no single function stands for: building the object, and operators."""
    return [{"qualname": name, "module": info["module"], "kind": "class", "params": info["params"] or [], "returns": name,
             "summary": info["summary"], "docstring": info.get("docstring", info["summary"]), "file": info["file"], "line": info["line"],
             "loc": info["loc"], "n_overloads": 0, "decorators": []} for name, info in classes.items() if info.get("file")]


OPERATOR_METHODS = {"<": "__lt__", "<=": "__le__", ">": "__gt__", ">=": "__ge__", "==": "__eq__", "!=": "__ne__", "in": "__contains__",
                    "&": "__and__", "|": "__or__", "^": "__xor__", "-": "__sub__", "+": "__add__"}


OPERATOR_NODES = {"<": ast.Lt, "<=": ast.LtE, ">": ast.Gt, ">=": ast.GtE, "==": ast.Eq, "!=": ast.NotEq, "in": (ast.In, ast.NotIn),
                  "&": ast.BitAnd, "|": ast.BitOr, "^": ast.BitXor, "-": ast.Sub, "+": ast.Add}


def operator_callables(classes: dict, usage: dict, by: str | None) -> list[dict]:
    """One entry per operator that the repository itself uses with objects of a class, for example `Version <`.

    A class entry alone was not enough: with it the LLM made one tool per class, the constructor, and
    never a comparison (runs of 2026-11-13). The entry is named like the operator's method, so its path
    is unique, but the test and the tool write the operator itself.
    """
    sources = ("docs", "tests") if by in (None, "both") else (by,)
    entries = []
    for c in class_callables(classes):
        seen = usage["classes"].get(c["qualname"], {}).get("operators", {})
        for op, method in OPERATOR_METHODS.items():
            if sum(seen.get(op, {}).get(s, 0) for s in sources):
                summary = f"The `{op}` operator with {c['qualname']} objects, as in `left {op} right`."
                entries.append({**c, "kind": "operator", "operator": op, "owner": c["qualname"], "qualname": f"{c['qualname']}.{method}",
                                "returns": "", "summary": summary,
                                "docstring": f"{summary} It is an operator, not a function: use it as an expression with `{op}`, "
                                             f"never as a call of `{method}`. At least one side is a {c['qualname']} object.\n\n"
                                             f"The class {c['qualname']}: {c['docstring']}"})
    return entries


def usage_note(c: dict, usage: dict, by: str) -> str:
    """How often the repository's own documentation or tests use this entry, as text for the listing."""
    sources = ("docs", "tests") if by == "both" else (by,)
    count = lambda row: sum(row.get(s, 0) for s in sources)  # noqa: E731
    if c["kind"] == "operator":
        return f"used {count(usage['classes'].get(c['owner'], {}).get('operators', {}).get(c['operator'], {}))} times"
    if c["kind"] != "class":
        return f"used {count(usage['callables'].get(function_path(c), {}))} times"
    info = usage["classes"].get(c["qualname"], {"built": {}, "operators": {}})
    operators = sorted(((count(n), op) for op, n in info["operators"].items() if count(n)), reverse=True)
    return f"built {count(info['built'])} times" + ("; used with " + ", ".join(f"{op} ({n})" for n, op in operators) if operators else "")


def usage_score(c: dict, usage: dict, by: str) -> float:
    """Sort key for the listing: the entry's share of all uses, in the documentation, the tests, or both."""
    sources = ("docs", "tests") if by == "both" else (by,)
    total = 0.0
    for s in sources:
        everything = sum(r[s] for r in usage["callables"].values()) + sum(k["built"][s] for k in usage["classes"].values()) or 1
        if c["kind"] == "operator":
            mine = usage["classes"].get(c["owner"], {}).get("operators", {}).get(c["operator"], {}).get(s, 0)
        elif c["kind"] == "class":
            info = usage["classes"].get(c["qualname"])
            mine = (info["built"][s] + sum(n[s] for n in info["operators"].values())) if info else 0
        else:
            mine = usage["callables"].get(function_path(c), {}).get(s, 0)
        total += mine / everything
    return total


def propose_messages(package: str, callables: list[dict], max_tools: int, usage: dict | None = None, by: str = "docs") -> list[dict]:
    """Ask which functions become tools. With `usage`, each entry shows how often the repository itself uses it.

    Entries of kind "class" (see class_callables) may be picked several times, once per operation.
    """
    where = {"docs": "documentation examples", "tests": "tests", "both": "documentation examples and tests"}[by]
    listing = "\n".join(f"- {c['kind']} {signature(c)} | {c['summary'][:110]}" + (f" | {usage_note(c, usage, by)}" if usage else "") for c in callables)
    has_classes = any(c["kind"] == "class" for c in callables)
    has_operators = any(c["kind"] == "operator" for c in callables)
    extra = ""
    if usage:
        extra += (f" After each entry you see how often the repository's own {where} use it. Prefer what is used often: that is what the "
                  "library is for.")
    if has_classes:
        extra += (" A `class` entry stands for uses that have no function of their own: building the object from text, which also checks "
                  "the text and gives its normal form, and operators such as <, == or `in`. You may make several tools from one class, one "
                  "per operation: give each its own name, and say the operation in the description.")
    if has_operators:
        extra += (" An `operator` entry stands for one operator used with objects of a class, for example comparing two of them with `<`. "
                  "A tool for it takes the values as text, builds the objects and returns the result of the operator. Operators are often "
                  "what the library is used for most, so do not skip them.")
    one_each = "Make one tool per library function." if not has_classes else "For all other entries, make one tool per library function."
    if usage or has_classes or has_operators:
        return [
            {"role": "system", "content": "You design tools for an AI agent. A tool is one Python function that wraps "
                                          "one function of a library and takes and returns plain JSON values. "
                                          "Reply with JSON only."},
            {"role": "user", "content": f"""The library `{package}` has these public functions, methods and properties:

{listing}

Pick at most {max_tools} that are the most useful for an agent solving tasks with this library. Choose from the whole list, and prefer the library's main features over rarely used ones.{extra} {one_each} Inputs must be JSON values: a tool can build a library object from a string, for example. Leave out what needs files or network, what depends on the computer the tool runs on, what returns a plain attribute with little use on its own, and what only makes sense inside the library.

Reply with a JSON list, one object per tool. "function" is the full path of the library function, exactly as listed, without its parameters:
[{{"function": "{function_path(callables[0])}", "name": "snake_case_tool_name", "description": "One sentence for a model that does not know this library."}}]"""},
        ]
    return [
        {"role": "system", "content": "You design tools for an AI agent. A tool is one Python function that wraps "
                                      "one function of a library and takes and returns plain JSON values. "
                                      "Reply with JSON only."},
        {"role": "user", "content": f"""The library `{package}` has these public functions, methods and properties:

{listing}

Pick at most {max_tools} that are the most useful for an agent solving tasks with this library. Choose from the whole list, and prefer the library's main features over rarely used ones. Make one tool per library function. Inputs must be JSON values: a tool can build a library object from a string, for example. Leave out what needs files or network, what depends on the computer the tool runs on, what returns a plain attribute with little use on its own, and what only makes sense inside the library.

Reply with a JSON list, one object per tool. "function" is the full path of the library function, exactly as listed, without its parameters:
[{{"function": "{function_path(callables[0])}", "name": "snake_case_tool_name", "description": "One sentence for a model that does not know this library."}}]"""},
    ]


SPEC_EXAMPLE = """Example, for a tool `is_private_ip` over the standard library's `ipaddress.ip_address`:
{"parameters": [{"name": "address", "type": "string", "description": "An IPv4 or IPv6 address", "required": true}],
 "direct_call": "ipaddress.ip_address(address).is_private",
 "samples": [{"address": "10.0.0.1"}, {"address": "8.8.8.8"}, {"address": "::1"}, {"address": "not an address"}]}"""

CODE_RULES = """Rules:
- Exactly one public function, named exactly as given. Helpers must start with an underscore.
- Type hints on all parameters and on the return value, with JSON types only: str, int, float, bool, None, list[...], dict[str, ...], and X | None.
- Return only JSON values. Convert library objects, for example with str(x), list(x) or sorted(x).
- If the input is invalid, raise ValueError with a clear message. Convert library errors that are not ValueError.
- The docstring says what the tool does, what each parameter means, and gives one example. A model reads only this docstring.
- Import only from the library and harmless parts of the Python standard library. Do not print, read or write files, or use the network. No code at module level except imports and definitions.

Example, for a tool `is_private_ip` over the standard library's `ipaddress`:
```python
from ipaddress import ip_address


def is_private_ip(address: str) -> bool:
    \"\"\"Check whether an IP address is private. address: an IPv4 or IPv6 address, e.g. '10.0.0.1' -> true.\"\"\"
    try:
        return ip_address(address).is_private
    except ValueError as e:
        raise ValueError(f"not a valid IP address: {address!r}") from e
```

Another example, for a tool `split_url` that returns several values:
```python
from urllib.parse import urlsplit


def split_url(url: str) -> dict[str, str | None]:
    \"\"\"Split a URL into scheme, host and path. url: a full URL, e.g. 'https://a.org/x' -> {"scheme": "https", "host": "a.org", "path": "/x"}.\"\"\"
    parts = urlsplit(url)
    return {"scheme": parts.scheme, "host": parts.hostname, "path": parts.path}
```"""


def target_context(pick: dict, root: Path, classes: dict) -> str:
    c = pick["callable"]
    lines = (root / c["file"]).read_text(encoding="utf-8").splitlines()
    source = "\n".join(lines[c["line"] - 1: c["line"] - 1 + min(c["loc"], 80)])
    text = f"It wraps this {c['kind']}:\n{signature(c)}\n\nDocstring:\n{c['docstring'][:1500]}\n\nSource code:\n```python\n{source}\n```"
    owner = classes.get(c["qualname"].split(".")[0]) if "." in c["qualname"] else None
    if owner:
        params = ", ".join(map(format_param, owner["params"])) if owner["params"] else "see the class"
        text += f"\n\nThe class is built like this: {owner['module']}.{c['qualname'].split('.')[0]}({params})\n{owner['summary'][:300]}"
    return text


def spec_messages(pick: dict, root: Path, classes: dict) -> list[dict]:
    return [
        {"role": "system", "content": "You write test plans for tools. Reply with JSON only."},
        {"role": "user", "content": f"""Plan a tool named `{pick['name']}`: {pick['description']}

{target_context(pick, root, classes)}

Reply with one JSON object:
- "parameters": the tool's inputs. Keep them few: only what a caller really needs, and leave rarely used options at the library's default. Each has "name", "type" (string, integer, number, boolean, array or object), "description", "required" (true or false). A parameter that is not required needs a "default".
- "direct_call": one Python expression that calls the library directly and gives the true result, without the tool. Use the parameter names as variables and the library's full dotted path. Use every parameter. No imports, lambdas or comprehensions. Everything the call needs must come from the parameters: for a method, a parameter gives the value that builds the object. Do not hard-code values such as a fixed date.
- "samples": 4 to 6 different inputs, each an object that maps parameter names to values. Include normal inputs and edge cases, and one invalid input if inputs can be invalid.

{SPEC_EXAMPLE}"""},
    ]


def code_messages(pick: dict, spec: dict, root: Path, classes: dict) -> list[dict]:
    parameters = "\n".join(f"- {p['name']} ({p['type']}{', optional' if not p.get('required', True) else ''}): {p.get('description', '')}"
                           for p in spec["parameters"]) or "- none"
    return [
        {"role": "system", "content": "You write one Python function that wraps a library function as a tool for an "
                                      "AI agent. Reply with one Python code block and nothing else."},
        {"role": "user", "content": f"""Write the tool `{pick['name']}`: {pick['description']}

Its parameters, with exactly these names:
{parameters}

{target_context(pick, root, classes)}

{CODE_RULES}"""},
    ]


# --- checks ----------------------------------------------------------------------------------


def parse_proposal(text: str, callables: list[dict]) -> tuple[list[dict], str | None, int]:
    """Valid picks, a problem to send back, and how many entries were dropped.

    A pick names its function by full path, and that path must be in the scraped API. Numbers would
    not do: a model may number its own picks, and each tool would then wrap the wrong function, with
    a correct-looking name and code that passes every check.
    """
    try:
        data = extract_json(text)
    except ValueError as e:
        return [], str(e), 0
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), None)
    if not isinstance(data, list):
        return [], "the reply must be a JSON list of tools", 0
    by_path = {function_path(c): c for c in callables}
    short = Counter(c["qualname"] for c in callables)
    by_path |= {c["qualname"]: c for c in callables if short[c["qualname"]] == 1}
    picks, names, used = [], set(), set()
    for item in data:
        if not isinstance(item, dict):
            continue
        target = by_path.get(re.split(r"[( ]", str(item.get("function", "")).strip())[0])
        name = str(item.get("name", ""))
        if target is None or (function_path(target) in used and target.get("kind") != "class"):
            continue  # an invented function, or a second tool for the same one (a class may give several, one per operation)
        if target.get("kind") == "class" and sum(function_path(p["callable"]) == function_path(target) for p in picks) >= MAX_PER_CLASS:
            continue
        if not TOOL_NAME.match(name) or name in names or not item.get("description"):
            continue
        used.add(function_path(target))
        names.add(name)
        picks.append({"callable": target, "name": name, "description": str(item["description"])})
    dropped = len(data) - len(picks)
    return picks, None if picks else 'no entry names a listed function in "function", with a snake_case name and a description', dropped


def parse_spec(text: str, pick: dict) -> tuple[dict | None, str | None]:
    try:
        spec = extract_json(text)
    except ValueError as e:
        return None, str(e)
    if not isinstance(spec, dict) or not isinstance(spec.get("direct_call"), str):
        return None, "the reply must be a JSON object with parameters, direct_call and samples"
    parameters, samples = spec.get("parameters", []), spec.get("samples")
    if not isinstance(parameters, list) or not isinstance(samples, list) or not all(isinstance(s, dict) for s in samples):
        return None, "parameters must be a list, and samples a list of objects"
    for p in parameters:
        if not isinstance(p, dict) or not TOOL_NAME.match(str(p.get("name", ""))) or p.get("type") not in JSON_TYPES:
            return None, f"this parameter needs a snake_case name and a JSON type: {json.dumps(p)[:200]}"
    names = [p["name"] for p in parameters]
    operator = pick["callable"].get("operator")
    target = pick["callable"]["owner"] if operator else pick["callable"]["qualname"].split(".")[-1]
    problem = direct_call_problem(spec["direct_call"], names, target)
    if problem:
        return None, problem
    if operator and not any(isinstance(node, OPERATOR_NODES[operator]) for node in ast.walk(ast.parse(spec["direct_call"], mode="eval"))):
        return None, f"direct_call must use the operator `{operator}` between the objects, as in `left {operator} right`"
    if len(samples) < (3 if names else 1):
        return None, "give at least 3 different samples"
    return spec, None


def static_problem(code: str, name: str, parameters: list[str]) -> tuple[str, str] | None:
    """(stage, error) for code that should not even be run, or None. Reads the code, runs nothing."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return "syntax", f"line {e.lineno}: {e.msg}"
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and not any(isinstance(n, ast.Call) for n in ast.walk(node)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        return "static", f"line {node.lineno}: no code at module level except imports, definitions and constants"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                return "static", "use absolute imports"
            modules = [node.module or ""]
        else:
            modules = []
        for module in modules:
            if module in DANGEROUS_MODULES or module.split(".")[0] in DANGEROUS_MODULES:
                return "static", f"do not import {module}"
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return "static", f"do not use {node.id}"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "static", f"do not use {node.attr}"
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    public = [n for n in functions if not n.startswith("_")]
    if name not in functions:
        return "static", f"the code must define a function named {name}"
    if public != [name]:
        return "static", f"only {name} may be public; helpers must start with an underscore. Found: {public}"
    function = functions[name]
    if function.returns is None:
        return "static", f"{name} needs a return type hint"
    if not ast.get_docstring(function):
        return "static", f"{name} needs a docstring: a model reads it as the description"
    arguments = function.args
    if arguments.vararg or arguments.kwarg:
        return "static", f"{name} may not use *args or **kwargs"
    given = [a for a in arguments.posonlyargs + arguments.args + arguments.kwonlyargs]
    untyped = [a.arg for a in given if a.annotation is None]
    if untyped:
        return "static", f"these parameters need type hints: {untyped}"
    if sorted(a.arg for a in given) != sorted(parameters):
        return "static", f"the parameters must be exactly {parameters}"
    return None


def run_worker(box: Box, name: str, code: str, spec: dict) -> dict:
    tool_file = box.scratch / f"{name}.py"
    tool_file.write_text(code, encoding="utf-8")
    request = {"tool_file": str(tool_file), "tool_name": name, "parameters": spec["parameters"],
               "direct_call": spec["direct_call"], "samples": spec["samples"]}
    try:
        process = subprocess.run(box.command(str(WORKER)), input=json.dumps(request), text=True,
                                 capture_output=True, timeout=WORKER_SECONDS, env=box.clean_env, cwd=box.scratch)
    except subprocess.TimeoutExpired:
        return {"ok": False, "stage": "runs", "error": f"the check did not finish in {WORKER_SECONDS} s"}
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "stage": "loads", "error": f"the check process died: {process.stderr[-800:]}"}


# --- one tool --------------------------------------------------------------------------------


@dataclass
class ToolResult:
    name: str
    wraps: str
    description: str
    accepted: bool = False
    code: str | None = None
    spec: dict | None = None
    check: dict | None = None
    attempts: list[dict] = field(default_factory=list)  # one {"stage", "error"} per checked version


async def build_tool(pick: dict, llm, box: Box, root: Path, classes: dict, rounds: int) -> ToolResult:
    """Write the test, then the code, then check and repair. `rounds` limits repairs after the first try."""
    name = pick["name"]
    result = ToolResult(name, f"{pick['callable']['module']}.{pick['callable']['qualname']}", pick["description"])
    spec_chat = spec_messages(pick, root, classes)
    code_chat, spec, code = None, None, None
    for _ in range(rounds + 1):
        if spec is None:
            reply = await llm.chat("spec", name, spec_chat)
            new_spec, problem = parse_spec(reply, pick)
            if problem:
                result.attempts.append({"stage": "spec", "error": problem})
                spec_chat += [{"role": "assistant", "content": reply},
                              {"role": "user", "content": f"This is not acceptable: {problem}\nReply with the corrected JSON only."}]
                continue
            names = sorted(p["name"] for p in new_spec["parameters"])
            if result.spec is None or names != sorted(p["name"] for p in result.spec["parameters"]):
                code_chat, code = code_messages(pick, new_spec, root, classes), None
            spec = result.spec = new_spec
        if code is None:
            reply = await llm.chat("code", name, code_chat)
            code = extract_code(reply)
        problem = static_problem(code, name, [p["name"] for p in spec["parameters"]])
        check = None
        if problem:
            stage, error = problem
        else:
            check = await asyncio.to_thread(run_worker, box, name, code, spec)
            stage, error = check["stage"], check.get("error")
        result.attempts.append({"stage": stage, "error": error})
        if check and check["ok"]:
            result.accepted, result.code, result.check = True, code, check
            return result
        result.code, result.check = code, check
        if stage == "spec":
            spec_chat += [{"role": "assistant", "content": json.dumps(spec)},
                          {"role": "user", "content": f"Running this plan failed: {error}\nReply with the corrected JSON only."}]
            spec = None
        else:
            code_chat += [{"role": "assistant", "content": f"```python\n{code}```"},
                          {"role": "user", "content": f"This code failed the check `{stage}`:\n{error}\n\nFix it. Reply with one Python code block and nothing else."}]
            code = None
    return result


# --- output ----------------------------------------------------------------------------------


SERVER = '''"""Serve the generated tools in tools/ over MCP: on stdio, or with `--http PORT`. One file per tool."""

import importlib.util
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("{name}", log_level="WARNING")
for path in sorted((Path(__file__).resolve().parent / "tools").glob("*.py")):
    spec = importlib.util.spec_from_file_location(f"generated_{{path.stem}}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    mcp.add_tool(getattr(module, path.stem))
if len(sys.argv) == 3 and sys.argv[1] == "--http":  # Streamable HTTP at http://127.0.0.1:PORT/mcp, e.g. for ToolGym
    mcp.settings.port = int(sys.argv[2])
    mcp.run(transport="streamable-http")
else:
    mcp.run()
'''

RUN_SERVER = '''#!/bin/sh
# Start these generated tools as an MCP server, in their own environment and sandbox.
# No arguments: stdio. `--http PORT`: Streamable HTTP at http://127.0.0.1:PORT/mcp.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
ENV_DIR="$ROOT/.cache/envs/{name}"
if [ ! -x "$ENV_DIR/bin/python" ]; then
    echo "No environment yet. Run: uv run repo2tools generate {url} --commit {commit} --tag {tag} --env-only" >&2
    exit 1
fi
PROFILE="$ROOT/.cache/envs/{name}.sb"
PREFIX=""
if [ -f "$PROFILE" ] && command -v sandbox-exec >/dev/null 2>&1; then
    exec env -i PATH=/usr/bin:/bin HOME="$ENV_DIR.tmp" TMPDIR="$ENV_DIR.tmp" PYTHONDONTWRITEBYTECODE=1 LANG=C.UTF-8 \\
        sandbox-exec -f "$PROFILE" "$ENV_DIR/bin/python" -I "$HERE/server.py" "$@"
fi
echo "WARNING: running generated code without a sandbox" >&2
exec env -i PATH=/usr/bin:/bin HOME="$ENV_DIR.tmp" TMPDIR="$ENV_DIR.tmp" PYTHONDONTWRITEBYTECODE=1 LANG=C.UTF-8 \\
    "$ENV_DIR/bin/python" -I "$HERE/server.py" "$@"
'''


def write_launchers(dest: Path, set_name: str, tag: str, url: str, commit: str) -> None:
    (dest / "server.py").write_text(SERVER.format(name=set_name), encoding="utf-8")
    script = dest / "run_server.sh"
    script.write_text(RUN_SERVER.format(name=set_name, url=url, commit=commit, tag=tag), encoding="utf-8")
    script.chmod(0o755)


def write_toolset(dest: Path, set_name: str, tag: str, meta: dict, tools: list[ToolResult]) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    (dest / "tools").mkdir(parents=True)
    for t in tools:
        header = (f"# Generated by repo2tools from {meta['url']} at {meta['commit'][:12]}, model {meta['model']}.\n"
                  f"# Wraps {t.wraps}. Checked automatically; not reviewed by a person.\n")
        (dest / "tools" / f"{t.name}.py").write_text(header + t.code, encoding="utf-8")
    write_launchers(dest, set_name, tag, meta["url"], meta["commit"])
    manifest = {**meta, "tools": [{"name": t.name, "wraps": t.wraps, "description": t.check.get("description"),
                                   "verified": t.check["verified"], "direct_call": t.spec["direct_call"],
                                   "samples": t.spec["samples"]} for t in tools]}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


async def end_to_end(script: Path, tools: list[ToolResult]) -> dict[str, str]:
    """Start the finished server for real, and call every tool on its samples over MCP."""
    problems: dict[str, str] = {}
    server = StdioServerParameters(command=str(script), args=[])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = {t.name for t in (await session.list_tools()).tools}
        for t in tools:
            if t.name not in listed:
                problems[t.name] = "not listed by the server"
                continue
            for row in t.check["samples"]:
                result = await session.call_tool(t.name, row["arguments"])
                if result.isError:
                    if row["result"] != "both_error":
                        problems[t.name] = f"error over MCP: {result.content[0].text[:200]}"
                elif row["result"] == "both_error":
                    problems[t.name] = "returned a value over MCP, but raised in the check"
                elif row["result"] in ("same", "same_values", "same_attributes"):
                    value = output_value(result)
                    if json.dumps(value, sort_keys=True, default=str) != json.dumps(row["tool"], sort_keys=True, default=str):
                        problems[t.name] = f"over MCP it returned {json.dumps(value)[:200]}, in the check {json.dumps(row['tool'])[:200]}"
    return problems


def write_report(path: Path, meta: dict, results: list[ToolResult], picks_count: int, n_callables: int, llm, seconds: float) -> dict:
    accepted = [r for r in results if r.accepted]
    rejected = [r for r in results if not r.accepted]
    first_try = Counter(r.attempts[0]["stage"] if r.attempts else "none" for r in results)
    every = Counter(a["stage"] for r in results for a in r.attempts)
    match_kinds = Counter(row["result"] for r in accepted for row in r.check["samples"])
    report = {**meta, "n_callables": n_callables, "picked": picks_count, "accepted": len(accepted),
              "verified": sum(r.check["verified"] for r in accepted), "rejected": len(rejected),
              "ok_on_first_try": first_try["ok"], "first_try_results": first_try, "all_check_results": every,
              "sample_results": match_kinds, "llm_tokens": dict(llm.tokens), "llm_requests": dict(llm.requests),
              "seconds": round(seconds), "tools": [asdict(r) for r in results]}
    path.with_suffix(".json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")

    lines = [
        f"# repo2tools report: {meta['set']}", "",
        f"- Repo: {meta['url']} at `{meta['commit']}`",
        f"- Package: `{meta['package']}`, {n_callables} public callables",
        f"- Model: `{meta['model']}`, thinking {'on' if meta['thinking'] else 'off'}, temperature 0",
        f"- Sandbox: {meta['sandbox']}",
        f"- Time: {seconds / 60:.1f} min. LLM tokens: {sum(llm.tokens.values()):,} in {sum(llm.requests.values())} requests "
        f"({', '.join(f'{k} {v:,}' for k, v in llm.tokens.items())})", "",
        "## Result", "",
        "| | Tools |", "| --- | --- |",
        f"| Picked by the LLM | {picks_count} (dropped: {meta.get('dropped_proposals', 0)}, for unknown functions, duplicates or bad names) |",
        f"| Accepted | {len(accepted)} |",
        f"| Accepted and confirmed against a direct library call | {report['verified']} |",
        f"| Passed all checks on the first try | {first_try['ok']} |",
        f"| Rejected after the repair rounds | {len(rejected)} |", "",
        "First try, by the first check that failed: "
        + (", ".join(f"{k}: {v}" for k, v in first_try.most_common()) or "none") + ".", "",
        "**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they "
        "can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, "
        "crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.", "",
        "## Accepted tools", "",
        "| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |", "| --- | --- | --- | --- | --- |",
    ]
    for r in accepted:
        kinds = Counter(row["result"] for row in r.check["samples"])
        same = sum(v for k, v in kinds.items() if k.startswith("same"))
        lines.append(f"| `{r.name}` | `{r.wraps}` | {len(r.attempts) - 1} | {same} / {kinds['both_error']} | "
                     f"{'yes' if r.check['verified'] else 'no: ' + ', '.join(k for k in kinds if not k.startswith('same'))} |")
    if rejected:
        lines += ["", "## Rejected tools", "", "| Tool | Wraps | Last failed check | Error |", "| --- | --- | --- | --- |"]
        for r in rejected:
            last = r.attempts[-1] if r.attempts else {"stage": "none", "error": ""}
            error = re.sub(r"\s+", " ", str(last["error"]))[:220].replace("|", "\\|")
            lines.append(f"| `{r.name}` | `{r.wraps}` | {last['stage']} | {error} |")
    lines += ["", "## Use", "", "```sh",
              f"uv run repo2tools run-model <exercises> --mode tools --base-url <url> --model <model> -- {meta['toolset']}/run_server.sh",
              "```", ""]
    path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return report


# --- main ------------------------------------------------------------------------------------


async def generate(args, llm=None) -> dict:
    url = checked_url(args.url)
    name = repo_name(url)
    tag = re.sub(r"[^a-z0-9._-]+", "-", (args.tag or args.model or "tools").lower())
    set_name = f"{name}-{tag}"
    root = CACHE / "repos" / name
    commit = clone(url, args.commit, root)
    base, package = find_package(root, args.package)
    native = native_code(base / package)
    if native:
        raise SystemExit(f"{package} has native code ({', '.join(native[:5])}). This first version handles pure-Python libraries only.")
    _, dependencies = project_metadata(root)
    toolset = ROOT / "toolsets" / "generated" / set_name
    out = ROOT / "out" / "generated" / set_name
    box = make_box(set_name, base, package, dependencies, toolset)
    print(f"{url} @ {commit[:12]}: package {package} in {base.relative_to(root.parent)}; own environment ready", file=sys.stderr)
    if args.env_only:
        if (toolset / "tools").is_dir():  # an existing tool set also gets the current server files
            write_launchers(toolset, set_name, tag, url, commit)
        return {"set": set_name, "env_only": True}

    out.mkdir(parents=True, exist_ok=True)
    callables, _ = scrape_package(base, package)
    classes = constructors(base, callables)
    (out / "api.json").write_text(json.dumps({"repo": url, "package": package, "commit": commit, "n_callables": len(callables),
                                              "callables": [asdict(c) for c in callables], "classes": classes}, indent=2), encoding="utf-8")
    if not callables:
        raise SystemExit(f"no public functions found in {package}")
    llm = llm or LLM(args.base_url, args.model, args.thinking, args.concurrency, out / "llm_log.jsonl")
    started = time.monotonic()

    # which functions become tools; big APIs are asked about in parts, so they fit the model's context
    items = [asdict(c) for c in callables]
    usage, by = None, getattr(args, "usage", None)
    operators = bool(getattr(args, "operators", False))
    if getattr(args, "classes", False):
        items = class_callables(classes) + items
    if by or operators:  # what the repository's own documentation and tests use, counted without running anything
        counted = count_usage(json.loads((out / "api.json").read_text()), root, base / package).as_json()
        (out / "usage.json").write_text(json.dumps(counted, indent=1), encoding="utf-8")
        if operators:  # which operators exist comes from the counts; the counts are shown only with --usage
            items = operator_callables(classes, counted, by) + items
        if by:
            usage = counted
            items.sort(key=lambda c: usage_score(c, usage, by), reverse=True)
    chunks = [items[i:i + LISTING_CHUNK] for i in range(0, len(items), LISTING_CHUNK)]
    picks: list[dict] = []
    dropped_picks = 0
    for chunk in chunks:
        share = max(1, round(args.max_tools * len(chunk) / len(items)))
        chat = propose_messages(package, chunk, share, usage, by or "docs")
        for _ in range(args.repair_rounds + 1):
            reply = await llm.chat("propose", package, chat, max_tokens=6000)
            found, problem, dropped = parse_proposal(reply, chunk)
            if not problem:
                dropped_picks += dropped
                seen = {p["name"] for p in picks}
                picks += [p for p in found if p["name"] not in seen][:share]
                break
            chat += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"This is not acceptable: {problem}\nReply with the corrected JSON list only."}]
    if not picks:
        raise SystemExit("the LLM proposed no usable tools; see the log in " + str(out / "llm_log.jsonl"))
    picks = picks[: args.max_tools]
    print(f"{len(picks)} tools picked out of {len(callables)} callables; {dropped_picks} proposals dropped", file=sys.stderr)

    async def one(pick):
        result = await build_tool(pick, llm, box, base, classes, args.repair_rounds)
        print(f"  {'ok ' if result.accepted else 'NO '} {result.name} ({len(result.attempts)} checks: "
              f"{' > '.join(a['stage'] for a in result.attempts)})", file=sys.stderr)
        return result

    results = await asyncio.gather(*(one(pick) for pick in picks))
    accepted = [r for r in results if r.accepted]
    sandbox = "macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable" if box.profile \
        else "NONE: this system has no sandbox-exec, only a separate environment"
    meta = {"url": url, "commit": commit, "package": package, "model": getattr(llm, "model", "unknown"), "thinking": getattr(llm, "thinking", False),
            "set": set_name, "toolset": str(toolset.relative_to(ROOT)), "sandbox": sandbox, "dependencies": dependencies,
            "dropped_proposals": dropped_picks, "pick": {"usage": by, "classes": bool(getattr(args, "classes", False)), "operators": operators}}
    write_toolset(toolset, set_name, tag, meta, accepted)

    # the finished server, over real MCP; anything that fails here leaves the tool set
    if accepted:
        problems = await end_to_end(toolset / "run_server.sh", accepted)
        for r in accepted:
            if r.name in problems:
                r.accepted = False
                r.attempts.append({"stage": "end_to_end", "error": problems[r.name]})
        if problems:
            write_toolset(toolset, set_name, tag, meta, [r for r in accepted if r.accepted])

    report = write_report(out / "report", meta, results, len(picks), len(callables), llm, time.monotonic() - started)
    print(f"{report['accepted']}/{len(picks)} tools accepted, {report['verified']} confirmed against the library, "
          f"{report['ok_on_first_try']} on the first try -> {toolset.relative_to(ROOT)}, {(out / 'report.md').relative_to(ROOT)}", file=sys.stderr)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="repo link (https or ssh), or a local folder")
    parser.add_argument("--commit", help="commit to use; default: the newest. The commit used is always recorded")
    parser.add_argument("--package", help="package name, if the automatic choice is wrong")
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint")
    parser.add_argument("--model", help="model name at that endpoint")
    parser.add_argument("--tag", help="second part of the tool set's name; default: the model")
    parser.add_argument("--max-tools", type=int, default=30)
    parser.add_argument("--repair-rounds", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--thinking", action="store_true", help="let Qwen3-style models think first")
    parser.add_argument("--usage", choices=("docs", "tests", "both"),
                        help="show the LLM how often the repository's own documentation examples, tests or both use each function (`repo2tools usage`)")
    parser.add_argument("--classes", action="store_true",
                        help="let the LLM also make tools from a class itself: building the object, and its operators")
    parser.add_argument("--operators", action="store_true",
                        help="also list each operator the repo uses with a class (e.g. Version <) as its own entry that can become a tool")
    parser.add_argument("--env-only", action="store_true", help="only (re)build the environment of an existing tool set")
    args = parser.parse_args()
    if not args.env_only and not (args.base_url and args.model):
        parser.error("--base-url and --model are needed")
    asyncio.run(generate(args))


if __name__ == "__main__":
    main()
