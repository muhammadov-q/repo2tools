"""Tests for toolgym_exercises.py."""

from exercise_check import check
from exercise_check import resolve
from toolgym_exercises import compose, exercise

RECORD = {"conversation": {"messages": [{"role": "user", "content": "Sort the allowed versions."}]}, "tools": []}


def entry(steps, passed=True):
    return {"uuid": "1234abcd-0000", "passed": passed, "answer": "The result is 2.0 and 1.0.", "steps": steps, "record": RECORD}


def test_the_answer_is_the_last_output():
    ex = exercise(entry([{"tool": "filter", "arguments": {"v": ["1.0", "2.0"]}, "output": ["1.0", "2.0"]},
                         {"tool": "sort", "arguments": {"v": ["1.0", "2.0"]}, "output": ["2.0", "1.0"]}]), "run-1")
    assert ex["answer"] == ["2.0", "1.0"] and ex["reference_call_count"] == 2 and ex["horizon"] == "short"
    assert ex["task"].startswith("Sort the allowed versions.") and "JSON value" in ex["task"]
    assert check(ex, ["2.0", "1.0"]) and not check(ex, ["1.0", "2.0"])  # order counts
    assert ex["toolgym_passed"] and ex["id"] == "toolgym-1234abcd"


def test_long_chains_and_rejected_entries_are_kept_and_marked():
    steps = [{"tool": "t", "arguments": {"i": i}, "output": i} for i in range(9)]
    ex = exercise(entry(steps, passed=False), "run-1")
    assert ex["horizon"] == "long" and not ex["toolgym_passed"] and ex["answer"] == 8


def test_a_chain_that_ends_in_an_error_has_no_answer():
    assert exercise(entry([{"tool": "t", "arguments": {}, "output": "Error executing tool t: bad"}]), "run-1") is None


def test_composed_exercise_asks_for_all_results_in_order():
    a = exercise(entry([{"tool": "filter", "arguments": {"v": ["1.0", "2.0"]}, "output": ["2.0"]},
                        {"tool": "sort", "arguments": {"v": ["2.0"]}, "output": ["2.0"]}]), "run-1")
    b = exercise(entry([{"tool": "norm", "arguments": {"v": "1.0-A"}, "output": "1.0a0"}], passed=False), "run-1")
    c = exercise(entry([{"tool": "t", "arguments": {"i": i}, "output": i} for i in range(6)]), "run-1")
    ex = compose([a, b, c], 1)
    assert ex["answer"] == [["2.0"], "1.0a0", 5] and ex["reference_call_count"] == 9 and ex["horizon"] == "long"
    assert "Task 1: Sort the allowed versions." in ex["task"] and "Task 3:" in ex["task"] and ex["task"].count("JSON value") == 0
    outputs = [["2.0"], ["2.0"], "1.0a0", 0, 1, 2, 3, 4, 5]  # what replaying the reference calls gives
    assert resolve(ex["reference_answer"], outputs) == ex["answer"]
    assert check(ex, [["2.0"], "1.0a0", 5]) and not check(ex, ["1.0a0", ["2.0"], 5])
    assert not ex["toolgym_passed"]  # one part was rejected by ToolGym
