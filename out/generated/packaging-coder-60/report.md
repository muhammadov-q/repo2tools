# repo2tools report: packaging-coder-60

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 0.9 min. LLM tokens: 192,675 in 128 requests (propose 5,038, spec 95,466, code 92,171)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 39 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 29 |
| Accepted and confirmed against a direct library call | 29 |
| Passed all checks on the first try | 21 |
| Rejected after the repair rounds | 10 |

First try, by the first check that failed: ok: 21, spec: 12, static: 3, differential: 2, loads: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `get_default_marker_environment` | `packaging.markers.default_environment` | 0 | 4 / 0 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `parse_metadata_email` | `packaging.metadata.parse_email` | 0 | 5 / 0 | yes |
| `create_empty_version_range` | `packaging.ranges.VersionRange.empty` | 0 | 4 / 0 | yes |
| `create_full_version_range` | `packaging.ranges.VersionRange.full` | 0 | 5 / 0 | yes |
| `create_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `intersect_version_ranges` | `packaging.ranges.VersionRange.intersection` | 3 | 5 / 0 | yes |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | 3 | 5 / 0 | yes |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | 2 | 5 / 0 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 2 | 4 / 1 | yes |
| `check_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 0 | 5 / 1 | yes |
| `check_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 0 | 5 / 0 | yes |
| `check_version_ranges_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `check_version_in_range` | `packaging.ranges.VersionRange.contains` | 1 | 6 / 0 | yes |
| `check_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `convert_specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 4 / 1 | yes |
| `check_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `check_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `check_specifier_sets_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `check_version_in_specifier_set` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 0 | yes |
| `parse_tag` | `packaging.tags.parse_tag` | 2 | 4 / 1 | yes |
| `generate_generic_tags` | `packaging.tags.generic_tags` | 0 | 5 / 0 | yes |
| `generate_compatible_tags` | `packaging.tags.compatible_tags` | 0 | 5 / 0 | yes |
| `canonicalize_package_name` | `packaging.utils.canonicalize_name` | 0 | 6 / 0 | yes |
| `check_normalized_package_name` | `packaging.utils.is_normalized_name` | 0 | 6 / 0 | yes |
| `canonicalize_version_string` | `packaging.utils.canonicalize_version` | 0 | 6 / 0 | yes |
| `parse_wheel_filename` | `packaging.utils.parse_wheel_filename` | 1 | 3 / 2 | yes |
| `parse_sdist_filename` | `packaging.utils.parse_sdist_filename` | 0 | 3 / 3 | yes |
| `parse_version_string` | `packaging.version.parse` | 0 | 4 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `resolve_dependency_groups` | `packaging.dependency_groups.resolve_dependency_groups` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["ExceptionGroup: [dependency-groups] data for 'optional' was malformed (1 sub-exception)", "TypeError: expected string or bytes-like object, go |
| `canonicalize_license_expression` | `packaging.licenses.canonicalize_license_expression` | runs | Input {"raw_license_expression": "mit"}: the tool raised RecursionError: maximum recursion depth exceeded, but the direct library call returned "MIT" Input {"raw_license_expression": "mit and (apache-2.0 or bsd-2-clause) |
| `create_metadata_from_email` | `packaging.metadata.Metadata.from_email` | differential | Input {"data": "Metadata-Version: 2.1\nName: example-package\nVersion: 1.0.0\nSummary: An example package\n", "validate": true}: the tool raised ValueError: Failed to parse email metadata: 'Metadata' object has no attrib |
| `convert_metadata_to_rfc822` | `packaging.metadata.Metadata.as_rfc822` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['ExceptionGroup: invalid metadata (1 sub-exception)']. Use samples that are valid for the library. |
| `create_pylock_from_dict` | `packaging.pylock.Pylock.from_dict` | spec | sample {"data": {"package": [{"name": "requests", "requires": ["urllib3"], "version": "2.28.1"}]}, "metadata": {"lock-version": "1.0"}} does not fit the parameters: got an unexpected keyword argument 'metadata' |
| `convert_pylock_to_dict` | `packaging.pylock.Pylock.to_dict` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: Pylock.__init__() missing 2 required keyword-only arguments: 'created_by' and 'packages'"]. Use samples that are valid for the libr |
| `validate_pylock` | `packaging.pylock.Pylock.validate` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["_PylockRequiredKeyError: Missing required value in 'packages'"]. Use samples that are valid for the library. |
| `generate_cpython_tags` | `packaging.tags.cpython_tags` | differential | Input {"python_version": [3, 9]}: the tool returned [{"abi": "cp39", "interpreter": "cp39", "platform": "macosx_27_0_arm64"}, {"abi": "cp39", "interpreter": "cp39", "platform": "macosx_27_0_universal2"}, {"abi": "cp39",  |
| `generate_pure_python_tags` | `packaging.tags.pure_python_tags` | differential | Input {"python_version": [3, 9]}: the tool returned ["py39-none-any"], but the direct library call returned ["py39-none-any", "py3-none-any", "py38-none-any", "py37-none-any", "py36-none-any", "py35-none-any", "py34-none |
| `create_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 0]', 'InvalidVersion: release must be a non-empty tuple |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-coder-60/run_server.sh
```
