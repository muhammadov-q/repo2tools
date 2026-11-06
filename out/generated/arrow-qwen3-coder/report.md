# repo2tools report: arrow-qwen3-coder

- Repo: https://github.com/arrow-py/arrow at `2224255c4acc594d734cef0bbc83360452a67983`
- Package: `arrow`, 53 public callables
- Model: `qwen3-coder`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 1.0 min. LLM tokens: 182,921 in 104 requests (propose 3,719, spec 105,568, code 73,634)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 30 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 18 |
| Accepted and confirmed against a direct library call | 12 |
| Passed all checks on the first try | 15 |
| Rejected after the repair rounds | 12 |

First try, by the first check that failed: ok: 15, spec: 10, fastmcp: 4, differential: 1.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `parse_date` | `arrow.api.get` | 0 | 2 / 3 | yes |
| `get_utc_now` | `arrow.api.utcnow` | 0 | 0 / 0 | no: unstable |
| `get_local_now` | `arrow.api.now` | 0 | 0 / 1 | no: unstable, both_error |
| `create_arrow_now` | `arrow.arrow.Arrow.now` | 0 | 0 / 4 | no: both_error, unstable |
| `create_arrow_utc` | `arrow.arrow.Arrow.utcnow` | 0 | 0 / 0 | no: unstable |
| `create_arrow_from_timestamp` | `arrow.arrow.Arrow.fromtimestamp` | 0 | 4 / 1 | yes |
| `create_arrow_from_string` | `arrow.arrow.Arrow.strptime` | 0 | 4 / 1 | yes |
| `generate_time_range` | `arrow.arrow.Arrow.range` | 2 | 5 / 0 | yes |
| `get_time_span` | `arrow.arrow.Arrow.span` | 3 | 4 / 1 | yes |
| `humanize_time_difference` | `arrow.arrow.Arrow.humanize` | 1 | 5 / 0 | yes |
| `extract_date_component` | `arrow.arrow.Arrow.date` | 0 | 4 / 1 | yes |
| `get_timestamp` | `arrow.arrow.Arrow.timestamp` | 0 | 5 / 0 | yes |
| `get_integer_timestamp` | `arrow.arrow.Arrow.int_timestamp` | 0 | 4 / 1 | yes |
| `clone_arrow` | `arrow.arrow.Arrow.clone` | 0 | 5 / 0 | yes |
| `format_ctime` | `arrow.arrow.Arrow.ctime` | 0 | 5 / 0 | yes |
| `factory_parse_date` | `arrow.factory.ArrowFactory.get` | 0 | 3 / 1 | yes |
| `factory_get_utc_now` | `arrow.factory.ArrowFactory.utcnow` | 0 | 0 / 0 | no: unstable |
| `factory_get_local_now` | `arrow.factory.ArrowFactory.now` | 0 | 0 / 0 | no: unstable |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `create_arrow_from_datetime` | `arrow.arrow.Arrow.fromdatetime` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'tzinfo' |
| `create_arrow_from_date` | `arrow.arrow.Arrow.fromdate` | differential | Input {"date": "2023-10-15"}: the tool raised ValueError: Failed to create Arrow object: 'str' object is not callable, but the direct library call returned "2023-10-15T00:00:00+00:00" Input {"date": "2023-12-31", "tzinfo |
| `round_down_time` | `arrow.arrow.Arrow.floor` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'floor' |
| `round_up_time` | `arrow.arrow.Arrow.ceil` | spec | the direct_call expression is wrong: AttributeError: 'dict' object has no attribute 'ceil' |
| `convert_timezone` | `arrow.arrow.Arrow.to` | spec | the direct_call expression is wrong: AttributeError: 'str' object has no attribute 'to' |
| `format_arrow_date` | `arrow.arrow.Arrow.format` | differential | Input {"date": {"day": 15, "hour": 14, "minute": 30, "month": 10, "second": 45, "year": 2023}}: the direct library call raised TypeError: expected string or bytes-like object, got 'NoneType', but the tool returned "2023- |
| `check_time_range` | `arrow.arrow.Arrow.is_between` | differential | Input {"bounds": "[]", "end": {"day": 8, "month": 5, "year": 2013}, "start": {"day": 5, "month": 5, "year": 2013}, "target": {"day": 8, "month": 5, "year": 2013}}: the tool raised ValidationError: 1 validation error for  |
| `extract_time_component` | `arrow.arrow.Arrow.time` | differential | Input {"day": 15, "month": 6, "year": 2023}: the direct library call raised TypeError: 'NoneType' object cannot be interpreted as an integer, but the tool returned {"hour": 0, "microsecond": 0, "minute": 0, "second": 0} |
| `modify_arrow_fields` | `arrow.arrow.Arrow.replace` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['TypeError: str.replace() takes no keyword arguments']. Use samples that are valid for the library. |
| `shift_time` | `arrow.arrow.Arrow.shift` | spec | sample {"arrow_object": "arrow.get('2023-01-01T00:00:00Z')", "invalid_param": 1, "months": 1, "years": 1} does not fit the parameters: got an unexpected keyword argument 'invalid_param' |
| `format_iso8601` | `arrow.arrow.Arrow.isoformat` | differential | Input {"day": 15, "hour": 14, "microsecond": 123456, "minute": 30, "month": 10, "second": 45, "year": 2023}: the direct library call raised TypeError: isoformat() argument 1 must be a unicode character, not None, but the |
| `format_with_strftime` | `arrow.arrow.Arrow.strftime` | spec | the direct_call expression is wrong: AttributeError: 'dict' object has no attribute 'strftime' |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/arrow-qwen3-coder/run_server.sh
```
