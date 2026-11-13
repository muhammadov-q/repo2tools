"""Write the pypa/packaging tools into ToolGym's catalog as one server folder.

    uv run python src/export_toolgym_catalog.py --dest ../tool-gym/gym/tools/mcp_servers/catalog

The folder gets mcp_server.json (each tool's MCP spec from our server plus its GYM_TYPES),
types.py (a copy of toolsets/pypa_packaging/toolgym_types.py), samples.json (sample pools from
packaging's test cases and our exercises), contribution.py and __init__.py. ToolGym then reaches
the running server through CSCS_MCP_URL_TEMPLATE, e.g. http://127.0.0.1:8765/mcp.
"""

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from packaging.markers import Marker
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_sdist_filename, parse_wheel_filename

HERE = Path(__file__).resolve().parent.parent  # the repository's root
TOOLSET = HERE / "toolsets" / "pypa_packaging"
sys.path.insert(0, str(TOOLSET))
from server import add_tools, mcp  # noqa: E402
from tools import GYM_TYPES  # noqa: E402

from make_packaging_exercises import INDEX, MARKERS, PLATFORMS, SPELLINGS  # noqa: E402

REPO = "kobiljon/pypa-packaging-tools"
NAME = REPO.replace("/", "_").replace("-", "_")  # ToolGym's catalog name for an owner/repo
PLATFORM_TAGS = ["manylinux_2_17_x86_64", "manylinux_2_28_aarch64", "musllinux_1_2_x86_64",
                 "macosx_11_0_arm64", "macosx_10_9_x86_64", "win_amd64", "linux_x86_64"]
PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]


def unique(items) -> list:
    return list(dict.fromkeys(items))


def samples() -> dict:
    cases = [json.loads(line) for line in open(HERE / "out" / "packaging" / "test_cases.jsonl")]
    exercises = [json.loads(line) for line in open(HERE / "out" / "packaging" / "exercises.jsonl")]

    def params(test, key):
        return [c["params"][key] for c in cases if c["test"] == test and isinstance(c["params"].get(key), str)]

    def valid(items, check):
        out = []
        for item in items:
            try:
                check(item)
            except Exception:  # noqa: BLE001  (any parse error means: not a usable sample)
                continue
            out.append(item)
        return unique(out)

    wheels = [*params("test_parse_wheel_filename", "filename"),
              *(f"{n.replace('-', '_')}-{v}-py3-none-any.whl" for n in ("requests", "typing-extensions", "tomli") for v in INDEX[n][:3]),
              *(f"numpy-{v}-cp312-cp312-{p}.whl" for v in INDEX["numpy"][1:4] for p in PLATFORM_TAGS[:4])]
    wheels = valid(wheels, parse_wheel_filename)
    return {
        "versions": unique([*params("test_valid_versions", "version"), *(v for vs in INDEX.values() for v in vs)]),
        "specifiers": valid([*params("test_specifiers", "spec_str"), *params("test_contains_exclusionary_bridges", "specifier"),
                             *params("test_is_subset", "left")], SpecifierSet),
        "requirements": unique(c["arguments"]["requirement"] for ex in exercises for c in ex["reference_calls"]
                               if c["tool"] == "parse_requirement"),
        "markers": valid([*MARKERS, *params("test_evaluates", "marker_string")], Marker),
        "project_names": unique([*(s for spellings in SPELLINGS.values() for s in spellings), *INDEX]),
        "package_names": unique(canonicalize_name(n) for n in INDEX),
        "wheel_filenames": wheels,
        "sdist_filenames": valid((f"{n.replace('-', '_')}-{v}.tar.gz" for n in INDEX for v in INDEX[n][-2:]), parse_sdist_filename),
        "wheel_tags": unique([*(str(t) for w in wheels for t in parse_wheel_filename(w)[3]), "py2.py3-none-any"]),
        "platform_tags": PLATFORM_TAGS,
        "python_versions": PYTHON_VERSIONS,
        "environments": [{"python_version": py, "python_full_version": f"{py}.0", "sys_platform": sp, "os_name": os_name,
                          "platform_system": system, "platform_machine": machines[0]}
                         for py in PYTHON_VERSIONS for sp, (_, os_name, system, machines) in PLATFORMS.items()],
    }


async def server_spec() -> dict:
    add_tools("function")
    tools = []
    for tool in await mcp.list_tools():
        parameters, output_type = GYM_TYPES[tool.name]
        assert set(parameters) == set(tool.inputSchema["properties"]), tool.name
        tools.append({
            "mcp_spec": {"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema},
            "gym_types": {"parameters": parameters, "output_type": output_type},
        })
    return {"name": NAME, "repo": REPO, "tools": tools}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", type=Path, required=True, help="the catalog folder of a ToolGym checkout")
    args = parser.parse_args()

    folder = args.dest / NAME
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mcp_server.json").write_text(json.dumps(asyncio.run(server_spec()), indent=2) + "\n")
    (folder / "samples.json").write_text(json.dumps(samples(), indent=1) + "\n")
    shutil.copy2(TOOLSET / "toolgym_types.py", folder / "types.py")
    (folder / "contribution.py").write_text(
        "from gym.tools.mcp_servers import ServerContribution\n\nfrom .types import ALL_TYPES\n\n"
        "SERVER_CONTRIBUTION = ServerContribution(types=ALL_TYPES)\n")
    (folder / "__init__.py").write_text('from .contribution import SERVER_CONTRIBUTION\n\n__all__ = ["SERVER_CONTRIBUTION"]\n')
    pools = json.loads((folder / "samples.json").read_text())
    print(f"{folder}\n" + ", ".join(f"{k} {len(v)}" for k, v in pools.items()))


if __name__ == "__main__":
    main()
