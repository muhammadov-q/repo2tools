# ToolGym types for pypa-packaging-handmade

Types proposed by `qwen3-32b`, then checked by 792 tool calls. A claim stands if at least 60% of its test calls work.

| | Count |
| --- | --- |
| Tools exported | 21 |
| Shared types proposed / kept | 6 / 6 |
| Parameters with a shared type: proposed / kept | 24 / 22 |
| Parameter claims tested / withdrawn | 24 / 2 |
| Output claims / kept | 14 / 10 |
| Data-flow links between tools | 49, over 49 tool pairs |
| Tools with no link | 4 |

## Types

| Type | Examples | Parameters |
| --- | --- | --- |
| `MarkerString` | 7 | `evaluate_marker.marker` |
| `SdistFilename` | 3 | `parse_sdist_filename.filename` |
| `SpecifierString` | 45 | `is_valid_specifier.specifier`, `version_satisfies.specifier`, `filter_versions.specifier`, `combine_specifiers.specifier_a`, `combine_specifiers.specifier_b`, `is_satisfiable.specifier`, `specifier_is_subset.specifier`, `specifier_is_subset.other`, `specifiers_overlap.specifier_a`, `specifiers_overlap.specifier_b` |
| `TagString` | 3 | `parse_tag.tag` |
| `VersionString` | 81 | `normalize_version.version`, `version_info.version`, `base_version.version`, `compare_versions.version_a`, `compare_versions.version_b`, `sort_versions.versions`, `canonicalize_version.version`, `version_satisfies.version` |
| `WheelFilename` | 8 | `parse_wheel_filename.filename` |

## Withdrawn parameter claims

| Parameter | Proposed type | Pairs that work |
| --- | --- | --- |
| `is_valid_version.version` | `VersionString` | 14 of 18 |
| `filter_versions.versions` | `VersionString` | 17 of 18 |

## Output claims

| Tool | Claim | Worked | Kept |
| --- | --- | --- | --- |
| `normalize_version` | NormalizedVersionString | 12 of 12 | yes |
| `version_info` | VersionInfoObject | 0 of 0 | no: no parameter has this type |
| `base_version` | BaseVersionString | 6 of 6 | yes |
| `sort_versions` | list[VersionString] | 12 of 12 | yes |
| `canonicalize_version` | NormalizedVersionString | 12 of 12 | yes |
| `filter_versions` | list[VersionString] | 10 of 12 | yes |
| `combine_specifiers` | SpecifierString | 9 of 9 | yes |
| `parse_requirement` | field specifier: SpecifierString | 12 of 12 | yes |
| `canonicalize_name` | ProjectName | 0 of 0 | no: no parameter has this type |
| `parse_wheel_filename` | field name: WheelFilename | 0 of 4 | no |
| `parse_wheel_filename` | field tags: list[TagString] | 4 of 4 | yes |
| `parse_sdist_filename` | field name: SdistFilename | 0 of 3 | no |
| `parse_tag` | list[TagString] | 3 of 3 | yes |
| `supported_tags` | list[TagString] | 4 of 4 | yes |

## Links

- `base_version` → `base_version` (direct)
- `base_version` → `canonicalize_version` (direct)
- `base_version` → `compare_versions` (direct)
- `base_version` → `normalize_version` (direct)
- `base_version` → `version_info` (direct)
- `base_version` → `version_satisfies` (direct)
- `canonicalize_version` → `base_version` (direct)
- `canonicalize_version` → `canonicalize_version` (direct)
- `canonicalize_version` → `compare_versions` (direct)
- `canonicalize_version` → `normalize_version` (direct)
- `canonicalize_version` → `version_info` (direct)
- `canonicalize_version` → `version_satisfies` (direct)
- `combine_specifiers` → `combine_specifiers` (direct)
- `combine_specifiers` → `filter_versions` (direct)
- `combine_specifiers` → `is_satisfiable` (direct)
- `combine_specifiers` → `is_valid_specifier` (direct)
- `combine_specifiers` → `specifier_is_subset` (direct)
- `combine_specifiers` → `specifiers_overlap` (direct)
- `combine_specifiers` → `version_satisfies` (direct)
- `filter_versions` → `base_version` (first element)
- `filter_versions` → `canonicalize_version` (first element)
- `filter_versions` → `compare_versions` (first element)
- `filter_versions` → `normalize_version` (first element)
- `filter_versions` → `sort_versions` (direct)
- `filter_versions` → `version_info` (first element)
- `filter_versions` → `version_satisfies` (first element)
- `normalize_version` → `base_version` (direct)
- `normalize_version` → `canonicalize_version` (direct)
- `normalize_version` → `compare_versions` (direct)
- `normalize_version` → `normalize_version` (direct)
- `normalize_version` → `version_info` (direct)
- `normalize_version` → `version_satisfies` (direct)
- `parse_requirement` → `combine_specifiers` (field specifier)
- `parse_requirement` → `filter_versions` (field specifier)
- `parse_requirement` → `is_satisfiable` (field specifier)
- `parse_requirement` → `is_valid_specifier` (field specifier)
- `parse_requirement` → `specifier_is_subset` (field specifier)
- `parse_requirement` → `specifiers_overlap` (field specifier)
- `parse_requirement` → `version_satisfies` (field specifier)
- `parse_tag` → `parse_tag` (first element)
- `parse_wheel_filename` → `parse_tag` (field tags, first element)
- `sort_versions` → `base_version` (first element)
- `sort_versions` → `canonicalize_version` (first element)
- `sort_versions` → `compare_versions` (first element)
- `sort_versions` → `normalize_version` (first element)
- `sort_versions` → `sort_versions` (direct)
- `sort_versions` → `version_info` (first element)
- `sort_versions` → `version_satisfies` (first element)
- `supported_tags` → `parse_tag` (first element)
