# repo2tools report: packaging-pick-usage-docs

- Repo: https://github.com/pypa/packaging at `c1d2a9d8f5ca7cc11b7d2e902ed5ee3e255e8560`
- Package: `packaging`, 92 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.1 min. LLM tokens: 165,191 in 120 requests (propose 5,887, spec 84,444, code 74,860)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 44 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 39 |
| Accepted and confirmed against a direct library call | 39 |
| Passed all checks on the first try | 32 |
| Rejected after the repair rounds | 5 |

First try, by the first check that failed: ok: 32, spec: 8, differential: 2, fastmcp: 1, runs: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `specifier_set_to_range` | `packaging.specifiers.SpecifierSet.to_range` | 0 | 5 / 0 | yes |
| `filter_specifier_set` | `packaging.specifiers.SpecifierSet.filter` | 1 | 5 / 0 | yes |
| `create_full_version_range` | `packaging.ranges.VersionRange.full` | 0 | 5 / 0 | yes |
| `filter_version_range` | `packaging.ranges.VersionRange.filter` | 0 | 5 / 0 | yes |
| `check_unsatisfiable_specifier_set` | `packaging.specifiers.SpecifierSet.is_unsatisfiable` | 0 | 6 / 0 | yes |
| `check_prerelease_version` | `packaging.version.Version.is_prerelease` | 0 | 5 / 1 | yes |
| `check_specifier_contains` | `packaging.specifiers.Specifier.contains` | 0 | 6 / 0 | yes |
| `filter_specifier` | `packaging.specifiers.Specifier.filter` | 1 | 5 / 0 | yes |
| `check_specifier_set_contains` | `packaging.specifiers.SpecifierSet.contains` | 0 | 5 / 0 | yes |
| `create_empty_version_range` | `packaging.ranges.VersionRange.empty` | 0 | 4 / 0 | yes |
| `create_singleton_version_range` | `packaging.ranges.VersionRange.singleton` | 0 | 4 / 1 | yes |
| `canonicalize_version` | `packaging.utils.canonicalize_version` | 3 | 6 / 0 | yes |
| `get_pre_release_segment` | `packaging.version.Version.pre` | 0 | 5 / 1 | yes |
| `get_version_range_complement` | `packaging.ranges.VersionRange.complement` | 2 | 5 / 0 | yes |
| `check_version_range_subset` | `packaging.ranges.VersionRange.is_subset` | 0 | 6 / 0 | yes |
| `canonicalize_package_name` | `packaging.utils.canonicalize_name` | 0 | 6 / 0 | yes |
| `get_release_components` | `packaging.version.Version.release` | 0 | 5 / 1 | yes |
| `get_post_release_number` | `packaging.version.Version.post` | 0 | 5 / 1 | yes |
| `check_post_release_version` | `packaging.version.Version.is_postrelease` | 0 | 5 / 0 | yes |
| `difference_version_ranges` | `packaging.ranges.VersionRange.difference` | 0 | 6 / 0 | yes |
| `check_disjoint_version_ranges` | `packaging.ranges.VersionRange.is_disjoint` | 3 | 5 / 0 | yes |
| `check_specifier_set_subset` | `packaging.specifiers.SpecifierSet.is_subset` | 0 | 5 / 0 | yes |
| `check_disjoint_specifier_sets` | `packaging.specifiers.SpecifierSet.is_disjoint` | 0 | 5 / 0 | yes |
| `validate_normalized_name` | `packaging.utils.is_normalized_name` | 0 | 6 / 0 | yes |
| `normalize_pre_release_segment` | `packaging.version.normalize_pre` | 0 | 6 / 0 | yes |
| `get_epoch_component` | `packaging.version.Version.epoch` | 0 | 5 / 0 | yes |
| `get_public_version` | `packaging.version.Version.public` | 0 | 5 / 1 | yes |
| `get_base_version` | `packaging.version.Version.base_version` | 0 | 5 / 1 | yes |
| `evaluate_marker` | `packaging.markers.Marker.evaluate` | 0 | 5 / 1 | yes |
| `check_version_range_superset` | `packaging.ranges.VersionRange.is_superset` | 3 | 5 / 0 | yes |
| `check_version_range_contains` | `packaging.ranges.VersionRange.contains` | 2 | 5 / 0 | yes |
| `check_specifier_set_superset` | `packaging.specifiers.SpecifierSet.is_superset` | 0 | 5 / 0 | yes |
| `parse_version_string` | `packaging.version.parse` | 0 | 4 / 1 | yes |
| `get_dev_release_number` | `packaging.version.Version.dev` | 0 | 5 / 0 | yes |
| `get_local_version_segment` | `packaging.version.Version.local` | 0 | 5 / 0 | yes |
| `check_dev_release_version` | `packaging.version.Version.is_devrelease` | 0 | 5 / 1 | yes |
| `get_minor_release_component` | `packaging.version.Version.minor` | 0 | 4 / 1 | yes |
| `get_micro_release_component` | `packaging.version.Version.micro` | 0 | 5 / 1 | yes |
| `get_major_release_component` | `packaging.version.Version.major` | 0 | 5 / 1 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `version_range_to_specifier_set` | `packaging.ranges.VersionRange.to_specifier_set` | differential | Input {"specifier_set": ">=1.0,<2.0"}: the tool raised ValueError: Invalid specifier set: '>=1.0,<2.0', but the direct library call returned "<2.0,>=1.0" Input {"specifier_set": "==1.0"}: the tool raised ValueError: Inva |
| `check_empty_version_range` | `packaging.ranges.VersionRange.is_empty` | differential | Input {"prereleases": true, "specifiers": ">=2,<1"}: the tool raised ValueError: Invalid specifiers format: '>=2,<1', but the direct library call returned true Input {"prereleases": true, "specifiers": ">=1,<2"}: the too |
| `canonicalize_license_expression` | `packaging.licenses.canonicalize_license_expression` | differential | Input {"raw_license_expression": "mit"}: the tool raised ValueError: maximum recursion depth exceeded, but the direct library call returned "MIT" Input {"raw_license_expression": "mit and (apache-2.0 or bsd-2-clause)"}:  |
| `union_version_ranges` | `packaging.ranges.VersionRange.union` | differential | Input {"range1": ">=1.0,<2.0", "range2": ">=2.0,<3.0"}: the tool raised ValueError: Failed to union version ranges '>=1.0,<2.0' and '>=2.0,<3.0': cannot create 'VersionRange' instances directly; use SpecifierSet.to_range |
| `construct_version_from_parts` | `packaging.version.Version.from_parts` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['InvalidVersion: release must be a non-empty tuple of non-negative integers, got [1, 0, 0]', 'InvalidVersion: release must be a non-empty tuple |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/packaging-pick-usage-docs/run_server.sh
```
