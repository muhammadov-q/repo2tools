# repo2tools report: packaging-pick-usage-docs-classes-operators

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.3 min. LLM tokens: 214,900 in 155 requests (propose 7,864, spec 104,816, code 102,220)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 55 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 48 |
| Accepted and confirmed against a direct library call | 48 |
| Passed all checks on the first try | 37 |
| Rejected after the repair rounds | 7 |

First try, by the first check that failed: ok: 37, spec: 10, differential: 4, fastmcp: 2, runs: 2.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `create_specifier_set` | `packaging.specifiers.SpecifierSet` | 0 | 4 / 1 | yes |
| `create_version` | `packaging.version.Version` | 0 | 5 / 1 | yes |
| `create_specifier` | `packaging.specifiers.Specifier` | 0 | 4 / 1 | yes |
| `create_marker` | `packaging.markers.Marker` | 0 | 3 / 2 | yes |
| `specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 5 / 1 | yes |
| `filter_with_version_range` | `packaging.ranges.VersionRange.filter` | 2 | 5 / 0 | yes |
| `is_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `is_version_range_empty` | `packaging.ranges.VersionRange.is_empty` | 2 | 5 / 1 | yes |
| `is_version_prerelease` | `packaging.version.Version.is_prerelease` | 0 | 5 / 1 | yes |
| `specifier_contains_version` | `packaging.specifiers.Specifier.contains` | 0 | 6 / 0 | yes |
| `filter_with_specifier` | `packaging.specifiers.Specifier.filter` | 1 | 5 / 0 | yes |
| `specifier_set_contains_version` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 1 | yes |
| `create_full_version_range` | `packaging.ranges.VersionRange.full` | 1 | 5 / 0 | yes |
| `create_empty_version_range` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `create_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `canonicalize_version_string` | `packaging.utils.canonicalize_version` | 0 | 6 / 0 | yes |
| `get_version_pre_release` | `packaging.version.Version.pre` | 0 | 5 / 1 | yes |
| `get_version_release` | `packaging.version.Version.release` | 0 | 5 / 1 | yes |
| `get_version_post_release` | `packaging.version.Version.post` | 0 | 5 / 1 | yes |
| `is_version_postrelease` | `packaging.version.Version.is_postrelease` | 0 | 5 / 0 | yes |
| `get_version_epoch` | `packaging.version.Version.epoch` | 0 | 5 / 0 | yes |
| `get_version_public` | `packaging.version.Version.public` | 0 | 5 / 1 | yes |
| `get_version_base` | `packaging.version.Version.base_version` | 0 | 5 / 1 | yes |
| `get_version_dev` | `packaging.version.Version.dev` | 0 | 5 / 1 | yes |
| `get_version_local` | `packaging.version.Version.local` | 0 | 4 / 2 | yes |
| `is_version_devrelease` | `packaging.version.Version.is_devrelease` | 0 | 5 / 1 | yes |
| `get_version_minor` | `packaging.version.Version.minor` | 0 | 5 / 1 | yes |
| `get_version_micro` | `packaging.version.Version.micro` | 0 | 5 / 0 | yes |
| `get_version_major` | `packaging.version.Version.major` | 0 | 4 / 1 | yes |
| `parse_version_string` | `packaging.version.parse` | 0 | 4 / 1 | yes |
| `normalize_pre_release` | `packaging.version.normalize_pre` | 0 | 5 / 0 | yes |
| `check_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `check_specifier_set_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `check_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `check_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 2 | 5 / 1 | yes |
| `check_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 3 | 5 / 0 | yes |
| `check_version_range_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `intersect_version_ranges` | `packaging.ranges.VersionRange.intersection` | 3 | 5 / 0 | yes |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | 3 | 4 / 1 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 0 | 5 / 1 | yes |
| `get_specifier_operator` | `packaging.specifiers.Specifier.operator` | 0 | 4 / 2 | yes |
| `get_specifier_version` | `packaging.specifiers.Specifier.version` | 0 | 4 / 2 | yes |
| `canonicalize_package_name` | `packaging.utils.canonicalize_name` | 0 | 5 / 0 | yes |
| `is_package_name_normalized` | `packaging.utils.is_normalized_name` | 0 | 6 / 0 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `get_default_marker_environment` | `packaging.markers.default_environment` | 0 | 4 / 0 | yes |
| `resolve_dependency_group` | `packaging.dependency_groups.DependencyGroupResolver.resolve` | 0 | 4 / 1 | yes |
| `lookup_dependency_group` | `packaging.dependency_groups.DependencyGroupResolver.lookup` | 1 | 4 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `create_version_range` | `packaging.ranges.VersionRange` | fastmcp | NameError: name 'Interval' is not defined |
| `version_range_to_specifier_set` | `packaging.ranges.VersionRange.to_specifier_set` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'to_specifier_set' |
| `filter_with_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | runs | Input {"iterable": ["1.2", "1.3", "1.4"], "prereleases": null, "specifiers": ">=1.2.3"}: the tool raised output is not JSON: 1.31.4, but the direct library call returned ["1.3", "1.4"] Input {"iterable": ["1.3", "1.5a1"] |
| `create_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 0]', 'InvalidVersion: release must be a non-empty tuple |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | fastmcp | NameError: name 'Interval' is not defined |
| `resolve_dependency_groups` | `packaging.dependency_groups.resolve_dependency_groups` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["ExceptionGroup: [dependency-groups] data for 'optional' was malformed (1 sub-exception)", "TypeError: expected string or bytes-like object, go |
| `canonicalize_license_expression` | `packaging.licenses.canonicalize_license_expression` | runs | Input {"raw_license_expression": "mit"}: the tool raised RecursionError: maximum recursion depth exceeded, but the direct library call returned "MIT" Input {"raw_license_expression": "mit and (apache-2.0 or bsd-2-clause) |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-usage-docs-classes-operators/run_server.sh
```
