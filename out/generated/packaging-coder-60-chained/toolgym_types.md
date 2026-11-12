# ToolGym types for packaging-coder-60-chained

Types proposed by `qwen3-32b (replayed)`, then checked by 1076 tool calls. A claim stands if at least 60% of its test calls work.

| | Count |
| --- | --- |
| Tools exported | 29 |
| Shared types proposed / kept | 10 / 10 |
| Parameters with a shared type: proposed / kept | 36 / 36 |
| Parameter claims tested / withdrawn | 36 / 0 |
| Output claims / kept | 31 / 17 |
| Data-flow links between tools | 69, over 59 tool pairs |
| Tools with no link | 8 |

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
| `get_default_marker_environment` | field implementation_name: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field implementation_version: VersionString | 3 of 3 | yes |
| `get_default_marker_environment` | field os_name: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field platform_machine: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field platform_release: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field platform_system: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field platform_version: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field python_full_version: VersionString | 3 of 3 | yes |
| `get_default_marker_environment` | field platform_python_implementation: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `get_default_marker_environment` | field python_version: VersionString | 3 of 3 | yes |
| `get_default_marker_environment` | field sys_platform: MarkerEnvironment | 0 of 0 | no: the output has another shape |
| `parse_metadata_email` | ParsedMetadata | 0 of 0 | no: no parameter has this type |
| `create_empty_version_range` | VersionRange | 0 of 9 | no |
| `create_full_version_range` | VersionRange | 0 of 12 | no |
| `create_singleton_version_range` | VersionRange | 0 of 12 | no |
| `intersect_version_ranges` | VersionRange | 12 of 12 | yes |
| `union_version_ranges` | VersionRange | 0 of 12 | no |
| `complement_version_range` | VersionRange | 0 of 12 | no |
| `difference_version_ranges` | VersionRange | 6 of 6 | yes |
| `convert_specifier_set_to_range` | VersionRange | 12 of 12 | yes |
| `parse_tag` | list[Tag] | 3 of 3 | yes |
| `generate_generic_tags` | list[Tag] | 4 of 4 | yes |
| `generate_compatible_tags` | list[Tag] | 4 of 4 | yes |
| `canonicalize_package_name` | NormalizedPackageName | 8 of 8 | yes |
| `canonicalize_version_string` | CanonicalizedVersion | 12 of 12 | yes |
| `parse_wheel_filename` | field name: PackageName | 6 of 6 | yes |
| `parse_wheel_filename` | field version: VersionString | 9 of 9 | yes |
| `parse_wheel_filename` | field tags: list[Tag] | 2 of 2 | yes |
| `parse_sdist_filename` | field name: PackageName | 6 of 6 | yes |
| `parse_sdist_filename` | field version: VersionString | 9 of 9 | yes |
| `parse_version_string` | ParsedVersion | 12 of 12 | yes |

## Links

- `canonicalize_package_name` → `canonicalize_package_name` (direct)
- `canonicalize_package_name` → `check_normalized_package_name` (direct)
- `canonicalize_version_string` → `canonicalize_version_string` (direct)
- `canonicalize_version_string` → `check_version_in_range` (direct)
- `canonicalize_version_string` → `check_version_in_specifier_set` (direct)
- `canonicalize_version_string` → `create_singleton_version_range` (direct)
- `canonicalize_version_string` → `parse_version_string` (direct)
- `convert_specifier_set_to_range` → `check_version_in_range` (direct)
- `convert_specifier_set_to_range` → `check_version_range_subset` (direct)
- `convert_specifier_set_to_range` → `check_version_range_superset` (direct)
- `convert_specifier_set_to_range` → `check_version_ranges_disjoint` (direct)
- `convert_specifier_set_to_range` → `complement_version_range` (direct)
- `convert_specifier_set_to_range` → `difference_version_ranges` (direct)
- `convert_specifier_set_to_range` → `intersect_version_ranges` (direct)
- `convert_specifier_set_to_range` → `union_version_ranges` (direct)
- `difference_version_ranges` → `check_version_in_range` (direct)
- `difference_version_ranges` → `check_version_range_subset` (direct)
- `difference_version_ranges` → `check_version_range_superset` (direct)
- `difference_version_ranges` → `check_version_ranges_disjoint` (direct)
- `difference_version_ranges` → `complement_version_range` (direct)
- `difference_version_ranges` → `difference_version_ranges` (direct)
- `difference_version_ranges` → `intersect_version_ranges` (direct)
- `difference_version_ranges` → `union_version_ranges` (direct)
- `generate_compatible_tags` → `parse_tag` (first element)
- `generate_generic_tags` → `parse_tag` (first element)
- `get_default_marker_environment` → `canonicalize_version_string` (field implementation_version)
- `get_default_marker_environment` → `canonicalize_version_string` (field python_full_version)
- `get_default_marker_environment` → `canonicalize_version_string` (field python_version)
- `get_default_marker_environment` → `check_version_in_range` (field implementation_version)
- `get_default_marker_environment` → `check_version_in_range` (field python_full_version)
- `get_default_marker_environment` → `check_version_in_range` (field python_version)
- `get_default_marker_environment` → `check_version_in_specifier_set` (field implementation_version)
- `get_default_marker_environment` → `check_version_in_specifier_set` (field python_full_version)
- `get_default_marker_environment` → `check_version_in_specifier_set` (field python_version)
- `get_default_marker_environment` → `create_singleton_version_range` (field implementation_version)
- `get_default_marker_environment` → `create_singleton_version_range` (field python_full_version)
- `get_default_marker_environment` → `create_singleton_version_range` (field python_version)
- `get_default_marker_environment` → `parse_version_string` (field implementation_version)
- `get_default_marker_environment` → `parse_version_string` (field python_full_version)
- `get_default_marker_environment` → `parse_version_string` (field python_version)
- `intersect_version_ranges` → `check_version_in_range` (direct)
- `intersect_version_ranges` → `check_version_range_subset` (direct)
- `intersect_version_ranges` → `check_version_range_superset` (direct)
- `intersect_version_ranges` → `check_version_ranges_disjoint` (direct)
- `intersect_version_ranges` → `complement_version_range` (direct)
- `intersect_version_ranges` → `difference_version_ranges` (direct)
- `intersect_version_ranges` → `intersect_version_ranges` (direct)
- `intersect_version_ranges` → `union_version_ranges` (direct)
- `parse_sdist_filename` → `canonicalize_package_name` (field name)
- `parse_sdist_filename` → `canonicalize_version_string` (field version)
- `parse_sdist_filename` → `check_normalized_package_name` (field name)
- `parse_sdist_filename` → `check_version_in_range` (field version)
- `parse_sdist_filename` → `check_version_in_specifier_set` (field version)
- `parse_sdist_filename` → `create_singleton_version_range` (field version)
- `parse_sdist_filename` → `parse_version_string` (field version)
- `parse_tag` → `parse_tag` (first element)
- `parse_version_string` → `canonicalize_version_string` (direct)
- `parse_version_string` → `check_version_in_range` (direct)
- `parse_version_string` → `check_version_in_specifier_set` (direct)
- `parse_version_string` → `create_singleton_version_range` (direct)
- `parse_version_string` → `parse_version_string` (direct)
- `parse_wheel_filename` → `canonicalize_package_name` (field name)
- `parse_wheel_filename` → `canonicalize_version_string` (field version)
- `parse_wheel_filename` → `check_normalized_package_name` (field name)
- `parse_wheel_filename` → `check_version_in_range` (field version)
- `parse_wheel_filename` → `check_version_in_specifier_set` (field version)
- `parse_wheel_filename` → `create_singleton_version_range` (field version)
- `parse_wheel_filename` → `parse_tag` (field tags, first element)
- `parse_wheel_filename` → `parse_version_string` (field version)
