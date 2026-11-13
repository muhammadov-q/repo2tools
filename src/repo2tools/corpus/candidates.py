"""Candidate repositories for the many-repo experiments: the most downloaded PyPI packages that are pure Python.

    uv run repo2tools corpus-candidates --scan 600 --want 100

It reads two public lists and nothing else: the monthly list of the most downloaded PyPI packages, and
PyPI's own description of each package's newest release. Nothing is cloned, and no package code is
downloaded or run. The result is a list for a person to approve: a repository enters an experiment only
after that.

Rules, applied to each package in download order (the first rule that fails is the reason it is left out):

    stubs       type stubs carry no code of their own (types-*, *-stubs)
    no wheel    the newest release has no wheel, so "pure Python" cannot be read from PyPI
    native      a wheel is built for one platform or interpreter: the package has compiled code
    too large   the source archive is larger than --max-sdist-mb (generated SDKs, bundled data)
    no repo     no GitHub repository is named in the package's links
    same repo   a more downloaded package already stands for this repository (monorepos count once)

Writes out/corpus/candidates.json and out/corpus/candidates.md.
"""

import argparse
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import httpx

from repo2tools.paths import REPO_ROOT

TOP_PACKAGES = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
PYPI = "https://pypi.org/pypi/{name}/json"
USER_AGENT = "repo2tools-corpus"  # a generic client name; no contact details are sent
GITHUB = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
NOT_A_REPO = {"sponsors", "orgs", "apps", "marketplace", "features", "topics"}  # github.com/<this>/... is not owner/name
PURE_WHEEL = re.compile(r"-(?:py3|py2\.py3|py3\.py2)-none-any\.whl$")


def fetch_json(url: str, timeout: int = 30) -> dict:
    response = httpx.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def github_repo(info: dict) -> str | None:
    """The package's GitHub repository as https://github.com/owner/name, from its links; the source link wins."""
    links = info.get("project_urls") or {}
    order = sorted(links.items(), key=lambda kv: 0 if re.search(r"source|repo|code|github", kv[0], re.I) else 1 if re.search(r"home", kv[0], re.I) else 2)
    for _, url in [*order, ("home_page", info.get("home_page") or "")]:
        match = GITHUB.match(url or "")
        if match and match.group(1).lower() not in NOT_A_REPO:
            return f"https://github.com/{match.group(1)}/{match.group(2).removesuffix('.git')}"
    return None


def license_of(info: dict) -> str:
    """The license as PyPI states it: the SPDX expression, else the license classifier, else the first line of the free text."""
    classifier = next((c.rsplit(" :: ", 1)[-1] for c in info.get("classifiers") or [] if c.startswith("License ::")), None)
    free_text = (info.get("license") or "").strip().splitlines()
    return info.get("license_expression") or classifier or (free_text[0][:40] if free_text else "not stated")


def assess(name: str, meta: dict, max_sdist_mb: float = 5.0) -> dict:
    """One package: what PyPI says about it, and `reason`: why it is left out, or None if it is a candidate."""
    info, files = meta.get("info") or {}, meta.get("urls") or []
    wheels = [f["filename"] for f in files if f.get("packagetype") == "bdist_wheel"]
    sdist_mb = max((f.get("size", 0) for f in files if f.get("packagetype") == "sdist"), default=0) / 1e6
    row = {"package": name, "version": info.get("version"), "repo": github_repo(info), "summary": (info.get("summary") or "").strip()[:120],
           "license": license_of(info), "dependencies": len([r for r in info.get("requires_dist") or [] if "extra ==" not in r]),
           "sdist_mb": round(sdist_mb, 2), "reason": None}
    if name.startswith("types-") or name.endswith("-stubs"):
        row["reason"] = "stubs"
    elif not wheels:
        row["reason"] = "no wheel"
    elif not all(PURE_WHEEL.search(w) for w in wheels):
        row["reason"] = "native"
    elif sdist_mb > max_sdist_mb:
        row["reason"] = "too large"
    elif not row["repo"]:
        row["reason"] = "no repo"
    return row


def select(rows: list[dict], want: int) -> list[dict]:
    """Candidates in download order, one per repository, at most `want`; later packages of a repository get the reason "same repo"."""
    seen, chosen = set(), []
    for row in rows:
        if row["reason"]:
            continue
        key = row["repo"].lower()
        if key in seen:
            row["reason"] = "same repo"
        elif len(chosen) < want:
            seen.add(key)
            chosen.append(row)
        else:
            row["reason"] = "beyond the number asked for"
    return chosen


def report(chosen: list[dict], rows: list[dict], source: dict) -> str:
    left_out = Counter(r["reason"] for r in rows if r["reason"])
    lines = ["# Candidate repositories", "",
             f"{len(chosen)} pure-Python packages with a GitHub repository, from the {len(rows)} most downloaded PyPI packages "
             f"(list of {source['list_updated']}, read on {source['read_on']}). Nothing was cloned or run to make this list.", "",
             "Left out: " + ", ".join(f"{n} {reason}" for reason, n in left_out.most_common()) + ".", "",
             "| # | Downloads rank | Package | Repository | License | Dependencies | What it is |", "| --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {i} | {r['rank']} | `{r['package']}` {r['version']} | {r['repo']} | {r['license']} | {r['dependencies']} | {r['summary'].replace('|', '/')} |"
              for i, r in enumerate(chosen, 1)]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scan", type=int, default=600, help="how many of the most downloaded packages to look at")
    parser.add_argument("--want", type=int, default=100, help="how many candidates to keep")
    parser.add_argument("--max-sdist-mb", type=float, default=5.0)
    parser.add_argument("-o", "--output", type=Path, default=REPO_ROOT / "out" / "corpus")
    args = parser.parse_args()

    top = fetch_json(TOP_PACKAGES)
    names = [row["project"] for row in top["rows"][:args.scan]]

    def one(item: tuple[int, str]) -> dict:
        rank, name = item
        try:
            row = assess(name, fetch_json(PYPI.format(name=name)), args.max_sdist_mb)
        except Exception as error:  # noqa: BLE001 (one unreachable package must not stop the list)
            row = {"package": name, "version": None, "repo": None, "summary": "", "license": "not stated", "dependencies": 0, "sdist_mb": 0,
                   "reason": f"not readable ({type(error).__name__})"}
        return {"rank": rank, **row}

    with ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(one, enumerate(names, 1)))
    chosen = select(rows, args.want)
    source = {"top_packages": TOP_PACKAGES, "list_updated": str(top.get("last_update", ""))[:10], "pypi": PYPI, "read_on": date.today().isoformat(),
              "scanned": len(rows), "max_sdist_mb": args.max_sdist_mb}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "candidates.json").write_text(json.dumps({"source": source, "candidates": chosen, "left_out": [r for r in rows if r["reason"]]}, indent=1) + "\n", encoding="utf-8")
    (args.output / "candidates.md").write_text(report(chosen, rows, source), encoding="utf-8")
    print(f"{len(chosen)} candidates from {len(rows)} packages -> {(args.output / 'candidates.md').relative_to(REPO_ROOT) if args.output.is_relative_to(REPO_ROOT) else args.output / 'candidates.md'}")
    print("left out: " + ", ".join(f"{n} {reason}" for reason, n in Counter(r["reason"] for r in rows if r["reason"]).most_common()))


if __name__ == "__main__":
    main()
