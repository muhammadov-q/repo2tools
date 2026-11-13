"""Tests for the trace format, forced tool use in `repo2tools run-model`, and `repo2tools analyze-traces`. No model, no network."""

import asyncio
import json
from argparse import Namespace
from types import SimpleNamespace

from openai.types.chat import ChatCompletion

from repo2tools.evaluation import run_model
from repo2tools.traces.analyze import Change, analyze, exact_repeats, flows, measure, merge_change, occurrences, prompts, repeated_arguments, sequences
from repo2tools.traces.format import SCHEMA, read_traces, tool_list_id, trace_from_calls, write_traces


class WordTokenizer:
    """Counts words in a simple rendering. Enough to test the arithmetic."""

    def text(self, text):
        return len(str(text).split())

    def prompt(self, messages, tools, thinking, generation_prompt):
        total = 2 if generation_prompt else 0
        total += sum(len(json.dumps(t).split()) for t in tools or [])
        for m in messages:
            total += 1 + self.text(m.get("content") or "")
            for c in m.get("tool_calls") or []:
                total += 1 + self.text(c["function"]["name"]) + self.text(c["function"]["arguments"])
        return total


def tool(name):
    return {"type": "function", "function": {"name": name, "description": f"The {name} tool does things", "parameters": {}}}


TOOLS = [tool(n) for n in ("parse", "filter", "sort", "evaluate", "other_a", "other_b", "other_c")]


def workflow_trace(lines=3, outputs=None):
    """parse a requirement, filter with its constraint, sort the result; for several lines."""
    calls = []
    for i in range(lines):
        constraint = f">={i}.0"
        versions = [f"{i}.{j} long version text here" for j in range(3)]
        calls += [{"tool": "parse", "arguments": {"line": f"lib{i}{constraint}"}, "output": json.dumps({"name": f"lib{i}", "constraint": constraint})},
                  {"tool": "filter", "arguments": {"versions": versions, "constraint": constraint}, "output": json.dumps(versions[1:])},
                  {"tool": "sort", "arguments": {"versions": versions[1:]}, "output": json.dumps(versions[2:] + versions[1:2])}]
    return trace_from_calls("reference", "t1", "Find the newest versions please", "You are helpful", TOOLS, calls, '"done"', horizon="long", kind="k", meta={"thinking": False})


def test_trace_round_trip_keeps_every_request(tmp_path):
    trace = workflow_trace()
    assert trace["schema"] == SCHEMA
    assert len(trace["requests"]) == 10  # 9 calls, then the final answer
    assert trace["requests"][0]["messages"][-1]["role"] == "user"
    assert len(trace["requests"][-1]["messages"]) == 2 + 2 * 9  # the full history
    assert trace["requests"][3]["tool_list_id"] == tool_list_id(TOOLS)
    assert list(trace["tool_lists"]) == [tool_list_id(TOOLS)]  # the list is stored once
    for name in ("a.jsonl", "a.jsonl.gz"):
        write_traces(tmp_path / name, [trace])
        assert read_traces(tmp_path / name) == [trace]


def test_requests_do_not_share_their_history():
    trace = workflow_trace(1)
    first, second = trace["requests"][0]["messages"], trace["requests"][1]["messages"]
    assert len(first) == 2 and len(second) == 4


def test_parts_add_up_to_the_rendered_prompt():
    tokenizer = WordTokenizer()
    trace = workflow_trace()
    m = measure(trace, tokenizer)
    assert prompts(m, Change(), tokenizer) == [tokenizer.prompt(r["messages"], TOOLS, False, True) for r in trace["requests"]]


def test_smaller_tool_list_saves_once_per_request():
    tokenizer = WordTokenizer()
    m = measure(workflow_trace(), tokenizer)
    base = prompts(m, Change(), tokenizer)
    after = prompts(m, Change(tool_list=m.tool_list - 10), tokenizer)
    assert [a - b for a, b in zip(base, after)] == [10] * 10


def test_keeping_newest_outputs_matches_rewriting_the_messages():
    tokenizer = WordTokenizer()
    trace = workflow_trace()
    m = measure(trace, tokenizer)
    after = prompts(m, Change(keep_outputs=2), tokenizer)
    expected = []
    for r in trace["requests"]:
        messages = json.loads(json.dumps(r["messages"]))
        outputs = [x for x in messages if x["role"] == "tool"]
        for x in outputs[:-2]:
            if tokenizer.text(x["content"]) > tokenizer.text("[old tool output removed]"):
                x["content"] = "[old tool output removed]"
        expected.append(tokenizer.prompt(messages, TOOLS, False, True))
    assert after == expected


def test_duplicate_outputs_are_counted_once():
    tokenizer = WordTokenizer()
    same = "a long output with very many different words in it"
    calls = [{"tool": "parse", "arguments": {"x": i}, "output": same} for i in range(3)]
    trace = trace_from_calls("reference", "t", "task", "system", TOOLS, calls, "1", meta={})
    m = measure(trace, tokenizer)
    base, after = prompts(m, Change(), tokenizer), prompts(m, Change(dedupe_outputs=True), tokenizer)
    assert base[0] == after[0] and base[1] == after[1]  # the first copy stays
    assert after[3] < base[3]


def test_neighbours_without_data_flow_are_not_a_workflow():
    tokenizer = WordTokenizer()
    m = measure(workflow_trace(), tokenizer)
    assert occurrences(m, ["filter", "sort"]) == [1, 4, 7]
    assert occurrences(m, ["parse", "filter", "sort"]) == [0, 3, 6]
    assert occurrences(m, ["sort", "parse"]) == []  # the end of one line and the start of the next


def test_sequence_counts_are_real_occurrences():
    tokenizer = WordTokenizer()
    rows = {tuple(r["sequence"]): r for r in sequences([measure(workflow_trace(), tokenizer)])}
    assert rows[("filter", "sort")]["times"] == 3
    assert rows[("parse", "filter", "sort")]["calls_saved"] == 6
    assert ("sort", "parse") not in rows


def test_merging_keeps_inputs_and_pays_for_the_new_tool():
    tokenizer = WordTokenizer()
    m = measure(workflow_trace(), tokenizer)
    change, saved = merge_change(m, ["filter", "sort"], tokenizer)
    assert saved == 3
    assert len(change.drop_requests) == 3
    assert change.tool_list > m.tool_list
    # the versions list the filter call needed must move into the remaining call
    sort_message = m.calls[2]["assistant"]
    assert change.message_saving[sort_message] < 0
    after = prompts(m, change, tokenizer)
    assert len(after) == len(m.message_counts) - 3
    assert sum(after) < sum(prompts(m, Change(), tokenizer))


def test_flow_ignores_trivial_values():
    earlier = {"output": {"ok": True, "name": "lib", "items": []}}
    assert flows(earlier, {"arguments": {"name": "lib"}})
    assert not flows(earlier, {"arguments": {"flag": True}})
    assert not flows(earlier, {"arguments": {"values": []}})
    assert flows({"output": []}, {"arguments": {"values": []}})  # the whole output, even if it is empty


def test_a_boolean_equal_to_a_flag_is_not_data_flow():
    """Regression: on real traces, version_satisfies > version_satisfies counted as a workflow because false == false."""
    assert not flows({"output": False}, {"arguments": {"include_prereleases": False}})
    assert not flows({"output": 3}, {"arguments": {"limit": 3}})


def test_exact_repeats_count_only_same_tool_and_arguments():
    calls = [{"tool": "sort", "arguments": {"v": ["1"]}, "output": "[]"}, {"tool": "sort", "arguments": {"v": ["1"]}, "output": "[]"},
             {"tool": "sort", "arguments": {"v": ["2"]}, "output": "[]"}, {"tool": "parse", "arguments": {"v": ["1"]}, "output": "[]"}]
    m = measure(trace_from_calls("model", "t", "task", "system", TOOLS, calls, "1", meta={}), WordTokenizer())
    assert exact_repeats(m) == 1


def test_repeated_arguments_are_found_and_sorted_by_origin():
    tokenizer = WordTokenizer()
    long_value = "one two three four five six seven eight nine ten"
    calls = [{"tool": "parse", "arguments": {"text": long_value}, "output": json.dumps("short")},
             {"tool": "sort", "arguments": {"text": long_value}, "output": json.dumps("short")},
             {"tool": "sort", "arguments": {"text": "not repeated at all"}, "output": json.dumps("short")}]
    m = measure(trace_from_calls("reference", "t", f"task {long_value}", "system", TOOLS, calls, "1", meta={}), tokenizer)
    found = repeated_arguments(m, tokenizer)
    assert found["from_task"] == 10  # the first use comes from the task
    assert found["from_tool_data"] == 10  # the second repeats the first call
    assert sum(found["message_saving"].values()) == 10 - tokenizer.text('{"$ref": 12}')


def test_analysis_runs_on_a_trace_without_tool_calls():
    tokenizer = WordTokenizer()
    trace = trace_from_calls("model", "t", "task", "system", TOOLS, [], "1", meta={}, horizon="long")
    result = analyze([measure(trace, tokenizer)], tokenizer)
    assert result["calls"] == 0 and result["requests"] == 1


def test_server_counts_are_compared():
    tokenizer = WordTokenizer()
    trace = workflow_trace(1)
    for r in trace["requests"]:
        r["usage"] = {"prompt_tokens": tokenizer.prompt(r["messages"], TOOLS, False, True) + 1, "completion_tokens": 5, "source": "server"}
    result = analyze([measure(trace, tokenizer)], tokenizer)
    assert result["server"]["requests"] == 4 and result["server"]["gap"] == 4
    assert result["completion_tokens"] == 20


# --- `repo2tools run-model`, with a scripted endpoint and tools ------------------------------------------


def completion(content=None, calls=None):
    message = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(calls)]
    return ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop", "message": message}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 7, "total_tokens": 107}})


class Endpoint:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.requests.append({**kwargs, "messages": json.loads(json.dumps(kwargs["messages"]))})
        return self.replies.pop(0)


class Session:
    async def call_tool(self, name, arguments):
        return SimpleNamespace(isError=False, structuredContent={"result": arguments.get("x", 0) + 1})


EXERCISE = {"id": "e1", "kind": "k", "horizon": "short", "task": "Add one to 41.", "answer": 42, "check": {"kind": "exact"},
            "reference_calls": [{"tool": "add", "arguments": {"x": 41}}], "reference_call_count": 1}
TOOL_LIST = [tool("add")]


def solve(replies, tool_choice="auto", mode="tools"):
    args = Namespace(mode=mode, model="m", thinking=False, tag=None, tool_choice=tool_choice, max_steps=4)
    endpoint = Endpoint(replies)
    result = asyncio.run(run_model.solve(EXERCISE, args, endpoint, Session() if mode == "tools" else None, TOOL_LIST if mode == "tools" else []))
    return result, endpoint


def test_a_run_saves_every_request_with_its_tokens():
    result, _ = solve([completion(calls=[("add", {"x": 41})]), completion(content="42")])
    assert result["passed"] and result["tokens"] == 214
    trace = result["full_trace"]
    assert [len(r["messages"]) for r in trace["requests"]] == [2, 4]
    assert trace["requests"][0]["usage"]["prompt_tokens"] == 100 and trace["requests"][0]["usage"]["source"] == "server"
    assert trace["requests"][1]["messages"][-1] == {"role": "tool", "tool_call_id": "c0", "content": "42"}
    assert trace["requests"][-1]["response"]["content"] == "42"
    assert trace["outcome"]["passed"] and trace["outcome"]["tool_calls"] == 1


def test_auto_does_not_force():
    _, endpoint = solve([completion(content="42")])
    assert endpoint.requests[0]["tool_choice"] == "auto"
    assert len(endpoint.requests[0]["tools"]) == 1


def test_no_tools_sends_no_tool_settings():
    result, endpoint = solve([completion(content="42")], mode="none")
    assert result["passed"]
    assert "tools" not in endpoint.requests[0] and "tool_choice" not in endpoint.requests[0]


def test_first_forces_only_the_first_request():
    result, endpoint = solve([completion(calls=[("add", {"x": 41})]), completion(content="42")], "first")
    assert [r["tool_choice"] for r in endpoint.requests] == ["required", "auto"]
    assert result["passed"]


def test_always_forces_every_request_and_submit_answer_ends_the_run():
    result, endpoint = solve([completion(calls=[("add", {"x": 41})]), completion(calls=[("submit_answer", {"answer": 42})])], "always")
    assert [r["tool_choice"] for r in endpoint.requests] == ["required", "required"]
    assert [t["function"]["name"] for t in endpoint.requests[0]["tools"]] == ["add", "submit_answer"]
    assert "submit_answer" in endpoint.requests[0]["messages"][0]["content"]
    assert result["passed"] and result["answer"] == 42 and result["finish"] == "answered"
    assert result["tool_calls"] == 1  # submit_answer is not counted as a call to a real tool
    assert result["tools_used"] == ["add"]


def example_file(tmp_path):
    good = trace_from_calls("toolgym", "b-two-tools", "Do the thing", "system", TOOLS,
                            [{"tool": "parse", "arguments": {"x": 1}, "output": '"p"'}, {"tool": "sort", "arguments": {"v": "p"}, "output": '["a", "b"]'}],
                            "The sorted list is a and b.", outcome={"passed": False, "tool_calls": 2})
    one_tool = trace_from_calls("toolgym", "a-one-tool", "Other", "system", TOOLS,
                                [{"tool": "sort", "arguments": {"v": 1}, "output": "[1]"}, {"tool": "sort", "arguments": {"v": 2}, "output": "[2]"}],
                                "x", outcome={"passed": True, "tool_calls": 2})
    failed = trace_from_calls("toolgym", "c-error", "Bad", "system", TOOLS,
                              [{"tool": "parse", "arguments": {}, "output": "Error executing tool parse: no"}, {"tool": "sort", "arguments": {}, "output": "[]"},
                               {"tool": "filter", "arguments": {}, "output": "[]"}], "x", outcome={"passed": False, "tool_calls": 3})
    short = trace_from_calls("toolgym", "d-short", "Short", "system", TOOLS, [{"tool": "parse", "arguments": {}, "output": '"p"'}], "x",
                             outcome={"passed": True, "tool_calls": 1})
    write_traces(tmp_path / "examples.jsonl", [one_tool, good, failed, short])
    return tmp_path / "examples.jsonl"


def test_examples_are_chosen_and_turned_into_messages(tmp_path):
    messages = run_model.load_examples(example_file(tmp_path), n=1, min_calls=2)
    # the run with the most different tools wins; the one with a failed call and the short one are left out
    assert [m["role"] for m in messages] == ["user", "assistant", "tool", "assistant", "tool", "assistant"]
    assert messages[0]["content"] == "Do the thing"
    assert messages[1]["tool_calls"][0]["id"] == "example0_call_0" and messages[2]["tool_call_id"] == "example0_call_0"
    assert messages[-1] == {"role": "assistant", "content": '["a", "b"]'}  # the last output, not ToolGym's sentence
    two = run_model.load_examples(example_file(tmp_path), n=2, min_calls=2)
    assert [m["content"] for m in two if m["role"] == "user"] == ["Do the thing", "Other"]
    assert {m["tool_call_id"] for m in two if m["role"] == "tool"} == {"example0_call_0", "example0_call_1", "example1_call_0", "example1_call_1"}


def test_examples_go_between_the_system_prompt_and_the_task(tmp_path):
    args = Namespace(mode="tools", model="m", thinking=False, tag=None, tool_choice="auto", max_steps=4,
                     example_messages=run_model.load_examples(example_file(tmp_path), n=1, min_calls=2))
    endpoint = Endpoint([completion(content="42")])
    result = asyncio.run(run_model.solve(EXERCISE, args, endpoint, Session(), TOOL_LIST))
    sent = endpoint.requests[0]["messages"]
    assert sent[0]["role"] == "system" and sent[1]["content"] == "Do the thing" and sent[-1]["content"] == EXERCISE["task"]
    assert len(sent) == 2 + 6
    assert result["full_trace"]["meta"]["example_messages"] == 6
    assert result["full_trace"]["requests"][0]["messages"] == sent  # the trace shows what was really sent


def test_always_gives_up_at_max_steps():
    result, endpoint = solve([completion(calls=[("add", {"x": 41})])] * 4, "always")
    assert not result["passed"] and result["finish"] == "max_steps" and len(endpoint.requests) == 4
