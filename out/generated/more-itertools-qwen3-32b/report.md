# repo2tools report: more-itertools-qwen3-32b

- Repo: https://github.com/more-itertools/more-itertools at `ceafee8ce96f4bc1eb74c528bc247c91d648a0bb`
- Package: `more_itertools`, 175 public callables
- Model: `qwen3-32b`, thinking off, temperature 0
- Sandbox: macOS sandbox-exec: no network, home folder unreadable, one scratch folder writable
- Time: 15.1 min. LLM tokens: 959,611 in 579 requests (propose 12,616, spec 476,620, code 470,375)

## Result

| | Tools |
| --- | --- |
| Picked by the LLM | 142 (dropped: 0, for unknown functions, duplicates or bad names) |
| Accepted | 50 |
| Accepted and confirmed against a direct library call | 49 |
| Passed all checks on the first try | 24 |
| Rejected after the repair rounds | 92 |

First try, by the first check that failed: spec: 72, ok: 24, differential: 13, static: 11, fastmcp: 10, runs: 6, loads: 4, syntax: 2.

**Limit of these checks:** the same model wrote the tool and the direct call it is compared with, so they can share a misunderstanding of the library. The checks catch wrapper bugs (wrong field, wrong conversion, crashes), not a wrong idea of what the library does. A real score needs exercises with known answers.

## Accepted tools

| Tool | Wraps | Repairs | Samples: same / both error | Confirmed |
| --- | --- | --- | --- | --- |
| `chunked` | `more_itertools.more.chunked` | 0 | 5 / 1 | yes |
| `last` | `more_itertools.more.last` | 3 | 6 / 0 | yes |
| `distinct_permutations` | `more_itertools.more.distinct_permutations` | 1 | 6 / 0 | yes |
| `windowed` | `more_itertools.more.windowed` | 1 | 5 / 1 | yes |
| `split_into` | `more_itertools.more.split_into` | 1 | 6 / 0 | yes |
| `repeat_each` | `more_itertools.more.repeat_each` | 0 | 5 / 1 | yes |
| `distribute` | `more_itertools.more.distribute` | 0 | 5 / 1 | yes |
| `sort_together` | `more_itertools.more.sort_together` | 1 | 4 / 2 | yes |
| `divide` | `more_itertools.more.divide` | 0 | 5 / 1 | yes |
| `difference` | `more_itertools.more.difference` | 1 | 2 / 4 | yes |
| `circular_shifts` | `more_itertools.more.circular_shifts` | 3 | 5 / 1 | yes |
| `partitions` | `more_itertools.more.partitions` | 3 | 5 / 1 | yes |
| `distinct_combinations` | `more_itertools.more.distinct_combinations` | 0 | 5 / 1 | yes |
| `all_unique` | `more_itertools.more.all_unique` | 0 | 5 / 1 | yes |
| `combination_index` | `more_itertools.more.combination_index` | 0 | 3 / 3 | yes |
| `combination_with_replacement_index` | `more_itertools.more.combination_with_replacement_index` | 0 | 5 / 1 | yes |
| `permutation_index` | `more_itertools.more.permutation_index` | 2 | 5 / 1 | yes |
| `chunked_even` | `more_itertools.more.chunked_even` | 0 | 5 / 1 | yes |
| `duplicates_everseen` | `more_itertools.more.duplicates_everseen` | 1 | 3 / 3 | yes |
| `duplicates_justseen` | `more_itertools.more.duplicates_justseen` | 0 | 4 / 2 | yes |
| `join_mappings` | `more_itertools.more.join_mappings` | 1 | 6 / 0 | yes |
| `nth_prime` | `more_itertools.more.nth_prime` | 0 | 5 / 1 | yes |
| `argmin` | `more_itertools.more.argmin` | 3 | 3 / 3 | yes |
| `extract` | `more_itertools.more.extract` | 0 | 4 / 2 | yes |
| `concurrent_tee` | `more_itertools.more.concurrent_tee` | 3 | 6 / 0 | yes |
| `subfactorial` | `more_itertools.more.subfactorial` | 0 | 4 / 1 | yes |
| `take` | `more_itertools.recipes.take` | 1 | 5 / 1 | yes |
| `consume` | `more_itertools.recipes.consume` | 1 | 6 / 0 | yes |
| `ncycles` | `more_itertools.recipes.ncycles` | 3 | 6 / 0 | yes |
| `pairwise` | `more_itertools.recipes.pairwise` | 2 | 6 / 0 | yes |
| `grouper` | `more_itertools.recipes.grouper` | 3 | 5 / 1 | yes |
| `unique_justseen` | `more_itertools.recipes.unique_justseen` | 0 | 3 / 3 | yes |
| `random_permutation` | `more_itertools.recipes.random_permutation` | 0 | 2 / 1 | yes |
| `random_combination_with_replacement` | `more_itertools.recipes.random_combination_with_replacement` | 0 | 2 / 1 | yes |
| `prepend` | `more_itertools.recipes.prepend` | 3 | 6 / 0 | yes |
| `sliding_window` | `more_itertools.recipes.sliding_window` | 0 | 5 / 1 | yes |
| `triplewise` | `more_itertools.recipes.triplewise` | 0 | 6 / 0 | yes |
| `subslices` | `more_itertools.recipes.subslices` | 1 | 5 / 1 | yes |
| `transpose_matrix` | `more_itertools.recipes.transpose` | 1 | 4 / 1 | yes |
| `reshape_matrix` | `more_itertools.recipes.reshape` | 0 | 6 / 0 | yes |
| `matrix_multiply` | `more_itertools.recipes.matmul` | 0 | 4 / 2 | yes |
| `prime_factors` | `more_itertools.recipes.factor` | 1 | 6 / 0 | yes |
| `is_prime` | `more_itertools.recipes.is_prime` | 0 | 6 / 0 | yes |
| `running_mean` | `more_itertools.recipes.running_mean` | 2 | 4 / 2 | yes |
| `running_median` | `more_itertools.recipes.running_median` | 0 | 5 / 1 | yes |
| `running_min` | `more_itertools.recipes.running_min` | 0 | 5 / 1 | yes |
| `random_derangement` | `more_itertools.recipes.random_derangement` | 0 | 1 / 1 | no: unstable, both_error |
| `polynomial_derivative` | `more_itertools.recipes.polynomial_derivative` | 1 | 6 / 0 | yes |
| `evaluate_polynomial` | `more_itertools.recipes.polynomial_eval` | 1 | 5 / 1 | yes |
| `index_of_values` | `more_itertools.recipes.iter_index` | 2 | 6 / 0 | yes |

## Rejected tools

| Tool | Wraps | Last failed check | Error |
| --- | --- | --- | --- |
| `first` | `more_itertools.more.first` | static | line 3: no code at module level except imports, definitions and constants |
| `nth_or_last` | `more_itertools.more.nth_or_last` | static | line 5: no code at module level except imports, definitions and constants |
| `ilen` | `more_itertools.more.ilen` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `iterate` | `more_itertools.more.iterate` | static | line 3: no code at module level except imports, definitions and constants |
| `with_iter` | `more_itertools.more.with_iter` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: 'str' object does not support the context manager protocol"]. Use samples that are valid for the library. |
| `one` | `more_itertools.more.one` | runs | Input {"iterable": ["hello"], "too_long": null, "too_short": null}: the tool raised output is not JSON: hello, but the direct library call returned "hello" |
| `strictly_n` | `more_itertools.more.strictly_n` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `intersperse` | `more_itertools.more.intersperse` | spec | this parameter needs a snake_case name and a JSON type: {"name": "filler_element", "type": "any", "description": "The filler element to intersperse among the items in the iterable.", "required": true} |
| `unique_to_each` | `more_itertools.more.unique_to_each` | differential | Input {"iterables": ["mississippi", "missouri"]}: the tool raised ValidationError: 2 validation errors for unique_to_eachArguments iterables.0 Input should be a valid list [type=list_type, input_value='mississippi', inpu |
| `spy` | `more_itertools.more.spy` | static | line 4: no code at module level except imports, definitions and constants |
| `interleave` | `more_itertools.more.interleave` | spec | direct_call may not use ListComp: only calls, attributes, names, constants and simple conditions |
| `interleave_longest` | `more_itertools.more.interleave_longest` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `interleave_evenly` | `more_itertools.more.interleave_evenly` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `collapse` | `more_itertools.more.collapse` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `split_at` | `more_itertools.more.split_at` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `split_before` | `more_itertools.more.split_before` | static | do not use eval |
| `split_after` | `more_itertools.more.split_after` | static | do not use eval |
| `split_when` | `more_itertools.more.split_when` | spec | this parameter needs a snake_case name and a JSON type: {"name": "pred", "type": "function", "description": "A function that takes two arguments (successive elements of the iterable) and returns a boolean indicating whet |
| `padded` | `more_itertools.more.padded` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `stagger` | `more_itertools.more.stagger` | differential | Input {"fill_value": null, "iterable": [0, 1, 2, 3], "longest": false, "offsets": [-1, 0, 1]}: the tool raised ValueError: An error occurred while staggering the iterable: stagger() got multiple values for argument 'offs |
| `zip_offset` | `more_itertools.more.zip_offset` | differential | Input {"fill_value": null, "iterables": ["0123", "abcdef"], "longest": false, "offsets": [0, 1]}: the tool raised ValidationError: 2 validation errors for zip_offsetArguments iterables.0 Input should be a valid list [typ |
| `adjacent` | `more_itertools.more.adjacent` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: 'str' object is not callable"]. Use samples that are valid for the library. |
| `groupby_transform` | `more_itertools.more.groupby_transform` | spec | only 1 samples gave a result to compare; 2 are needed. Add valid samples with different inputs. |
| `count_cycle` | `more_itertools.more.count_cycle` | differential | Input {"iterable": ["A", "B"], "n": 3}: the tool returned [[0, "A"], [0, "B"]], but the direct library call returned [[0, "A"], [0, "B"], [1, "A"], [1, "B"], [2, "A"], [2, "B"]] Input {"iterable": [1, 2, 3], "n": 2}: the |
| `mark_ends` | `more_itertools.more.mark_ends` | differential | Input {"iterable": ["Single"]}: the tool returned [[false, true, "Single"]], but the direct library call returned [[true, true, "Single"]] |
| `locate` | `more_itertools.more.locate` | differential | Input {"iterable": [], "pred": "bool", "window_size": null}: the tool raised ValueError: pred must be a callable function, but the direct library call returned [] |
| `longest_common_prefix` | `more_itertools.more.longest_common_prefix` | static | line 4: no code at module level except imports, definitions and constants |
| `lstrip` | `more_itertools.more.lstrip` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `rstrip` | `more_itertools.more.rstrip` | static | line 3: no code at module level except imports, definitions and constants |
| `strip` | `more_itertools.more.strip` | spec | this parameter needs a snake_case name and a JSON type: {"name": "pred_function", "type": "function", "description": "A function that takes an item and returns a boolean indicating whether the item should be stripped.",  |
| `always_reversible` | `more_itertools.more.always_reversible` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `consecutive_groups` | `more_itertools.more.consecutive_groups` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `exactly_n` | `more_itertools.more.exactly_n` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `map_reduce` | `more_itertools.more.map_reduce` | differential | Input {"iterable": ["a", "b", "b", "c", "c", "c"], "keyfunc": "lambda x: x.upper()", "reducefunc": "sum", "valuefunc": "lambda x: 1"}: the direct library call raised TypeError: 'str' object is not callable, but the tool  |
| `rlocate` | `more_itertools.more.rlocate` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `replace` | `more_itertools.more.replace` | static | do not use eval |
| `set_partitions` | `more_itertools.more.set_partitions` | differential | Input {"iterable": ["a", "b", "c"], "k": 2}: the tool returned [], but the direct library call returned [[["a"], ["b", "c"]], [["a", "b"], ["c"]], [["b"], ["a", "c"]]] Input {"iterable": ["a", "b", "c"]}: the tool return |
| `only` | `more_itertools.more.only` | spec | this parameter needs a snake_case name and a JSON type: {"name": "default_value", "type": "any", "description": "The value to return if the iterable is empty.", "required": false, "default": null} |
| `ichunked` | `more_itertools.more.ichunked` | static | line 5: no code at module level except imports, definitions and constants |
| `iequals` | `more_itertools.more.iequals` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `filter_except` | `more_itertools.more.filter_except` | static | line 3: no code at module level except imports, definitions and constants |
| `map_except` | `more_itertools.more.map_except` | spec | direct_call may not use Starred: only calls, attributes, names, constants and simple conditions |
| `map_if` | `more_itertools.more.map_if` | static | do not use eval |
| `sample` | `more_itertools.more.sample` | runs | Input {"iterable": ["a", "b", "c"], "k": 2, "weights": [0.1, 0.2, 0.7]}: the tool raised output is not JSON: ac, but the direct library call returned ["a", "c"] Input {"iterable": [10, 20, 30], "k": 0}: the tool raised o |
| `is_sorted` | `more_itertools.more.is_sorted` | differential | Input {"iterable": [1, 2, 3, 4, 5], "key": "None", "reverse": false, "strict": false}: the direct library call raised TypeError: 'str' object is not callable, but the tool returned true Input {"iterable": [5, 4, 3, 2, 1] |
| `nth_product` | `more_itertools.more.nth_product` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['IndexError: ', 'IndexError: list index out of range']. Use samples that are valid for the library. |
| `nth_permutation` | `more_itertools.more.nth_permutation` | runs | Input {"index": 5, "iterable": ["g", "h", "i", "j", "k"], "r": 2}: the tool raised output is not JSON: hh, but the direct library call returned ["h", "i"] Input {"index": 0, "iterable": [], "r": 0}: the tool raised outpu |
| `nth_combination_with_replacement` | `more_itertools.more.nth_combination_with_replacement` | runs | Input {"index": 5, "iterable": [0, 1, 2, 3, 4], "r": 3}: the tool raised output is not JSON: 011, but the direct library call returned [0, 1, 1] Input {"index": 0, "iterable": ["a", "b", "c"], "r": 2}: the tool raised ou |
| `value_chain` | `more_itertools.more.value_chain` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `product_index` | `more_itertools.more.product_index` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `zip_broadcast` | `more_itertools.more.zip_broadcast` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['IndexError: list index out of range', "TypeError: 'NoneType' object is not iterable", 'TypeError: isinstance() arg 2 must be a type, a tuple o |
| `unique_in_window` | `more_itertools.more.unique_in_window` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `classify_unique` | `more_itertools.more.classify_unique` | spec | this parameter needs a snake_case name and a JSON type: {"name": "key_function", "type": "function", "description": "A function to extract a comparison key from each element. If None, the element itself is used.", "requi |
| `minmax` | `more_itertools.more.minmax` | spec | direct_call may not use Starred: only calls, attributes, names, constants and simple conditions |
| `constrained_batches` | `more_itertools.more.constrained_batches` | fastmcp | PydanticSchemaGenerationError: Unable to generate pydantic-core schema for typing.Iterator[typing.Tuple[typing.Any, ...]]. Set `arbitrary_types_allowed=True` in the model_config to ignore this error or implement `__get_p |
| `gray_product` | `more_itertools.more.gray_product` | differential | Input {"iterables": [["A", "B"], ["C", "D"], ["1", "2"]], "repeat": 1}: the tool returned [["A", "C", "1"], ["B", "C", "1"], ["B", "D", "1"], ["A", "D", "1"], ["A", "D", "2"], ["B", "D", "2"], ["B", "C", "2"], ["A", "C", |
| `partial_product` | `more_itertools.more.partial_product` | differential | Input {"iterables": [], "repeat": 1}: the direct library call raised IndexError: list index out of range, but the tool returned [] Input {"iterables": ["not an iterable"], "repeat": 1}: the direct library call raised Ind |
| `takewhile_inclusive` | `more_itertools.more.takewhile_inclusive` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `outer_product` | `more_itertools.more.outer_product` | static | do not use eval |
| `iter_suppress` | `more_itertools.more.iter_suppress` | differential | Input {"exceptions": ["IndexError", "KeyError", "TypeError"], "iterable": "iter([1, 2, 3])"}: the tool raised ValidationError: 3 validation errors for iter_suppressArguments exceptions.0 Input should be a subclass of Exc |
| `filter_map` | `more_itertools.more.filter_map` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `powerset_of_sets` | `more_itertools.more.powerset_of_sets` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: 'str' object is not callable"]. Use samples that are valid for the library. |
| `argmax` | `more_itertools.more.argmax` | static | line 5: no code at module level except imports, definitions and constants |
| `synchronized` | `more_itertools.more.synchronized` | fastmcp | PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema For further information visit https://errors.pydantic.dev/2.14/u/invalid-for-json-schema |
| `random_ordered_range` | `more_itertools.more.random_ordered_range` | differential | Input {"start": 1, "step": 1, "stop": 5}: the tool raised ValueError: Invalid input for range parameters., but the direct library call returned [3, 2, 4, 1] Input {"start": 0, "step": 1, "stop": 0}: the tool raised Value |
| `tabulate` | `more_itertools.recipes.tabulate` | static | the parameters must be exactly ['function', 'start'] |
| `tail` | `more_itertools.recipes.tail` | static | line 5: no code at module level except imports, definitions and constants |
| `nth` | `more_itertools.recipes.nth` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `all_equal` | `more_itertools.recipes.all_equal` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: 'str' object is not callable"]. Use samples that are valid for the library. |
| `quantify` | `more_itertools.recipes.quantify` | spec | this parameter needs a snake_case name and a JSON type: {"name": "predicate", "type": "function", "description": "A predicate function to apply to each item in the iterable. Defaults to the built-in `bool` function.", "r |
| `pad_none` | `more_itertools.recipes.pad_none` | runs | the check did not finish in 90 s |
| `dotproduct` | `more_itertools.recipes.dotproduct` | differential | Input {"vec1": [1, 2], "vec2": [3]}: the tool raised ValueError: Vectors must be of the same length., but the direct library call returned 3 |
| `flatten` | `more_itertools.recipes.flatten` | differential | Input {"list_of_lists": "not a list of lists"}: the tool raised ValidationError: 1 validation error for flattenArguments list_of_lists Input should be a valid list [type=list_type, input_value='not a list of lists', inpu |
| `repeatfunc` | `more_itertools.recipes.repeatfunc` | spec | direct_call may not use Starred: only calls, attributes, names, constants and simple conditions |
| `roundrobin` | `more_itertools.recipes.roundrobin` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `partition` | `more_itertools.recipes.partition` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ["TypeError: 'str' object is not callable"]. Use samples that are valid for the library. |
| `powerset` | `more_itertools.recipes.powerset` | static | line 4: no code at module level except imports, definitions and constants |
| `unique_everseen` | `more_itertools.recipes.unique_everseen` | spec | only 1 samples gave a result to compare; 2 are needed. Add valid samples with different inputs. |
| `unique` | `more_itertools.recipes.unique` | static | line 4: no code at module level except imports, definitions and constants |
| `iter_except` | `more_itertools.recipes.iter_except` | spec | the direct call failed on every sample, so nothing can be compared. Errors: ['TypeError: issubclass() arg 2 must be a class, a tuple of classes, or a union']. Use samples that are valid for the library. |
| `first_true` | `more_itertools.recipes.first_true` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `random_product` | `more_itertools.recipes.random_product` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `random_combination` | `more_itertools.recipes.random_combination` | static | line 4: no code at module level except imports, definitions and constants |
| `nth_combination` | `more_itertools.recipes.nth_combination` | runs | Input {"index": 0, "iterable": ["a", "b", "c", "d"], "r": 2}: the tool raised output is not JSON: dc, but the direct library call returned ["a", "b"] |
| `convolve_iterables` | `more_itertools.recipes.convolve` | differential | Input {"kernel": [], "signal": [1, 2, 3]}: the tool returned [], but the direct library call returned [0, 0, 0] |
| `prime_sieve` | `more_itertools.recipes.sieve` | differential | Input {"n": 1}: the tool raised ValueError: n must be an integer greater than or equal to 2, but the direct library call returned [] |
| `eulers_totient` | `more_itertools.recipes.totient` | differential | Input {"n": -5}: the tool raised ValueError: n must be a non-negative integer., but the direct library call returned -5 |
| `sum_of_squares` | `more_itertools.recipes.sum_of_squares` | spec | the reply must be a JSON object with parameters, direct_call and samples |
| `running_max` | `more_itertools.recipes.running_max` | differential | Input {"iterable": [4, 3, 7, 0, 8, 1, 6, 2, 9, 5], "maxlen": null}: the tool returned [], but the direct library call returned [4, 4, 7, 7, 8, 8, 8, 8, 9, 9] Input {"iterable": [4, 3, 7, 0, 8, 1, 6, 2, 9, 5], "maxlen": 3 |
| `running_statistics` | `more_itertools.recipes.running_statistics` | differential | Input {"iterable": [1, 2, 3, 4, 5], "maxlen": null}: the tool returned [{"maximum": 1, "mean": 1.0, "median": 1, "minimum": 1, "size": 1}, {"maximum": 2, "mean": 1.5, "median": 1.5, "minimum": 1, "size": 2}, {"maximum":  |
| `multinomial_coefficient` | `more_itertools.recipes.multinomial` | spec | direct_call may not use LtE: only calls, attributes, names, constants and simple conditions |
| `polynomial_from_roots` | `more_itertools.recipes.polynomial_from_roots` | spec | the reply must be a JSON object with parameters, direct_call and samples |

## Use

```sh
uv run python run_model.py <exercises> --mode tools --base-url <url> --model <model> -- toolsets/generated/more-itertools-qwen3-32b/run_server.sh
```
