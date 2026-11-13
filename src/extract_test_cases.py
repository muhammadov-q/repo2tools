"""pytest plugin: dump the parameters of every collected test case as JSON lines.

Parametrized tests are tables of (input, expected) pairs that the library's authors
already checked, so they are the seed data for exercises.

Usage (from the source repo, nothing is executed beyond collection):
    PYTHONPATH=<this dir>:src TEST_CASES_OUT=cases.jsonl \
        pytest --collect-only -q -p extract_test_cases tests
"""

import json
import os


def _jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_jsonable(v) for v in value]
        return sorted(items, key=repr) if isinstance(value, (set, frozenset)) else items
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if callable(value) and hasattr(value, "__name__"):
        return f"<callable {value.__name__}>"
    return f"<{type(value).__name__} {value!r}>"


def pytest_collection_modifyitems(session, config, items):
    with open(os.environ["TEST_CASES_OUT"], "w") as out:
        for item in items:
            callspec = getattr(item, "callspec", None)
            record = {
                "nodeid": item.nodeid,
                "file": item.nodeid.split("::")[0],
                "test": item.originalname if hasattr(item, "originalname") else item.name,
                "cls": item.cls.__name__ if getattr(item, "cls", None) else None,
                "params": {k: _jsonable(v) for k, v in callspec.params.items()} if callspec else {},
            }
            out.write(json.dumps(record) + "\n")
