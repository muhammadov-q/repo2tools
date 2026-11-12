"""Set up ToolGym to run on tools served from this computer, and run its checks or its pipeline.

    uv run python toolgym_local.py install ../tool-gym
    uv run python toolgym_local.py chains ../tool-gym repo2tools_packaging_coder_60 --tool-server toolsets/generated/packaging-coder-60/run_server.sh
    uv run python toolgym_local.py generate ../tool-gym repo2tools_packaging_coder_60 --tool-server ... \\
        --base-url http://127.0.0.1:18000/v1 --model qwen3-32b --min-length 2 --max-length 4 --chains 20

ToolGym's tracked code runs tools in Podman containers or on the CSCS cluster. `install` makes
local variants in ToolGym's own `local/` folders, which its .gitignore leaves out, so the checkout
stays clean:

  gym/tools/mcp_servers/chain_check/local/composition.py   the 2-step chain check, over HTTP
  gym/generation/pipelines/local/repo2tools/               the `basic` pipeline, over HTTP, with
                                                           the server, chain length and number of
                                                           chains taken from environment variables;
                                                           it can drop chains that loop on a tool,
                                                           and it saves every entry as JSON

The variants are made by copying ToolGym's files and replacing a few lines. If ToolGym changes so
that a line is no longer found, `install` stops and says which. This repo holds no ToolGym code.

`chains` and `generate` start the tool server (`--tool-server`, with `--http PORT`), point ToolGym
at it through CSCS_MCP_URL_TEMPLATE, run, and stop the server. The API key for `generate` comes
from $OPENAI_API_KEY or .vllm_api_key, and is passed to ToolGym in the environment, not in a file.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8765

CHAIN_CHECK = [
    ("from gym.tools.executors.podman import PodmanToolExecutor\n",
     "from gym.tools.executors.cscs import CscsServerEntry, CscsToolExecutor, build_cscs_url_map\n"
     "from gym.tools.mcp_servers import discover\n"),
    ("    port = PodmanToolExecutor(timeout_seconds=TIMEOUT)\n",
     "    entries = [CscsServerEntry.from_repo(e.server.repo) for e in discover() if e.server.repo is not None]\n"
     "    port = CscsToolExecutor(url_map=build_cscs_url_map(entries), timeout_seconds=TIMEOUT)\n"),
]
PIPELINE = {
    "pipeline.py": [
        ("from data_gen.pipelines import Pipeline, PipelineBuilder\n",
         "import os\nfrom collections import Counter\n\nfrom data_gen.pipelines import FilterEdge, Pipeline, PipelineBuilder\n"),
        # drop chains that loop: a random walk on a small graph likes to call one tool again and again
        ("        .then(build_template_edge(shared))\n",
         "        .then(FilterEdge(inner=build_template_edge(shared), predicate=_no_loops))\n"),
        ("def build_pipeline(\n",
         "MAX_TOOL_USES = int(os.environ.get(\"REPO2TOOLS_MAX_TOOL_USES\", \"0\"))  # 0 = no limit\n\n\n"
         "def _no_loops(entry) -> bool:\n"
         "    names = [step.tool.name for step in entry.trace_template.steps]\n"
         "    if not MAX_TOOL_USES:\n"
         "        return True\n"
         "    in_a_row = any(a == b for a, b in zip(names, names[1:]))\n"
         "    return not in_a_row and max(Counter(names).values()) <= MAX_TOOL_USES\n\n\n"
         "def build_pipeline(\n"),
        ("INCLUDE_SERVERS: list[str] | None = None  # None = every discovered server\n",
         'INCLUDE_SERVERS: list[str] | None = os.environ["REPO2TOOLS_SERVERS"].split(",")\n'),
        ('NAME = "basic-default"\n', 'NAME = os.environ.get("REPO2TOOLS_RUN_NAME", "repo2tools")\n'),
    ],
    "persistence.py": [('OUTPUT_ROOT = Path("results/gym/basic")\n', 'OUTPUT_ROOT = Path("results/gym/repo2tools")\n')],
    "stages/sig.py": [
        ("from data_gen.pipelines import NamedEdge, wrap\n", "import os\n\nfrom data_gen.pipelines import NamedEdge, wrap\n"),
        ("N_FANOUT = 2\n", 'N_FANOUT = int(os.environ.get("REPO2TOOLS_CHAINS", "2"))\n'),
        ("N_STEPS = 7\n", 'N_STEPS = int(os.environ.get("REPO2TOOLS_WALK_STEPS", "7"))\n'),
        ("MIN_TRACE_LENGTH: int | None = None\n", 'MIN_TRACE_LENGTH: int | None = int(os.environ.get("REPO2TOOLS_MIN_LENGTH", "1"))\n'),
        ("MAX_TRACE_LENGTH = 4\n", 'MAX_TRACE_LENGTH = int(os.environ.get("REPO2TOOLS_MAX_LENGTH", "4"))\n'),
    ],
    "reporting.py": [  # also save every entry as JSON, for toolgym_traces.py
        ("from pathlib import Path\n", "import json\nfrom pathlib import Path\n"),
        ("from data_gen.pipelines.basic.stages.apertus_format import ApertusFormattedEntry\n",
         "from data_gen.pipelines.basic.stages.apertus_format import ApertusFormattedEntry\n"
         "from data_gen.pipelines.basic.stages.apertus_format.schemas import encode_apertus_record\n"),
        ('        render_apertus_entry_md(entry), encoding="utf-8"\n    )\n',
         '        render_apertus_entry_md(entry), encoding="utf-8"\n    )\n'
         '    data = {"uuid": entry.uuid, "passed": entry.validation.passed, "answer": entry.answer.text,\n'
         '            "steps": [{"tool": s.tool_name, "server": s.server_name, "arguments": s.args, "output": s.result}\n'
         '                      for s in entry.executed_trace.steps],\n'
         '            "distractors": len(entry.distractor_tools), "record": encode_apertus_record(entry.apertus_record)}\n'
         '    (entries_dir / f"entry_{entry.uuid}.json").write_text(json.dumps(data, default=str), encoding="utf-8")\n'),
    ],
    "stages/apertus.py": [  # ToolGym @ c136f8d: a chain whose last output is an empty list raises ValueError and ends the run
        ('        name="apertus",\n', '        name="apertus",\n        catch={"on": (ValueError,)},\n'),
    ],
    "stages/post_validation.py": [
        ("from gym.tools.executors.podman import PodmanToolExecutor\n", ""),
        ("        tool_executor=PodmanToolExecutor(timeout_seconds=None),\n", "        tool_executor=shared.tool_port,\n"),
    ],
}


def patched(text: str, replacements: list[tuple[str, str]], where: str) -> str:
    for old, new in replacements:
        if text.count(old) != 1:
            raise SystemExit(f"{where}: expected exactly one line {old.strip()!r}. ToolGym has changed; update toolgym_local.py.")
        text = text.replace(old, new)
    return text


def install(toolgym: Path) -> None:
    chain = toolgym / "gym/tools/mcp_servers/chain_check"
    source = chain / "composition.py"
    (chain / "local/composition.py").write_text(patched(source.read_text(), CHAIN_CHECK, str(source)))
    basic = toolgym / "gym/generation/pipelines/basic"
    local = toolgym / "gym/generation/pipelines/local"
    target = local / "repo2tools"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(basic, target, ignore=shutil.ignore_patterns("__pycache__", "README.md"))
    (local / "__init__.py").touch()
    for name, replacements in PIPELINE.items():
        path = target / name
        path.write_text(patched(path.read_text(), replacements, str(basic / name)))
    print(f"installed: {chain / 'local/composition.py'}\ninstalled: {target}")


class ToolServer:
    """The tool set's own server on http://127.0.0.1:PORT/mcp, for as long as the block runs."""

    def __init__(self, command: Path, port: int):
        self.command, self.port, self.process = command, port, None

    def __enter__(self):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", self.port)) == 0:
                raise SystemExit(f"port {self.port} is already in use")
        self.process = subprocess.Popen([str(self.command), "--http", str(self.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", self.port)) == 0:
                    return self
            if self.process.poll() is not None:
                break
            time.sleep(0.1)
        raise SystemExit(f"the tool server did not start: {self.command}")

    def __exit__(self, *exc):
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()


def api_key(base_url: str) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    keyfile = HERE / ".vllm_api_key"
    if not key and "127.0.0.1" in base_url and keyfile.is_file():
        key = keyfile.read_text().strip()
    if not key:
        raise SystemExit("set OPENAI_API_KEY")
    return key


def run_in_toolgym(toolgym: Path, module: str, arguments: list[str], env: dict, tool_server: Path, port: int) -> int:
    environment = {**os.environ, **env, "CSCS_MCP_URL_TEMPLATE": f"http://127.0.0.1:{port}/mcp"}
    environment.pop("VIRTUAL_ENV", None)  # ToolGym has its own environment
    with ToolServer(tool_server.resolve(), port):
        return subprocess.run(["uv", "run", "python", "-m", module, *arguments], cwd=toolgym, env=environment).returncode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "chains", "generate"):
        sub = commands.add_parser(name)
        sub.add_argument("toolgym", type=Path, help="a ToolGym checkout")
        if name == "install":
            continue
        sub.add_argument("server", help="the catalog name, e.g. repo2tools_packaging_coder_60")
        sub.add_argument("--tool-server", type=Path, required=True, help="the tool set's run_server.sh")
        sub.add_argument("--port", type=int, default=PORT)
        if name == "chains":
            sub.add_argument("--dry-run", action="store_true", help="list the chains without running them")
        else:
            sub.add_argument("--base-url", required=True)
            sub.add_argument("--model", required=True)
            sub.add_argument("--min-length", type=int, default=2)
            sub.add_argument("--max-length", type=int, default=4)
            sub.add_argument("--chains", type=int, default=20, help="how many chains to sample")
            sub.add_argument("--walk-steps", type=int, help="length of the random walk a chain is cut from; default: 3 x max length")
            sub.add_argument("--max-tool-uses", type=int, default=0,
                             help="drop chains that call a tool twice in a row, or more often than this in total; 0 keeps all")
            sub.add_argument("--run-name")
    args = parser.parse_args()
    toolgym = args.toolgym.resolve()
    if args.command == "install":
        install(toolgym)
    elif args.command == "chains":
        sys.exit(run_in_toolgym(toolgym, "gym.tools.mcp_servers.chain_check.local", [*(["--dry-run"] if args.dry_run else []), args.server],
                                {}, args.tool_server, args.port))
    else:
        env = {"LLM_ENDPOINT": args.base_url, "LLM_MODEL": args.model, "LLM_API_KEY": api_key(args.base_url),
               "REPO2TOOLS_SERVERS": args.server, "REPO2TOOLS_CHAINS": str(args.chains),
               "REPO2TOOLS_MIN_LENGTH": str(args.min_length), "REPO2TOOLS_MAX_LENGTH": str(args.max_length),
               "REPO2TOOLS_WALK_STEPS": str(args.walk_steps or 3 * args.max_length),
               "REPO2TOOLS_MAX_TOOL_USES": str(args.max_tool_uses),
               "REPO2TOOLS_RUN_NAME": args.run_name or f"{args.server}-len{args.min_length}-{args.max_length}"}
        sys.exit(run_in_toolgym(toolgym, "gym.generation.pipelines.local.repo2tools", [], env, args.tool_server, args.port))


if __name__ == "__main__":
    main()
