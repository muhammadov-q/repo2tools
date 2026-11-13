"""Bundle the packaging exercises, tools and checker into one folder and a zip for Alex.

    uv run repo2tools handover
Writes out/handover/packaging-exercises-v0/ and out/handover/packaging-exercises-v0.zip.
The bundle installs packaging from GitHub at the commit pinned in pyproject.toml, so it runs on
any machine with uv.
"""

import shutil
import tomllib
from pathlib import Path

from repo2tools.paths import REPO_ROOT

HERE = Path(__file__).resolve().parent  # exercise_check.py and reference_calls.py are next to this file
NAME = "packaging-exercises-v0"
FILES = {
    "README.md": REPO_ROOT / "docs" / "handover" / "README.md",
    "exercises.jsonl": REPO_ROOT / "out" / "packaging" / "exercises.jsonl",
    "exercises_preview.md": REPO_ROOT / "out" / "packaging" / "exercises_preview.md",
    "exercise_check.py": HERE / "exercise_check.py",
    "run_reference_calls.py": HERE / "reference_calls.py",
    "server.py": REPO_ROOT / "toolsets" / "pypa_packaging" / "server.py",
    "tools.py": REPO_ROOT / "toolsets" / "pypa_packaging" / "tools.py",
    "coarse_tools.py": REPO_ROOT / "toolsets" / "pypa_packaging" / "coarse_tools.py",
}
# In the bundle the files lie flat next to each other and are run as scripts.
FLATTEN = {
    "from repo2tools.evaluation.exercise_check import": "from exercise_check import",
    "uv run repo2tools check-tools": "uv run python run_reference_calls.py",
}
PYPROJECT = """\
[project]
name = "packaging-exercises"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.26,<2",
    "{packaging}",
]

[tool.uv]
package = false
"""


def main() -> None:
    dependencies = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    packaging = next(d for d in dependencies if d.startswith("packaging"))
    out = REPO_ROOT / "out" / "handover"
    bundle = out / NAME
    shutil.rmtree(bundle, ignore_errors=True)
    bundle.mkdir(parents=True)
    for name, source in FILES.items():
        if source.suffix != ".py":
            shutil.copy2(source, bundle / name)
            continue
        text = source.read_text(encoding="utf-8")
        for packaged, flat in FLATTEN.items():
            text = text.replace(packaged, flat)
        if "repo2tools." in text:
            raise SystemExit(f"{source.name} still needs the repo2tools package; add the import to FLATTEN")
        (bundle / name).write_text(text, encoding="utf-8")
    (bundle / "pyproject.toml").write_text(PYPROJECT.format(packaging=packaging))
    archive = shutil.make_archive(str(out / NAME), "zip", root_dir=out, base_dir=NAME)
    print(f"{bundle}\n{archive}")


if __name__ == "__main__":
    main()
