# repo2tools report: packaging-pick-usage-docs-classes-r3

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.2 min. LLM tokens: 199,957 in 141 requests (propose 6,724, spec 91,829, code 101,404)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 48 (dropped: 1, for unknown functions, duplicates or bad names) |
| Accepted | 41 |
| Accepted and confirmed against a direct library call | 41 |
| Passed all checks on the first try | 29 |
| Rejected after the repair rounds | 7 |

First try, by the first check that failed: ok: 29, spec: 11, differential: 4, fastmcp: 2, runs: 1, static: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `create_specifier_set` | `packaging.specifiers.SpecifierSet` | 0 | 5 / 1 | yes |
| `create_version` | `packaging.version.Version` | 0 | 5 / 1 | yes |
| `create_specifier` | `packaging.specifiers.Specifier` | 0 | 4 / 1 | yes |
| `specifier_set_contains` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 1 | yes |
| `is_specifier_set_unsatisfiable` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `is_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `is_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `is_specifier_set_disjoint` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `is_version_prerelease` | `packaging.version.Version.is_prerelease` | 0 | 5 / 1 | yes |
| `get_version_release` | `packaging.version.Version.release` | 0 | 5 / 1 | yes |
| `get_version_pre` | `packaging.version.Version.pre` | 0 | 5 / 0 | yes |
| `get_version_post` | `packaging.version.Version.post` | 0 | 5 / 0 | yes |
| `get_version_dev` | `packaging.version.Version.dev` | 0 | 5 / 1 | yes |
| `get_version_local` | `packaging.version.Version.local` | 0 | 4 / 2 | yes |
| `is_version_postrelease` | `packaging.version.Version.is_postrelease` | 0 | 5 / 1 | yes |
| `is_version_devrelease` | `packaging.version.Version.is_devrelease` | 0 | 5 / 1 | yes |
| `get_version_major` | `packaging.version.Version.major` | 0 | 4 / 1 | yes |
| `get_version_minor` | `packaging.version.Version.minor` | 0 | 5 / 1 | yes |
| `get_version_micro` | `packaging.version.Version.micro` | 0 | 5 / 0 | yes |
| `get_version_epoch` | `packaging.version.Version.epoch` | 0 | 5 / 0 | yes |
| `get_version_public` | `packaging.version.Version.public` | 0 | 5 / 1 | yes |
| `get_version_base` | `packaging.version.Version.base_version` | 0 | 5 / 1 | yes |
| `canonicalize_version` | `packaging.utils.canonicalize_version` | 0 | 6 / 0 | yes |
| `is_normalized_name` | `packaging.utils.is_normalized_name` | 2 | 6 / 0 | yes |
| `parse_version` | `packaging.version.parse` | 0 | 4 / 1 | yes |
| `normalize_pre` | `packaging.version.normalize_pre` | 0 | 5 / 0 | yes |
| `specifier_contains` | `packaging.specifiers.Specifier.contains` | 0 | 6 / 0 | yes |
| `filter_specifier` | `packaging.specifiers.Specifier.filter` | 0 | 5 / 0 | yes |
| `get_specifier_operator` | `packaging.specifiers.Specifier.operator` | 0 | 6 / 0 | yes |
| `get_specifier_version` | `packaging.specifiers.Specifier.version` | 0 | 4 / 1 | yes |
| `get_full_version_range` | `packaging.ranges.VersionRange.full` | 2 | 5 / 0 | yes |
| `get_empty_version_range` | `packaging.ranges.VersionRange.empty` | 2 | 3 / 0 | yes |
| `get_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 1 | 3 / 1 | yes |
| `range_contains` | `packaging.ranges.VersionRange.contains` | 2 | 6 / 0 | yes |
| `is_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 2 | 5 / 1 | yes |
| `is_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 1 | 5 / 0 | yes |
| `is_version_range_disjoint` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | 3 | 5 / 0 | yes |
| `intersection_version_ranges` | `packaging.ranges.VersionRange.intersection` | 3 | 5 / 0 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 1 | 5 / 1 | yes |
| `filter_version_range` | `packaging.ranges.VersionRange.filter` | 1 | 4 / 0 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `filter_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | runs | Input {"iterable": ["1.2", "1.3", "1.4"], "prereleases": null, "specifiers": ">=1.2.3"}: the tool raised output is not JSON: 1.31.4, but the direct library call returned ["1.3", "1.4"] Input {"iterable": [{"ver": "1.2"}, |
| `canonicalize_name` | `packaging.utils.canonicalize_name` | runs | Input {"name": "Django"}: the tool raised RecursionError: maximum recursion depth exceeded, but the direct library call returned "django" Input {"name": "oslo.concurrency"}: the tool raised RecursionError: maximum recurs |
| `create_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 1]', 'InvalidVersion: release must be a non-empty tuple |
| `create_version_range` | `packaging.ranges.VersionRange` | fastmcp | NameError: name 'Interval' is not defined |
| `range_to_specifier_set` | `packaging.ranges.VersionRange.to_specifier_set` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'to_specifier_set' |
| `is_version_range_empty` | `packaging.ranges.VersionRange.is_empty` | differential | Input {"prereleases": true, "range_string": ">=2,<1"}: the tool raised ValueError: Invalid version range: '>=2,<1', but the direct library call returned true Input {"prereleases": true, "range_string": ">=1,<2"}: the too |
| `complement_version_range` | `packaging.ranges.VersionRange.complement` | fastmcp | NameError: name 'Interval' is not defined |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-usage-docs-classes-r3/run_server.sh
```
