# ToolGym types for more-itertools-qwen3-32b

Types proposed by `qwen3-32b`, then checked by 421 tool calls. A claim stands if at least 60% of its test calls work.

| | Count |
| --- | --- |
| Tools exported | 50 |
| Shared types proposed / kept | 2 / 2 |
| Parameters with a shared type: proposed / kept | 5 / 3 |
| Parameter claims tested / withdrawn | 5 / 2 |
| Output claims / kept | 22 / 19 |
| Data-flow links between tools | 21, over 21 tool pairs |
| Tools with no link | 30 |

## Types

| Type | Examples | Parameters |
| --- | --- | --- |
| `ListArray` | 4 | `sort_together.iterables` |
| `Matrix` | 6 | `transpose_matrix.matrix`, `reshape_matrix.matrix` |

## Withdrawn parameter claims

| Parameter | Proposed type | Pairs that work |
| --- | --- | --- |
| `matrix_multiply.m1` | `Matrix` | 5 of 6 |
| `matrix_multiply.m2` | `Matrix` | 4 of 6 |

## Output claims

| Tool | Claim | Worked | Kept |
| --- | --- | --- | --- |
| `chunked` | ListArray | 4 of 4 | yes |
| `distinct_permutations` | ListArray | 3 of 4 | yes |
| `windowed` | ListArray | 3 of 4 | yes |
| `split_into` | ListArray | 4 of 4 | yes |
| `distribute` | ListArray | 4 of 4 | yes |
| `sort_together` | ListArray | 4 of 4 | yes |
| `divide` | ListArray | 4 of 4 | yes |
| `circular_shifts` | ListArray | 4 of 4 | yes |
| `partitions` | ListArray | 4 of 4 | yes |
| `distinct_combinations` | ListArray | 4 of 4 | yes |
| `chunked_even` | ListArray | 4 of 4 | yes |
| `nth_prime` | Prime | 0 of 0 | no: no parameter has this type |
| `concurrent_tee` | ListArray | 4 of 4 | yes |
| `pairwise` | ListArray | 4 of 4 | yes |
| `grouper` | ListArray | 3 of 3 | yes |
| `sliding_window` | ListArray | 4 of 4 | yes |
| `triplewise` | ListArray | 4 of 4 | yes |
| `subslices` | ListArray | 4 of 4 | yes |
| `transpose_matrix` | Matrix | 8 of 8 | yes |
| `reshape_matrix` | Matrix | 4 of 8 | no |
| `matrix_multiply` | Matrix | 8 of 8 | yes |
| `random_derangement` | Derangement | 0 of 0 | no: no parameter has this type |

## Links

- `chunked` → `sort_together` (direct)
- `chunked_even` → `sort_together` (direct)
- `circular_shifts` → `sort_together` (direct)
- `concurrent_tee` → `sort_together` (direct)
- `distinct_combinations` → `sort_together` (direct)
- `distinct_permutations` → `sort_together` (direct)
- `distribute` → `sort_together` (direct)
- `divide` → `sort_together` (direct)
- `grouper` → `sort_together` (direct)
- `matrix_multiply` → `reshape_matrix` (direct)
- `matrix_multiply` → `transpose_matrix` (direct)
- `pairwise` → `sort_together` (direct)
- `partitions` → `sort_together` (direct)
- `sliding_window` → `sort_together` (direct)
- `sort_together` → `sort_together` (direct)
- `split_into` → `sort_together` (direct)
- `subslices` → `sort_together` (direct)
- `transpose_matrix` → `reshape_matrix` (direct)
- `transpose_matrix` → `transpose_matrix` (direct)
- `triplewise` → `sort_together` (direct)
- `windowed` → `sort_together` (direct)
