"""Tests for repo_usage.py, and for picking tools with usage counts and classes in repo2tools.py."""

import asyncio
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

import repo2tools
from repo_usage import Api, Usage, count_usage, example_blocks
from scrape_repo import constructors, scrape_package
from test_repo2tools import ScriptedLLM, options
from tool_worker import direct_call_problem

LIBRARY = '''"""Money amounts such as "12.50 EUR"."""


class Amount:
    """An amount of money in one currency.

    >>> Amount("12.50 EUR").currency
    'EUR'
    """

    def __init__(self, text: str) -> None:
        number, _, currency = text.strip().partition(" ")
        if not currency.isalpha() or len(currency) != 3:
            raise ValueError(f"not an amount: {text!r}")
        self.cents, self._currency = round(float(number) * 100), currency.upper()

    @property
    def currency(self) -> str:
        """The three-letter currency code."""
        return self._currency

    def rounded(self) -> "Amount":
        """The amount without cents."""
        return Amount(f"{round(self.cents / 100)} {self._currency}")

    def __lt__(self, other: "Amount") -> bool:
        return self.cents < other.cents

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Amount) and (self.cents, self._currency) == (other.cents, other._currency)

    def __str__(self) -> str:
        return f"{self.cents / 100:.2f} {self._currency}"


def parse(text: str) -> Amount:
    """Read an amount from text."""
    return Amount(text)


def currencies() -> list[str]:
    """The currency codes this library knows."""
    return ["CHF", "EUR", "USD"]


def rarely(text: str) -> str:
    """Something nobody uses."""
    return text
'''
DOCS = '''Amounts
=======

.. doctest::

    >>> from money import Amount, parse
    >>> a = parse("12.50 EUR")
    >>> a.currency
    'EUR'
    >>> a < Amount("20 EUR")
    True
    >>> Amount("1 EUR") < Amount("2 EUR")
    True

.. code-block:: python

    import money
    print(money.currencies())
'''
TESTS = '''import money
from money import Amount


def test_rounding():
    a = Amount("12.50 EUR")
    assert a.rounded() == Amount("12 EUR")
    assert a.rounded().currency == "EUR"
    assert money.parse("1 USD") == Amount("1 USD")


def test_unknown(thing):
    assert thing.currency == "CHF"
'''


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "money"
    (root / "money").mkdir(parents=True)
    (root / "money" / "__init__.py").write_text(LIBRARY)
    (root / "docs").mkdir()
    (root / "docs" / "index.rst").write_text(DOCS)
    (root / "tests").mkdir()
    (root / "tests" / "test_money.py").write_text(TESTS)
    (root / "pyproject.toml").write_text('[project]\nname = "money"\ndependencies = []\n')
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-C", str(root)]
    for command in (["init", "--quiet"], ["add", "."], ["commit", "--quiet", "-m", "init"]):
        subprocess.run([*git, *command], check=True)
    return root


def api_of(root: Path) -> dict:
    callables, _ = scrape_package(root, "money")
    return {"package": "money", "callables": [asdict(c) for c in callables], "classes": constructors(root, callables)}


# --- counting ----------------------------------------------------------------------------------


def test_docs_and_tests_are_counted_apart(repo):
    usage = count_usage(api_of(repo), repo, repo / "money")
    rows, amount = usage.callables, usage.classes["Amount"]
    assert rows["money.parse"] == {"docs": 1, "tests": 1, "guessed_docs": 0, "guessed_tests": 0}
    assert rows["money.currencies"]["docs"] == 1 and rows["money.currencies"]["tests"] == 0  # through the module, in a code block
    assert rows["money.rarely"] == {"docs": 0, "tests": 0, "guessed_docs": 0, "guessed_tests": 0}
    # `a = parse(...)` is an Amount, by parse's return annotation; the class docstring's example counts as documentation
    assert rows["money.Amount.currency"]["docs"] == 2
    # a.rounded() twice, and `.currency` on its result, which is an Amount again
    assert rows["money.Amount.rounded"]["tests"] == 2 and rows["money.Amount.currency"]["tests"] == 1
    # `thing.currency`: the class of `thing` is unknown, and Amount is the only class in that file with this member
    assert rows["money.Amount.currency"]["guessed_tests"] == 1
    assert amount["built"] == {"docs": 4, "tests": 3}
    assert amount["operators"]["<"] == {"docs": 2, "tests": 0} and amount["operators"]["=="] == {"docs": 0, "tests": 2}
    assert usage.files == {"docs": 1, "tests": 1} and usage.unparsed == 0


def test_ranking_by_source(repo):
    result = count_usage(api_of(repo), repo, repo / "money").as_json()
    assert result["ranking"]["docs"][0] == "money.Amount.currency" and "money.Amount.rounded" not in result["ranking"]["docs"]
    assert result["ranking"]["tests"][0] == "money.Amount.rounded"
    assert "money.rarely" not in result["ranking"]["both"] and len(result["ranking"]["both"]) == 4


def test_nothing_is_imported_or_run(repo, tmp_path):
    marker = tmp_path / "ran"
    (repo / "tests" / "test_evil.py").write_text(f"import money\nopen({str(marker)!r}, 'w').write('x')\nmoney.parse('1 EUR')\n")
    usage = count_usage(api_of(repo), repo, repo / "money")
    assert usage.callables["money.parse"]["tests"] == 2 and not marker.exists()


def test_names_from_other_packages_are_not_counted():
    api = {"package": "money", "callables": [{"module": "money", "qualname": "parse", "returns": "Amount"},
                                             {"module": "money", "qualname": "Amount.currency", "returns": "str"}], "classes": {"Amount": {"module": "money"}}}
    usage = Usage(Api(api))
    usage.scan("from other import parse, Amount\nparse('x')\nAmount('1 EUR').currency\n", "tests")
    assert usage.callables["money.parse"]["tests"] == 0 and usage.classes["Amount"]["built"]["tests"] == 0
    usage.scan("import money as m\nfrom money import parse as p\nm.parse('1 EUR')\np('2 EUR').currency\n", "tests")
    assert usage.callables["money.parse"]["tests"] == 2 and usage.callables["money.Amount.currency"]["tests"] == 1


def test_example_blocks():
    text = ("Text\n\n    >>> x = f(1)\n    >>> for i in y:\n    ...     g(i)\n    result\n\n.. code-block:: python\n\n    a = 1\n\n    b = 2\nprose\n"
            "```python\nc = 3\n```\n```sh\nrm -rf /\n```\n")
    assert example_blocks(text) == ["x = f(1)\nfor i in y:\n    g(i)", "a = 1\n\nb = 2", "c = 3"]
    # a doctest run that is not valid as a whole is read statement by statement, and the rest is kept
    assert example_blocks(">>> a = f(1)\n>>> this is $ not python\n>>> b = g(2)\n") == ["a = f(1)", "this is $ not python", "b = g(2)"]


# --- picking tools -------------------------------------------------------------------------------


def listing(repo, by="docs", classes=True):
    api = api_of(repo)
    usage = count_usage(api, repo, repo / "money").as_json()
    items = (repo2tools.class_callables(api["classes"]) if classes else []) + api["callables"]
    items.sort(key=lambda c: repo2tools.usage_score(c, usage, by), reverse=True)
    return repo2tools.propose_messages("money", items, 5, usage, by)[1]["content"], items


def test_the_listing_shows_usage_and_puts_the_most_used_first(repo):
    text, items = listing(repo)
    assert items[0]["kind"] == "class" and items[0]["qualname"] == "Amount" and {c["qualname"] for c in items[-2:]} == {"rarely", "Amount.rounded"}  # not used in the docs
    assert "- class money.Amount(text: str) -> Amount | An amount of money in one currency. | built 4 times; used with < (2)" in text
    assert "money.rarely(text: str) -> str | Something nobody uses. | used 0 times" in text
    assert "how often the repository's own documentation examples use it" in text and "several tools from one class" in text
    both, _ = listing(repo, by="both")
    assert "built 7 times; used with == (2), < (2)" in both and "documentation examples and tests use it" in both


def test_without_the_new_options_the_prompt_is_the_old_one(repo):
    api = api_of(repo)
    text = repo2tools.propose_messages("money", api["callables"], 5)[1]["content"]
    assert "Make one tool per library function." in text and "used" not in text.split("Pick at most")[0] and "class entry" not in text
    assert "how often" not in text


def test_a_class_may_give_several_tools_a_function_only_one(repo):
    api = api_of(repo)
    items = repo2tools.class_callables(api["classes"]) + api["callables"]
    proposal = [{"function": "money.Amount", "name": "compare_amounts", "description": "Compare two amounts with <."},
                {"function": "money.Amount", "name": "normalize_amount", "description": "Build an amount and give its normal text."},
                {"function": "money.parse", "name": "parse_amount", "description": "Read an amount."},
                {"function": "money.parse", "name": "parse_amount_again", "description": "Read an amount, again."}]
    picks, problem, dropped = repo2tools.parse_proposal(json.dumps(proposal), items)
    assert problem is None and [p["name"] for p in picks] == ["compare_amounts", "normalize_amount", "parse_amount"] and dropped == 1
    many = [{"function": "money.Amount", "name": f"tool_{i}", "description": "An operation on amounts."} for i in range(10)]
    assert len(repo2tools.parse_proposal(json.dumps(many), items)[0]) == repo2tools.MAX_PER_CLASS
    # without class entries in the listing, a class cannot be picked
    assert repo2tools.parse_proposal(json.dumps(proposal[:1]), api["callables"])[0] == []


def test_a_test_may_use_the_operators_a_class_defines():
    assert direct_call_problem("money.Amount(a) < money.Amount(b)", ["a", "b"], "Amount") is None
    assert direct_call_problem("-1 if money.Amount(a) < money.Amount(b) else (0 if money.Amount(a) == money.Amount(b) else 1)", ["a", "b"], "Amount") is None
    assert direct_call_problem("version in pkg.SpecifierSet(spec)", ["version", "spec"], "SpecifierSet") is None
    assert direct_call_problem("str(pkg.SpecifierSet(a) & pkg.SpecifierSet(b))", ["a", "b"], "SpecifierSet") is None
    assert "may not use Pow" in direct_call_problem("money.Amount(a).cents ** 99", ["a"], "Amount")
    assert "must use the library's Amount" in direct_call_problem("a < b", ["a", "b"], "Amount")


def test_generate_with_usage_and_classes_builds_a_tool_from_an_operator(repo, tmp_path, monkeypatch):
    root = tmp_path / "root"
    monkeypatch.setattr(repo2tools, "ROOT", root)
    monkeypatch.setattr(repo2tools, "CACHE", root / ".cache")
    root.mkdir()
    spec = {"parameters": [{"name": "first", "type": "string", "description": "an amount", "required": True},
                           {"name": "second", "type": "string", "description": "an amount", "required": True}],
            "direct_call": "money.Amount(first) < money.Amount(second)",
            "samples": [{"first": "1 EUR", "second": "2 EUR"}, {"first": "5 EUR", "second": "2 EUR"}, {"first": "2 EUR", "second": "2 EUR"}, {"first": "x", "second": "2 EUR"}]}
    code = ('```python\nfrom money import Amount\n\n\ndef is_smaller_amount(first: str, second: str) -> bool:\n'
            '    """Check whether the first amount is smaller than the second. first, second: amounts such as \'12.50 EUR\'."""\n'
            '    return Amount(first) < Amount(second)\n```')
    llm = ScriptedLLM({("propose", "money"): [json.dumps([{"function": "money.Amount", "name": "is_smaller_amount", "description": "Compare two amounts with <."}])],
                       ("spec", "is_smaller_amount"): [json.dumps(spec)], ("code", "is_smaller_amount"): [code]})
    report = asyncio.run(repo2tools.generate(options(repo, usage="docs", classes=True), llm=llm))
    assert report["accepted"] == 1 and report["pick"] == {"usage": "docs", "classes": True}
    tool = report["tools"][0]
    assert tool["wraps"] == "money.Amount" and [r["result"] for r in tool["check"]["samples"]] == ["same", "same", "same", "both_error"]
    prompt = llm.chats[0][2][1]["content"]
    assert prompt.index("class money.Amount") < prompt.index("function money.parse") and "built 4 times; used with < (2)" in prompt
    usage = json.loads((root / "out" / "generated" / "money-test" / "usage.json").read_text())
    assert usage["classes"]["Amount"]["built"]["docs"] == 4
    # the test writer sees the class it has to use
    assert "class Amount:" in llm.chats[1][2][1]["content"]
