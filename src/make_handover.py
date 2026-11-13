"""Bundle the packaging exercises, tools and checker into one folder and a zip for Alex.

    python3 -I make_handover.py
Writes out/handover/packaging-exercises-v0/ and out/handover/packaging-exercises-v0.zip.
The bundle installs packaging from GitHub at the commit pinned in pyproject.toml, so it runs on
any machine with uv.
"""

import shutil
import tomllib
from pathlib import Path

SRC = Path(__file__).resolve().parent
HERE = SRC.parent  # the repository's root
NAME = "packaging-exercises-v0"
FILES = {
    "README.md": HERE / "handover" / "README.md",
    "exercises.jsonl": HERE / "out" / "packaging" / "exercises.jsonl",
    "exercises_preview.md": HERE / "out" / "packaging" / "exercises_preview.md",
    "exercise_check.py": SRC / "exercise_check.py",
    "run_reference_calls.py": SRC / "run_reference_calls.py",
    "server.py": HERE / "toolsets" / "pypa_packaging" / "server.py",
    "tools.py": HERE / "toolsets" / "pypa_packaging" / "tools.py",
    "coarse_tools.py": HERE / "toolsets" / "pypa_packaging" / "coarse_tools.py",
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
    dependencies = tomllib.loads((HERE / "pyproject.toml").read_text())["project"]["dependencies"]
    packaging = next(d for d in dependencies if d.startswith("packaging"))
    out = HERE / "out" / "handover"
    bundle = out / NAME
    shutil.rmtree(bundle, ignore_errors=True)
    bundle.mkdir(parents=True)
    for name, source in FILES.items():
        shutil.copy2(source, bundle / name)
    (bundle / "pyproject.toml").write_text(PYPROJECT.format(packaging=packaging))
    archive = shutil.make_archive(str(out / NAME), "zip", root_dir=out, base_dir=NAME)
    print(f"{bundle}\n{archive}")


if __name__ == "__main__":
    main()
