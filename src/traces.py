"""One format for agent traces: every request of a run, with its full messages and token counts.

A trace file has one JSON object per line, one per run of one task:

    schema       "repo2tools.trace/1"
    source       where it comes from: "reference" (a known-good solution replayed through the tools),
                 "model" (a model's run), later e.g. "alex" or "toolgym"
    task_id, task, kind, horizon   the task, if it comes from an exercise file
    model, tool_set                who solved it, with which tools
    tool_lists   {id: [tools]}: each distinct tool list once, in OpenAI function format
    requests     one entry per request to the model, in order:
        index, messages        everything sent, except the tools
        tool_list_id           which tool list went with it, or null
        tool_choice            "auto", "required", or null if no tools were offered
        response               the assistant message that came back
        finish_reason, seconds
        usage                  prompt_tokens, completion_tokens, total_tokens, and source: "server"
                               (the endpoint's count) or "tokenizer" (counted afterwards)
    outcome      passed, answer, finish, tool_calls, tool_errors
    meta         anything else, e.g. thinking on or off

`messages` repeats a growing history on purpose: the repetition in it is what we measure.

Other sources fit if they give a list of tool calls with their outputs: use trace_from_calls().
"""

import gzip
import hashlib
import json
from pathlib import Path

SCHEMA = "repo2tools.trace/1"


def tool_list_id(tools: list[dict]) -> str:
    return hashlib.sha256(json.dumps(tools, sort_keys=True).encode()).hexdigest()[:12]


def new_trace(source: str, task_id: str, task: str, tools: list[dict] | None, *, kind=None, horizon=None, model=None,
              tool_set=None, meta=None) -> dict:
    return {"schema": SCHEMA, "source": source, "task_id": task_id, "task": task, "kind": kind, "horizon": horizon,
            "model": model, "tool_set": tool_set, "tool_lists": {tool_list_id(tools): tools} if tools else {},
            "requests": [], "outcome": None, "meta": meta or {}}


def add_request(trace: dict, messages: list[dict], tools: list[dict] | None, tool_choice, response: dict,
                finish_reason, usage: dict | None, seconds: float | None = None, usage_source: str = "server") -> None:
    list_id = tool_list_id(tools) if tools else None
    if list_id and list_id not in trace["tool_lists"]:
        trace["tool_lists"][list_id] = tools
    trace["requests"].append({
        "index": len(trace["requests"]),
        "messages": json.loads(json.dumps(messages)),  # a copy: the run keeps adding to its list
        "tool_list_id": list_id, "tool_choice": tool_choice, "response": response, "finish_reason": finish_reason,
        "usage": {**usage, "source": usage_source} if usage else None,
        "seconds": None if seconds is None else round(seconds, 2)})


def trace_from_calls(source: str, task_id: str, task: str, system: str, tools: list[dict], calls: list[dict], final_answer: str,
                     *, outcome=None, **fields) -> dict:
    """Build a trace from recorded calls [{"tool", "arguments", "output"}], one call per request.

    For runs that were not recorded request by request: known-good solutions, ToolGym chains, other harnesses.
    Token counts are left out; analyze_traces.py counts them. One call per request is the most
    expensive way to run the calls: a model that groups calls sends fewer requests.
    """
    trace = new_trace(source, task_id, task, tools, **fields)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    for i, call in enumerate(calls):
        assistant = {"role": "assistant", "content": "", "tool_calls": [
            {"id": f"call_{i}", "type": "function",
             "function": {"name": call["tool"], "arguments": json.dumps(call["arguments"])}}]}
        add_request(trace, messages, tools, "auto", assistant, "tool_calls", None)
        messages = [*messages, assistant, {"role": "tool", "tool_call_id": f"call_{i}", "content": call["output"]}]
    add_request(trace, messages, tools, "auto", {"role": "assistant", "content": final_answer}, "stop", None)
    trace["outcome"] = outcome
    return trace


def write_traces(path: Path, traces: list[dict]) -> None:
    """Write a trace file; a name ending in .gz is compressed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with (gzip.open if path.suffix == ".gz" else open)(path, "wt", encoding="utf-8") as f:
        for trace in traces:
            f.write(json.dumps(trace) + "\n")


def read_traces(path: Path) -> list[dict]:
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt", encoding="utf-8") as f:
        traces = [json.loads(line) for line in f]
    for trace in traces:
        if trace.get("schema") != SCHEMA:
            raise ValueError(f"{path}: not a {SCHEMA} file")
    return traces
