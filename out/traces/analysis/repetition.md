# What repeats in the traces

Tokenizer: `Qwen/Qwen3-8B`, with its chat template. Savings are simulated on recorded runs; effects on accuracy are not measured.

## ToolGym chains, tools: toolgym-generated, long tasks

12 runs, 116 requests, 104 tool calls (8.7 per run). Prompt tokens: **320,987**. The model's replies: 6,898.

**Sent before:** 282,065 of 320,987 prompt tokens (88%) were already sent in an earlier request of the same run.

**Repeated calls:** 34 of 104 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 2.4 of the 6 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| older tool outputs | 136,031 | 42.4% |
| tool list | 125,141 | 39.0% |
| the model's earlier calls | 24,343 | 7.6% |
| newest tool output | 18,665 | 5.8% |
| system prompt and task | 15,995 | 5.0% |
| end of prompt (start of the model's reply) | 812 | 0.3% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 320,987 | 0% | 38,922 | 0% |
| Tool list: only the 5 tools a perfect search finds | 296,682 | 8% | 36,392 | 7% |
| Tool list: only the tools this run used (best case) | 252,784 | 21% | 31,840 | 18% |
| Old outputs: keep the newest 5 in full | 257,225 | 20% | 22,412 | 42% |
| Old outputs: keep the newest 3 in full | 223,627 | 30% | 22,011 | 43% |
| Old outputs: keep the newest 1 in full | 188,878 | 41% | 21,385 | 45% |
| Old outputs: replace exact duplicates | 319,389 | 0% | 38,488 | 1% |
| Arguments: refer to values from earlier calls | 316,660 | 1% | 37,541 | 4% |
| Together: 5 tools, newest 5 outputs, references | 228,593 | 29% | 18,501 | 52% |
| Prefix cache on the server (same context, less reading) | 38,922 | 88% | 38,922 | 0% |

### Repeated arguments

Arguments hold 2,294 tokens (each counted once). Of these, 1,853 are copies of earlier arguments or outputs, and 72 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `version` (1,217 tokens), `tag` (392 tokens), `name` (244 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| parse_tag > parse_tag > parse_tag > parse_tag | 7 | 4 | 21 | 31% | 1% |
| parse_tag > parse_tag > parse_tag | 9 | 4 | 18 | 33% | 1% |
| canonicalize_version_string > parse_version_string > parse_version_string | 8 | 6 | 16 | 7% | 0% |
| parse_tag > parse_tag | 15 | 4 | 15 | 24% | 0% |
| parse_version_string > canonicalize_version_string > parse_version_string > parse_version_string | 5 | 5 | 15 | 7% | 1% |
| parse_version_string > parse_version_string > canonicalize_version_string | 7 | 6 | 14 | 6% | 0% |
| parse_version_string > parse_version_string | 13 | 6 | 13 | 5% | -1% |
| parse_version_string > canonicalize_version_string > parse_version_string | 6 | 5 | 12 | 5% | -0% |

## ToolGym chains, tools: toolgym-generated, short tasks

33 runs, 109 requests, 76 tool calls (2.3 per run). Prompt tokens: **280,630**. The model's replies: 5,498.

**Sent before:** 178,709 of 280,630 prompt tokens (64%) were already sent in an earlier request of the same run.

**Repeated calls:** 3 of 76 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 2.0 of the 6 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 111,684 | 39.8% |
| older tool outputs | 89,473 | 31.9% |
| newest tool output | 60,533 | 21.6% |
| system prompt and task | 12,291 | 4.4% |
| the model's earlier calls | 5,886 | 2.1% |
| end of prompt (start of the model's reply) | 763 | 0.3% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 280,630 | 0% | 101,921 | 0% |
| Tool list: only the 5 tools a perfect search finds | 265,222 | 5% | 97,268 | 5% |
| Tool list: only the tools this run used (best case) | 215,921 | 23% | 82,333 | 19% |
| Old outputs: keep the newest 5 in full | 280,630 | 0% | 101,921 | 0% |
| Old outputs: keep the newest 3 in full | 271,734 | 3% | 93,025 | 9% |
| Old outputs: keep the newest 1 in full | 191,683 | 32% | 42,273 | 59% |
| Old outputs: replace exact duplicates | 280,553 | 0% | 101,864 | 0% |
| Arguments: refer to values from earlier calls | 280,100 | 0% | 101,444 | 0% |
| Together: 5 tools, newest 5 outputs, references | 264,692 | 6% | 96,791 | 5% |
| Prefix cache on the server (same context, less reading) | 101,921 | 64% | 101,921 | 0% |

### Repeated arguments

Arguments hold 1,250 tokens (each counted once). Of these, 709 are copies of earlier arguments or outputs, and 201 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `environment` (324 tokens), `tag` (215 tokens), `version` (170 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| generate_compatible_tags > parse_tag | 7 | 7 | 7 | 55% | 57% |
| canonicalize_package_name > canonicalize_package_name | 4 | 4 | 4 | 1% | -0% |
| canonicalize_package_name > canonicalize_package_name > check_normalized_package_name | 2 | 2 | 4 | 1% | -0% |
| canonicalize_version_string > parse_version_string > check_version_in_specifier_set | 2 | 2 | 4 | 2% | -0% |
| generate_compatible_tags > parse_tag > parse_tag | 2 | 2 | 4 | 27% | 20% |
| canonicalize_package_name > check_normalized_package_name | 3 | 3 | 3 | 1% | -0% |
| canonicalize_version_string > parse_version_string | 3 | 3 | 3 | 1% | -0% |
| generate_generic_tags > parse_tag | 3 | 3 | 3 | 1% | -0% |

## ToolGym chains, tools: toolgym-handmade, long tasks

8 runs, 88 requests, 80 tool calls (10.0 per run). Prompt tokens: **180,642**. The model's replies: 4,802.

**Sent before:** 161,798 of 180,642 prompt tokens (90%) were already sent in an earlier request of the same run.

**Repeated calls:** 3 of 80 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 6.6 of the 11 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 120,318 | 66.6% |
| system prompt and task | 26,686 | 14.8% |
| the model's earlier calls | 20,852 | 11.5% |
| older tool outputs | 10,517 | 5.8% |
| newest tool output | 1,653 | 0.9% |
| end of prompt (start of the model's reply) | 616 | 0.3% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 180,642 | 0% | 18,844 | 0% |
| Tool list: only the 5 tools a perfect search finds | 142,593 | 21% | 15,385 | 18% |
| Tool list: only the tools this run used (best case) | 142,593 | 21% | 15,385 | 18% |
| Old outputs: keep the newest 5 in full | 176,776 | 2% | 17,971 | 5% |
| Old outputs: keep the newest 3 in full | 174,930 | 3% | 17,910 | 5% |
| Old outputs: keep the newest 1 in full | 172,934 | 4% | 17,839 | 5% |
| Old outputs: replace exact duplicates | 180,615 | 0% | 18,826 | 0% |
| Arguments: refer to values from earlier calls | 180,086 | 0% | 18,728 | 1% |
| Together: 5 tools, newest 5 outputs, references | 138,171 | 24% | 14,396 | 24% |
| Prefix cache on the server (same context, less reading) | 18,844 | 90% | 18,844 | 0% |

### Repeated arguments

Arguments hold 1,326 tokens (each counted once). Of these, 268 are copies of earlier arguments or outputs, and 414 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `versions` (133 tokens), `version` (81 tokens), `specifier` (34 tokens), `version_b` (20 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| filter_versions > sort_versions | 4 | 3 | 4 | 4% | -1% |
| sort_versions > filter_versions | 3 | 3 | 3 | 2% | -1% |
| canonicalize_version > canonicalize_version | 2 | 2 | 2 | 1% | -1% |
| canonicalize_version > is_valid_version | 2 | 2 | 2 | 1% | -1% |
| sort_versions > version_satisfies | 2 | 2 | 2 | 1% | -1% |

## ToolGym chains, tools: toolgym-handmade, short tasks

15 runs, 75 requests, 60 tool calls (4.0 per run). Prompt tokens: **100,689**. The model's replies: 5,121.

**Sent before:** 78,212 of 100,689 prompt tokens (78%) were already sent in an earlier request of the same run.

**Repeated calls:** 1 of 60 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 3.3 of the 7 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 72,875 | 72.4% |
| system prompt and task | 14,365 | 14.3% |
| the model's earlier calls | 9,582 | 9.5% |
| older tool outputs | 2,070 | 2.1% |
| newest tool output | 1,272 | 1.3% |
| end of prompt (start of the model's reply) | 525 | 0.5% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 100,689 | 0% | 22,477 | 0% |
| Tool list: only the 5 tools a perfect search finds | 80,109 | 20% | 18,361 | 18% |
| Tool list: only the tools this run used (best case) | 65,429 | 35% | 15,425 | 31% |
| Old outputs: keep the newest 5 in full | 100,689 | 0% | 22,477 | 0% |
| Old outputs: keep the newest 3 in full | 100,384 | 0% | 22,172 | 1% |
| Old outputs: keep the newest 1 in full | 99,371 | 1% | 21,884 | 3% |
| Old outputs: replace exact duplicates | 100,621 | 0% | 22,409 | 0% |
| Arguments: refer to values from earlier calls | 99,943 | 1% | 22,089 | 2% |
| Together: 5 tools, newest 5 outputs, references | 79,363 | 21% | 17,973 | 20% |
| Prefix cache on the server (same context, less reading) | 22,477 | 78% | 22,477 | 0% |

### Repeated arguments

Arguments hold 1,857 tokens (each counted once). Of these, 524 are copies of earlier arguments or outputs, and 818 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `versions` (484 tokens), `version` (40 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| sort_versions > filter_versions | 6 | 6 | 6 | 6% | -2% |
| sort_versions > filter_versions > sort_versions | 3 | 3 | 6 | 8% | 1% |
| sort_versions > sort_versions | 4 | 4 | 4 | 4% | -1% |
| filter_versions > sort_versions | 3 | 3 | 3 | 3% | -1% |
| canonicalize_name > is_valid_specifier | 2 | 2 | 2 | 2% | -1% |

## known-good, long tasks

20 runs, 362 requests, 342 tool calls (17.1 per run). Prompt tokens: **1,392,571**. The model's replies: 24,459.

**Sent before:** 1,302,185 of 1,392,571 prompt tokens (94%) were already sent in an earlier request of the same run.

**Repeated calls:** 7 of 342 calls had the same tool and arguments as an earlier call of the same run.

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

## qwen3-8b, tools: generated-coder, tool choice: auto, short tasks

222 runs, 317 requests, 123 tool calls (0.6 per run). Prompt tokens: **1,285,353**. The model's replies: 7,787.

Our count against the server's: 0.00% apart over 317 requests.

**Sent before:** 383,359 of 1,285,353 prompt tokens (30%) were already sent in an earlier request of the same run.

**Tools:** each run used 0.4 of the 22 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 1,241,055 | 96.6% |
| system prompt and task | 34,881 | 2.7% |
| the model's earlier calls | 6,150 | 0.5% |
| end of prompt (start of the model's reply) | 2,219 | 0.2% |
| newest tool output | 732 | 0.1% |
| older tool outputs | 316 | 0.0% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 1,285,353 | 0% | 901,994 | 0% |
| Tool list: only the 5 tools a perfect search finds | 364,527 | 72% | 256,401 | 72% |
| Tool list: only the tools this run used (best case) | 99,704 | 92% | 59,670 | 93% |
| Old outputs: keep the newest 5 in full | 1,285,353 | 0% | 901,994 | 0% |
| Old outputs: keep the newest 3 in full | 1,285,353 | 0% | 901,994 | 0% |
| Old outputs: keep the newest 1 in full | 1,285,255 | 0% | 901,896 | 0% |
| Old outputs: replace exact duplicates | 1,285,353 | 0% | 901,994 | 0% |
| Arguments: refer to values from earlier calls | 1,285,316 | 0% | 901,957 | 0% |
| Together: 5 tools, newest 5 outputs, references | 364,490 | 72% | 256,364 | 72% |
| Prefix cache on the server (same context, less reading) | 901,994 | 30% | 901,994 | 0% |

### Repeated arguments

Arguments hold 1,997 tokens (each counted once). Of these, 165 are copies of earlier arguments or outputs, and 860 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `specifier_set` (154 tokens), `version` (11 tokens).

## qwen3-8b, tools: generated-coder-60, tool choice: auto, short tasks

222 runs, 397 requests, 212 tool calls (1.0 per run). Prompt tokens: **2,009,249**. The model's replies: 11,311.

Our count against the server's: 0.00% apart over 397 requests.

**Sent before:** 881,383 of 2,009,249 prompt tokens (44%) were already sent in an earlier request of the same run.

**Repeated calls:** 3 of 212 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 0.7 of the 29 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 1,948,476 | 97.0% |
| system prompt and task | 44,151 | 2.2% |
| the model's earlier calls | 11,084 | 0.6% |
| end of prompt (start of the model's reply) | 2,779 | 0.1% |
| newest tool output | 1,924 | 0.1% |
| older tool outputs | 835 | 0.0% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 2,009,249 | 0% | 1,127,866 | 0% |
| Tool list: only the 5 tools a perfect search finds | 384,891 | 81% | 218,681 | 81% |
| Tool list: only the tools this run used (best case) | 153,086 | 92% | 82,344 | 93% |
| Old outputs: keep the newest 5 in full | 2,009,228 | 0% | 1,127,845 | 0% |
| Old outputs: keep the newest 3 in full | 2,009,158 | 0% | 1,127,796 | 0% |
| Old outputs: keep the newest 1 in full | 2,008,848 | 0% | 1,127,619 | 0% |
| Old outputs: replace exact duplicates | 2,009,149 | 0% | 1,127,785 | 0% |
| Arguments: refer to values from earlier calls | 2,009,152 | 0% | 1,127,783 | 0% |
| Together: 5 tools, newest 5 outputs, references | 384,773 | 81% | 218,577 | 81% |
| Prefix cache on the server (same context, less reading) | 1,127,866 | 44% | 1,127,866 | 0% |

### Repeated arguments

Arguments hold 3,188 tokens (each counted once). Of these, 299 are copies of earlier arguments or outputs, and 1,467 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `specifier_set` (232 tokens), `version` (67 tokens).

## qwen3-8b, tools: traces, tool choice: always, long tasks

20 runs, 502 requests, 502 tool calls (25.1 per run). Prompt tokens: **2,277,489**. The model's replies: 27,921.

Our count against the server's: 0.00% apart over 502 requests.

**Sent before:** 2,175,202 of 2,277,489 prompt tokens (96%) were already sent in an earlier request of the same run.

**Repeated calls:** 250 of 502 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 2.9 of the 22 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 1,371,464 | 60.2% |
| the model's earlier calls | 519,206 | 22.8% |
| system prompt and task | 238,257 | 10.5% |
| older tool outputs | 137,466 | 6.0% |
| newest tool output | 7,582 | 0.3% |
| end of prompt (start of the model's reply) | 3,514 | 0.2% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 2,277,489 | 0% | 102,287 | 0% |
| Tool list: only the 5 tools a perfect search finds | 1,266,486 | 44% | 61,695 | 40% |
| Tool list: only the tools this run used (best case) | 1,155,671 | 49% | 57,338 | 44% |
| Old outputs: keep the newest 5 in full | 2,212,509 | 3% | 99,081 | 3% |
| Old outputs: keep the newest 3 in full | 2,205,613 | 3% | 98,752 | 3% |
| Old outputs: keep the newest 1 in full | 2,198,152 | 3% | 98,458 | 4% |
| Old outputs: replace exact duplicates | 2,260,551 | 1% | 101,144 | 1% |
| Arguments: refer to values from earlier calls | 2,166,290 | 5% | 95,764 | 6% |
| Together: 5 tools, newest 5 outputs, references | 1,090,307 | 52% | 51,966 | 49% |
| Prefix cache on the server (same context, less reading) | 102,287 | 96% | 102,287 | 0% |

### Repeated arguments

Arguments hold 16,239 tokens (each counted once). Of these, 10,603 are copies of earlier arguments or outputs, and 1,150 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `environment` (4,509 tokens), `versions` (3,174 tokens), `marker` (2,067 tokens), `specifier` (732 tokens), `version` (121 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| sort_versions > sort_versions > sort_versions > sort_versions | 12 | 2 | 36 | 9% | 3% |
| sort_versions > sort_versions > sort_versions | 16 | 2 | 32 | 8% | 2% |
| sort_versions > sort_versions | 27 | 2 | 27 | 7% | 1% |
| parse_requirement > evaluate_marker | 9 | 4 | 9 | 1% | 0% |
| parse_requirement > evaluate_marker > version_satisfies > version_satisfies | 2 | 2 | 6 | 1% | 0% |
| filter_versions > submit_answer | 5 | 5 | 5 | 1% | -0% |
| filter_versions > sort_versions | 4 | 4 | 4 | 0% | -0% |
| filter_versions > version_satisfies | 4 | 1 | 4 | 1% | 0% |

## qwen3-8b, tools: traces, tool choice: auto, long tasks

20 runs, 31 requests, 49 tool calls (2.5 per run). Prompt tokens: **102,797**. The model's replies: 4,557.

Our count against the server's: 0.00% apart over 31 requests.

**Sent before:** 36,310 of 102,797 prompt tokens (35%) were already sent in an earlier request of the same run.

**Repeated calls:** 4 of 49 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 0.7 of the 21 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 82,429 | 80.2% |
| system prompt and task | 13,931 | 13.6% |
| the model's earlier calls | 3,756 | 3.7% |
| older tool outputs | 1,389 | 1.4% |
| newest tool output | 1,075 | 1.0% |
| end of prompt (start of the model's reply) | 217 | 0.2% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 102,797 | 0% | 66,487 | 0% |
| Tool list: only the 5 tools a perfect search finds | 41,059 | 60% | 26,085 | 61% |
| Tool list: only the tools this run used (best case) | 28,272 | 72% | 15,851 | 76% |
| Old outputs: keep the newest 5 in full | 102,267 | 1% | 66,250 | 0% |
| Old outputs: keep the newest 3 in full | 102,087 | 1% | 66,195 | 0% |
| Old outputs: keep the newest 1 in full | 101,972 | 1% | 66,153 | 1% |
| Old outputs: replace exact duplicates | 102,797 | 0% | 66,487 | 0% |
| Arguments: refer to values from earlier calls | 102,593 | 0% | 66,371 | 0% |
| Together: 5 tools, newest 5 outputs, references | 40,325 | 61% | 25,732 | 61% |
| Prefix cache on the server (same context, less reading) | 66,487 | 35% | 66,487 | 0% |

### Repeated arguments

Arguments hold 1,134 tokens (each counted once). Of these, 300 are copies of earlier arguments or outputs, and 273 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `environment` (120 tokens), `specifier` (101 tokens), `marker` (69 tokens), `version` (10 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| parse_requirement > evaluate_marker | 2 | 1 | 2 | -0% | 0% |

## qwen3-8b, tools: traces, tool choice: auto, short tasks

222 runs, 448 requests, 226 tool calls (1.0 per run). Prompt tokens: **1,257,255**. The model's replies: 8,960.

Our count against the server's: 0.00% apart over 448 requests.

**Sent before:** 627,635 of 1,257,255 prompt tokens (50%) were already sent in an earlier request of the same run.

**Tools:** each run used 1.0 of the 21 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 1,191,232 | 94.7% |
| system prompt and task | 49,351 | 3.9% |
| the model's earlier calls | 9,814 | 0.8% |
| newest tool output | 3,639 | 0.3% |
| end of prompt (start of the model's reply) | 3,136 | 0.2% |
| older tool outputs | 83 | 0.0% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 1,257,255 | 0% | 629,620 | 0% |
| Tool list: only the 5 tools a perfect search finds | 346,343 | 72% | 178,266 | 72% |
| Tool list: only the tools this run used (best case) | 160,241 | 87% | 85,813 | 86% |
| Old outputs: keep the newest 5 in full | 1,257,255 | 0% | 629,620 | 0% |
| Old outputs: keep the newest 3 in full | 1,257,255 | 0% | 629,620 | 0% |
| Old outputs: keep the newest 1 in full | 1,257,208 | 0% | 629,573 | 0% |
| Old outputs: replace exact duplicates | 1,257,255 | 0% | 629,620 | 0% |
| Arguments: refer to values from earlier calls | 1,257,248 | 0% | 629,613 | 0% |
| Together: 5 tools, newest 5 outputs, references | 346,336 | 72% | 178,259 | 72% |
| Prefix cache on the server (same context, less reading) | 629,620 | 50% | 629,620 | 0% |

### Repeated arguments

Arguments hold 3,152 tokens (each counted once). Of these, 23 are copies of earlier arguments or outputs, and 2,168 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `specifier` (23 tokens).

## qwen3-8b, tools: traces, tool choice: first, long tasks

20 runs, 126 requests, 106 tool calls (5.3 per run). Prompt tokens: **425,668**. The model's replies: 6,248.

Our count against the server's: 0.00% apart over 126 requests.

**Sent before:** 353,731 of 425,668 prompt tokens (83%) were already sent in an earlier request of the same run.

**Repeated calls:** 5 of 106 calls had the same tool and arguments as an earlier call of the same run.

**Tools:** each run used 1.6 of the 21 tools offered, on average.

### What the prompts consist of

| Part | Tokens, all requests | Share |
| --- | --- | --- |
| tool list | 335,034 | 78.7% |
| system prompt and task | 57,660 | 13.5% |
| the model's earlier calls | 19,841 | 4.7% |
| older tool outputs | 8,692 | 2.0% |
| newest tool output | 3,559 | 0.8% |
| end of prompt (start of the model's reply) | 882 | 0.2% |

### What each idea would save (simulated)

| Idea | All requests | Saved | Final context | Saved |
| --- | --- | --- | --- | --- |
| Nothing changed | 425,668 | 0% | 71,937 | 0% |
| Tool list: only the 5 tools a perfect search finds | 174,612 | 59% | 32,097 | 55% |
| Tool list: only the tools this run used (best case) | 132,079 | 69% | 25,100 | 65% |
| Old outputs: keep the newest 5 in full | 424,710 | 0% | 71,376 | 1% |
| Old outputs: keep the newest 3 in full | 422,604 | 1% | 70,718 | 2% |
| Old outputs: keep the newest 1 in full | 419,427 | 1% | 70,288 | 2% |
| Old outputs: replace exact duplicates | 425,668 | 0% | 71,937 | 0% |
| Arguments: refer to values from earlier calls | 424,698 | 0% | 71,468 | 1% |
| Together: 5 tools, newest 5 outputs, references | 172,684 | 59% | 31,067 | 57% |
| Prefix cache on the server (same context, less reading) | 71,937 | 83% | 71,937 | 0% |

### Repeated arguments

Arguments hold 2,828 tokens (each counted once). Of these, 813 are copies of earlier arguments or outputs, and 1,057 are copies from the task. Only values of 8+ tokens count.

Most copied arguments: `environment` (520 tokens), `marker` (252 tokens), `versions` (41 tokens).

### Same call sequences, if one bigger tool did them

Only workflows: each step after the first uses an earlier step's output. The rows overlap, so do not add them up. The count includes the new tool's line in the tool list, and the inputs the bigger tool still needs.

| Sequence | Times | Runs | Calls saved | Prompt tokens saved | Final context saved |
| --- | --- | --- | --- | --- | --- |
| parse_requirement > evaluate_marker | 3 | 2 | 3 | 2% | -0% |
