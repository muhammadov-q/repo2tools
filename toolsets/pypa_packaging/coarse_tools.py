"""Coarser tools over pypa/packaging, for the granularity experiment (2026-10-30).

The same library cut at three granularities:
- function: tools.py, about one tool per library function (21 tools)
- feature:  check_requirement, one call per dependency line
- workflow: check_requirements, one call for a whole requirements list

Written by Claude in a chat session, like version 0 of tools.py. Same conventions: plain JSON in
and out, invalid input raises ValueError, unset marker variables come from BASELINE_ENVIRONMENT.
"""

from typing import TypedDict

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from tools import BASELINE_ENVIRONMENT


class RequirementCheck(TypedDict):
    name: str
    applies: bool
    newest_allowed: str | None


def _requirement(line: str) -> Requirement:
    try:
        return Requirement(line)
    except InvalidRequirement as e:
        raise ValueError(f"not a valid requirement: {line!r}: {e}") from e


def _newest(req: Requirement, versions: list[str], include_prereleases: bool) -> str | None:
    try:
        allowed = list(req.specifier.filter(versions, prereleases=include_prereleases))
        return max(allowed, key=Version) if allowed else None
    except InvalidVersion as e:
        raise ValueError(str(e)) from e


def check_requirement(requirement: str, available_versions: list[str], environment: dict | None = None,
                      include_prereleases: bool = False) -> RequirementCheck:
    """Check one dependency line, e.g. 'tomli>=1.1; python_version < "3.11"', against the versions
    available on a package index, for a target environment. Returns the normalized project name,
    whether the line's environment marker applies, and the newest available version that satisfies
    its version constraint (null if none does, or if the marker does not apply).
    environment maps marker variables (python_version, sys_platform, platform_machine, os_name, ...)
    to values; variables not given are those of CPython 3.12.0 on Linux x86_64.
    Pre-releases are excluded unless include_prereleases is true."""
    req = _requirement(requirement)
    env = {**BASELINE_ENVIRONMENT, **(environment or {})}
    applies = req.marker is None or req.marker.evaluate(env)
    return {"name": canonicalize_name(req.name), "applies": applies,
            "newest_allowed": _newest(req, available_versions, include_prereleases) if applies else None}


def check_requirements(requirements: list[str], index: dict[str, list[str]], environment: dict | None = None,
                       include_prereleases: bool = False) -> dict[str, str | None]:
    """Check a whole requirements list against a package index for a target environment.
    index maps project names to their available versions (names are normalized before lookup).
    Returns a map from the normalized name of every requirement whose environment marker applies
    to the newest available version that satisfies its constraint (null if none fits).
    Requirements whose marker does not apply are left out.
    environment maps marker variables (python_version, sys_platform, platform_machine, os_name, ...)
    to values; variables not given are those of CPython 3.12.0 on Linux x86_64.
    Pre-releases are excluded unless include_prereleases is true."""
    available = {canonicalize_name(name): versions for name, versions in index.items()}
    result = {}
    for line in requirements:
        check = check_requirement(line, [], environment)
        if not check["applies"]:
            continue
        if check["name"] not in available:
            raise ValueError(f"{check['name']!r} is not on the index")
        result[check["name"]] = _newest(_requirement(line), available[check["name"]], include_prereleases)
    return result


FEATURE_TOOLS = [check_requirement]
WORKFLOW_TOOLS = [check_requirements]
