"""Tests for the candidate list of the many-repo experiments. No network: PyPI's answers are written here."""

from repo2tools.corpus.candidates import assess, github_repo, report, select


def meta(wheels=("x-1.0-py3-none-any.whl",), sdist_mb=0.1, links=None, **info):
    files = [{"packagetype": "bdist_wheel", "filename": w, "size": 1000} for w in wheels]
    files.append({"packagetype": "sdist", "filename": "x-1.0.tar.gz", "size": int(sdist_mb * 1e6)})
    return {"info": {"version": "1.0", "summary": "A thing.", "project_urls": links if links is not None else {"Source": "https://github.com/me/x"}, **info}, "urls": files}


def test_a_pure_python_package_with_a_repository_is_a_candidate():
    row = assess("x", meta(license_expression="MIT", requires_dist=["a>=1", "b; extra == 'dev'"]))
    assert row["reason"] is None and row["repo"] == "https://github.com/me/x" and row["license"] == "MIT" and row["dependencies"] == 1


def test_reasons_to_leave_a_package_out():
    assert assess("types-x", meta())["reason"] == "stubs" and assess("x-stubs", meta())["reason"] == "stubs"
    assert assess("x", meta(wheels=()))["reason"] == "no wheel"
    assert assess("x", meta(wheels=("x-1.0-cp312-cp312-manylinux_2_17_x86_64.whl", "x-1.0-py3-none-any.whl")))["reason"] == "native"
    assert assess("x", meta(sdist_mb=9))["reason"] == "too large"
    assert assess("x", meta(links={"Docs": "https://x.readthedocs.io"}))["reason"] == "no repo"


def test_the_repository_is_read_from_the_links():
    assert github_repo({"project_urls": {"Homepage": "https://x.org", "Source Code": "https://github.com/me/x.git"}}) == "https://github.com/me/x"
    assert github_repo({"project_urls": {"Changelog": "https://github.com/me/x/blob/main/HISTORY.md"}}) == "https://github.com/me/x"
    assert github_repo({"project_urls": {"Funding": "https://github.com/sponsors/me"}, "home_page": "https://github.com/me/x"}) == "https://github.com/me/x"
    assert github_repo({"project_urls": None, "home_page": "https://gitlab.com/me/x"}) is None
    assert assess("x", meta(license="BSD\nlong text", classifiers=[]))["license"] == "BSD"
    assert assess("x", meta())["license"] == "not stated"


def test_one_candidate_per_repository_in_download_order():
    rows = [{"rank": i, **assess(name, meta(links={"Source": f"https://github.com/me/{repo}"}))}
            for i, (name, repo) in enumerate([("a", "mono"), ("b", "Mono"), ("c", "other"), ("d", "third")], 1)]
    chosen = select(rows, 2)
    assert [r["package"] for r in chosen] == ["a", "c"]
    assert [r["reason"] for r in rows] == [None, "same repo", None, "beyond the number asked for"]
    text = report(chosen, rows, {"list_updated": "2026-11-01", "read_on": "2026-11-13"})
    assert "2 pure-Python packages" in text and "| 2 | 3 | `c` 1.0 | https://github.com/me/other |" in text and "1 same repo" in text
