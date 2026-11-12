"""Put a generated tool set into ToolGym's catalog, with types that are checked by running the tools.

    uv run python generated_to_toolgym.py toolsets/generated/packaging-coder-60 \\
        --dest ../tool-gym/gym/tools/mcp_servers/catalog --base-url http://127.0.0.1:18000/v1 --model qwen3-32b

ToolGym builds tool chains from types: a tool's output can feed another tool's input if the types
match. Generated tools only have JSON types (string, array, ...), so this script adds semantic ones:

  1. Observe: start the tool set's own server and call every tool on its sample inputs. Inputs that
     work, and their outputs, are the examples.
  2. Propose (LLM): one small shared vocabulary of types, e.g. the same "VersionString" for every
     parameter that takes a version. A second question asks which fields of object outputs hold
     values of those types.
  3. Check by running (no LLM): a type is a claim that its values are interchangeable. So for every
     two parameters of a type, the values of one are tried on the other, and every typed output is
     fed into the parameters that would consume it. Claims that fail are withdrawn: the parameter
     keeps its own private examples, and the output becomes a plain JSON type.
  4. Write the catalog folder: mcp_server.json, types.json, types.py, contribution.py, __init__.py.

A type's sample pool is the set of example values that worked. ToolGym samples chain inputs from it.
On/off flags get a type of their own each, so that a tool's true/false result is not chained into an
unrelated flag (in ToolGym's hand-typed catalogs these were 35 of 144 links for our packaging tools).

Afterwards, in the ToolGym checkout: `uv run python -m gym.tools.mcp_servers.check`, and
`chain_check` with the server running (`run_server.sh --http 8765`,
CSCS_MCP_URL_TEMPLATE=http://127.0.0.1:8765/mcp). This repo contains no ToolGym code: types.py
imports ToolGym's classes when ToolGym loads it.
"""

import argparse
import asyncio
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from repo2tools import LLM, extract_json
from run_reference_calls import output_value

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "generated"  # reports go here; tests point this at a temporary folder
PRIMITIVES = {"string", "integer", "number", "boolean", "array", "object"}
TYPE_NAME = re.compile(r"[A-Z][A-Za-z0-9]*$")
KEEP_RATE = 0.6  # a claim stands if at least this share of the test calls works
PAIR_VALUES = 3  # values of one parameter tried on another parameter of the same type
MAX_POOL = 60


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True)


def camel(text: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", text) if part)


def json_kind(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def unique(values: list) -> list:
    seen, out = set(), []
    for v in values:
        key = canonical(v)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def parse_type(text) -> tuple[str, str] | None:
    """("one", T) or ("list", T) for a type the LLM named, or None for a plain JSON type."""
    if isinstance(text, dict) and isinstance(text.get("list_of"), str):
        text = f"list[{text['list_of']}]"
    if not isinstance(text, str):
        return None
    match = re.fullmatch(r"(?:list|List|array)\[(\w+)\]|(\w+)\[\]", text.strip())
    if match:
        name = match.group(1) or match.group(2)
        return ("list", name) if TYPE_NAME.match(name) and name.lower() not in PRIMITIVES else None
    name = text.strip()
    return ("one", name) if TYPE_NAME.match(name) and name.lower() not in PRIMITIVES else None


# --- 1. observe --------------------------------------------------------------------------------


class Server:
    """The tool set's own MCP server, started the same way a model would use it."""

    def __init__(self, session: ClientSession):
        self.session = session
        self.calls = 0

    async def call(self, tool: str, arguments: dict):
        """(worked, value). A tool error, or a call that breaks the protocol, counts as not worked."""
        self.calls += 1
        try:
            result = await self.session.call_tool(tool, arguments)
            if result.isError:
                return False, None
            return True, output_value(result)
        except Exception:  # noqa: BLE001  (e.g. output that is not JSON)
            return False, None


async def observe(server: Server, manifest: dict) -> dict:
    """Per tool: its MCP spec and the sample calls that worked, with their outputs."""
    listed = {t.name: t for t in (await server.session.list_tools()).tools}
    tools = {}
    for entry in manifest["tools"]:
        spec = listed.get(entry["name"])
        if spec is None:
            continue
        examples = []
        for sample in entry["samples"]:
            worked, value = await server.call(entry["name"], sample)
            if worked:
                examples.append({"arguments": sample, "output": value})
        tools[entry["name"]] = {"description": spec.description, "input_schema": spec.inputSchema,
                                "wraps": entry["wraps"], "examples": examples}
    return tools


# --- 2. propose --------------------------------------------------------------------------------


def short(value, limit: int = 110) -> str:
    text = json.dumps(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def propose_messages(tools: dict) -> list[dict]:
    blocks = []
    for name, tool in tools.items():
        lines = [f"### {name}", (tool["description"] or "").split("\n")[0][:160], f"wraps {tool['wraps']}"]
        for param, schema in tool["input_schema"].get("properties", {}).items():
            values = unique([e["arguments"][param] for e in tool["examples"] if e["arguments"].get(param) is not None])
            kind = schema.get("type") or "/".join(sorted({o.get("type", "?") for o in schema.get("anyOf", [])}))
            lines.append(f"- parameter `{param}` ({kind}), e.g. {', '.join(short(v) for v in values[:3]) or 'no example'}")
        outputs = unique([e["output"] for e in tool["examples"]])
        lines.append(f"- output, e.g. {', '.join(short(v, 160) for v in outputs[:3])}")
        blocks.append("\n".join(lines))
    listing = "\n\n".join(blocks)
    return [
        {"role": "system", "content": "You assign semantic types to the inputs and outputs of tools, so that tools can be "
                                      "chained: the output of one tool becomes the input of another. Reply with JSON only."},
        {"role": "user", "content": f"""These tools come from one library:

{listing}

Give types to their parameters and outputs.

Step 1: find the kinds of values this library works with. Look at the example values: strings that follow a format or name a specific kind of thing (for example an email address, a date, an identifier) are a kind of value. Give each kind a CamelCase type name, such as `EmailAddress`.
Step 2: give every parameter and every output a type.
- Use the same type for every parameter and output that holds the same kind of value in the same format, across all tools. Two things have the same type only if a value of one can be used as the other.
- Most string parameters hold one of the kinds from step 1. Use plain `string` only for free text that fits no kind.
- A list of values of one type is written `list[TypeName]`.
- An output that is an object can list which of its fields have a type. Leave out the other fields.
- Flags and counts get a plain JSON type: boolean, integer or number.

Reply with one JSON object, types first:
{{"types": [{{"name": "TypeName", "description": "what it is, with one example value"}}],
 "tools": {{"tool_name": {{"parameters": {{"param": "TypeName"}}, "output": "TypeName"}},
           "other_tool": {{"parameters": {{"items": "list[TypeName]", "strict": "boolean"}}, "output": {{"fields": {{"name": "OtherType", "all": "list[TypeName]"}}}}}}}}}}
Include every tool and every parameter."""},
    ]


def read_proposal(reply: str, tools: dict) -> dict:
    """{tool: {"parameters": {param: parsed type or None}, "output": parsed type, {"fields": {...}} or None}}."""
    data = extract_json(reply)
    data = data.get("tools", data) if isinstance(data, dict) else {}
    proposal = {}
    for name, tool in tools.items():
        given = data.get(name) if isinstance(data.get(name), dict) else {}
        parameters = given.get("parameters") if isinstance(given.get("parameters"), dict) else {}
        output = given.get("output")
        if isinstance(output, dict) and isinstance(output.get("fields"), dict):
            fields = {f: parse_type(t) for f, t in output["fields"].items() if isinstance(f, str) and f.isidentifier() and not f.startswith("_")}
            parsed_output = {"fields": {f: t for f, t in fields.items() if t}} if any(fields.values()) else None
        else:
            parsed_output = parse_type(output)
        proposal[name] = {"parameters": {p: parse_type(parameters.get(p)) for p in tool["input_schema"].get("properties", {})},
                          "output": parsed_output}
    return proposal


def fields_messages(tools: dict, proposal: dict, wanted: list[str]) -> list[dict]:
    """Ask which fields of object outputs hold values of the types already named for parameters."""
    examples: dict[str, list] = {}
    for name, tool in tools.items():
        for param, parsed in proposal[name]["parameters"].items():
            if parsed:
                values = [e["arguments"][param] for e in tool["examples"] if e["arguments"].get(param) is not None]
                examples.setdefault(parsed[1], []).extend(v for value in values for v in (value if parsed[0] == "list" and isinstance(value, list) else [value]))
    vocabulary = "\n".join(f"- `{name}`, e.g. {', '.join(short(v, 60) for v in unique(values)[:3])}" for name, values in sorted(examples.items()))
    outputs = "\n\n".join(f"### {name}\n{short(tools[name]['examples'][0]['output'], 500)}" for name in wanted)
    return [
        {"role": "system", "content": "You assign semantic types to the fields of tool outputs, so that tools can be chained. Reply with JSON only."},
        {"role": "user", "content": f"""These types are used for the inputs of a library's tools:

{vocabulary}

These tools return objects. One example output each:

{outputs}

For each tool, say which top-level fields hold a value of one of the types above: `TypeName` for one value, `list[TypeName]` for a list of them. Leave out fields that fit no type.

Reply with one JSON object: {{"tool_name": {{"field": "TypeName", "other_field": "list[TypeName]"}}}}"""},
    ]


def read_fields(reply: str, wanted: list[str]) -> dict:
    data = extract_json(reply)
    data = data if isinstance(data, dict) else {}
    found = {}
    for name in wanted:
        given = data.get(name) if isinstance(data.get(name), dict) else {}
        fields = {f: parse_type(t) for f, t in given.items() if isinstance(f, str) and f.isidentifier() and not f.startswith("_")}
        if any(fields.values()):
            found[name] = {"fields": {f: t for f, t in fields.items() if t}}
    return found


# --- 3. check by running ------------------------------------------------------------------------


class Typing:
    """The current type of every parameter, and each type's pool of example values."""

    def __init__(self, tools: dict, proposal: dict):
        self.tools = tools
        self.param: dict[tuple[str, str], tuple[str, str]] = {}  # (tool, param) -> ("one" | "list" | "private" | "boolean", type name)
        self.dropped: list[tuple[str, str]] = []  # optional parameters no example uses
        for name, tool in tools.items():
            for param in tool["input_schema"].get("properties", {}):
                values = self.values(name, param)
                if not values:
                    self.dropped.append((name, param))
                elif all(isinstance(v, bool) for v in values):
                    self.param[name, param] = ("boolean", "boolean")
                else:
                    proposed = proposal[name]["parameters"].get(param)
                    fits = proposed and (proposed[0] == "one" or all(isinstance(v, list) for v in values))
                    self.param[name, param] = proposed if fits else self.private(name, param)

    def values(self, tool: str, param: str) -> list:
        return unique([e["arguments"][param] for e in self.tools[tool]["examples"] if e["arguments"].get(param) is not None])

    @staticmethod
    def private(tool: str, param: str) -> tuple[str, str]:
        return ("private", camel(tool) + camel(param))

    def members(self, type_name: str) -> list[tuple[str, str]]:
        return [key for key, (kind, name) in self.param.items() if name == type_name and kind in ("one", "list")]

    def pool(self, type_name: str, without: tuple[str, str] | None = None) -> list:
        """Example values of a type: single values, and the elements of list parameters."""
        values = []
        for key in self.members(type_name):
            if key == without:
                continue
            for v in self.values(*key):
                values += v if self.param[key][0] == "list" else [v]
        return unique(values)

    def base(self, tool: str) -> dict:
        return dict(self.tools[tool]["examples"][0]["arguments"])


async def check_parameters(server: Server, typing: Typing, rng: random.Random) -> list[dict]:
    """Keep a type only among parameters whose example values work on each other.

    For every two parameters A and B of a type, B's values are tried on A. If a pair fails in either
    direction, the parameter in the most failing pairs leaves the type, until all pairs work. One
    parameter with the wrong kind of values (free text typed as a code) would otherwise fill the
    type's pool with values the others reject.
    """
    log = []
    for type_name in sorted({name for kind, name in typing.param.values() if kind in ("one", "list")}):
        members = typing.members(type_name)
        elements = {key: unique([x for v in typing.values(*key) for x in (v if typing.param[key][0] == "list" else [v])]) for key in members}
        rate: dict[tuple, float] = {}
        for consumer in members:
            for source in members:
                if consumer == source:
                    continue
                values = [v for v in elements[source] if canonical(v) not in {canonical(x) for x in elements[consumer]}]
                if not values:
                    continue  # the same values: nothing new is claimed
                tool, param = consumer
                tries = rng.sample(values, min(PAIR_VALUES, len(values)))
                worked = [(await server.call(tool, {**typing.base(tool), param: [v] if typing.param[consumer][0] == "list" else v}))[0] for v in tries]
                rate[consumer, source] = sum(worked) / len(worked)
        remaining = list(members)
        while True:
            failing = [(c, s) for (c, s), r in rate.items() if r < KEEP_RATE and c in remaining and s in remaining]
            if not failing:
                break
            in_pairs = {m: sum(m in pair for pair in failing) for m in remaining}
            worst = max(remaining, key=lambda m: (in_pairs[m], -sum(r for pair, r in rate.items() if m in pair)))
            remaining.remove(worst)
            typing.param[worst] = typing.private(*worst)
        for tool, param in members:
            mine = [r for (c, s), r in rate.items() if (tool, param) in (c, s)]
            log.append({"tool": tool, "parameter": param, "type": type_name, "pairs": len(mine),
                        "pairs_working": sum(r >= KEEP_RATE for r in mine), "kept": (tool, param) in remaining})
    return log


GENERIC_WORDS = {"String", "List", "Type", "Value", "Name", "Object", "Data", "Info", "Result"}


def words(type_name: str) -> set[str]:
    return set(re.findall(r"[A-Z][a-z0-9]*", type_name)) - GENERIC_WORDS


async def try_type(server: Server, typing: Typing, type_name: str, values: list, rng: random.Random) -> dict:
    """Feed output values into the parameters of this type."""
    consumers = typing.members(type_name)
    kinds = {json_kind(v) for v in typing.pool(type_name)}
    values = unique([v for v in values if v is not None])
    if not consumers or not values:
        return {"tried": 0, "worked": 0, "kept": False, "why": "no parameter has this type" if not consumers else "no example value"}
    if {json_kind(v) for v in values} - kinds:
        return {"tried": 0, "worked": 0, "kept": False, "why": "the output has another shape"}
    worked = []
    for tool, param in rng.sample(consumers, min(3, len(consumers))):
        for value in rng.sample(values, min(4, len(values))):
            argument = [value] if typing.param[tool, param][0] == "list" else value
            worked.append((await server.call(tool, {**typing.base(tool), param: argument}))[0])
    return {"tried": len(worked), "worked": sum(worked), "kept": sum(worked) / len(worked) >= KEEP_RATE}


async def output_works(server: Server, typing: Typing, type_name: str, values: list, rng: random.Random) -> dict:
    """Test an output claim by chaining. The result names the type that was kept, which can differ.

    An LLM often gives an output a narrower name than any input has, e.g. NormalizedPackageName where
    parameters take PackageName. A type no parameter has is useless for chains, so the claim is then
    tried on the parameter types that share a word with it, and the one that works best is kept.
    """
    if typing.members(type_name):
        return {**await try_type(server, typing, type_name, values, rng), "type": type_name}
    shared = sorted({name for kind, name in typing.param.values() if kind in ("one", "list")})
    best = None
    for candidate in sorted((c for c in shared if words(c) & words(type_name)), key=lambda c: -len(words(c) & words(type_name))):
        test = await try_type(server, typing, candidate, values, rng)
        if test["kept"] and (best is None or test["worked"] / test["tried"] > best["worked"] / best["tried"]):
            best = {**test, "type": candidate, "why": f"no parameter has type {type_name}; works as {candidate}"}
    return best or {"tried": 0, "worked": 0, "kept": False, "why": "no parameter has this type", "type": type_name}


def plain_output(outputs: list) -> str:
    kinds = {json_kind(v) for v in outputs if v is not None}
    return kinds.pop() if len(kinds) == 1 else "string"


async def check_outputs(server: Server, typing: Typing, proposal: dict, rng: random.Random) -> tuple[dict, list[dict]]:
    """Each tool's output type: {"kind": "plain" | "one" | "list" | "object", ...}. Claims are tested by chaining."""
    outputs, log = {}, []
    for tool, info in typing.tools.items():
        values = [e["output"] for e in info["examples"]]
        proposed = proposal[tool]["output"]
        result = {"kind": "plain", "type": plain_output(values)}
        if isinstance(proposed, tuple):
            kind, type_name = proposed
            shape_ok = kind == "one" or all(isinstance(v, list) for v in values)
            flat = [x for v in values for x in v] if kind == "list" and shape_ok else values
            test = await output_works(server, typing, type_name, flat, rng) if shape_ok else {"tried": 0, "worked": 0, "kept": False, "why": "the output has another shape", "type": type_name}
            log.append({"tool": tool, "output": f"list[{type_name}]" if kind == "list" else type_name, **test})
            if test["kept"]:
                result = {"kind": kind, "type": test["type"]}
        elif isinstance(proposed, dict) and all(isinstance(v, dict) for v in values):
            fields = {}
            for field, (kind, type_name) in proposed["fields"].items():
                present = [v[field] for v in values if v.get(field) is not None]
                shape_ok = bool(present) and (kind == "one" or all(isinstance(v, list) for v in present))
                flat = [x for v in present for x in v] if kind == "list" and shape_ok else present
                test = await output_works(server, typing, type_name, flat, rng) if shape_ok else {"tried": 0, "worked": 0, "kept": False, "why": "the field is missing or has another shape", "type": type_name}
                log.append({"tool": tool, "output": f"field {field}: {'list[' + type_name + ']' if kind == 'list' else type_name}", **test})
                if test["kept"]:
                    fields[field] = (kind, test["type"])
            if fields:
                result = {"kind": "object", "type": camel(tool) + "Output", "fields": fields}
        outputs[tool] = result
    return outputs, log


# --- 4. write the catalog folder ---------------------------------------------------------------

TYPES_PY = '''"""ToolGym types for a tool set generated by repo2tools. Everything is read from types.json.

- A pool type samples one of its example values. The examples are tool inputs that worked.
- A list type samples a few values of its element type; its first element can be taken out.
- An object type is a tool's object output; the listed fields can be taken out.
"""

import ast
import copy
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pydantic
from pydantic import ConfigDict, create_model

from gym.tools.shared import validate_extraction_selectors
from gym.tools.shared.types import GymOutputOnlyTypeFactory, GymType
from modules.trace_generation.protocols import ExtractionProjection, Projection, TypeMaterializationError

_SPEC = json.loads((Path(__file__).parent / "types.json").read_text())


def _parse(s: str) -> Any:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError) as exc:
            raise TypeMaterializationError(f"not JSON or a Python literal: {s[:80]!r}") from exc


@dataclass(frozen=True, eq=False)
class PoolType(GymType):
    """Samples from example values. Accepts any value of the same JSON kind, not only the examples."""

    values: tuple = ()

    def random_sample(self, rng: random.Random) -> Any:
        return copy.deepcopy(rng.choice(self.values))

    def from_str(self, s: str) -> Any:
        if all(isinstance(v, str) for v in self.values):
            return s
        return _parse(s)


@dataclass(frozen=True, eq=False)
class ListType(GymType):
    element: PoolType | None = None
    min_items: int = 1
    max_items: int = 4

    def random_sample(self, rng: random.Random) -> list:
        pool = list(self.element.values)
        size = rng.randint(min(self.min_items, len(pool)), min(self.max_items, len(pool)))
        return copy.deepcopy(rng.sample(pool, size))

    def from_str(self, s: str) -> list:
        value = _parse(s)
        if not isinstance(value, list):
            raise TypeMaterializationError(f"{self.name} must be a list, got {type(value).__name__}")
        return value

    def get_projections(self) -> tuple[Projection, ...]:
        return (ExtractionProjection(target=self.element, selector=(0,)),)


@dataclass(frozen=True, eq=False)
class ObjectType(GymOutputOnlyTypeFactory):
    model: type[pydantic.BaseModel] | None = None
    fields: tuple[tuple[str, Any], ...] = ()

    def from_str(self, s: str) -> pydantic.BaseModel:
        try:
            return self.model.model_validate(_parse(s))
        except pydantic.ValidationError as exc:
            raise TypeMaterializationError(f"Invalid {self!s} payload: {exc}") from exc

    def get_projections(self) -> tuple[Projection, ...]:
        return tuple(ExtractionProjection(target=target, selector=(name,)) for name, target in self.fields)

    def __post_init__(self) -> None:
        parent_post_init = getattr(super(), "__post_init__", None)
        if callable(parent_post_init):
            parent_post_init()
        validate_extraction_selectors(self, self.model)


_POOLS = {name: PoolType(name=name, values=tuple(values)) for name, values in _SPEC["pools"].items()}
_LISTS = {name: ListType(name=name, element=_POOLS[spec["element"]], min_items=spec["min_items"], max_items=spec["max_items"])
          for name, spec in _SPEC["lists"].items()}
_BY_NAME = {**_POOLS, **_LISTS}
_OBJECTS = {
    name: ObjectType(
        name=name,
        model=create_model(name, __config__=ConfigDict(frozen=True, extra="ignore"), **{f: (Any, None) for f in spec["fields"]}),
        fields=tuple((f, _BY_NAME[target]) for f, target in spec["fields"].items()),
    )
    for name, spec in _SPEC["objects"].items()
}

ALL_TYPES = (*_POOLS.values(), *_LISTS.values(), *_OBJECTS.values())
'''


def taken_type_names(dest: Path, own_folder: str) -> set[str]:
    """Type names other catalog servers and ToolGym's shared types already use."""
    files = [p for p in dest.glob("*/types.py") if p.parent.name != own_folder]
    files += [p for p in dest.glob("*/types.json") if p.parent.name != own_folder]
    shared = dest.parents[1] / "shared" / "types.py"
    names = set()
    for path in [*files, shared] if shared.is_file() else files:
        text = path.read_text(encoding="utf-8")
        names |= set(re.findall(r'name\s*=\s*"(\w+)"', text))
        if path.suffix == ".json":
            spec = json.loads(text)
            names |= {n for section in ("pools", "lists", "objects") for n in spec.get(section, {})}
    return names


def build_catalog(set_name: str, typing: Typing, outputs: dict, taken: set[str]) -> tuple[dict, dict]:
    """(mcp_server.json, types.json)."""
    rename: dict[str, str] = {}

    def final(name: str) -> str:
        if name not in rename:
            new = name
            while new in taken or new in rename.values():
                new += "X"
            rename[name] = new
        return rename[name]

    pools: dict[str, list] = {}
    lists: dict[str, dict] = {}
    objects: dict[str, dict] = {}

    def pool_type(name: str, values: list) -> str:
        pools.setdefault(final(name), values[:MAX_POOL])
        return final(name)

    def list_type(element: str, sizes: list[int]) -> str:
        name = final(element + "List")
        lists.setdefault(name, {"element": final(element), "min_items": 1, "max_items": 4})
        if sizes:
            lists[name]["min_items"] = max(1, min(lists[name]["min_items"], min(sizes)))
        return name

    shared_names = {name for kind, name in typing.param.values() if kind in ("one", "list")}
    for name in sorted(shared_names):
        pool_type(name, typing.pool(name))

    tools = []
    for tool, info in typing.tools.items():
        parameters = {}
        for param in info["input_schema"].get("properties", {}):
            if (tool, param) in typing.dropped:
                continue
            kind, name = typing.param[tool, param]
            if kind == "boolean":
                # its own type, not ToolGym's `boolean`: otherwise every true/false output links to every flag
                parameters[param] = pool_type(camel(tool) + camel(param), [False, True])
            elif kind == "private":
                parameters[param] = pool_type(name, typing.values(tool, param))
            elif kind == "one":
                parameters[param] = final(name)
            else:
                parameters[param] = list_type(name, [len(v) for v in typing.values(tool, param)])
        out = outputs[tool]
        if out["kind"] == "plain":
            output_type = out["type"]
        elif out["kind"] == "one":
            output_type = final(out["type"])
        elif out["kind"] == "list":
            output_type = list_type(out["type"], [])
        else:
            output_type = final(out["type"])
            objects[output_type] = {"fields": {f: (final(n) if k == "one" else list_type(n, [])) for f, (k, n) in out["fields"].items()}}
        schema = json.loads(json.dumps(info["input_schema"]))
        schema["properties"] = {p: v for p, v in schema.get("properties", {}).items() if p in parameters}
        schema["required"] = [p for p in schema.get("required", []) if p in parameters]
        tools.append({"mcp_spec": {"name": tool, "description": info["description"], "inputSchema": schema},
                      "gym_types": {"parameters": parameters, "output_type": output_type}})
    repo = "repo2tools/" + re.sub(r"[^a-z0-9]+", "-", set_name.lower()).strip("-")
    name = repo.replace("/", "_").replace("-", "_")
    return {"name": name, "repo": repo, "tools": tools}, {"pools": pools, "lists": lists, "objects": objects}


def links(server: dict, types: dict) -> list[tuple[str, str, str]]:
    """(from tool, to tool, how): the data-flow links these types give, without ToolGym's casts to plain types."""
    produces = defaultdict(list)  # type name -> [(tool, how)]
    for tool in server["tools"]:
        out = tool["gym_types"]["output_type"]
        name = tool["mcp_spec"]["name"]
        produces[out].append((name, "direct"))
        if out in types["lists"]:
            produces[types["lists"][out]["element"]].append((name, "first element"))
        for field, target in types["objects"].get(out, {}).get("fields", {}).items():
            produces[target].append((name, f"field {field}"))
            if target in types["lists"]:
                produces[types["lists"][target]["element"]].append((name, f"field {field}, first element"))
    semantic = set(types["pools"]) | set(types["lists"])
    found = []
    for tool in server["tools"]:
        for type_name in set(tool["gym_types"]["parameters"].values()):
            if type_name in semantic:
                found += [(source, tool["mcp_spec"]["name"], how) for source, how in produces.get(type_name, [])]
    return sorted(set(found))


def write_report(path: Path, set_name: str, model: str, typing: Typing, proposal: dict, param_log: list, output_log: list,
                 server: dict, types: dict, calls: int, skipped: list[str]) -> dict:
    proposed_names = {t[1] for p in proposal.values() for t in p["parameters"].values() if t}
    proposed_params = sum(bool(t) for p in proposal.values() for t in p["parameters"].values())
    kept_shared = {name for kind, name in typing.param.values() if kind in ("one", "list")}
    shared_params = sum(kind in ("one", "list") for kind, _ in typing.param.values())
    found = links(server, types)
    isolated = [t["mcp_spec"]["name"] for t in server["tools"]
                if not any(t["mcp_spec"]["name"] in (a, b) for a, b, _ in found)]
    summary = {"set": set_name, "model": model, "tools": len(server["tools"]), "tools_without_working_samples": skipped,
               "types_proposed": len(proposed_names), "types_kept": len(kept_shared),
               "parameters": len(typing.param), "parameters_with_proposed_type": proposed_params, "parameters_with_shared_type": shared_params,
               "parameter_claims_tested": len(param_log), "parameter_claims_withdrawn": sum(not e["kept"] for e in param_log),
               "output_claims": len(output_log), "output_claims_kept": sum(e["kept"] for e in output_log),
               "links": len(found), "linked_tool_pairs": len({(a, b) for a, b, _ in found}), "isolated_tools": isolated,
               "check_calls": calls, "parameter_checks": param_log, "output_checks": output_log,
               "links_list": [list(x) for x in found]}
    path.with_suffix(".json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    lines = [f"# ToolGym types for {set_name}", "",
             f"Types proposed by `{model}`, then checked by {calls} tool calls. A claim stands if at least {KEEP_RATE:.0%} of its test calls work.", "",
             "| | Count |", "| --- | --- |",
             f"| Tools exported | {len(server['tools'])} |",
             f"| Shared types proposed / kept | {len(proposed_names)} / {len(kept_shared)} |",
             f"| Parameters with a shared type: proposed / kept | {proposed_params} / {shared_params} |",
             f"| Parameter claims tested / withdrawn | {len(param_log)} / {summary['parameter_claims_withdrawn']} |",
             f"| Output claims / kept | {len(output_log)} / {summary['output_claims_kept']} |",
             f"| Data-flow links between tools | {len(found)}, over {summary['linked_tool_pairs']} tool pairs |",
             f"| Tools with no link | {len(isolated)} |", ""]
    if skipped:
        lines += [f"Left out, because no sample input worked: {', '.join(skipped)}.", ""]
    lines += ["## Types", "", "| Type | Examples | Parameters |", "| --- | --- | --- |"]
    for name in sorted(kept_shared):
        members = ", ".join(f"`{t}.{p}`" for t, p in typing.members(name))
        lines.append(f"| `{name}` | {len(typing.pool(name))} | {members} |")
    withdrawn = [e for e in param_log if not e["kept"]]
    if withdrawn:
        lines += ["", "## Withdrawn parameter claims", "", "| Parameter | Proposed type | Pairs that work |", "| --- | --- | --- |"]
        lines += [f"| `{e['tool']}.{e['parameter']}` | `{e['type']}` | {e['pairs_working']} of {e['pairs']} |" for e in withdrawn]
    lines += ["", "## Output claims", "", "| Tool | Claim | Worked | Kept |", "| --- | --- | --- | --- |"]
    lines += [f"| `{e['tool']}` | {e['output']} | {e['worked']} of {e['tried']} | {'yes' if e['kept'] else 'no' + (': ' + e['why'] if e.get('why') else '')} |" for e in output_log]
    lines += ["", "## Links", ""] + [f"- `{a}` → `{b}` ({how})" for a, b, how in found] + [""]
    path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return summary


async def export(toolset: Path, dest: Path, llm, seed: int = 0) -> dict:
    manifest = json.loads((toolset / "manifest.json").read_text())
    set_name = manifest["set"]
    rng = random.Random(seed)
    async with stdio_client(StdioServerParameters(command=str(toolset / "run_server.sh"), args=[])) as (read, write), \
            ClientSession(read, write) as session:
        await session.initialize()
        server = Server(session)
        tools = await observe(server, manifest)
        skipped = [name for name, tool in tools.items() if not tool["examples"]]
        tools = {name: tool for name, tool in tools.items() if tool["examples"]}
        chat = propose_messages(tools)
        proposal = None
        for _ in range(3):
            reply = await llm.chat("types", set_name, chat, max_tokens=8000)
            try:
                proposal = read_proposal(reply, tools)
                break
            except ValueError as e:
                chat += [{"role": "assistant", "content": reply}, {"role": "user", "content": f"{e}. Reply with the JSON object only."}]
        if proposal is None:
            raise SystemExit("the LLM gave no usable types")
        # object outputs: a second question, about their fields. An LLM tends to name the whole object
        # ("ParsedWheel"), which no parameter takes, so the object would give no links.
        objects = [name for name, tool in tools.items() if all(isinstance(e["output"], dict) for e in tool["examples"])
                   and not isinstance(proposal[name]["output"], dict)]
        if objects and any(t for p in proposal.values() for t in p["parameters"].values()):
            try:
                found = read_fields(await llm.chat("fields", set_name, fields_messages(tools, proposal, objects), max_tokens=3000), objects)
            except ValueError:
                found = {}
            for name, fields in found.items():
                proposal[name]["output"] = fields
        typing = Typing(tools, proposal)
        param_log = await check_parameters(server, typing, rng)
        outputs, output_log = await check_outputs(server, typing, proposal, rng)
        calls = server.calls

    folder_name = "repo2tools_" + re.sub(r"[^a-z0-9]+", "_", set_name.lower()).strip("_")
    server_json, types_json = build_catalog(set_name, typing, outputs, taken_type_names(dest, folder_name))
    assert server_json["name"] == folder_name
    folder = dest / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mcp_server.json").write_text(json.dumps(server_json, indent=2) + "\n", encoding="utf-8")
    (folder / "types.json").write_text(json.dumps(types_json, indent=1) + "\n", encoding="utf-8")
    (folder / "types.py").write_text(TYPES_PY, encoding="utf-8")
    (folder / "contribution.py").write_text(
        "from gym.tools.mcp_servers import ServerContribution\n\nfrom .types import ALL_TYPES\n\n"
        "SERVER_CONTRIBUTION = ServerContribution(types=ALL_TYPES)\n", encoding="utf-8")
    (folder / "__init__.py").write_text('from .contribution import SERVER_CONTRIBUTION\n\n__all__ = ["SERVER_CONTRIBUTION"]\n', encoding="utf-8")

    out = OUT / set_name
    out.mkdir(parents=True, exist_ok=True)
    (out / "toolgym_catalog.json").write_text(json.dumps({"mcp_server": server_json, "types": types_json}, indent=1), encoding="utf-8")
    summary = write_report(out / "toolgym_types", set_name, getattr(llm, "model", "unknown"), typing, proposal, param_log, output_log,
                           server_json, types_json, calls, skipped)
    print(f"{folder}\n{summary['tools']} tools; shared types {summary['types_proposed']} proposed, {summary['types_kept']} kept; "
          f"parameter claims {summary['parameter_claims_tested']} tested, {summary['parameter_claims_withdrawn']} withdrawn; "
          f"output claims {summary['output_claims_kept']} of {summary['output_claims']} kept; "
          f"{summary['links']} links, {len(summary['isolated_tools'])} tools with none")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("toolset", type=Path, help="a folder under toolsets/generated/")
    parser.add_argument("--dest", type=Path, required=True, help="the catalog folder of a ToolGym checkout")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--thinking", action="store_true")
    args = parser.parse_args()
    toolset = args.toolset.resolve()
    set_name = json.loads((toolset / "manifest.json").read_text())["set"]
    llm = LLM(args.base_url, args.model, args.thinking, 1, OUT / set_name / "toolgym_llm_log.jsonl")
    asyncio.run(export(toolset, args.dest.resolve(), llm))


if __name__ == "__main__":
    main()
