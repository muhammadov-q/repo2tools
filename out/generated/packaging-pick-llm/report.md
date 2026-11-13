# repo2tools report: packaging-pick-llm

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.3 min. LLM tokens: 181,563 in 126 requests (propose 5,036, spec 96,527, code 80,000)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 39 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 31 |
| Accepted and confirmed against a direct library call | 30 |
| Passed all checks on the first try | 20 |
| Rejected after the repair rounds | 8 |

First try, by the first check that failed: ok: 20, spec: 13, differential: 3, static: 2, runs: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `default_environment` | `packaging.markers.default_environment` | 0 | 2 / 0 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `parse_metadata_email` | `packaging.metadata.parse_email` | 0 | 5 / 0 | yes |
| `create_metadata_from_email` | `packaging.metadata.Metadata.from_email` | 2 | 0 / 2 | no: unstable, both_error |
| `create_empty_version_range` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `create_full_version_range` | `packaging.ranges.VersionRange.full` | 0 | 5 / 0 | yes |
| `create_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `intersect_version_ranges` | `packaging.ranges.VersionRange.intersection` | 3 | 5 / 0 | yes |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | 3 | 5 / 0 | yes |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | 0 | 5 / 0 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 2 | 4 / 2 | yes |
| `check_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 0 | 5 / 1 | yes |
| `check_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 1 | 5 / 0 | yes |
| `check_version_ranges_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `check_version_in_range` | `packaging.ranges.VersionRange.contains` | 1 | 6 / 0 | yes |
| `check_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `convert_specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 4 / 1 | yes |
| `check_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `check_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `check_specifier_sets_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `check_version_in_specifier_set` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 0 | yes |
| `generate_cpython_tags` | `packaging.tags.cpython_tags` | 1 | 5 / 0 | yes |
| `generate_generic_tags` | `packaging.tags.generic_tags` | 0 | 5 / 0 | yes |
| `generate_pure_python_tags` | `packaging.tags.pure_python_tags` | 3 | 3 / 1 | yes |
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
| `resolve_dependency_groups` | `packaging.dependency_groups.resolve_dependency_groups` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["ExceptionGroup: [dependency-groups] data for 'nonexistent' was malformed (1 sub-exception)", "ExceptionGroup: [dependency-groups] data for 'op |
| `canonicalize_license_expression` | `packaging.licenses.canonicalize_license_expression` | runs | Input {"raw_license_expression": "mit"}: the tool raised RecursionError: maximum recursion depth exceeded, but the direct library call returned "MIT" Input {"raw_license_expression": "mit and (apache-2.0 or bsd-2-clause) |
| `convert_metadata_to_rfc822` | `packaging.metadata.Metadata.as_rfc822` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'copy' |
| `create_pylock_from_dict` | `packaging.pylock.Pylock.from_dict` | spec | sample {"data": {"package": [{"name": "requests", "requires": ["urllib3"], "version": "2.28.1"}]}, "metadata": {"lock-version": "1.0"}} does not fit the parameters: got an unexpected keyword argument 'metadata' |
| `convert_pylock_to_dict` | `packaging.pylock.Pylock.to_dict` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['TypeError: asdict() should be called on dataclass instances']. Use samples that are valid for the library. |
| `validate_pylock` | `packaging.pylock.Pylock.validate` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["_PylockRequiredKeyError: Missing required value in 'packages'"]. Use samples that are valid for the library. |
| `parse_tag` | `packaging.tags.parse_tag` | end_to_end | over MCP it returned ["py3-none-any", "py2-none-any"], in the check ["py2-none-any", "py3-none-any"] |
| `create_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 0]', 'InvalidVersion: release must be a non-empty tuple |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-llm/run_server.sh
```
