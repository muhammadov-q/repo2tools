# repo2tools

Turn a Python repository into tools an AI model can call, and measure how well models use those tools.

Tool-Gym track of the "Agentic Reasoning, Tooling" project at the University of Bern. Author: Kobiljon Muhammadov. Supervisor: Roman Macháček.

## Status

| Part | State |
| --- | --- |
| Scan a repo's public functions (`scrape_repo.py`) | Works |
| Tools over pypa/packaging: 21 small, 2 coarser | Work; written with Claude in a chat, not generated automatically |
| MCP server for those tools | Works |
| 242 exercises with known answers | Work |
| Run a model with or without tools, and score it | Works |
| Export the tools to ToolGym's catalog | Works; ToolGym's own checks accept all 21 tools |
| `repo2tools.py <url>`: repo link in, generated tools out | Built and tested with a scripted LLM; first run with a real model is pending |
| Trace collection (`traces.py`, `run_model.py`, `collect_reference_traces.py`) | Works for known-good solutions; model runs pending |
| Repetition analysis (`analyze_traces.py`) | Works on known-good solutions; model runs pending |
| Context compression in a real run | Only simulated so far |

## Results so far

Qwen3-8B served with vLLM on an RTX 4090, 30 October 2026, temperature 0, one run per exercise. Details in `out/runs/`.

| Exercises | With tools | Without tools |
| --- | --- | --- |
| Short (222, 1 tool call) | 94% | 60% |
| Long (20, 10 to 23 tool calls) | 0 of 20 | 0 of 20 |
| Long, model may think first | 12 of 20, with 0 tool calls | 10 of 20 |

The same 20 long tasks with tools of different sizes (thinking off):

| Tool set | Calls a task needs | Passed |
| --- | --- | --- |
| 21 small tools | 10 to 23 | 0 of 20 |
| 1 tool per requirement line | 4 to 6 | 1 of 20 |
| 1 tool for the whole task | 1 | 16 of 20 |
| All 23 together | 1 | 16 of 20 |

These are first results: one small model, one run, and 20 long tasks of one kind.

## Quick start

Needs [uv](https://docs.astral.sh/uv/). This replays a known-good solution for every exercise through the tools:

```sh
uv run python run_reference_calls.py out/packaging/exercises.jsonl -- uv run python toolsets/pypa_packaging/server.py
```

The last line should say `242/242 exercises solved by their reference calls`.

To run a model, start an OpenAI-compatible server with tool calling. `cluster/README.md` shows how on UBELIX. Then:

```sh
export OPENAI_API_KEY=<the server's key>
uv run python run_model.py out/packaging/exercises.jsonl --mode tools --base-url http://127.0.0.1:18000/v1 --model qwen3-8b -- uv run python toolsets/pypa_packaging/server.py
uv run python run_model.py out/packaging/exercises.jsonl --mode none --base-url http://127.0.0.1:18000/v1 --model qwen3-8b
python3 -I compare_runs.py out/runs/qwen3-8b-tools.jsonl out/runs/qwen3-8b-none.jsonl
```

## From a repo link to tools

```sh
uv run python repo2tools.py https://github.com/pypa/packaging --commit c1d2a9d \
    --base-url http://127.0.0.1:18000/v1 --model qwen3-8b
```

It clones the repo at a recorded commit, finds the package (`src/` layout or top level), and scrapes its public API. Then, for up to `--max-tools` functions, an LLM writes a test and the code, one tool per library function. Each tool must pass these checks, with errors going back to the LLM for a few repair rounds (`--repair-rounds`):

| Check | What it means |
| --- | --- |
| `static` | Read without running: one public function, type hints, a docstring, no dangerous imports |
| `loads` | The file imports |
| `fastmcp` | FastMCP accepts it, with the agreed parameters |
| `runs` | It runs on the sample inputs; bad input gives `ValueError`, not a crash |
| `differential` | Same result as a direct library call on the same input |

The result goes to `toolsets/generated/<repo>-<model>/` (one file per tool, `server.py`, `run_server.sh`, `manifest.json`) and `out/generated/<repo>-<model>/` (`report.md`, `api.json`, and `llm_log.jsonl` with every LLM request). First version: pure-Python libraries, one tool per function.

**Limits of the checks.** The same model writes the tool and the direct call it is compared with, in separate requests, so the two can share a misunderstanding of the library. The check also sees only what the sample inputs reach: a tool that drops a requirement's extras passes if no sample has extras. A real score needs exercises with known answers.

**Untrusted code.** Repo code and generated code run only in their own environment under `.cache/envs/`:

- Only repos you name are cloned. The repo is never built or installed: its dependencies come as wheels (`--no-build`), and the package is copied in, so no `setup.py` runs.
- Generated code gets an empty environment, so no API keys.
- On macOS it runs inside `sandbox-exec`: no network, no reading the home folder (SSH keys, the API key), writing only to one scratch folder. `tests/test_repo2tools.py` runs hostile code to check this.
- Other systems have no such sandbox. The tool then warns, and the report says so. Only use repos you trust there.

To score generated tools on exercises, use `run_model.py` with `run_server.sh` as the server command. `run_reference_calls.py` needs the hand-made tool names, so it doesn't work on generated tools.

## Traces and repetition

A trace records every request of a run, with its full messages and token counts. `traces.py` describes the format. There's one format for all sources, and anything with a list of tool calls and outputs can be added with `trace_from_calls()`.

```sh
# known-good solutions, no model (the file is 4.6 MB, so it isn't committed)
uv run python collect_reference_traces.py out/packaging/exercises.jsonl -o out/traces/reference-function.jsonl -- uv run python toolsets/pypa_packaging/server.py

# model runs save traces to out/traces/. --tool-choice first|always forces tool use
uv run python run_model.py out/packaging/exercises.jsonl --mode tools --horizon long --tool-choice always \
    --base-url http://127.0.0.1:18000/v1 --model qwen3-8b -- uv run python toolsets/pypa_packaging/server.py

# what repeats, and how many tokens each compression idea would save
uv run --group analysis python analyze_traces.py out/traces/reference-function.jsonl out/traces/*.gz -o out/traces/analysis
```

The analysis counts tokens with the model's own tokenizer and chat template. The parts of a prompt add up to exactly the rendered prompt. Savings are simulated on recorded runs, and their effect on accuracy is not measured.

## Tests

```sh
uv run --group dev --group analysis pytest
```

No GPU or API key needed. The LLM and the endpoint are scripted.

## What's here

| Path | What it does |
| --- | --- |
| `repo2tools.py` | Repo link to checked tools; see above. |
| `tool_worker.py` | Checks one generated tool. It runs inside the tool set's environment and sandbox. |
| `traces.py` | The trace format. |
| `collect_reference_traces.py`, `analyze_traces.py` | Known-good solutions as traces; what repeats and what compression would save. |
| `scrape_repo.py` | Static `ast` scan of a package's public API: signatures, types, defaults, docstrings, source location. Never imports the package. |
| `toolsets/pypa_packaging/tools.py` | 21 tools over pypa/packaging (versions, version constraints, requirements, markers, names, wheel files, tags). `GYM_TYPES` holds their ToolGym types. |
| `toolsets/pypa_packaging/coarse_tools.py` | The same library cut coarser: `check_requirement` (one requirement line) and `check_requirements` (a whole list). |
| `toolsets/pypa_packaging/server.py` | Serves the tools over MCP (stdio, or Streamable HTTP with `--http PORT`). `--level function\|feature\|workflow\|all` picks the tool set. |
| `extract_test_cases.py` | pytest plugin: writes the parameters of every collected test case as JSON lines. Collection only; no tests run. |
| `make_packaging_exercises.py` | Builds the exercises. Short ones come from packaging's test cases; the answer is the test's expected value, confirmed by a direct library call. Long ones check a requirements list against a made-up package index. |
| `exercise_check.py` | Stdlib-only answer checker and `$ref` resolver, for any harness that runs the exercises. |
| `run_reference_calls.py` | Replays every known-good solution through an MCP server and checks the answers. This tests the tools, not a model. |
| `run_model.py`, `compare_runs.py` | Run a model on the exercises, and put two runs side by side. |
| `make_handover.py`, `handover/README.md` | Build a self-contained zip of the exercises and tools for Alex's benchmark. |
| `toolsets/pypa_packaging/toolgym_types.py`, `export_toolgym_catalog.py` | Write the tools into a ToolGym checkout as a catalog server. This repo contains no ToolGym code. |
| `analyze_catalog_chains.py`, `check_exercise_edges.py` | Summarise ToolGym's chain listings, and check that the links the exercises need are in ToolGym's graph. |
| `cluster/` | How to serve a model on UBELIX, with the Slurm job script. |
| `out/` | Results: `baseline/` (ToolGym's catalog today), `packaging/` (API, exercises, tool check), `packaging_toolgym/` (ToolGym's view of our tools), `runs/` (model runs). |

## Rebuild from source

These steps need clones next to this repo: `../source-repos/packaging` (pypa/packaging at `c1d2a9d`), `../source-repos/arrow`, and `../tool-gym` (private, ask Roman for access).

```sh
# scrape a public API
python3 -I scrape_repo.py ../source-repos/arrow arrow -o out/arrow_api.json
python3 -I scrape_repo.py ../source-repos/packaging/src packaging -o out/packaging/api.json

# ToolGym's catalog today (offline; no LLM, no servers)
(cd ../tool-gym && uv run python -m gym.tools.mcp_servers.check --no-report-file) > out/baseline/check.txt
(cd ../tool-gym && uv run python -m gym.tools.mcp_servers.chain_check --dry-run) > out/baseline/chains.txt
python3 -I analyze_catalog_chains.py out/baseline/check.txt out/baseline/chains.txt

# packaging: test cases, then exercises (test_cases.jsonl is 17 MB and not committed)
(cd ../source-repos/packaging && PYTHONPATH="$OLDPWD:src" TEST_CASES_OUT="$OLDPWD/out/packaging/test_cases.jsonl" \
    uvx --with pretend --with tomli_w pytest --collect-only -q -p no:cacheprovider -p extract_test_cases tests --ignore=tests/property)
uv run python make_packaging_exercises.py --per-kind 20 --long 20 --seed 0

# add the tools to ToolGym, then see which links it finds
uv run python export_toolgym_catalog.py --dest ../tool-gym/gym/tools/mcp_servers/catalog
(cd ../tool-gym && uv run python -m gym.tools.mcp_servers.chain_check --dry-run kobiljon_pypa_packaging_tools) > out/packaging_toolgym/chains_packaging.txt
python3 -I check_exercise_edges.py out/packaging_toolgym/chains_packaging.txt out/packaging/exercises.jsonl \
    ../tool-gym/gym/tools/mcp_servers/catalog/kobiljon_pypa_packaging_tools/mcp_server.json
```

## Exercise format (one JSON object per line)

| Field | Meaning |
| --- | --- |
| `id`, `kind` | e.g. `packaging-specifier_contains-007`, `specifier_contains` |
| `horizon` | `short` (1 call) or `long` (8+ calls in the reference solution) |
| `task` | The task in plain language, as given to the model |
| `answer`, `check` | The correct answer (a JSON value) and how to compare: `exact` (canonical JSON, so `true` ≠ `1`) or `set_equal` (lists, order ignored) |
| `reference_calls` | One known-good solution: `[{"tool", "arguments"}]`. `{"$ref": [i, key...]}` refers to the output of call `i` |
| `reference_answer` | How the answer is built from those outputs |
| `reference_call_count` | Length of the reference solution; a model may need more or fewer calls |
| `library_functions` | Library functions the task depends on |
| `source_repo`, `provenance` | Repo and commit, and where the answer comes from (test case node id, or generator) |

A harness gives the model `task` plus a tool set (these tools, another granularity, distractors, or none), parses the model's final JSON answer, and calls `exercise_check.check(exercise, answer)`. The answer never depends on the tool set, so different tool sets can be compared on the same exercises.
