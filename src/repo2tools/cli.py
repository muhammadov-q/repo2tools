"""The `repo2tools` command: one entry point for every step.

    uv run repo2tools <command> [arguments]
    uv run repo2tools <command> --help

Each command is the `main()` of one module and is imported only when it is used, so `repo2tools --help` stays
fast and a command never needs the optional dependencies of another.
"""

import importlib
import sys

from repo2tools import __version__

# command -> (module, one line for --help), grouped as in the README
COMMANDS: dict[str, dict[str, tuple[str, str]]] = {
    "Synthesis: repository -> tools": {
        "generate": ("repo2tools.synthesis.pipeline", "repository link -> checked tools, in their own environment and sandbox"),
        "scrape": ("repo2tools.synthesis.scrape", "list a package's public API without importing it"),
        "usage": ("repo2tools.synthesis.usage", "count how a repository's own docs and tests use its API"),
        "repair-chains": ("repo2tools.synthesis.chain_repair", "rewrite tools whose output no other tool accepts"),
        "usability": ("repo2tools.synthesis.usability", "let a small model try each tool; rewrite unclear names and descriptions"),
    },
    "Evaluation: exercises and model runs": {
        "make-exercises": ("repo2tools.evaluation.packaging_exercises", "build exercises with known answers from packaging's test cases"),
        "check-tools": ("repo2tools.evaluation.reference_calls", "replay every known-good solution through a tool server"),
        "run-model": ("repo2tools.evaluation.run_model", "let a model solve the exercises, with or without tools"),
        "compare-runs": ("repo2tools.evaluation.compare_runs", "put two model runs side by side"),
        "handover": ("repo2tools.evaluation.handover", "build a self-contained zip of exercises and tools"),
    },
    "Traces": {
        "reference-traces": ("repo2tools.traces.reference", "known-good solutions as traces"),
        "analyze-traces": ("repo2tools.traces.analyze", "what repeats in traces, and what compression would save"),
    },
    "ToolGym": {
        "toolgym-types": ("repo2tools.toolgym.type_inference", "ToolGym types for a generated tool set, checked by running the tools"),
        "toolgym-export": ("repo2tools.toolgym.catalog_export", "write the hand-made tools into a ToolGym catalog"),
        "toolgym-local": ("repo2tools.toolgym.local", "run ToolGym's chain check and pipeline on tools served from this computer"),
        "toolgym-traces": ("repo2tools.toolgym.traces", "ToolGym run results as traces"),
        "toolgym-exercises": ("repo2tools.toolgym.exercises", "ToolGym's synthetic tasks as exercises with known answers"),
        "toolgym-chains": ("repo2tools.toolgym.catalog_chains", "summarise ToolGym's chain listings"),
        "toolgym-edges": ("repo2tools.toolgym.exercise_edges", "check that the links the exercises need are in ToolGym's graph"),
    },
}
MODULES = {name: module for group in COMMANDS.values() for name, (module, _) in group.items()}


def usage() -> str:
    lines = ["usage: repo2tools <command> [arguments]", "       repo2tools <command> --help", ""]
    for title, group in COMMANDS.items():
        lines.append(f"{title}:")
        lines += [f"  {name:<18} {text}" for name, (_, text) in group.items()]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(usage())
        return
    if argv[0] == "--version":
        print(f"repo2tools {__version__}")
        return
    command, rest = argv[0], argv[1:]
    if command not in MODULES:
        sys.exit(f"repo2tools: unknown command {command!r}\n\n{usage()}")
    sys.argv = [f"repo2tools {command}", *rest]  # the module's own argument parser reads the rest
    importlib.import_module(MODULES[command]).main()


if __name__ == "__main__":
    main()
