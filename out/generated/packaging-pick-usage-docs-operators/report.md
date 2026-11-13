# repo2tools report: packaging-pick-usage-docs-operators

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.3 min. LLM tokens: 232,004 in 134 requests (propose 6,722, spec 131,693, code 93,589)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 42 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 33 |
| Accepted and confirmed against a direct library call | 33 |
| Passed all checks on the first try | 21 |
| Rejected after the repair rounds | 9 |

First try, by the first check that failed: ok: 21, spec: 16, differential: 3, fastmcp: 1, runs: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 4 / 1 | yes |
| `specifier_set_contains` | `packaging.specifiers.SpecifierSet.__contains__` | 1 | 5 / 0 | yes |
| `version_range_full` | `packaging.ranges.VersionRange.full` | 1 | 5 / 0 | yes |
| `filter_version_range` | `packaging.ranges.VersionRange.filter` | 1 | 5 / 0 | yes |
| `is_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `is_version_range_empty` | `packaging.ranges.VersionRange.is_empty` | 3 | 5 / 1 | yes |
| `specifier_contains` | `packaging.specifiers.Specifier.contains` | 0 | 5 / 0 | yes |
| `filter_specifier` | `packaging.specifiers.Specifier.filter` | 1 | 5 / 1 | yes |
| `specifier_set_check_contains` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 1 | yes |
| `specifier_equal` | `packaging.specifiers.Specifier.__eq__` | 0 | 2 / 4 | yes |
| `specifier_set_equal` | `packaging.specifiers.SpecifierSet.__eq__` | 0 | 5 / 0 | yes |
| `specifier_set_intersection` | `packaging.specifiers.SpecifierSet.__and__` | 1 | 5 / 1 | yes |
| `version_range_empty` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `version_range_singleton` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `canonicalize_version` | `packaging.utils.canonicalize_version` | 3 | 6 / 0 | yes |
| `version_range_complement` | `packaging.ranges.VersionRange.complement` | 0 | 5 / 0 | yes |
| `canonicalize_package_name` | `packaging.utils.canonicalize_name` | 0 | 6 / 0 | yes |
| `version_range_union_method` | `packaging.ranges.VersionRange.union` | 3 | 5 / 0 | yes |
| `version_range_difference` | `packaging.ranges.VersionRange.difference` | 0 | 5 / 1 | yes |
| `is_version_range_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 2 | 5 / 0 | yes |
| `is_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `is_specifier_set_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `is_normalized_package_name` | `packaging.utils.is_normalized_name` | 0 | 6 / 0 | yes |
| `normalize_pre_release` | `packaging.version.normalize_pre` | 0 | 5 / 0 | yes |
| `is_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 2 | 5 / 0 | yes |
| `version_range_check_contains` | `packaging.ranges.VersionRange.contains` | 2 | 5 / 0 | yes |
| `is_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `parse_version` | `packaging.version.parse` | 0 | 4 / 1 | yes |
| `version_equal` | `packaging.version.Version.__eq__` | 0 | 5 / 1 | yes |
| `version_less_than` | `packaging.version.Version.__lt__` | 0 | 5 / 1 | yes |
| `version_less_equal` | `packaging.version.Version.__le__` | 0 | 5 / 1 | yes |
| `version_greater_than` | `packaging.version.Version.__gt__` | 0 | 5 / 1 | yes |
| `version_greater_equal` | `packaging.version.Version.__ge__` | 0 | 5 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `version_range_contains` | `packaging.ranges.VersionRange.__contains__` | spec | direct_call must use the library's VersionRange |
| `version_range_equal` | `packaging.ranges.VersionRange.__eq__` | spec | direct_call may not use __eq__ |
| `version_range_intersection` | `packaging.ranges.VersionRange.__and__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `version_range_to_specifier_set` | `packaging.ranges.VersionRange.to_specifier_set` | differential | Input {"specifier_set": ">=1.0,<2.0"}: the tool raised ValueError: Invalid specifier set: '>=1.0,<2.0', but the direct library call returned "<2.0,>=1.0" Input {"specifier_set": "==1.0"}: the tool raised ValueError: Inva |
| `filter_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | differential | Input {"iterable": [{"ver": "1.2"}, {"ver": "1.3"}], "prereleases": null, "specifiers": ">=1.2.3"}: the tool returned [{"ver": "1.3"}], but the direct library call returned [] |
| `version_range_union` | `packaging.ranges.VersionRange.__or__` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'from_specifier_set' |
| `canonicalize_license_expression` | `packaging.licenses.canonicalize_license_expression` | runs | Input {"raw_license_expression": "mit"}: the tool raised RecursionError: maximum recursion depth exceeded, but the direct library call returned "MIT" Input {"raw_license_expression": "mit and (apache-2.0 or bsd-2-clause) |
| `is_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | spec | the direct_call expression is wrong: AttributeError: type object 'VersionRange' has no attribute 'parse' |
| `create_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 1]', 'InvalidVersion: release must be a non-empty tuple |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-usage-docs-operators/run_server.sh
```
