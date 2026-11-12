# Usability repair: packaging-coder-60 -> packaging-coder-60-usable

`qwen3-8b` uses the tools. `qwen3-32b` writes new names and descriptions for tools with a failed task; it sees only the tasks marked for repair. A rewrite is kept if the small model then gets more of those right. The code of the tools is unchanged, and every rewritten tool passed the checks of repo2tools.py again. "After" is measured through the new tool set's own server.

**9 of 11 tools with a failed task were rewritten** (0 renamed); the set has 29 tools.

| Right calls | Before | After |
| --- | --- | --- |
| Tool alone, held-out tasks | 44 of 58 (76%) | 49 of 58 (84%) |
| In the whole set, held-out tasks | 43 of 58 (74%) | 48 of 58 (83%) |
| Tool alone, tasks used for the repair | 68 of 77 (88%) | 74 of 77 (96%) |
| In the whole set, tasks used for the repair | 61 of 77 (79%) | 68 of 77 (88%) |
| Held-out tasks of the rewritten tools, both settings | 22 of 40 (55%) | 32 of 40 (80%) |
| Held-out tasks of the other tools, both settings | 65 of 76 (86%) | 65 of 76 (86%) |

## Tools with a failed task

| Tool | New name | Repair tasks right, before to after | All tasks right, before to after | Tries | Result |
| --- | --- | --- | --- | --- | --- |
| `canonicalize_version_string` |  | 4 to 5 of 6 | 10 to 11 of 12 | 3 | rewritten |
| `check_specifier_set_subset` |  | 4 to 6 of 6 | 6 to 10 of 10 | 1 | rewritten |
| `check_specifier_set_superset` |  | 1 to 3 of 6 | 2 to 4 of 10 | 3 | rewritten |
| `check_specifier_sets_disjoint` |  | 3 to 3 of 6 | 4 to 5 of 10 | 3 | no rewrite was better |
| `check_version_in_range` |  | 4 to 6 of 6 | 5 to 10 of 12 | 2 | rewritten |
| `check_version_range_superset` |  | 3 to 6 of 6 | 5 to 10 of 10 | 1 | rewritten |
| `create_singleton_version_range` |  | 2 to 3 of 4 | 4 to 4 of 8 | 3 | rewritten |
| `evaluate_marker` |  | 4 to 6 of 6 | 5 to 9 of 10 | 1 | rewritten |
| `generate_compatible_tags` |  | 4 to 4 of 6 | 8 to 8 of 10 | 3 | no rewrite was better |
| `parse_metadata_email` |  | 5 to 6 of 6 | 8 to 9 of 10 | 2 | rewritten |
| `parse_version_string` |  | 3 to 4 of 4 | 7 to 8 of 8 | 1 | rewritten |

## Tools that got worse

- `check_version_ranges_disjoint`: 10 to 9 of 10 (not rewritten itself)
- `parse_sdist_filename`: 6 to 5 of 6 (not rewritten itself)

## New names and descriptions

### `canonicalize_version_string`

Before: Return a canonical form of a version string. version: A version string to canonicalize, e.g. '1.0.0' -> '1'. strip_trailing_zero: Whether to strip trailing zeros from the release segment, e.g. '1.0.0' with strip_trailing_zero=False -> '1.0.0'.

After: Convert a version string into its canonical form using standard normalization rules. Returns the result as a string. Invalid versions are returned as-is. Parameters: 'version' (string) is the version to canonicalize. 'strip_trailing_zero' (boolean, default true) determines whether to remove trailing zeros from the release segment. Example: '1.0.0' becomes '1' when strip_trailing_zero is true. Always call this tool directly with the version string to check.

### `check_specifier_set_subset`

Before: Check if one specifier set is a subset of another. specifier_set1: The first specifier set to check. specifier_set2: The second specifier set to check against. >>> check_specifier_set_subset('>=3.12,<3.13', '>=3.12') True

After: Check if all versions matching the first specifier set also match the second. Use when comparing version specifier sets (e.g., from package requirements). specifier_set1 (string): the set to check if it is a subset. specifier_set2 (string): the set to check against. Returns true if every version in specifier_set1 is also in specifier_set2, otherwise false. Example: '>=3.12,<3.13' is a subset of '>=3.12' → true.

### `check_specifier_set_superset`

Before: Check if one specifier set is a superset of another. specifier_set1: The first specifier set to check. specifier_set2: The second specifier set to check against. >>> check_specifier_set_superset('>=3.12', '>=3.12,<3.13') True

After: Check if all versions in specifier_set2 are included in specifier_set1. Use when verifying if one version requirement fully includes another. specifier_set1 (string): the potential superset version requirement. specifier_set2 (string): the potential subset version requirement. Returns true if every version in specifier_set2 is also in specifier_set1, otherwise false.

### `check_version_in_range`

Before: Check if a version is contained within a version range. :param specifier_set: A specifier set that can be converted to a version range :param version: The version string to check against the range :returns: True if the version is contained in the range, False otherwise >>> check_version_in_range(">=1.0,<2.0", "1.5") True >>> check_version_in_range(">=1.0,<2.0", "2.0") False

After: Check if a version string is contained in a version range derived from a specifier set. Use when you need to verify if a specific version satisfies a version range. Parameters: 'specifier_set' (string) is the version range definition (e.g., '>=1.0,<2.0'), and 'version' (string) is the version to check. Returns true if the version is in the range, false otherwise. This tool uses the full version range logic, not direct specifier matching.

### `check_version_range_superset`

Before: Check if one version range is a superset of another. outer_range: A version range specifier string for the outer range, inner_range: A version range specifier string for the inner range. >>> check_version_range_superset(">=1.0,<2.0", ">=1.5,<1.8") True

After: Check if all versions in one range are included in another. Returns true if every version in inner_range is also in outer_range. Parameters: outer_range (string) is the larger version range, inner_range (string) is the smaller version range to check. Example: check_version_range_superset('>=1.0,<2.0', '>=1.5,<1.8') returns true. Output is a boolean (true or false).

### `create_singleton_version_range`

Before: Return a version range that only accepts a single specific version. version: A PEP 440 compliant version string, e.g. '1.0' -> '{1.0}'. prereleases: Whether to include pre-release versions.

After: Returns a version range that includes exactly one PEP 440 version and excludes local versions. 'version' is a string like '1.0.0'. 'prereleases' is a bool or null (default null): use null to exclude prereleases, or set to true to include them. Output is a JSON string like '<VersionRange '[1.0.0, 1.0.0]' pre=False>'.

### `evaluate_marker`

Before: Evaluate a marker expression against an environment. A marker is a string that specifies conditions for package dependencies. This tool evaluates whether the marker matches the given environment. Args: marker: A marker expression to evaluate, e.g. "python_version >= '3.6'" environment: Mapping containing keys and values to override the detected environment context: The context in which the marker is evaluated, which influences what marker names are considered valid. Accepted values are "metadata" (default), "lock_file", and "requirement" Returns: True if the marker matches the environment, otherwise False Example: >>> evaluate_marker("python_version >= '3.6'", {"python_version": "3.8"}) True

After: Evaluates a package marker expression against an environment and returns true or false. Markers define conditions for dependencies. Parameters: 'marker' (string, e.g., 'python_version >= '3.6''), 'environment' (optional mapping of environment variables), 'context' (string, one of 'metadata', 'lock_file', or 'requirement'). Returns a boolean indicating whether the marker matches the environment.

### `parse_metadata_email`

Before: Parse distribution metadata stored as email headers. data: Distribution metadata as email headers, e.g. 'Name: example Version: 1.0 ' -> {'core': {'name': 'example', 'version': '1.0'}, 'unparsed': {}}.

After: Parse a metadata string in email header format (e.g., 'Name: value') into a JSON object. The output has two keys: 'core' for recognized metadata fields (like name, version) parsed into standard types, and 'unparsed' for unrecognized or multi-value fields. Input: 'data' (string) is the raw metadata string. Output: a JSON object with 'core' and 'unparsed' dictionaries as shown in examples.

### `parse_version_string`

Before: Parse the given version string. This is identical to the Version constructor. >>> parse_version_string('1.0.dev1') '1.0.dev1' :param version: The version string to parse. :raises ValueError: When the version string is not a valid version.

After: Parse a version string and return it in normalized format as a JSON string. This tool is used to convert version strings into standardized representations. The input is a string version, and the output is a string in the format shown in examples, such as '1.0.0' or '1.0.0a1'.

