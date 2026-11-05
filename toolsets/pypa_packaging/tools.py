"""Tools synthesized from pypa/packaging, version 0: about one tool per library function.

Written by Claude in a chat session on 2026-10-23 as the per-function granularity level and
as a reference set; later versions come from the automated LLM pipeline. Every tool takes and
returns plain JSON values (strings, booleans, lists, small objects), so one tool's output can
be passed to the next. Invalid input raises ValueError, which MCP reports as a tool error.

GYM_TYPES gives each tool's semantic parameter and output types for ToolGym's signature graph.
"""

from typing import TypedDict

from packaging.markers import InvalidMarker, Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.tags import compatible_tags, cpython_tags, parse_tag as _parse_tag
from packaging.utils import (
    InvalidName,
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name as _canonicalize_name,
    canonicalize_version as _canonicalize_version,
    parse_sdist_filename as _parse_sdist_filename,
    parse_wheel_filename as _parse_wheel_filename,
)
from packaging.version import InvalidVersion, Version

# Marker variables not given by the caller are taken from here, never from the machine
# running the server, so answers don't depend on where the tools run.
BASELINE_ENVIRONMENT = {
    "implementation_name": "cpython",
    "implementation_version": "3.12.0",
    "os_name": "posix",
    "platform_machine": "x86_64",
    "platform_python_implementation": "CPython",
    "platform_release": "6.8.0",
    "platform_system": "Linux",
    "platform_version": "#1 SMP",
    "python_full_version": "3.12.0",
    "python_version": "3.12",
    "sys_platform": "linux",
}


def _version(version: str) -> Version:
    try:
        return Version(version)
    except InvalidVersion as e:
        raise ValueError(f"not a valid PEP 440 version: {version!r}") from e


def _specifier_set(specifier: str, prereleases: bool | None = None) -> SpecifierSet:
    try:
        return SpecifierSet(specifier, prereleases=prereleases)
    except InvalidSpecifier as e:
        raise ValueError(f"not a valid version specifier: {specifier!r}") from e


class VersionInfo(TypedDict):
    epoch: int
    release: list[int]
    pre: list[str | int] | None
    post: int | None
    dev: int | None
    local: str | None
    public: str
    base_version: str
    is_prerelease: bool
    is_postrelease: bool
    is_devrelease: bool


class RequirementInfo(TypedDict):
    name: str
    extras: list[str]
    specifier: str
    marker: str | None
    url: str | None


class WheelInfo(TypedDict):
    name: str
    version: str
    build_tag: list[int | str] | None
    tags: list[str]


class SdistInfo(TypedDict):
    name: str
    version: str


# --- versions -------------------------------------------------------------------------------


def is_valid_version(version: str) -> bool:
    """Check whether a string is a valid version under Python's version rules (PEP 440)."""
    try:
        Version(version)
    except InvalidVersion:
        return False
    return True


def normalize_version(version: str) -> str:
    """Return the normalized PEP 440 form of a version string, e.g. '1.0-BETA2' -> '1.0b2'."""
    return str(_version(version))


def version_info(version: str) -> VersionInfo:
    """Split a PEP 440 version into its parts: epoch, release numbers, pre-, post- and
    dev-release, local label, public and base version, and whether it is a pre-, post- or
    dev-release."""
    v = _version(version)
    return {
        "epoch": v.epoch,
        "release": list(v.release),
        "pre": list(v.pre) if v.pre else None,
        "post": v.post,
        "dev": v.dev,
        "local": v.local,
        "public": v.public,
        "base_version": v.base_version,
        "is_prerelease": v.is_prerelease,
        "is_postrelease": v.is_postrelease,
        "is_devrelease": v.is_devrelease,
    }


def base_version(version: str) -> str:
    """Return the base version: the epoch and release numbers only, without pre-, post-,
    dev-release or local parts, e.g. '1!2.0rc1.post3+abc' -> '1!2.0'."""
    return _version(version).base_version


def compare_versions(version_a: str, version_b: str) -> int:
    """Compare two PEP 440 versions. Returns -1 if version_a is older, 0 if they are equal,
    1 if version_a is newer."""
    a, b = _version(version_a), _version(version_b)
    return (a > b) - (a < b)


def sort_versions(versions: list[str], descending: bool = False) -> list[str]:
    """Sort version strings from oldest to newest (or newest first if descending is true),
    using PEP 440 ordering. The strings are returned unchanged."""
    return sorted(versions, key=_version, reverse=descending)


def canonicalize_version(version: str, strip_trailing_zero: bool = True) -> str:
    """Return the canonical form of a version used for comparing file names: normalized and,
    by default, without trailing '.0' release segments, e.g. '1.0.0' -> '1'."""
    return _canonicalize_version(_version(version), strip_trailing_zero=strip_trailing_zero)


# --- specifiers (version constraints such as '>=1.0,<2') -----------------------------------


def is_valid_specifier(specifier: str) -> bool:
    """Check whether a string is a valid version constraint (specifier set), e.g. '>=1.0,<2'."""
    try:
        SpecifierSet(specifier)
    except InvalidSpecifier:
        return False
    return True


def version_satisfies(version: str, specifier: str, include_prereleases: bool | None = None) -> bool:
    """Check whether a version is allowed by a version constraint such as '>=1.0,!=1.3,<2'.
    include_prereleases: true allows pre-releases, false excludes them, null (default) follows
    PEP 440: pre-releases match only if the constraint itself mentions one."""
    return _specifier_set(specifier).contains(version, prereleases=include_prereleases)


def filter_versions(versions: list[str], specifier: str, include_prereleases: bool | None = None) -> list[str]:
    """Keep only the versions allowed by a version constraint, in their original order.
    include_prereleases: true keeps pre-releases, false drops them, null (default) follows
    PEP 440: pre-releases are kept only if nothing else matches or the constraint mentions one."""
    return list(_specifier_set(specifier).filter(versions, prereleases=include_prereleases))


def combine_specifiers(specifier_a: str, specifier_b: str) -> str:
    """Combine two version constraints into one that requires both, e.g. '>=1.0' and '<2' ->
    '<2,>=1.0'."""
    return str(_specifier_set(specifier_a) & _specifier_set(specifier_b))


def is_satisfiable(specifier: str) -> bool:
    """Check whether at least one version could satisfy a version constraint, e.g.
    '>=2,<1' cannot."""
    return not _specifier_set(specifier).is_unsatisfiable()


def specifier_is_subset(specifier: str, other: str, include_prereleases: bool | None = None) -> bool:
    """Check whether every version allowed by `specifier` is also allowed by `other`, e.g.
    '>=3.12,<3.13' is a subset of '>=3.12'."""
    return _specifier_set(specifier, include_prereleases).is_subset(_specifier_set(other, include_prereleases))


def specifiers_overlap(specifier_a: str, specifier_b: str) -> bool:
    """Check whether at least one version is allowed by both version constraints."""
    return not _specifier_set(specifier_a).is_disjoint(_specifier_set(specifier_b))


# --- requirements and markers ---------------------------------------------------------------


def parse_requirement(requirement: str) -> RequirementInfo:
    """Parse a dependency line such as 'requests[socks]>=2.31; python_version < "3.13"' into
    its name, extras, version constraint, environment marker and URL."""
    try:
        r = Requirement(requirement)
    except InvalidRequirement as e:
        raise ValueError(f"not a valid requirement: {requirement!r}: {e}") from e
    return {
        "name": r.name,
        "extras": sorted(r.extras),
        "specifier": str(r.specifier),
        "marker": str(r.marker) if r.marker else None,
        "url": r.url,
    }


def evaluate_marker(marker: str, environment: dict | None = None) -> bool:
    """Evaluate an environment marker such as 'python_version < "3.11" and sys_platform ==
    "win32"'. environment maps marker variables (python_version, sys_platform, os_name,
    platform_machine, extra, ...) to values; variables not given are those of CPython 3.12.0
    on Linux x86_64."""
    try:
        m = Marker(marker)
    except InvalidMarker as e:
        raise ValueError(f"not a valid marker: {marker!r}: {e}") from e
    env = {**BASELINE_ENVIRONMENT, **(environment or {})}
    for key in ("extras", "dependency_groups"):
        if isinstance(env.get(key), list):
            env[key] = frozenset(env[key])
    return m.evaluate(env)


# --- names, files and tags ------------------------------------------------------------------


def canonicalize_name(name: str) -> str:
    """Return the normalized project name used by package indexes, e.g. 'Typing_Extensions' ->
    'typing-extensions'."""
    try:
        return _canonicalize_name(name, validate=True)
    except InvalidName as e:
        raise ValueError(f"not a valid project name: {name!r}") from e


def parse_wheel_filename(filename: str) -> WheelInfo:
    """Parse a wheel file name such as 'numpy-2.1.0-cp312-cp312-manylinux_2_17_x86_64.whl'
    into project name, version, build tag and the set of compatibility tags it declares."""
    try:
        name, version, build, tags = _parse_wheel_filename(filename)
    except InvalidWheelFilename as e:
        raise ValueError(str(e)) from e
    return {
        "name": name,
        "version": str(version),
        "build_tag": list(build) if build else None,
        "tags": sorted(str(t) for t in tags),
    }


def parse_sdist_filename(filename: str) -> SdistInfo:
    """Parse a source distribution file name such as 'requests-2.31.0.tar.gz' into project name
    and version."""
    try:
        name, version = _parse_sdist_filename(filename)
    except InvalidSdistFilename as e:
        raise ValueError(str(e)) from e
    return {"name": name, "version": str(version)}


def parse_tag(tag: str) -> list[str]:
    """Expand a compressed compatibility tag such as 'py2.py3-none-any' into the individual
    tags it stands for."""
    try:
        return sorted(str(t) for t in _parse_tag(tag))
    except ValueError as e:
        raise ValueError(f"not a valid tag: {tag!r}") from e


def supported_tags(python_version: str, platforms: list[str]) -> list[str]:
    """List the wheel tags a CPython interpreter accepts, most preferred first.
    python_version is like '3.12'; platforms are platform tags such as
    ['manylinux_2_17_x86_64', 'linux_x86_64'], most preferred first."""
    try:
        major, minor = (int(p) for p in python_version.split("."))
    except ValueError as e:
        raise ValueError(f"python_version must look like '3.12', got {python_version!r}") from e
    abi = f"cp{major}{minor}"
    tags = [*cpython_tags((major, minor), abis=[abi], platforms=platforms),
            *compatible_tags((major, minor), interpreter=abi, platforms=platforms)]
    return [str(t) for t in tags]


TOOLS = [
    is_valid_version, normalize_version, version_info, base_version, compare_versions,
    sort_versions, canonicalize_version,
    is_valid_specifier, version_satisfies, filter_versions, combine_specifiers, is_satisfiable,
    specifier_is_subset, specifiers_overlap,
    parse_requirement, evaluate_marker,
    canonicalize_name, parse_wheel_filename, parse_sdist_filename, parse_tag, supported_tags,
]

# (parameter types, output type). Custom types are defined in toolgym_types.py; object outputs
# have their own types so ToolGym can extract fields (e.g. RequirementInfo.specifier).
_V, _VS, _S = "PackageVersion", "VersionList", "VersionSpecifier"
GYM_TYPES = {
    "is_valid_version": ({"version": "string"}, "boolean"),
    "normalize_version": ({"version": _V}, _V),
    "version_info": ({"version": _V}, "VersionInfo"),
    "base_version": ({"version": _V}, _V),
    "compare_versions": ({"version_a": _V, "version_b": _V}, "integer"),
    "sort_versions": ({"versions": _VS, "descending": "boolean"}, _VS),
    "canonicalize_version": ({"version": _V, "strip_trailing_zero": "boolean"}, _V),
    "is_valid_specifier": ({"specifier": "string"}, "boolean"),
    "version_satisfies": ({"version": _V, "specifier": _S, "include_prereleases": "boolean"}, "boolean"),
    "filter_versions": ({"versions": _VS, "specifier": _S, "include_prereleases": "boolean"}, _VS),
    "combine_specifiers": ({"specifier_a": _S, "specifier_b": _S}, _S),
    "is_satisfiable": ({"specifier": _S}, "boolean"),
    "specifier_is_subset": ({"specifier": _S, "other": _S, "include_prereleases": "boolean"}, "boolean"),
    "specifiers_overlap": ({"specifier_a": _S, "specifier_b": _S}, "boolean"),
    "parse_requirement": ({"requirement": "RequirementString"}, "RequirementInfo"),
    "evaluate_marker": ({"marker": "EnvironmentMarker", "environment": "MarkerEnvironment"}, "boolean"),
    "canonicalize_name": ({"name": "ProjectName"}, "PackageName"),
    "parse_wheel_filename": ({"filename": "WheelFilename"}, "WheelInfo"),
    "parse_sdist_filename": ({"filename": "SdistFilename"}, "SdistInfo"),
    "parse_tag": ({"tag": "WheelTag"}, "WheelTagList"),
    "supported_tags": ({"python_version": "PythonVersion", "platforms": "PlatformTagList"}, "WheelTagList"),
}
assert set(GYM_TYPES) == {t.__name__ for t in TOOLS}
