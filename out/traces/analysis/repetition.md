# What repeats in the traces

Tokenizer: `Qwen/Qwen3-8B`, with its chat template. Savings are simulated on recorded runs; effects on accuracy are not measured.

## known-good, long tasks

20 runs, 362 requests, 342 tool calls (17.1 per run). Prompt tokens: **1,392,571**. The model's replies: 24,459.

**Sent before:** 1,302,185 of 1,392,571 prompt tokens (94%) were already sent in an earlier request of the same run.

**Tools:** each run used 4.6 of the 21 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 962,558 | 69.1% |
| the model's earlier calls | 182,893 | 13.1% |
| system prompt and task | 166,167 | 11.9% |
| older tool outputs | 70,266 | 5.0% |
| newest tool output | 8,153 | 0.6% |
| end of prompt (start of the model's reply) | 2,534 | 0.2% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 1,392,571 | 0% | 90,386 | 0% |
| Tool list: only the 5 tools a perfect search finds | 703,884 | 49% | 52,364 | 42% |
| Tool list: only the tools this run used (best case) | 692,226 | 50% | 51,668 | 43% |
| Old outputs: keep the newest 5 in full | 1,366,074 | 2% | 86,729 | 4% |
| Old outputs: keep the newest 3 in full | 1,358,038 | 2% | 86,199 | 5% |
| Old outputs: keep the newest 1 in full | 1,348,835 | 3% | 85,533 | 5% |
| Old outputs: replace exact duplicates | 1,392,571 | 0% | 90,386 | 0% |
| Arguments: refer to values from earlier calls | 1,374,853 | 1% | 87,935 | 3% |
| Together: 5 tools, newest 5 outputs, references | 659,669 | 53% | 46,256 | 49% |
| Prefix cache on the server (same context, less reading) | 90,386 | 94% | 90,386 | 0% |

### Repeated arguments

Arguments hold 9,644 tokens (each counted once). Of these, 3,851 are copies of earlier arguments or outputs, and 1,638 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `environment` (1,686 tokens), `versions` (1,180 tokens), `marker` (545 tokens), `specifier` (440 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| filter_versions > sort_versions | 79 | 20 | 79 | 22% | 2% |
| parse_requirement > filter_versions > sort_versions | 32 | 17 | 64 | 17% | 2% |
| parse_requirement > canonicalize_name > filter_versions > sort_versions | 18 | 13 | 54 | 15% | 2% |
| parse_requirement > evaluate_marker | 49 | 18 | 49 | 13% | 2% |
| parse_requirement > canonicalize_name > filter_versions | 18 | 13 | 36 | 9% | 0% |
| parse_requirement > evaluate_marker > filter_versions > sort_versions | 11 | 8 | 33 | 9% | 1% |
| parse_requirement > filter_versions | 32 | 17 | 32 | 7% | -0% |
| parse_requirement > canonicalize_name | 22 | 13 | 22 | 5% | -0% |

## known-good, short tasks

222 runs, 444 requests, 222 tool calls (1.0 per run). Prompt tokens: **1,245,580**. The model's replies: 12,584.

**Sent before:** 616,331 of 1,245,580 prompt tokens (49%) were already sent in an earlier request of the same run.

**Tools:** each run used 1.0 of the 21 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 1,180,596 | 94.8% |
| system prompt and task | 48,958 | 3.9% |
| the model's earlier calls | 9,300 | 0.7% |
| newest tool output | 3,618 | 0.3% |
| end of prompt (start of the model's reply) | 3,108 | 0.2% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 1,245,580 | 0% | 629,249 | 0% |
| Tool list: only the 5 tools a perfect search finds | 343,040 | 72% | 177,979 | 72% |
| Tool list: only the tools this run used (best case) | 157,232 | 87% | 85,075 | 86% |
| Old outputs: keep the newest 5 in full | 1,245,580 | 0% | 629,249 | 0% |
| Old outputs: keep the newest 3 in full | 1,245,580 | 0% | 629,249 | 0% |
| Old outputs: keep the newest 1 in full | 1,245,580 | 0% | 629,249 | 0% |
| Old outputs: replace exact duplicates | 1,245,580 | 0% | 629,249 | 0% |
| Arguments: refer to values from earlier calls | 1,245,580 | 0% | 629,249 | 0% |
| Together: 5 tools, newest 5 outputs, references | 343,040 | 72% | 177,979 | 72% |
| Prefix cache on the server (same context, less reading) | 629,249 | 49% | 629,249 | 0% |

### Repeated arguments

Arguments hold 3,086 tokens (each counted once). Of these, 0 are copies of earlier arguments or outputs, and 2,213 are copies from the task. Only values of 8+ tokens count.
