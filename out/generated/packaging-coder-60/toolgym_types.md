# ToolGym types for packaging-coder-60

Types proposed by `qwen3-32b`, then checked by 1035 tool calls. A claim stands if at least 60% of its test calls work.

| | Count |
| --- | --- |
| Tools exported | 29 |
| Shared types proposed / kept | 10 / 10 |
| Parameters with a shared type: proposed / kept | 36 / 36 |
| Parameter claims tested / withdrawn | 36 / 0 |
| Output claims / kept | 18 / 7 |
| Data-flow links between tools | 16, over 16 tool pairs |
| Tools with no link | 17 |

## Types

| Type | Examples | Parameters |
| --- | --- | --- |
| `MarkerEnvironment` | 3 | `evaluate_marker.environment` |
| `MarkerExpression` | 5 | `evaluate_marker.marker` |
| `MetadataEmail` | 5 | `parse_metadata_email.data` |
| `PackageName` | 10 | `canonicalize_package_name.name`, `check_normalized_package_name.name` |
| `SdistFilename` | 3 | `parse_sdist_filename.filename` |
| `SpecifierSet` | 27 | `check_specifier_set_unsatisfiable.specifiers`, `convert_specifier_set_to_range.specifiers`, `check_specifier_set_subset.specifier_set1`, `check_specifier_set_subset.specifier_set2`, `check_specifier_set_superset.specifier_set1`, `check_specifier_set_superset.specifier_set2`, `check_specifier_sets_disjoint.specifier_set1`, `check_specifier_sets_disjoint.specifier_set2`, `check_version_in_specifier_set.specifier_set` |
| `Tag` | 3 | `parse_tag.tag` |
| `VersionRange` | 27 | `intersect_version_ranges.range1`, `intersect_version_ranges.range2`, `union_version_ranges.version_range_a`, `union_version_ranges.version_range_b`, `complement_version_range.version_specifier`, `difference_version_ranges.version_range_a`, `difference_version_ranges.version_range_b`, `check_version_range_subset.range1`, `check_version_range_subset.range2`, `check_version_range_superset.outer_range`, `check_version_range_superset.inner_range`, `check_version_ranges_disjoint.range1`, `check_version_ranges_disjoint.range2`, `check_version_in_range.specifier_set` |
| `VersionString` | 19 | `create_singleton_version_range.version`, `check_version_in_range.version`, `check_version_in_specifier_set.version`, `canonicalize_version_string.version`, `parse_version_string.version` |
| `WheelFilename` | 3 | `parse_wheel_filename.filename` |

## Output claims

| Tool | Claim | Worked | Kept |
| --- | --- | --- | --- |
| `get_default_marker_environment` | MarkerEnvironment | 1 of 1 | yes |
| `parse_metadata_email` | ParsedMetadata | 0 of 0 | no: no parameter has this type |
| `create_empty_version_range` | VersionRange | 0 of 9 | no |
| `create_full_version_range` | VersionRange | 0 of 12 | no |
| `create_singleton_version_range` | VersionRange | 0 of 12 | no |
| `intersect_version_ranges` | VersionRange | 0 of 12 | no |
| `union_version_ranges` | VersionRange | 0 of 12 | no |
| `complement_version_range` | VersionRange | 0 of 12 | no |
| `difference_version_ranges` | VersionRange | 0 of 6 | no |
| `convert_specifier_set_to_range` | VersionRange | 0 of 12 | no |
| `parse_tag` | list[Tag] | 3 of 3 | yes |
| `generate_generic_tags` | list[Tag] | 4 of 4 | yes |
| `generate_compatible_tags` | list[Tag] | 4 of 4 | yes |
| `canonicalize_package_name` | NormalizedPackageName | 8 of 8 | yes |
| `canonicalize_version_string` | CanonicalizedVersion | 10 of 12 | yes |
| `parse_wheel_filename` | ParsedWheel | 0 of 0 | no: no parameter has this type |
| `parse_sdist_filename` | ParsedSdist | 0 of 0 | no: no parameter has this type |
| `parse_version_string` | ParsedVersion | 12 of 12 | yes |

## Links

- `canonicalize_package_name` → `canonicalize_package_name` (direct)
- `canonicalize_package_name` → `check_normalized_package_name` (direct)
- `canonicalize_version_string` → `canonicalize_version_string` (direct)
- `canonicalize_version_string` → `check_version_in_range` (direct)
- `canonicalize_version_string` → `check_version_in_specifier_set` (direct)
- `canonicalize_version_string` → `create_singleton_version_range` (direct)
- `canonicalize_version_string` → `parse_version_string` (direct)
- `generate_compatible_tags` → `parse_tag` (first element)
- `generate_generic_tags` → `parse_tag` (first element)
- `get_default_marker_environment` → `evaluate_marker` (direct)
- `parse_tag` → `parse_tag` (first element)
- `parse_version_string` → `canonicalize_version_string` (direct)
- `parse_version_string` → `check_version_in_range` (direct)
- `parse_version_string` → `check_version_in_specifier_set` (direct)
- `parse_version_string` → `create_singleton_version_range` (direct)
- `parse_version_string` → `parse_version_string` (direct)
