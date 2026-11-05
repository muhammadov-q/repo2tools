# Exercise preview: one example per kind

## version_compare (short, 1 calls)

```text
Compare the Python package versions '1!1.0.dev0' and '1!1.0a0.post0' using PEP 440 ordering. Answer -1 if '1!1.0.dev0' is older, 0 if both are equal, or 1 if '1!1.0.dev0' is newer.
```

Answer: `-1` (check: exact)

Reference calls:

```text
  0. compare_versions({"version_a": "1!1.0.dev0", "version_b": "1!1.0a0.post0"})
```

## version_normalize (short, 1 calls)

```text
What is the normalized PEP 440 spelling of the version 'v1.0'? Answer with the version string.
```

Answer: `"1.0"` (check: exact)

Reference calls:

```text
  0. normalize_version({"version": "v1.0"})
```

## version_base (short, 1 calls)

```text
What is the base version of '1!1.0a1.post5', meaning its epoch and release numbers without any pre-, post-, dev-release or local part? Answer with the version string.
```

Answer: `"1!1.0"` (check: exact)

Reference calls:

```text
  0. base_version({"version": "1!1.0a1.post5"})
```

## version_is_prerelease (short, 1 calls)

```text
Under PEP 440, is '1.0.post1+dev' a pre-release? Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. version_info({"version": "1.0.post1+dev"})
```

## version_valid (short, 1 calls)

```text
Is '1.0+foo&asd' a valid version string under PEP 440? Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. is_valid_version({"version": "1.0+foo&asd"})
```

## specifier_contains (short, 1 calls)

```text
Is version '1.0.dev0' allowed by the version constraint '>=0.9,!=0.9,<=1.0' when pre-releases are excluded? Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. version_satisfies({"version": "1.0.dev0", "specifier": ">=0.9,!=0.9,<=1.0", "include_prereleases": false})
```

## specifier_filter (short, 1 calls)

```text
From the versions ["0.9", "1.0", "1.5", "2.0"], which are allowed by the version constraint '==1.*,>=1.0'? Answer with a JSON list in the original order.
```

Answer: `["1.0", "1.5"]` (check: exact)

Reference calls:

```text
  0. filter_versions({"versions": ["0.9", "1.0", "1.5", "2.0"], "specifier": "==1.*,>=1.0"})
```

## specifier_satisfiable (short, 1 calls)

```text
Can any version at all satisfy the version constraint '==1.0,>=2.0'? Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. is_satisfiable({"specifier": "==1.0,>=2.0"})
```

## specifier_subset (short, 1 calls)

```text
Is every version allowed by the constraint '' also allowed by '>=3.12'? Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. specifier_is_subset({"specifier": "", "other": ">=3.12"})
```

## name_canonicalize (short, 1 calls)

```text
What is the normalized project name, as package indexes compare names, for 'fOo'? Answer with the name.
```

Answer: `"foo"` (check: exact)

Reference calls:

```text
  0. canonicalize_name({"name": "fOo"})
```

## version_canonicalize (short, 1 calls)

```text
What is the canonical form of version '1.0' used to compare file names (normalized, with trailing '.0' release parts removed)? Answer with the version string.
```

Answer: `"1"` (check: exact)

Reference calls:

```text
  0. canonicalize_version({"version": "1.0"})
```

## wheel_tags (short, 1 calls)

```text
Which compatibility tags does the wheel file 'pyvirtualcam-0.13.0-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl' declare? Answer with a JSON list of tags such as 'py3-none-any'.
```

Answer: `["cp310-cp310-manylinux2014_x86_64", "cp310-cp310-manylinux_2_17_x86_64"]` (check: set_equal)

Reference calls:

```text
  0. parse_wheel_filename({"filename": "pyvirtualcam-0.13.0-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"})
```

## marker_evaluate (short, 1 calls)

```text
Does the environment marker 'extra == 'security'' evaluate to true when extra is 'quux'? Other marker variables are those of CPython 3.12.0 on Linux x86_64. Answer true or false.
```

Answer: `false` (check: exact)

Reference calls:

```text
  0. evaluate_marker({"marker": "extra == 'security'", "environment": {"extra": "quux"}})
```

## requirements_check (long, 18 calls)

```text
Target environment: CPython 3.11 on Linux (aarch64).
Available versions on the package index:
- charset-normalizer: 2.1.1, 3.3.2, 3.4.0, 3.4.1.dev2
- colorama: 0.4.4, 0.4.5, 0.4.6
- numpy: 1.24.4, 1.26.4, 2.0.2, 2.1.3, 2.2.0rc1
- pywin32: 305, 306, 308
- requests: 2.25.1, 2.28.2, 2.31.0, 2.32.3, 2.33.0rc1
- urllib3: 1.26.18, 1.26.20, 2.0.7, 2.2.3, 2.3.0b1
Requirements:
1. urllib3>=1.26.20
2. Requests
3. NumPy; platform_machine == "arm64"
4. colorama<0.4.6
5. PyWin32>=305,<308
6. charset-normalizer!=3.4.0,>=3.3.2; sys_platform == "win32"
For every requirement whose environment marker applies to the target environment, find the newest available version that satisfies its version constraint, without pre-releases. Answer with a JSON object that maps the normalized project name to that version, or to null if no available version fits. Leave out requirements whose marker does not apply.
```

Answer: `{"urllib3": "2.2.3", "requests": "2.32.3", "colorama": "0.4.5", "pywin32": "306"}` (check: exact)

Reference calls:

```text
  0. parse_requirement({"requirement": "urllib3>=1.26.20"})
  1. filter_versions({"versions": ["1.26.18", "1.26.20", "2.0.7", "2.2.3", "2.3.0b1"], "specifier": {"$ref": [0, "specifier"]}, "include_prereleases": false})
  2. sort_versions({"versions": {"$ref": [1]}, "descending": true})
  3. parse_requirement({"requirement": "Requests"})
  4. canonicalize_name({"name": {"$ref": [3, "name"]}})
  5. filter_versions({"versions": ["2.25.1", "2.28.2", "2.31.0", "2.32.3", "2.33.0rc1"], "specifier": {"$ref": [3, "specifier"]}, "include_prereleases": false})
  6. sort_versions({"versions": {"$ref": [5]}, "descending": true})
  7. parse_requirement({"requirement": "NumPy; platform_machine == \"arm64\""})
  8. evaluate_marker({"marker": {"$ref": [7, "marker"]}, "environment": {"python_version": "3.11", "python_full_version": "3.11.0", "sys_platform": "linux", "os_name": "posix", "platform_system": "Linux", "platform_machine": "aarch64"}})
  9. parse_requirement({"requirement": "colorama<0.4.6"})
  10. filter_versions({"versions": ["0.4.4", "0.4.5", "0.4.6"], "specifier": {"$ref": [9, "specifier"]}, "include_prereleases": false})
  11. sort_versions({"versions": {"$ref": [10]}, "descending": true})
  12. parse_requirement({"requirement": "PyWin32>=305,<308"})
  13. canonicalize_name({"name": {"$ref": [12, "name"]}})
  14. filter_versions({"versions": ["305", "306", "308"], "specifier": {"$ref": [12, "specifier"]}, "include_prereleases": false})
  15. sort_versions({"versions": {"$ref": [14]}, "descending": true})
  16. parse_requirement({"requirement": "charset-normalizer!=3.4.0,>=3.3.2; sys_platform == \"win32\""})
  17. evaluate_marker({"marker": {"$ref": [16, "marker"]}, "environment": {"python_version": "3.11", "python_full_version": "3.11.0", "sys_platform": "linux", "os_name": "posix", "platform_system": "Linux", "platform_machine": "aarch64"}})
```
