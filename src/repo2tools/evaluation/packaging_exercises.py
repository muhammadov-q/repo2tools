"""Build exercises for the pypa/packaging tools.

Short exercises (1 tool call) come from packaging's own parametrized tests: the task is one
test case and the answer is the test's expected value. A direct call to the library must give
the same answer; cases where the two differ are dropped and counted.

Long exercises (8 or more calls) check a small requirements list against a made-up package
index for a target environment. Their answers come from direct library calls.

Usage:
    uv run repo2tools make-exercises [--per-kind 20] [--long 20] [--seed 0]
Reads out/packaging/test_cases.jsonl (from `evaluation/test_case_plugin.py`) and writes
out/packaging/exercises.jsonl and out/packaging/exercises_preview.md.
"""

import argparse
import json
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, canonicalize_version, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from repo2tools.paths import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "toolsets" / "pypa_packaging"))
from tools import BASELINE_ENVIRONMENT  # noqa: E402  (the marker tool's documented defaults)

OUT = REPO_ROOT / "out" / "packaging"
REPO = REPO_ROOT.parent / "source-repos" / "packaging"
EXACT, SET_EQUAL = {"kind": "exact"}, {"kind": "set_equal"}
REF0 = {"$ref": [0]}


def call(tool: str, **arguments) -> dict:
    return {"tool": tool, "arguments": {k: v for k, v in arguments.items() if v is not None}}


def short(kind, task, answer, calls, library, check=EXACT, reference_answer=REF0) -> dict:
    return {"kind": kind, "horizon": "short", "task": task, "answer": answer, "check": check,
            "reference_calls": calls, "reference_answer": reference_answer, "library_functions": library}


def pre_clause(prereleases: bool | None) -> str:
    return {True: " when pre-releases are explicitly allowed", False: " when pre-releases are excluded", None: ""}[prereleases]


# --- short exercises: one builder per kind; each returns (exercise, library answer) or None ---


def version_compare(c):
    p = c["params"]
    sign = {"<callable lt>": -1, "<callable gt>": 1, "<callable eq>": 0}.get(p["op"])
    if sign is None:
        return None
    a, b = p["left"], p["right"]
    task = (f"Compare the Python package versions '{a}' and '{b}' using PEP 440 ordering. Answer -1 if "
            f"'{a}' is older, 0 if both are equal, or 1 if '{a}' is newer.")
    return short("version_compare", task, sign, [call("compare_versions", version_a=a, version_b=b)],
                 ["packaging.version.Version"]), (Version(a) > Version(b)) - (Version(a) < Version(b))


def version_normalize(c):
    v, expected = c["params"]["version"], c["params"]["normalized"]
    task = f"What is the normalized PEP 440 spelling of the version '{v}'? Answer with the version string."
    return short("version_normalize", task, expected, [call("normalize_version", version=v)],
                 ["packaging.version.Version.__str__"]), str(Version(v))


def version_base(c):
    v, expected = c["params"]["version"], c["params"]["base_version"]
    task = (f"What is the base version of '{v}', meaning its epoch and release numbers without any pre-, "
            "post-, dev-release or local part? Answer with the version string.")
    return short("version_base", task, expected, [call("base_version", version=v)],
                 ["packaging.version.Version.base_version"]), Version(v).base_version


def version_is_prerelease(c):
    v, expected = c["params"]["version"], c["params"]["expected"]
    task = f"Under PEP 440, is '{v}' a pre-release? Answer true or false."
    return short("version_is_prerelease", task, expected, [call("version_info", version=v)],
                 ["packaging.version.Version.is_prerelease"], reference_answer={"$ref": [0, "is_prerelease"]}), \
        Version(v).is_prerelease


def version_valid(c):
    v = c["params"]["version"]
    expected = c["test"] == "test_valid_versions"
    try:
        Version(v)
        library = True
    except InvalidVersion:
        library = False
    task = f"Is '{v}' a valid version string under PEP 440? Answer true or false."
    return short("version_valid", task, expected, [call("is_valid_version", version=v)],
                 ["packaging.version.Version"]), library


def specifier_contains(c):
    p = c["params"]
    spec = p.get("spec_str", p.get("specifier"))
    v, pre = p["version"], p.get("prereleases")
    if not isinstance(v, str) or v.startswith("<"):
        return None
    task = f"Is version '{v}' allowed by the version constraint '{spec}'{pre_clause(pre)}? Answer true or false."
    return short("specifier_contains", task, p["expected"],
                 [call("version_satisfies", version=v, specifier=spec, include_prereleases=pre)],
                 ["packaging.specifiers.SpecifierSet.contains"]), SpecifierSet(spec).contains(v, prereleases=pre)


def specifier_filter(c):
    p = c["params"]
    spec, versions, expected = p["specifier"], p["input"], p["expected"]
    if any(not isinstance(v, str) or v.startswith("<") for v in [*versions, *expected]):
        return None
    pre = p["prereleases"] if p["prereleases"] is not None else p["specifier_prereleases"]
    task = (f"From the versions {json.dumps(versions)}, which are allowed by the version constraint "
            f"'{spec}'{pre_clause(pre)}? Answer with a JSON list in the original order.")
    return short("specifier_filter", task, expected,
                 [call("filter_versions", versions=versions, specifier=spec, include_prereleases=pre)],
                 ["packaging.specifiers.SpecifierSet.filter"]), list(SpecifierSet(spec).filter(versions, prereleases=pre))


def specifier_satisfiable(c):
    spec = c["params"]["spec_str"]
    expected = c["test"] == "test_satisfiable"
    task = f"Can any version at all satisfy the version constraint '{spec}'? Answer true or false."
    return short("specifier_satisfiable", task, expected, [call("is_satisfiable", specifier=spec)],
                 ["packaging.specifiers.SpecifierSet.is_unsatisfiable"]), not SpecifierSet(spec).is_unsatisfiable()


def specifier_subset(c):
    p = c["params"]
    a, b = (p["left"], p["right"]) if c["test"] == "test_is_subset" else (p["right"], p["left"])
    pre = p["prereleases"]
    task = f"Is every version allowed by the constraint '{a}' also allowed by '{b}'{pre_clause(pre)}? Answer true or false."
    library = SpecifierSet(a, prereleases=pre).is_subset(SpecifierSet(b, prereleases=pre))
    return short("specifier_subset", task, p["expected"],
                 [call("specifier_is_subset", specifier=a, other=b, include_prereleases=pre)],
                 ["packaging.specifiers.SpecifierSet.is_subset"]), library


def name_canonicalize(c):
    name, expected = c["params"]["name"], c["params"]["expected"]
    try:
        library = canonicalize_name(name, validate=True)
    except ValueError:
        return None
    task = f"What is the normalized project name, as package indexes compare names, for '{name}'? Answer with the name."
    return short("name_canonicalize", task, expected, [call("canonicalize_name", name=name)],
                 ["packaging.utils.canonicalize_name"]), library


def version_canonicalize(c):
    v, expected = c["params"]["version"], c["params"]["expected"]
    try:
        library = canonicalize_version(Version(v))
    except InvalidVersion:
        return None
    task = (f"What is the canonical form of version '{v}' used to compare file names (normalized, with "
            "trailing '.0' release parts removed)? Answer with the version string.")
    return short("version_canonicalize", task, expected, [call("canonicalize_version", version=v)],
                 ["packaging.utils.canonicalize_version"]), library


def wheel_tags(c):
    p = c["params"]
    expected = sorted(re.findall(r"<Tag <([^ >]+) @", " ".join(p["tags"])))
    library = sorted(str(t) for t in parse_wheel_filename(p["filename"])[3])
    task = (f"Which compatibility tags does the wheel file '{p['filename']}' declare? Answer with a JSON list "
            "of tags such as 'py3-none-any'.")
    return short("wheel_tags", task, expected, [call("parse_wheel_filename", filename=p["filename"])],
                 ["packaging.utils.parse_wheel_filename"], check=SET_EQUAL,
                 reference_answer={"$ref": [0, "tags"]}), library


def marker_evaluate(c):
    p = c["params"]
    if p["environment"] is None:
        return None  # the test uses the machine's own environment
    m, env = p["marker_string"], p["environment"]
    env_text = " and ".join(f"{k} is '{v}'" for k, v in env.items())
    task = (f"Does the environment marker '{m}' evaluate to true when {env_text}? Other marker variables are "
            "those of CPython 3.12.0 on Linux x86_64. Answer true or false.")
    return short("marker_evaluate", task, p["expected"], [call("evaluate_marker", marker=m, environment=env)],
                 ["packaging.markers.Marker.evaluate"]), Marker(m).evaluate({**BASELINE_ENVIRONMENT, **env})


SHORT_KINDS = [  # builder, then the tests it reads: (file, class or None, test function)
    (version_compare, [("test_version.py", "TestVersion", "test_comparison_true")]),
    (version_normalize, [("test_version.py", "TestVersion", "test_normalized_versions")]),
    (version_base, [("test_version.py", "TestVersion", "test_version_base_version")]),
    (version_is_prerelease, [("test_version.py", "TestVersion", "test_version_is_prerelease")]),
    (version_valid, [("test_version.py", "TestVersion", "test_valid_versions"),
                     ("test_version.py", "TestVersion", "test_invalid_versions")]),
    (specifier_contains, [("test_specifiers.py", "TestSpecifier", "test_specifiers"),
                          ("test_specifiers.py", "TestSpecifierSet", "test_contains_exclusionary_bridges")]),
    (specifier_filter, [("test_specifiers.py", "TestSpecifierSet", "test_specifier_filter")]),
    (specifier_satisfiable, [("test_specifiers.py", "TestIsUnsatisfiable", "test_satisfiable"),
                             ("test_specifiers.py", "TestIsUnsatisfiable", "test_unsatisfiable")]),
    (specifier_subset, [("test_specifiers.py", "TestSpecifierSet", "test_is_subset"),
                        ("test_specifiers.py", "TestSpecifierSet", "test_is_superset")]),
    (name_canonicalize, [("test_utils.py", None, "test_canonicalize_name")]),
    (version_canonicalize, [("test_utils.py", None, "test_canonicalize_version")]),
    (wheel_tags, [("test_utils.py", None, "test_parse_wheel_filename")]),
    (marker_evaluate, [("test_markers.py", "TestMarker", "test_evaluates")]),
]


def stratified_sample(rng: random.Random, items: list, n: int) -> list:
    """Sample up to n items, spreading them evenly over the different answers."""
    groups = defaultdict(list)
    for item in items:
        groups[json.dumps(item["answer"], sort_keys=True)].append(item)
    for group in groups.values():
        rng.shuffle(group)
    picked, queues = [], [groups[k] for k in sorted(groups)]
    while len(picked) < n and any(queues):
        for queue in queues:
            if queue and len(picked) < n:
                picked.append(queue.pop())
    return picked


def build_short(cases: list[dict], rng: random.Random, per_kind: int, stats: Counter) -> list[dict]:
    by_test = defaultdict(list)
    for c in cases:
        by_test[(Path(c["file"]).name, c["cls"], c["test"])].append(c)
    exercises = []
    for builder, tests in SHORT_KINDS:
        kind, agreed = builder.__name__, []
        for key in tests:
            for c in by_test[key]:
                built = builder(c)
                if built is None:
                    stats[f"{kind}: skipped"] += 1
                    continue
                ex, library = built
                if json.dumps(library, sort_keys=True) != json.dumps(ex["answer"], sort_keys=True) and \
                        not (ex["check"] == SET_EQUAL and sorted(library) == sorted(ex["answer"])):
                    stats[f"{kind}: dropped, library disagrees with test"] += 1
                    continue
                ex["provenance"] = {"test": c["nodeid"], "answer_from": "test expected value, confirmed by a direct library call"}
                agreed.append(ex)
        stats[f"{kind}: usable cases"] += len(agreed)
        exercises += stratified_sample(rng, agreed, per_kind)
    return exercises


# --- long exercises: check a requirements list against a made-up index ----------------------

INDEX = {  # made-up availability lists in realistic shapes, not real PyPI data
    "requests": ["2.25.1", "2.28.2", "2.31.0", "2.32.3", "2.33.0rc1"],
    "urllib3": ["1.26.18", "1.26.20", "2.0.7", "2.2.3", "2.3.0b1"],
    "numpy": ["1.24.4", "1.26.4", "2.0.2", "2.1.3", "2.2.0rc1"],
    "typing-extensions": ["4.5.0", "4.7.1", "4.9.0", "4.12.2", "4.13.0rc1"],
    "colorama": ["0.4.4", "0.4.5", "0.4.6"],
    "tomli": ["1.2.3", "2.0.1", "2.0.2", "2.1.0"],
    "importlib-metadata": ["4.13.0", "6.11.0", "7.2.1", "8.5.0", "8.6.0a1"],
    "pywin32": ["305", "306", "308"],
    "exceptiongroup": ["1.1.3", "1.2.0", "1.2.2"],
    "charset-normalizer": ["2.1.1", "3.3.2", "3.4.0", "3.4.1.dev2"],
}
SPELLINGS = {
    "requests": ["requests", "Requests"], "numpy": ["numpy", "NumPy"],
    "typing-extensions": ["typing-extensions", "typing_extensions", "Typing_Extensions"],
    "importlib-metadata": ["importlib-metadata", "importlib_metadata"], "pywin32": ["pywin32", "PyWin32"],
    "charset-normalizer": ["charset-normalizer", "charset_normalizer", "Charset.Normalizer"],
}
MARKERS = ['python_version < "3.11"', 'python_version >= "3.10"', 'sys_platform == "win32"',
           'sys_platform != "win32"', 'platform_machine == "arm64"',
           'python_version < "3.9" or sys_platform == "darwin"', 'os_name == "nt" and python_version >= "3.12"']
PLATFORMS = {  # sys_platform: (label, os_name, platform_system, machines)
    "linux": ("Linux", "posix", "Linux", ["x86_64", "aarch64"]),
    "darwin": ("macOS", "posix", "Darwin", ["arm64", "x86_64"]),
    "win32": ("Windows", "nt", "Windows", ["AMD64"]),
}


def random_specifier(rng: random.Random, versions: list[str]) -> str:
    finals = sorted((v for v in versions if not Version(v).is_prerelease), key=Version)
    i = rng.randrange(len(finals) - 1)
    lo, hi = finals[i], finals[rng.randrange(i + 1, len(finals))]
    major_minor = ".".join(str(n) for n in Version(lo).release[:2])
    return rng.choice([
        f">={lo}", f">={lo},<{hi}", f"<{hi}", f"!={hi},>={lo}", f"=={Version(lo).release[0]}.*",
        f"~={major_minor}" if len(Version(lo).release) > 1 else f">={lo}", "",
    ])


def environment(rng: random.Random) -> dict:
    python = rng.choice(["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"])
    sys_platform = rng.choice(sorted(PLATFORMS))
    _, os_name, system, machines = PLATFORMS[sys_platform]
    return {"python_version": python, "python_full_version": f"{python}.0", "sys_platform": sys_platform,
            "os_name": os_name, "platform_system": system, "platform_machine": rng.choice(machines)}


def requirements_check(rng: random.Random, n: int) -> dict:
    env = environment(rng)
    names = rng.sample(sorted(INDEX), rng.randint(4, 6))
    lines = []
    for name in names:
        extras = "[socks]" if name == "requests" and rng.random() < 0.3 else ""
        marker = f"; {rng.choice(MARKERS)}" if rng.random() < 0.5 else ""
        lines.append(f"{rng.choice(SPELLINGS.get(name, [name]))}{extras}{random_specifier(rng, INDEX[name])}{marker}")
    shown = sorted({*names, rng.choice(sorted(INDEX))})  # plus one package nobody asked for

    calls, answer, reference_answer = [], {}, {}
    for line in lines:
        req = Requirement(line)
        calls.append(call("parse_requirement", requirement=line))
        parsed = len(calls) - 1
        if req.marker is not None:
            calls.append(call("evaluate_marker", marker={"$ref": [parsed, "marker"]}, environment=env))
            if not req.marker.evaluate({**BASELINE_ENVIRONMENT, **env}):
                continue
        name = canonicalize_name(req.name)
        if name != req.name:
            calls.append(call("canonicalize_name", name={"$ref": [parsed, "name"]}))
        allowed = list(req.specifier.filter(INDEX[name], prereleases=False))
        calls.append(call("filter_versions", versions=INDEX[name], specifier={"$ref": [parsed, "specifier"]},
                          include_prereleases=False))
        if not allowed:
            answer[name] = reference_answer[name] = None
            continue
        calls.append(call("sort_versions", versions={"$ref": [len(calls) - 1]}, descending=True))
        answer[name] = max(allowed, key=Version)
        reference_answer[name] = {"$ref": [len(calls) - 1, 0]}

    label, _, _, _ = PLATFORMS[env["sys_platform"]]
    task = "\n".join([
        f"Target environment: CPython {env['python_version']} on {label} ({env['platform_machine']}).",
        "Available versions on the package index:",
        *(f"- {name}: {', '.join(INDEX[name])}" for name in shown),
        "Requirements:",
        *(f"{i}. {line}" for i, line in enumerate(lines, 1)),
        "For every requirement whose environment marker applies to the target environment, find the newest "
        "available version that satisfies its version constraint, without pre-releases. Answer with a JSON "
        "object that maps the normalized project name to that version, or to null if no available version "
        "fits. Leave out requirements whose marker does not apply.",
    ])
    return {"kind": "requirements_check", "horizon": "long", "task": task, "answer": answer, "check": EXACT,
            "reference_calls": calls, "reference_answer": reference_answer,
            "library_functions": ["packaging.requirements.Requirement", "packaging.markers.Marker.evaluate",
                                  "packaging.utils.canonicalize_name", "packaging.specifiers.SpecifierSet.filter",
                                  "packaging.version.Version"],
            "provenance": {"generator": "requirements_check", "index": "made-up versions, not real PyPI data",
                           "answer_from": "direct library calls"}}


def build_long(rng: random.Random, n: int) -> list[dict]:
    exercises = []
    while len(exercises) < n:
        ex = requirements_check(rng, len(exercises))
        if len(ex["reference_calls"]) >= 8:
            exercises.append(ex)
    return exercises


def preview(exercises: list[dict]) -> str:
    out = ["# Exercise preview: one example per kind", ""]
    seen = set()
    for ex in exercises:
        if ex["kind"] in seen:
            continue
        seen.add(ex["kind"])
        calls = "\n".join(f"  {i}. {c['tool']}({json.dumps(c['arguments'])})" for i, c in enumerate(ex["reference_calls"]))
        out += [f"## {ex['kind']} ({ex['horizon']}, {ex['reference_call_count']} calls)", "", "```text", ex["task"], "```", "",
                f"Answer: `{json.dumps(ex['answer'])}` (check: {ex['check']['kind']})", "", "Reference calls:", "",
                "```text", calls, "```", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-kind", type=int, default=20, help="short exercises per kind")
    parser.add_argument("--long", type=int, default=20, help="number of long exercises")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    cases = [json.loads(line) for line in open(OUT / "test_cases.jsonl")]
    stats = Counter()
    exercises = build_short(cases, rng, args.per_kind, stats) + build_long(rng, args.long)
    counters = Counter()
    for ex in exercises:
        counters[ex["kind"]] += 1
        ex["id"] = f"packaging-{ex['kind']}-{counters[ex['kind']]:03d}"
        ex["source_repo"] = f"pypa/packaging@{commit}"
        ex["reference_call_count"] = len(ex["reference_calls"])
    exercises = [{k: ex[k] for k in ("id", "kind", "horizon", "task", "answer", "check", "reference_calls",
                                     "reference_answer", "reference_call_count", "library_functions",
                                     "source_repo", "provenance")} for ex in exercises]

    with open(OUT / "exercises.jsonl", "w") as f:
        for ex in exercises:
            f.write(json.dumps(ex) + "\n")
    (OUT / "exercises_preview.md").write_text(preview(exercises))

    for key in sorted(stats):
        print(f"  {key}: {stats[key]}", file=sys.stderr)
    horizons = Counter(ex["horizon"] for ex in exercises)
    calls = [ex["reference_call_count"] for ex in exercises if ex["horizon"] == "long"]
    print(f"{len(exercises)} exercises ({dict(horizons)}); long ones need {min(calls)} to {max(calls)} reference "
          f"calls -> {OUT / 'exercises.jsonl'}", file=sys.stderr)


if __name__ == "__main__":
    main()
