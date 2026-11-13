"""ToolGym semantic types for the pypa/packaging tools (repo2tools, version 0).

Copied into ToolGym's catalog as types.py by `repo2tools toolgym-export`; imports only what a
catalog folder may import. Sample pools come from packaging's own test cases (samples.json,
written next to this file by the same script).

- Enum types sample real strings: versions, version constraints, requirements, markers, names,
  file names and tags.
- List types sample a few elements; their first element can be extracted (e.g. the newest
  version after sorting).
- Object types are tool outputs whose fields can be extracted into the types above.
"""

import ast
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pydantic
from pydantic import BaseModel, ConfigDict

from gym.tools.shared import validate_extraction_selectors
from gym.tools.shared.types import GymEnumTypeFactory, GymOutputOnlyTypeFactory, GymType
from modules.trace_generation.protocols import (
    ExtractionProjection,
    TypeRepresentation,
    Projection,
    TypeMaterializationError,
)

_SAMPLES = json.loads((Path(__file__).parent / "samples.json").read_text())


def _parse(s: str) -> Any:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError) as exc:
            raise TypeMaterializationError(f"not JSON or a Python literal: {s[:80]!r}") from exc


def _enum(name: str, key: str, **kwargs) -> GymEnumTypeFactory:
    return GymEnumTypeFactory(name=name, choices=tuple(_SAMPLES[key]), **kwargs)


PACKAGE_VERSION_TYPE = _enum("PackageVersion", "versions")
VERSION_SPECIFIER_TYPE = _enum("VersionSpecifier", "specifiers")
REQUIREMENT_STRING_TYPE = _enum("RequirementString", "requirements")
ENVIRONMENT_MARKER_TYPE = _enum("EnvironmentMarker", "markers")
PROJECT_NAME_TYPE = _enum("ProjectName", "project_names")
# a normalized name is still a valid project name
PACKAGE_NAME_TYPE = _enum("PackageName", "package_names", projections=(PROJECT_NAME_TYPE,))
WHEEL_FILENAME_TYPE = _enum("WheelFilename", "wheel_filenames")
SDIST_FILENAME_TYPE = _enum("SdistFilename", "sdist_filenames")
WHEEL_TAG_TYPE = _enum("WheelTag", "wheel_tags")
PLATFORM_TAG_TYPE = _enum("PlatformTag", "platform_tags")
PYTHON_VERSION_TYPE = _enum("PythonVersion", "python_versions")


@dataclass(frozen=True, eq=False)
class ListTypeFactory(GymType):
    """A JSON list of values of one enum type; its first element can be extracted."""

    element: GymEnumTypeFactory | None = None
    min_items: int = 2
    max_items: int = 6

    def random_sample(self, rng: random.Random) -> list:
        pool = list(self.element.choices)
        return rng.sample(pool, rng.randint(self.min_items, min(self.max_items, len(pool))))

    def from_str(self, s: str) -> list:
        value = _parse(s)
        if not isinstance(value, list):
            raise TypeMaterializationError(f"{self.name} must be a list, got {type(value).__name__}")
        return value

    def get_projections(self) -> tuple[Projection, ...]:
        return (ExtractionProjection(target=self.element, selector=(0,)),)


VERSION_LIST_TYPE = ListTypeFactory(name="VersionList", element=PACKAGE_VERSION_TYPE, min_items=3)
WHEEL_TAG_LIST_TYPE = ListTypeFactory(name="WheelTagList", element=WHEEL_TAG_TYPE)
PLATFORM_TAG_LIST_TYPE = ListTypeFactory(name="PlatformTagList", element=PLATFORM_TAG_TYPE, min_items=1, max_items=3)


@dataclass(frozen=True, eq=False)
class MarkerEnvironmentTypeFactory(GymType):
    """Values for environment-marker variables: a Python version on one platform."""

    name: str = "MarkerEnvironment"

    def random_sample(self, rng: random.Random) -> dict:
        return rng.choice(_SAMPLES["environments"])

    def from_str(self, s: str) -> dict:
        value = _parse(s)
        if not isinstance(value, dict):
            raise TypeMaterializationError(f"{self.name} must be an object")
        return value


MARKER_ENVIRONMENT_TYPE = MarkerEnvironmentTypeFactory()


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class VersionInfo(_Model):
    epoch: int
    release: list[int]
    public: str
    base_version: str
    is_prerelease: bool


class RequirementInfo(_Model):
    name: str
    extras: list[str]
    specifier: str
    marker: str | None = None
    url: str | None = None


class WheelInfo(_Model):
    name: str
    version: str
    tags: list[str]


class SdistInfo(_Model):
    name: str
    version: str


@dataclass(frozen=True, eq=False)
class ObjectTypeFactory(GymOutputOnlyTypeFactory):
    """A tool's object output; the listed fields can be extracted into other types."""

    model: type[BaseModel] | None = None
    fields: tuple[tuple[str, TypeRepresentation], ...] = ()

    def from_str(self, s: str) -> BaseModel:
        try:
            return self.model.model_validate(_parse(s))
        except pydantic.ValidationError as exc:
            raise TypeMaterializationError(f"Invalid {self!s} payload: {exc}") from exc

    def get_projections(self) -> tuple[Projection, ...]:
        return tuple(ExtractionProjection(target=target, selector=(field,)) for field, target in self.fields)

    def __post_init__(self) -> None:
        parent_post_init = getattr(super(), "__post_init__", None)
        if callable(parent_post_init):
            parent_post_init()
        validate_extraction_selectors(self, self.model)


VERSION_INFO_TYPE = ObjectTypeFactory(
    name="VersionInfo", model=VersionInfo,
    fields=(("base_version", PACKAGE_VERSION_TYPE), ("public", PACKAGE_VERSION_TYPE)),
)
REQUIREMENT_INFO_TYPE = ObjectTypeFactory(
    name="RequirementInfo", model=RequirementInfo,
    fields=(("name", PROJECT_NAME_TYPE), ("specifier", VERSION_SPECIFIER_TYPE), ("marker", ENVIRONMENT_MARKER_TYPE)),
)
WHEEL_INFO_TYPE = ObjectTypeFactory(
    name="WheelInfo", model=WheelInfo,
    fields=(("name", PACKAGE_NAME_TYPE), ("version", PACKAGE_VERSION_TYPE), ("tags", WHEEL_TAG_LIST_TYPE)),
)
SDIST_INFO_TYPE = ObjectTypeFactory(
    name="SdistInfo", model=SdistInfo,
    fields=(("name", PACKAGE_NAME_TYPE), ("version", PACKAGE_VERSION_TYPE)),
)

ALL_TYPES = (
    PACKAGE_VERSION_TYPE, VERSION_SPECIFIER_TYPE, REQUIREMENT_STRING_TYPE, ENVIRONMENT_MARKER_TYPE,
    PROJECT_NAME_TYPE, PACKAGE_NAME_TYPE, WHEEL_FILENAME_TYPE, SDIST_FILENAME_TYPE, WHEEL_TAG_TYPE,
    PLATFORM_TAG_TYPE, PYTHON_VERSION_TYPE, VERSION_LIST_TYPE, WHEEL_TAG_LIST_TYPE, PLATFORM_TAG_LIST_TYPE,
    MARKER_ENVIRONMENT_TYPE, VERSION_INFO_TYPE, REQUIREMENT_INFO_TYPE, WHEEL_INFO_TYPE, SDIST_INFO_TYPE,
)
