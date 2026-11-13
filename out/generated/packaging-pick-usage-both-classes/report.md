# repo2tools report: packaging-pick-usage-both-classes

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.7 min. LLM tokens: 256,554 in 179 requests (propose 7,236, spec 113,988, code 135,330)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 60 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 46 |
| Accepted and confirmed against a direct library call | 45 |
| Passed all checks on the first try | 35 |
| Rejected after the repair rounds | 14 |

First try, by the first check that failed: ok: 35, spec: 12, differential: 8, fastmcp: 2, static: 2, loads: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `parse_version` | `packaging.version.Version` | 0 | 5 / 1 | yes |
| `parse_specifier_set` | `packaging.specifiers.SpecifierSet` | 0 | 4 / 1 | yes |
| `specifier_set_contains` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 0 | yes |
| `is_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 5 / 0 | yes |
| `specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 5 / 0 | yes |
| `range_contains_version` | `packaging.ranges.VersionRange.contains` | 2 | 6 / 0 | yes |
| `get_empty_version_range` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `get_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `is_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 2 | 5 / 1 | yes |
| `intersect_version_ranges` | `packaging.ranges.VersionRange.intersection` | 0 | 5 / 0 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 2 | 5 / 1 | yes |
| `filter_versions_by_range` | `packaging.ranges.VersionRange.filter` | 2 | 5 / 0 | yes |
| `parse_version_string` | `packaging.version.parse` | 0 | 4 / 1 | yes |
| `canonicalize_version_string` | `packaging.utils.canonicalize_version` | 0 | 6 / 0 | yes |
| `canonicalize_package_name` | `packaging.utils.canonicalize_name` | 0 | 6 / 0 | yes |
| `is_version_prerelease` | `packaging.version.Version.is_prerelease` | 0 | 5 / 1 | yes |
| `get_version_release` | `packaging.version.Version.release` | 0 | 5 / 1 | yes |
| `get_version_pre_release` | `packaging.version.Version.pre` | 0 | 6 / 0 | yes |
| `get_version_post_release` | `packaging.version.Version.post` | 0 | 5 / 1 | yes |
| `get_version_dev_number` | `packaging.version.Version.dev` | 0 | 5 / 0 | yes |
| `get_version_local_segment` | `packaging.version.Version.local` | 0 | 5 / 0 | yes |
| `get_version_epoch` | `packaging.version.Version.epoch` | 0 | 5 / 0 | yes |
| `get_version_base` | `packaging.version.Version.base_version` | 0 | 5 / 1 | yes |
| `get_version_public` | `packaging.version.Version.public` | 0 | 5 / 1 | yes |
| `is_version_postrelease` | `packaging.version.Version.is_postrelease` | 0 | 5 / 1 | yes |
| `is_version_devrelease` | `packaging.version.Version.is_devrelease` | 0 | 5 / 1 | yes |
| `get_version_major` | `packaging.version.Version.major` | 0 | 4 / 1 | yes |
| `get_version_minor` | `packaging.version.Version.minor` | 0 | 5 / 1 | yes |
| `get_version_micro` | `packaging.version.Version.micro` | 0 | 5 / 0 | yes |
| `parse_specifier` | `packaging.specifiers.Specifier` | 0 | 4 / 1 | yes |
| `specifier_contains` | `packaging.specifiers.Specifier.contains` | 0 | 6 / 0 | yes |
| `filter_versions_by_specifier` | `packaging.specifiers.Specifier.filter` | 1 | 5 / 0 | yes |
| `filter_versions_by_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | 1 | 5 / 0 | yes |
| `parse_marker` | `packaging.markers.Marker` | 0 | 4 / 1 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `parse_metadata_from_email` | `packaging.metadata.Metadata.from_email` | 3 | 0 / 2 | no: unstable, both_error |
| `create_tag` | `packaging.tags.Tag` | 0 | 5 / 0 | yes |
| `generate_cpython_tags` | `packaging.tags.cpython_tags` | 1 | 5 / 0 | yes |
| `generate_system_tags` | `packaging.tags.sys_tags` | 1 | 4 / 0 | yes |
| `generate_compatible_tags` | `packaging.tags.compatible_tags` | 0 | 5 / 0 | yes |
| `generate_platform_tags` | `packaging.tags.platform_tags` | 0 | 2 / 0 | yes |
| `get_interpreter_name` | `packaging.tags.interpreter_name` | 0 | 4 / 0 | yes |
| `get_interpreter_version` | `packaging.tags.interpreter_version` | 0 | 5 / 0 | yes |
| `get_interpreter_abi` | `packaging.tags.interpreter_abi` | 0 | 2 / 0 | yes |
| `resolve_dependency_group` | `packaging.dependency_groups.DependencyGroupResolver.resolve` | 0 | 4 / 1 | yes |
| `lookup_dependency_group` | `packaging.dependency_groups.DependencyGroupResolver.lookup` | 1 | 4 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `create_version_range` | `packaging.ranges.VersionRange` | fastmcp | NameError: name 'Interval' is not defined |
| `is_version_range_empty` | `packaging.ranges.VersionRange.is_empty` | differential | Input {"prereleases": true, "range_string": ">=2,<1"}: the tool raised ValueError: Invalid version range: '>=2,<1', but the direct library call returned true Input {"prereleases": true, "range_string": ">=1,<2"}: the too |
| `get_full_version_range` | `packaging.ranges.VersionRange.full` | differential | Input {"admit_arbitrary": true, "prereleases": null}: the tool returned "<VersionRange '(-inf, +inf)'>", but the direct library call returned "<VersionRange '(-inf, +inf)' arbitrary>" Input {"admit_arbitrary": true, "pre |
| `is_version_range_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `is_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: cannot create 'VersionRange' instances directly; use SpecifierSet.to_range(), VersionRange.full(), VersionRange.empty(), or Version |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_legacy' |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | fastmcp | NameError: name 'Interval' is not defined |
| `convert_metadata_to_rfc822` | `packaging.metadata.Metadata.as_rfc822` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['ExceptionGroup: invalid metadata (1 sub-exception)']. Use samples that are valid for the library. |
| `parse_tag_string` | `packaging.tags.parse_tag` | end_to_end | over MCP it returned ["py2-none-any", "py3-none-any"], in the check ["py3-none-any", "py2-none-any"] |
| `generate_pure_python_tags` | `packaging.tags.pure_python_tags` | differential | Input {"python_version": [3, 9]}: the tool returned ["py3-none-any", "py30-none-any", "py31-none-any", "py32-none-any", "py33-none-any", "py34-none-any", "py35-none-any", "py36-none-any", "py37-none-any", "py38-none-any" |
| `generate_generic_tags` | `packaging.tags.generic_tags` | differential | Input {"abis": ["cp39", "abi3"], "interpreter": "py39", "platforms": ["linux_x86_64"]}: the tool returned [{"abi": "cp39", "interpreter": "py39", "platform": "linux_x86_64"}, {"abi": "abi3", "interpreter": "py39", "platf |
| `resolve_dependency_groups` | `packaging.dependency_groups.resolve_dependency_groups` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["ExceptionGroup: [dependency-groups] data for 'optional' was malformed (1 sub-exception)", "TypeError: expected string or bytes-like object, go |
| `load_pylock_from_dict` | `packaging.pylock.Pylock.from_dict` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["_PylockRequiredKeyError: Missing required value in 'packages'"]. Use samples that are valid for the library. |
| `convert_pylock_to_dict` | `packaging.pylock.Pylock.to_dict` | static | do not use __name__ |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-usage-both-classes/run_server.sh
```
