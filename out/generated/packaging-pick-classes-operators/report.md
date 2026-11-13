# repo2tools report: packaging-pick-classes-operators

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.7 min. LLM tokens: 335,521 in 189 requests (propose 7,927, spec 225,534, code 102,060)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 60 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 45 |
| Accepted and confirmed against a direct library call | 45 |
| Passed all checks on the first try | 31 |
| Rejected after the repair rounds | 15 |

First try, by the first check that failed: ok: 31, spec: 27, differential: 2.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `marker_equality` | `packaging.markers.Marker.__eq__` | 0 | 5 / 1 | yes |
| `marker_inequality` | `packaging.markers.Marker.__ne__` | 1 | 4 / 1 | yes |
| `marker_intersection` | `packaging.markers.Marker.__and__` | 1 | 5 / 1 | yes |
| `marker_union` | `packaging.markers.Marker.__or__` | 1 | 5 / 1 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `create_empty_version_range` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `create_full_version_range` | `packaging.ranges.VersionRange.full` | 0 | 5 / 0 | yes |
| `create_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 5 / 1 | yes |
| `intersect_version_ranges` | `packaging.ranges.VersionRange.intersection` | 3 | 5 / 0 | yes |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | 3 | 5 / 0 | yes |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | 0 | 5 / 0 | yes |
| `check_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 0 | 5 / 1 | yes |
| `check_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 0 | 5 / 0 | yes |
| `check_version_ranges_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `check_version_in_range` | `packaging.ranges.VersionRange.contains` | 1 | 5 / 0 | yes |
| `convert_range_to_specifier_set` | `packaging.ranges.VersionRange.to_specifier_set` | 1 | 5 / 0 | yes |
| `specifier_equality` | `packaging.specifiers.Specifier.__eq__` | 0 | 5 / 1 | yes |
| `specifier_inequality` | `packaging.specifiers.Specifier.__ne__` | 0 | 4 / 2 | yes |
| `version_in_specifier` | `packaging.specifiers.Specifier.__contains__` | 1 | 6 / 0 | yes |
| `specifier_set_equality` | `packaging.specifiers.SpecifierSet.__eq__` | 0 | 6 / 0 | yes |
| `specifier_set_inequality` | `packaging.specifiers.SpecifierSet.__ne__` | 0 | 5 / 1 | yes |
| `version_in_specifier_set` | `packaging.specifiers.SpecifierSet.__contains__` | 1 | 5 / 0 | yes |
| `specifier_set_intersection` | `packaging.specifiers.SpecifierSet.__and__` | 1 | 5 / 1 | yes |
| `check_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 5 / 0 | yes |
| `convert_specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 4 / 1 | yes |
| `check_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `check_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `check_specifier_sets_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `check_version_in_specifier_set` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 0 | yes |
| `filter_versions_by_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | 3 | 5 / 0 | yes |
| `tag_equality` | `packaging.tags.Tag.__eq__` | 1 | 5 / 0 | yes |
| `version_less_than` | `packaging.version.Version.__lt__` | 0 | 5 / 1 | yes |
| `version_less_equal` | `packaging.version.Version.__le__` | 0 | 5 / 1 | yes |
| `version_greater_than` | `packaging.version.Version.__gt__` | 0 | 5 / 1 | yes |
| `version_greater_equal` | `packaging.version.Version.__ge__` | 0 | 5 / 0 | yes |
| `version_equality` | `packaging.version.Version.__eq__` | 0 | 5 / 1 | yes |
| `version_inequality` | `packaging.version.Version.__ne__` | 0 | 5 / 1 | yes |
| `get_version_epoch` | `packaging.version.Version.epoch` | 0 | 5 / 0 | yes |
| `get_version_release` | `packaging.version.Version.release` | 0 | 5 / 1 | yes |
| `get_version_pre` | `packaging.version.Version.pre` | 0 | 5 / 0 | yes |
| `get_version_post` | `packaging.version.Version.post` | 0 | 5 / 1 | yes |
| `get_version_dev` | `packaging.version.Version.dev` | 0 | 5 / 0 | yes |
| `get_version_local` | `packaging.version.Version.local` | 0 | 5 / 0 | yes |
| `get_version_public` | `packaging.version.Version.public` | 0 | 5 / 1 | yes |
| `get_version_base` | `packaging.version.Version.base_version` | 0 | 5 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `version_range_less_than` | `packaging.ranges.VersionRange.__lt__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_less_equal` | `packaging.ranges.VersionRange.__le__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_greater_than` | `packaging.ranges.VersionRange.__gt__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_greater_equal` | `packaging.ranges.VersionRange.__ge__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_equality` | `packaging.ranges.VersionRange.__eq__` | spec | direct_call must use the library's VersionRange |
| `version_range_inequality` | `packaging.ranges.VersionRange.__ne__` | spec | the direct_call expression is wrong: ModuleNotFoundError: No module named 'VersionRange' |
| `version_in_range` | `packaging.ranges.VersionRange.__contains__` | spec | direct_call must use the library's VersionRange |
| `version_range_intersection` | `packaging.ranges.VersionRange.__and__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_union` | `packaging.ranges.VersionRange.__or__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_difference` | `packaging.ranges.VersionRange.__sub__` | spec | direct_call may not use __sub__ |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `specifier_intersection` | `packaging.specifiers.Specifier.__and__` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: unsupported operand type(s) for &: 'Specifier' and 'Specifier'"]. Use samples that are valid for the library. |
| `tag_contains` | `packaging.tags.Tag.__contains__` | spec | direct_call may not use Starred: only calls, attributes, names, constants and simple conditions |
| `version_in_version` | `packaging.version.Version.__contains__` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: argument of type 'Version' is not iterable"]. Use samples that are valid for the library. |
| `add_versions` | `packaging.version.Version.__add__` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: unsupported operand type(s) for +: 'Version' and 'Version'"]. Use samples that are valid for the library. |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-classes-operators/run_server.sh
```
