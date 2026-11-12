# Usability repair: packaging-coder-60 -> packaging-coder-60-usable

`qwen3-8b` uses the tools. `qwen3-32b` writes new names and descriptions for tools with a failed task; it sees only the tasks marked for repair. A rewrite is kept if the small model then gets more of those right. The code of the tools is unchanged, and every rewritten tool passed the checks of repo2tools.py again. "After" is measured through the new tool set's own server.

**10 of 12 tools with a failed task were rewritten** (0 renamed); the set has 29 tools.

| Right calls | Before | After |
| --- | --- | --- |
| Tool alone, held-out tasks | 43 of 58 (74%) | 51 of 58 (88%) |
| In the whole set, held-out tasks | 43 of 58 (74%) | 45 of 58 (78%) |
| Tool alone, tasks used for the repair | 67 of 77 (87%) | 73 of 77 (95%) |
| In the whole set, tasks used for the repair | 61 of 77 (79%) | 69 of 77 (90%) |
| Held-out tasks of the rewritten tools, both settings | 26 of 44 (59%) | 36 of 44 (82%) |
| Held-out tasks of the other tools, both settings | 60 of 72 (83%) | 60 of 72 (83%) |

## Tools with a failed task

| Tool | New name | Repair tasks right, before to after | All tasks right, before to after | Tries | Result |
| --- | --- | --- | --- | --- | --- |
| `canonicalize_version_string` |  | 4 to 5 of 6 | 10 to 11 of 12 | 3 | rewritten |
| `check_specifier_set_subset` |  | 4 to 6 of 6 | 6 to 6 of 10 | 1 | rewritten |
| `check_specifier_set_superset` |  | 2 to 5 of 6 | 3 to 6 of 10 | 3 | rewritten |
| `check_specifier_sets_disjoint` |  | 3 to 3 of 6 | 4 to 4 of 10 | 3 | no rewrite was better |
| `check_version_in_range` |  | 4 to 6 of 6 | 5 to 10 of 12 | 3 | rewritten |
| `check_version_range_superset` |  | 3 to 6 of 6 | 5 to 10 of 10 | 1 | rewritten |
| `create_full_version_range` |  | 5 to 6 of 6 | 9 to 10 of 10 | 1 | rewritten |
| `create_singleton_version_range` |  | 2 to 3 of 4 | 4 to 6 of 8 | 3 | rewritten |
| `evaluate_marker` |  | 3 to 6 of 6 | 4 to 10 of 10 | 1 | rewritten |
| `generate_compatible_tags` |  | 4 to 4 of 6 | 7 to 8 of 10 | 3 | no rewrite was better |
| `parse_metadata_email` |  | 5 to 6 of 6 | 8 to 10 of 10 | 1 | rewritten |
| `parse_version_string` |  | 3 to 4 of 4 | 7 to 8 of 8 | 1 | rewritten |

## Tools that got worse

- `complement_version_range`: 10 to 9 of 10 (not rewritten itself)
- `difference_version_ranges`: 8 to 7 of 8 (not rewritten itself)
- `parse_sdist_filename`: 6 to 5 of 6 (not rewritten itself)

## New names and descriptions

### `canonicalize_version_string`

Before: Return a canonical form of a version string. version: A version string to canonicalize, e.g. '1.0.0' -> '1'. strip_trailing_zero: Whether to strip trailing zeros from the release segment, e.g. '1.0.0' with strip_trailing_zero=False -> '1.0.0'.

After: Convert a version string into its canonical form using standard normalization rules. Returns the normalized version as a string. If the input is invalid, it is returned unchanged. Parameters: 'version' (string) is the version to canonicalize. 'strip_trailing_zero' (boolean, default true) determines whether to remove trailing zeros from the release segment.

### `check_specifier_set_subset`

Before: Check if one specifier set is a subset of another. specifier_set1: The first specifier set to check. specifier_set2: The second specifier set to check against. >>> check_specifier_set_subset('>=3.12,<3.13', '>=3.12') True

After: Check if all versions matching the first specifier set also match the second. Returns true if the first is a subset of the second. Parameters: specifier_set1 (string) - the set to check; specifier_set2 (string) - the set to check against. Uses the packaging library's SpecifierSet.is_subset method. Output is a boolean.

### `check_specifier_set_superset`

Before: Check if one specifier set is a superset of another. specifier_set1: The first specifier set to check. specifier_set2: The second specifier set to check against. >>> check_specifier_set_superset('>=3.12', '>=3.12,<3.13') True

After: Check if all versions matching the second specifier set also match the first. Returns true if specifier_set1 is a superset of specifier_set2. Parameters: specifier_set1 (string) - the set to check against; specifier_set2 (string) - the set to check. Both are version specifier strings like '>=3.12' or '>=3.12,<3.13'.

### `check_version_in_range`

Before: Check if a version is contained within a version range. :param specifier_set: A specifier set that can be converted to a version range :param version: The version string to check against the range :returns: True if the version is contained in the range, False otherwise >>> check_version_in_range(">=1.0,<2.0", "1.5") True >>> check_version_in_range(">=1.0,<2.0", "2.0") False

After: Check if a version is contained in a version range derived from a specifier set. Parameters: specifier_set (string, e.g., '>=1.0,<2.0'), version (string, e.g., '0.9'). Returns True if the version is in the range, False otherwise. This tool uses SpecifierSet.to_range().contains() from the packaging library.

### `check_version_range_superset`

Before: Check if one version range is a superset of another. outer_range: A version range specifier string for the outer range, inner_range: A version range specifier string for the inner range. >>> check_version_range_superset(">=1.0,<2.0", ">=1.5,<1.8") True

After: Check if all versions in `inner_range` are included in `outer_range`. `outer_range` and `inner_range` are version range strings (e.g., '>=1.0,<2.0'). Returns true if every version in `inner_range` is also in `outer_range`. Use to verify if one version range fully contains another. Both ranges must use the same pre-release policy.

### `create_full_version_range`

Before: Return a full version range that accepts all versions. admit_arbitrary: whether to admit arbitrary strings as versions; prereleases: whether to include pre-release versions. Example: create_full_version_range() -> 'VersionRange(full)'.

After: Returns a VersionRange object that includes all PEP 440 versions and optionally arbitrary strings. Set `admit_arbitrary` (bool, default true) to restrict or allow arbitrary versions. Set `prereleases` (bool or null, default null) to include, exclude, or leave unspecified pre-release versions. Output is a VersionRange representing the full version range.

### `create_singleton_version_range`

Before: Return a version range that only accepts a single specific version. version: A PEP 440 compliant version string, e.g. '1.0' -> '{1.0}'. prereleases: Whether to include pre-release versions.

After: Returns a VersionRange that includes exactly one specific PEP 440 version, excluding local versions and optionally excluding prereleases. Parameters: 'version' (string, a valid PEP 440 version), 'prereleases' (bool or null, default null). When 'prereleases' is null, the range excludes prereleases. Output is a VersionRange object representing the singleton range.

### `evaluate_marker`

Before: Evaluate a marker expression against an environment. A marker is a string that specifies conditions for package dependencies. This tool evaluates whether the marker matches the given environment. Args: marker: A marker expression to evaluate, e.g. "python_version >= '3.6'" environment: Mapping containing keys and values to override the detected environment context: The context in which the marker is evaluated, which influences what marker names are considered valid. Accepted values are "metadata" (default), "lock_file", and "requirement" Returns: True if the marker matches the environment, otherwise False Example: >>> evaluate_marker("python_version >= '3.6'", {"python_version": "3.8"}) True

After: Evaluates a package marker expression against a given environment. Markers define conditions for dependencies. Use this tool to determine if a marker matches the environment. Parameters: `marker` (string, e.g., 'python_version >= '3.6''), `environment` (optional mapping of environment variables), and `context` (string, one of 'metadata', 'lock_file', or 'requirement'). Returns a boolean indicating whether the marker evaluates to true in the given context.

### `parse_metadata_email`

Before: Parse distribution metadata stored as email headers. data: Distribution metadata as email headers, e.g. 'Name: example Version: 1.0 ' -> {'core': {'name': 'example', 'version': '1.0'}, 'unparsed': {}}.

After: Parse distribution metadata in email header format into structured data. Parameters: 'data' (string) is metadata in the form of email headers (e.g., 'Name: example\nVersion: 1.0\n'). Returns a tuple of two dictionaries: the first contains parsed core metadata fields, the second contains unparsed or unrecognized fields. Fields with multiple values are stored as lists.

### `parse_version_string`

Before: Parse the given version string. This is identical to the Version constructor. >>> parse_version_string('1.0.dev1') '1.0.dev1' :param version: The version string to parse. :raises ValueError: When the version string is not a valid version.

After: Parse a version string into a Version object using the packaging library. This function is equivalent to the Version constructor. It accepts a string version and returns the parsed Version object. If the version string is invalid, a ValueError is raised. Use this tool to convert version strings into standardized Version objects for comparison or validation. Parameter: version (string) – the version string to parse. Output: a Version object representing the parsed version.

