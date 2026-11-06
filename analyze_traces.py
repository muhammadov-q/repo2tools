"""Show what repeats in agent traces, and how many tokens each compression idea would save.

    uv run --group analysis python analyze_traces.py out/traces/reference-function.jsonl out/traces/<run>.jsonl.gz \\
        -o out/traces/analysis

This reports tokens saved, not accuracy. A compression idea can hurt a model's answers, and that is
not measured here. Every saving is a simulation over a recorded run: same requests, less text.

Two numbers per idea:
  all requests   the sum of the prompt tokens of all requests of a run (what a server must read)
  final context  the prompt tokens of the last request (what the model must hold at the end)

Tokens are counted with the model's own tokenizer and chat template. The parts of a prompt (tool
list, each message) are measured as differences between rendered prompts, so they add up to exactly
the rendered prompt. Where a trace has the server's count, the report shows how far we are from it.
"""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from traces import read_traces

OLD_OUTPUT_STUB = "[old tool output removed]"
SAME_OUTPUT_STUB = "[same output as an earlier call]"
VALUE_REFERENCE = '{"$ref": 12}'  # what a repeated value would be replaced with
MIN_VALUE_TOKENS = 8  # shorter values are not worth a reference
RETRIEVED_TOOLS = 5


class Tokenizer:
    """Counts with a model's real tokenizer and chat template. Downloads only the tokenizer files."""

    def __init__(self, name: str):
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(name)
        self.text = lru_cache(maxsize=200_000)(self._text)

    def _text(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def prompt(self, messages: list[dict], tools: list[dict] | None, thinking: bool, generation_prompt: bool) -> int:
        rendered = self.tokenizer.apply_chat_template(messages, tools=tools or None, tokenize=False, enable_thinking=thinking,
                                                      add_generation_prompt=generation_prompt)
        return self._text(rendered)


def call_text(call: dict) -> str:
    return json.dumps({"name": call["function"]["name"], "arguments": call["function"]["arguments"]})


def parsed_output(message: dict):
    content = message.get("content") or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


@dataclass
class Measured:
    """A trace split into parts with token counts. All prompts are built from these parts."""

    trace: dict
    messages: list[dict]  # the full history, ending with the last response
    message_counts: list[int]  # messages[i] is included in a request's prompt if i < message_counts[request]
    costs: list[int]  # tokens of each message; costs[0] holds the system and task together
    first_user: int  # index of the first user message; the part up to it is one block
    tool_list: int
    generation: int
    tool_names: list[str]
    tools: list[dict]
    thinking: bool
    server_prompts: list[int | None] = field(default_factory=list)
    completions: list[int] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)  # {name, assistant, position, tool_message, arguments, output}


def measure(trace: dict, tokenizer) -> Measured | None:
    """Split a trace. Returns None if its requests are not one growing history (nothing to simulate)."""
    requests = trace["requests"]
    if not requests:
        return None
    last = requests[-1]
    messages = [*last["messages"], last["response"]]
    counts = [len(r["messages"]) for r in requests]
    for r in requests:
        if r["messages"] != messages[: len(r["messages"])]:
            return None
    list_id = last.get("tool_list_id")
    tools = trace["tool_lists"].get(list_id, []) if list_id else []
    thinking = bool(trace.get("meta", {}).get("thinking"))
    first_user = next(i for i, m in enumerate(messages) if m["role"] == "user")
    # the template needs a user message, so everything up to the first one is measured as one block
    rendered = [tokenizer.prompt(messages[: i + 1], None, thinking, False) for i in range(first_user, len(messages))]
    costs = [0] * first_user + [rendered[0]] + [b - a for a, b in zip(rendered, rendered[1:])]
    context = messages[: counts[-1]]
    with_list = tokenizer.prompt(context, tools, thinking, True) if tools else None
    without = tokenizer.prompt(context, None, thinking, True)
    generation = without - tokenizer.prompt(context, None, thinking, False)
    measured = Measured(trace, messages, counts, costs, first_user, with_list - without if tools else 0, generation,
                        [t["function"]["name"] for t in tools], tools, thinking)
    for r in requests:
        usage = r.get("usage") or {}
        measured.server_prompts.append(usage.get("prompt_tokens") if usage.get("source") == "server" else None)
        measured.completions.append(usage["completion_tokens"] if usage.get("completion_tokens") is not None
                                    else tokenizer.text(json.dumps(r["response"].get("tool_calls") or r["response"].get("content") or "")))
    # tool calls in order, with the message that holds the call and the message that holds the output
    outputs = {m.get("tool_call_id"): i for i, m in enumerate(messages) if m["role"] == "tool"}
    for i, m in enumerate(messages):
        for position, call in enumerate(m.get("tool_calls") or []):
            try:
                arguments = json.loads(call["function"]["arguments"] or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            where = outputs.get(call.get("id"))
            measured.calls.append({"name": call["function"]["name"], "assistant": i, "position": position, "tool_message": where,
                                   "arguments": arguments, "output": parsed_output(messages[where]) if where is not None else None})
    return measured


@dataclass
class Change:
    """A compression idea, as changes to the parts of a prompt."""

    tool_list: int | None = None  # tokens of the tool list, if different
    keep_outputs: int | None = None  # keep this many newest tool outputs in full, shorten the older ones
    dedupe_outputs: bool = False  # an output identical to an earlier one is replaced by a short note
    message_saving: dict[int, int] = field(default_factory=dict)  # tokens saved in a message, wherever it is sent
    drop_requests: set[int] = field(default_factory=set)  # requests that no longer happen


def prompts(m: Measured, change: Change, tokenizer) -> list[int]:
    """The prompt tokens of every request that still happens, after a change."""
    tool_list = m.tool_list if change.tool_list is None else change.tool_list
    stub_saving = {}
    out_indexes = [i for i, msg in enumerate(m.messages) if msg["role"] == "tool"]
    result = []
    seen_outputs: dict[str, int] = {}
    duplicate = set()
    if change.dedupe_outputs:
        for i in out_indexes:
            content = m.messages[i].get("content") or ""
            if content in seen_outputs:
                duplicate.add(i)
            seen_outputs.setdefault(content, i)

    def shortened(i: int, stub: str) -> int:
        key = (i, stub)
        if key not in stub_saving:
            # never counts as saved if the output is already shorter than the note
            stub_saving[key] = max(0, tokenizer.text(m.messages[i].get("content") or "") - tokenizer.text(stub))
        return stub_saving[key]

    for index, count in enumerate(m.message_counts):
        if index in change.drop_requests:
            continue
        total = tool_list + m.generation
        sent_outputs = [i for i in out_indexes if i < count]
        old = set(sent_outputs[: -change.keep_outputs]) if change.keep_outputs else set()
        if change.keep_outputs == 0:
            old = set(sent_outputs)
        for i in range(count):
            cost = m.costs[i] - change.message_saving.get(i, 0)
            if i in old:
                cost -= shortened(i, OLD_OUTPUT_STUB)
            elif i in duplicate:
                cost -= shortened(i, SAME_OUTPUT_STUB)
            total += cost
        result.append(total)
    return result


def all_values(value):
    """A JSON value and everything inside it."""
    yield value
    if isinstance(value, dict):
        for v in value.values():
            yield from all_values(v)
    elif isinstance(value, list):
        for v in value:
            yield from all_values(v)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True)


def repeated_arguments(m: Measured, tokenizer) -> dict:
    """Arguments whose value was already there: in an earlier output or argument, or in the task."""
    seen: set[str] = set()
    task = next((msg.get("content") or "" for msg in m.messages if msg["role"] == "user"), "")
    found = {"argument_tokens": 0, "from_tool_data": 0, "from_task": 0, "message_saving": defaultdict(int), "by_name": Counter(), "request_savings": defaultdict(int)}
    reference = tokenizer.text(VALUE_REFERENCE)
    for call in m.calls:
        for name, value in call["arguments"].items():
            text = canonical(value)
            tokens = tokenizer.text(text)
            found["argument_tokens"] += tokens
            if text in seen and tokens >= MIN_VALUE_TOKENS:
                found["from_tool_data"] += tokens
                found["by_name"][name] += tokens
                found["message_saving"][call["assistant"]] += tokens - reference
            elif (text in task or (isinstance(value, str) and value in task)) and tokens >= MIN_VALUE_TOKENS:
                found["from_task"] += tokens
        for value in call["arguments"].values():
            seen.update(canonical(v) for v in all_values(value))
        if call["tool_message"] is not None:
            content = m.messages[call["tool_message"]].get("content") or ""
            try:
                seen.update(canonical(v) for v in all_values(json.loads(content)))
            except json.JSONDecodeError:
                seen.add(canonical(content))
    return found


def flows(earlier: dict, later: dict) -> bool:
    """Whether a later call uses an earlier call's output, whole or a meaningful part of it."""
    arguments = list(later["arguments"].values())
    # a boolean or number that equals a flag is a coincidence, not data flow (as in ToolGym's type links)
    if isinstance(earlier["output"], (str, list, dict)) and any(canonical(v) == canonical(earlier["output"]) for v in arguments):
        return True
    parts = {canonical(v) for v in all_values(earlier["output"]) if isinstance(v, (str, list, dict)) and v not in ("", [], {})}
    return any(canonical(v) in parts for argument in arguments for v in all_values(argument))


def occurrences(m: Measured, sequence: list[str]) -> list[int]:
    """Where a sequence runs in a trace, without overlaps. Each step after the first must use an
    earlier step's output: calls that only happen to be neighbours are not a workflow."""
    n, names, found, i = len(sequence), [c["name"] for c in m.calls], [], 0
    while i <= len(names) - n:
        window = m.calls[i: i + n]
        if names[i: i + n] == sequence and all(any(flows(c, window[j]) for c in window[:j]) for j in range(1, n)):
            found.append(i)
            i += n
        else:
            i += 1
    return found


def sequences(all_measured: list[Measured], lengths=(2, 3, 4)) -> list[dict]:
    """Workflows that repeat, with the most calls saved first. The rows overlap, so do not add them up."""
    candidates = {tuple(c["name"] for c in m.calls[i: i + n]) for m in all_measured for n in lengths
                  for i in range(len(m.calls) - n + 1)}
    rows = []
    for key in candidates:
        counts = [len(occurrences(m, list(key))) for m in all_measured]
        times = sum(counts)
        if times >= 2:
            rows.append({"sequence": list(key), "times": times, "traces": sum(c > 0 for c in counts), "calls_saved": times * (len(key) - 1)})
    return sorted(rows, key=lambda r: (-r["calls_saved"], len(r["sequence"]), r["sequence"]))


def merge_change(m: Measured, sequence: list[str], tokenizer) -> tuple[Change, int]:
    """If one bigger tool did `sequence`, only its last call remains. Returns the change and the calls saved.

    Inputs of the removed calls that did not come from an earlier step move into the remaining call,
    and the new tool makes the tool list one (average) tool longer.
    """
    n = len(sequence)
    change, saved = Change(), 0
    removed_at: Counter = Counter()
    for start in occurrences(m, sequence):
        window = m.calls[start: start + n]
        for j, call in enumerate(window[:-1]):
            saved += 1
            removed_at[call["assistant"]] += 1
            raw = m.messages[call["assistant"]]["tool_calls"][call["position"]]
            change.message_saving[call["assistant"]] = change.message_saving.get(call["assistant"], 0) + tokenizer.text(call_text(raw))
            if call["tool_message"] is not None:
                change.message_saving[call["tool_message"]] = m.costs[call["tool_message"]]
            for value in call["arguments"].values():
                fake = {"arguments": {"x": value}}
                if not any(flows(c, fake) for c in window[:j]):
                    last = window[-1]["assistant"]
                    change.message_saving[last] = change.message_saving.get(last, 0) - tokenizer.text(canonical(value))
    # an assistant message with nothing left: the whole message goes, and so does the request that produced it
    for assistant, removed in removed_at.items():
        if removed == len(m.messages[assistant]["tool_calls"]):
            change.message_saving[assistant] = m.costs[assistant]
            change.drop_requests.add(m.message_counts.index(assistant))
    if saved and m.tools:
        change.tool_list = m.tool_list + round(m.tool_list / len(m.tools))
    return change, saved


def tool_list_of(m: Measured, names: set[str], tokenizer) -> int:
    """Tokens of a tool list that keeps only these tools."""
    kept = [t for t in m.tools if t["function"]["name"] in names]
    context = m.messages[: m.message_counts[-1]]
    if not kept:
        return 0
    return tokenizer.prompt(context, kept, m.thinking, True) - tokenizer.prompt(context, None, m.thinking, True)


def retrieved(m: Measured, k: int) -> set[str]:
    """The tools a perfect search would return: those the run used, then others, up to k."""
    used = {c["name"] for c in m.calls if c["name"] in m.tool_names}
    extra = [n for n in m.tool_names if n not in used]
    return used | set(extra[: max(0, k - len(used))])


def exact_repeats(m: Measured) -> int:
    """Calls with the same tool and arguments as an earlier call of the same run: the model going in circles."""
    seen, repeats = set(), 0
    for call in m.calls:
        key = (call["name"], canonical(call["arguments"]))
        repeats += key in seen
        seen.add(key)
    return repeats


def analyze(all_measured: list[Measured], tokenizer) -> dict:
    """Totals over a group of traces."""
    ideas: dict[str, list] = defaultdict(lambda: [0, 0])
    parts = Counter()
    first_time, resent = 0, 0
    server_gap, server_total, server_requests = 0, 0, 0
    arguments = Counter()
    by_name = Counter()
    used_tools, offered_tools = 0, 0
    best = sequences(all_measured)

    def record(idea: str, values: list[int]):
        ideas[idea][0] += sum(values)
        ideas[idea][1] += values[-1] if values else 0

    for m in all_measured:
        base = prompts(m, Change(), tokenizer)
        record("Nothing changed", base)
        # what the prompts consist of, over all requests
        parts["tool list"] += m.tool_list * len(m.message_counts)
        parts["end of prompt (start of the model's reply)"] += m.generation * len(m.message_counts)
        newest_output = {}
        for number, count in enumerate(m.message_counts):
            sent = [i for i in range(count) if m.messages[i]["role"] == "tool"]
            newest_output[number] = sent[-1] if sent else None
            for i in range(count):
                role = m.messages[i]["role"]
                if i <= m.first_user:
                    parts["system prompt and task"] += m.costs[i]
                elif role == "assistant":
                    parts["the model's earlier calls"] += m.costs[i]
                elif i == newest_output[number]:
                    parts["newest tool output"] += m.costs[i]
                else:
                    parts["older tool outputs"] += m.costs[i]
        # read for the first time versus sent again
        previous = 0
        for value in base:
            first_time += min(value, max(0, value - previous))
            resent += min(value, previous)
            previous = value
        # distance from the server's own count
        for ours, theirs in zip(base, m.server_prompts):
            if theirs is not None:
                server_gap += abs(ours - theirs)
                server_total += theirs
                server_requests += 1

        used_tools += len({c["name"] for c in m.calls})
        offered_tools += len(m.tool_names)
        if m.tools:
            record(f"Tool list: only the {RETRIEVED_TOOLS} tools a perfect search finds", prompts(m, Change(tool_list=tool_list_of(m, retrieved(m, RETRIEVED_TOOLS), tokenizer)), tokenizer))
            record("Tool list: only the tools this run used (best case)", prompts(m, Change(tool_list=tool_list_of(m, {c["name"] for c in m.calls}, tokenizer)), tokenizer))
        for k in (5, 3, 1):
            record(f"Old outputs: keep the newest {k} in full", prompts(m, Change(keep_outputs=k), tokenizer))
        record("Old outputs: replace exact duplicates", prompts(m, Change(dedupe_outputs=True), tokenizer))
        repeats = repeated_arguments(m, tokenizer)
        record("Arguments: refer to values from earlier calls", prompts(m, Change(message_saving=dict(repeats["message_saving"])), tokenizer))
        arguments["argument tokens"] += repeats["argument_tokens"]
        arguments["copied from earlier calls or outputs"] += repeats["from_tool_data"]
        arguments["copied from the task"] += repeats["from_task"]
        by_name.update(repeats["by_name"])
        record(f"Together: {RETRIEVED_TOOLS} tools, newest 5 outputs, references",
               prompts(m, Change(tool_list=tool_list_of(m, retrieved(m, RETRIEVED_TOOLS), tokenizer) if m.tools else 0, keep_outputs=5,
                                 message_saving=dict(repeats["message_saving"])), tokenizer))
        # a server that keeps the common start of the prompt reads only what is new, with the same context
        ideas["Prefix cache on the server (same context, less reading)"][0] += base[-1] if base else 0
        ideas["Prefix cache on the server (same context, less reading)"][1] += base[-1] if base else 0

    # one bigger tool for the most common sequence
    sequence_rows = []
    for row in best[:8]:
        total, final, calls = 0, 0, 0
        for m in all_measured:
            change, saved = merge_change(m, row["sequence"], tokenizer)
            values = prompts(m, change, tokenizer)
            total += sum(values)
            final += values[-1] if values else 0
            calls += saved
        sequence_rows.append({**row, "calls_saved": calls, "tokens_after": total, "final_after": final})
    return {"traces": len(all_measured), "requests": sum(len(m.message_counts) for m in all_measured),
            "calls": sum(len(m.calls) for m in all_measured), "exact_repeated_calls": sum(exact_repeats(m) for m in all_measured),
            "completion_tokens": sum(sum(m.completions) for m in all_measured),
            "ideas": {k: {"all_requests": v[0], "final_context": v[1]} for k, v in ideas.items()},
            "parts": dict(parts), "first_time": first_time, "resent": resent, "arguments": dict(arguments),
            "repeated_argument_names": by_name.most_common(5), "sequences": sequence_rows, "used_tools": used_tools, "offered_tools": offered_tools,
            "server": {"requests": server_requests, "tokens": server_total, "gap": server_gap}}


def markdown(name: str, result: dict) -> str:
    base = result["ideas"]["Nothing changed"]
    calls_avg = result["calls"] / result["traces"] if result["traces"] else 0
    lines = [f"## {name}", "",
             f"{result['traces']} runs, {result['requests']} requests, {result['calls']} tool calls ({calls_avg:.1f} per run). "
             f"Prompt tokens: **{base['all_requests']:,}**. The model's replies: {result['completion_tokens']:,}.", ""]
    if result["server"]["requests"]:
        s = result["server"]
        lines += [f"Our count against the server's: {s['gap'] / max(1, s['tokens']):.2%} apart over {s['requests']} requests.", ""]
    total = result["first_time"] + result["resent"]
    if total:
        lines += [f"**Sent before:** {result['resent']:,} of {total:,} prompt tokens ({result['resent'] / total:.0%}) were already sent in an earlier request of the same run.", ""]
    if result["exact_repeated_calls"]:
        lines += [f"**Repeated calls:** {result['exact_repeated_calls']} of {result['calls']} calls had the same tool and arguments as an earlier call of the same run.", ""]
    if result["offered_tools"]:
        lines += [f"**Tools:** each run used {result['used_tools'] / result['traces']:.1f} of the {result['offered_tools'] / result['traces']:.0f} tools offered, on average.", ""]
    lines += ["### What the prompts consist of", "", "| Part | Tokens, all requests | Share |", "| --- | --- | --- |"]
    parts_total = sum(result["parts"].values())
    for part, tokens in sorted(result["parts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {part} | {tokens:,} | {tokens / max(1, parts_total):.1%} |")
    lines += ["", "### What each idea would save (simulated)", "",
              "| Idea | All requests | Saved | Final context | Saved |", "| --- | --- | --- | --- | --- |"]
    for idea, value in result["ideas"].items():
        saved = 1 - value["all_requests"] / max(1, base["all_requests"])
        saved_final = 1 - value["final_context"] / max(1, base["final_context"])
        lines.append(f"| {idea} | {value['all_requests']:,} | {saved:.0%} | {value['final_context']:,} | {saved_final:.0%} |")
    if result["arguments"].get("argument tokens"):
        a = result["arguments"]
        lines += ["", "### Repeated arguments", "",
                  f"Arguments hold {a['argument tokens']:,} tokens (each counted once). Of these, {a.get('copied from earlier calls or outputs', 0):,} "
                  f"are copies of earlier arguments or outputs, and {a.get('copied from the task', 0):,} are copies from the task. Only values of {MIN_VALUE_TOKENS}+ tokens count."]
        if result["repeated_argument_names"]:
            lines += ["", "Most copied arguments: " + ", ".join(f"`{n}` ({t:,} tokens)" for n, t in result["repeated_argument_names"]) + "."]
    if result["sequences"]:
        lines += ["", "### Same call sequences, if one bigger tool did them", "",
                  "Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. "
                  "The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.", "",
                  "| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |", "| --- | --- | --- | --- | --- | --- |"]
        for row in result["sequences"]:
            lines.append(f"| {' > '.join(row['sequence'])} | {row['times']} | {row['traces']} | {row['calls_saved']} | "
                         f"{1 - row['tokens_after'] / max(1, base['all_requests']):.0%} | {1 - row['final_after'] / max(1, base['final_context']):.0%} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path, help="trace files (.jsonl or .jsonl.gz)")
    parser.add_argument("-o", "--output", type=Path, help="folder for repetition.md and repetition.json")
    parser.add_argument("--tokenizer", default="Qwen/Qwen3-8B")
    parser.add_argument("--min-calls", type=int, default=0, help="only runs with at least this many tool calls")
    args = parser.parse_args()
    tokenizer = Tokenizer(args.tokenizer)
    groups: dict[str, list[Measured]] = defaultdict(list)
    skipped = Counter()
    for path in args.files:
        for trace in read_traces(path):
            m = measure(trace, tokenizer)
            if m is None:
                skipped[path.name] += 1
                continue
            if len(m.calls) < args.min_calls:
                continue
            label = "known-good" if trace["source"] == "reference" else \
                f"{trace.get('model')}, tools: {trace.get('tool_set')}, tool choice: {trace.get('meta', {}).get('tool_choice', 'auto')}"
            groups[f"{label}, {trace.get('horizon')} tasks"].append(m)
    results = {name: analyze(group, tokenizer) for name, group in sorted(groups.items())}
    text = "# What repeats in the traces\n\n" \
           f"Tokenizer: `{args.tokenizer}`, with its chat template. Savings are simulated on recorded runs; effects on accuracy are not measured.\n\n" + \
           "\n".join(markdown(name, result) for name, result in results.items())
    if skipped:
        text += f"\nSkipped, because their requests are not one growing history: {dict(skipped)}\n"
    print(text)
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "repetition.md").write_text(text, encoding="utf-8")
        (args.output / "repetition.json").write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
