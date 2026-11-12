# Usability of packaging-coder-60-usable

`qwen3-8b` gets one task per checked sample call: 135 tasks for 29 tools. A task is right when the model calls the tool it was written for, with arguments that give the known result.

| | Tool alone | In the whole set |
| --- | --- | --- |
| **Right call** | **123 of 135 (91%)** | **116 of 135 (86%)** |
| Right call, held-out tasks only | 49 of 58 (84%) | 48 of 58 (83%) |
| No tool call | 8 | 2 |
| Only other tools called | 0 | 12 |
| Tool called, wrong arguments | 4 | 3 |
| Run failed | 0 | 2 |
| Final answer equals the known result | 103 of 135 (76%) | 119 of 135 (88%) |

## Per tool

| Tool | Tool alone | In the whole set | Problems | Called instead |
| --- | --- | --- | --- | --- |
| `canonicalize_package_name` | 6 of 6 | 5 of 6 | no_call 1 |  |
| `canonicalize_version_string` | 5 of 6 | 6 of 6 | no_call 1 |  |
| `check_normalized_package_name` | 5 of 6 | 6 of 6 | no_call 1 |  |
| `check_specifier_set_subset` | 5 of 5 | 5 of 5 |  |  |
| `check_specifier_set_superset` | 4 of 5 | 0 of 5 | wrong_tool 5, bad_arguments 1 | `check_specifier_set_subset` 4, `check_version_range_superset` 1 |
| `check_specifier_set_unsatisfiable` | 6 of 6 | 6 of 6 |  |  |
| `check_specifier_sets_disjoint` | 4 of 5 | 1 of 5 | wrong_tool 4, no_call 1 | `check_version_ranges_disjoint` 4 |
| `check_version_in_range` | 6 of 6 | 4 of 6 | wrong_tool 2 | `check_version_in_specifier_set` 2 |
| `check_version_in_specifier_set` | 5 of 5 | 5 of 5 |  |  |
| `check_version_range_subset` | 5 of 5 | 5 of 5 |  |  |
| `check_version_range_superset` | 5 of 5 | 5 of 5 |  |  |
| `check_version_ranges_disjoint` | 5 of 5 | 4 of 5 | wrong_tool 1 | `check_specifier_sets_disjoint` 1 |
| `complement_version_range` | 5 of 5 | 5 of 5 |  |  |
| `convert_specifier_set_to_range` | 3 of 4 | 3 of 4 | no_call 2 |  |
| `create_empty_version_range` | 3 of 3 | 3 of 3 |  |  |
| `create_full_version_range` | 5 of 5 | 5 of 5 |  |  |
| `create_singleton_version_range` | 2 of 4 | 2 of 4 | bad_arguments 4 |  |
| `difference_version_ranges` | 4 of 4 | 4 of 4 |  |  |
| `evaluate_marker` | 4 of 5 | 5 of 5 | no_call 1 |  |
| `generate_compatible_tags` | 5 of 5 | 3 of 5 | error 2 |  |
| `generate_generic_tags` | 5 of 5 | 5 of 5 |  |  |
| `get_default_marker_environment` | 1 of 1 | 1 of 1 |  |  |
| `intersect_version_ranges` | 5 of 5 | 5 of 5 |  |  |
| `parse_metadata_email` | 4 of 5 | 5 of 5 | no_call 1 |  |
| `parse_sdist_filename` | 2 of 3 | 3 of 3 | no_call 1 |  |
| `parse_tag` | 4 of 4 | 4 of 4 |  |  |
| `parse_version_string` | 4 of 4 | 4 of 4 |  |  |
| `parse_wheel_filename` | 2 of 3 | 3 of 3 | no_call 1 |  |
| `union_version_ranges` | 4 of 5 | 4 of 5 | bad_arguments 2 |  |
