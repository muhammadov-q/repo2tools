"""repo2tools: turn a Python repository into tools an AI model can call, and measure how well models use them.

Sub-packages:
    synthesis   repository link -> checked tools (API scan, usage scan, generation, sandboxed checks, repairs)
    evaluation  exercises with known answers, reference calls, model runs
    traces      one format for agent traces, and what repeats in them
    toolgym     types, catalog folders and runs for ToolGym

Everything is used from a checkout of the repository: tool sets, results and caches live next to the code.
"""

__version__ = "0.2.0"
