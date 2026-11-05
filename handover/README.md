# packaging exercises, version 0

Exercises for measuring tools synthesized from [pypa/packaging](https://github.com/pypa/packaging), the library behind Python's version and dependency rules (pip uses it). From Kobiljon's Tool-Gym track.

## What's inside

| File | What it is |
| --- | --- |
| `exercises.jsonl` | 242 exercises, one JSON object per line: 222 short (1 tool call), 20 long (10 to 23 calls) |
| `exercises_preview.md` | One readable example of each of the 14 kinds |
| `tools.py`, `server.py` | The 21 tools and an MCP server for them (stdio, or Streamable HTTP) |
| `exercise_check.py` | The answer checker. Stdlib only, so you can copy it into any harness |
| `run_reference_calls.py` | Plays each exercise's known-good solution through the server and checks it. A worked example of the loop |
| `pyproject.toml` | uv project: `mcp` 1.x and packaging at the exact commit the exercises come from |

## Check that it runs (needs `uv`)

```sh
uv run python run_reference_calls.py exercises.jsonl -- uv run python server.py
```

Expected last line: `242/242 exercises solved by their reference calls`.

## Where the answers come from

- **Short exercises:** each one is a test case from packaging's own test suite. The answer is the test's expected value, and a direct library call agrees.
- **Long exercises:** a requirements list is checked against a small made-up package index. The answer comes from direct library calls.
- So the answers never depend on the tools. You can score any tool set on the same exercises: these tools, coarser or finer tools, extra distractor tools, or no tools at all.

## Evaluating a model

1. Start the tools: `uv run python server.py` (stdio), or `uv run python server.py --http 8765`, which serves `http://127.0.0.1:8765/mcp`.
2. For each exercise, give the model `task` plus the tool list from MCP `tools/list`.
3. Run the model's tool calls through MCP until it gives a final answer.
4. Parse the final answer as a JSON value (true/false, a number, a string, a list or an object).
5. Score it with `exercise_check.check(exercise, answer)`, which returns true or false.

Useful numbers per `kind` and `horizon`:
- success rate;
- number of tool calls;
- invalid calls (tool errors);
- whether the model picked the tools in `reference_calls`, which is a tool-retrieval signal;
- the same run without tools, as a baseline.

## Exercise fields

| Field | Meaning |
| --- | --- |
| `id`, `kind` | e.g. `packaging-specifier_contains-007`, `specifier_contains` |
| `horizon` | `short` (1 call) or `long` (8+ calls in the reference solution) |
| `task` | The task in plain language, as given to the model |
| `answer`, `check` | The correct answer and how to compare: `exact` (canonical JSON, so `true` is not `1`) or `set_equal` (a list, order ignored) |
| `reference_calls` | One known-good solution: `[{"tool", "arguments"}]`. `{"$ref": [i, key...]}` means "the output of call i" |
| `reference_answer` | How the answer is built from those outputs |
| `reference_call_count` | Length of the reference solution. A model may need more or fewer calls |
| `library_functions` | Library functions the task depends on |
| `source_repo`, `provenance` | Repo and commit; the test case or generator the answer comes from |

## Known limits

- The task texts come from templates, so they read a bit uniform. An LLM paraphrase step comes later.
- The long exercises use a made-up package index, not real PyPI data.
- 6 of the 21 tools aren't needed by any exercise yet. They act as distractors.
