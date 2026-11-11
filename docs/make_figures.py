"""Draw the README figures, in a light and a dark version each.

    uv run --with matplotlib python docs/make_figures.py

pipeline-*.png  the three stages of the project
results-*.png   (a) exercises solved per tool set, from out/runs/;
                (b) what the prompt tokens of a run consist of, from out/traces/analysis/repetition.json

All numbers are read from result files in this repository, so the figures can be rebuilt.
"""

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
THEMES = {
    "light": {"surface": "#ffffff", "ink": "#0b0b0b", "muted": "#52514e", "line": "#c9c8c2", "neutral": "#f3f2ee",
              "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]},
    "dark": {"surface": "#0d1117", "ink": "#f0efec", "muted": "#c3c2b7", "line": "#4a4a46", "neutral": "#1c2128",
             "series": ["#3987e5", "#d95926", "#199e70", "#c98500"]},
}
plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def mix(color: str, surface: str, share: float) -> tuple:
    a, b = matplotlib.colors.to_rgb(color), matplotlib.colors.to_rgb(surface)
    return tuple(share * x + (1 - share) * y for x, y in zip(a, b))


# --- pipeline diagram ---------------------------------------------------------------------------

KINDS = {"llm": (0, "LLM"), "run": (2, "CHECKED BY RUNNING"), "ext": (1, "EXTERNAL"), "data": (None, "DATA")}


def pipeline(theme: dict, path: pathlib.Path) -> None:
    fig = plt.figure(figsize=(13, 6.9), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 130)
    ax.set_ylim(0, 69)
    ax.axis("off")
    fig.patch.set_facecolor(theme["surface"])

    def box(x, y, w, h, kind, title, text):
        slot, tag = KINDS[kind]
        color = theme["line"] if slot is None else theme["series"][slot]
        fill = theme["neutral"] if slot is None else mix(color, theme["surface"], 0.13)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.1", fc=fill, ec=color, lw=1.6))
        ax.text(x + 1.3, y + h - 1.9, tag, fontsize=7.2, color=theme["muted"], va="center")
        ax.text(x + 1.3, y + h - 4.6, title, fontsize=12.2, fontweight="bold", color=theme["ink"], va="center")
        ax.text(x + 1.3, y + h - 6.7, text, fontsize=9.4, color=theme["muted"], va="top", linespacing=1.35)
        return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}

    def arrow(a, b, **kwargs):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, lw=1.5, color=theme["muted"], shrinkA=1.5, shrinkB=1.5, **kwargs))

    def lane(x, y, number, title, text):
        label = ax.text(x, y, f"{number}   {title}", fontsize=10.5, fontweight="bold", color=theme["ink"], va="center")
        fig.canvas.draw()
        right = ax.transData.inverted().transform(label.get_window_extent().get_points())[1][0]
        ax.text(right + 1.6, y, text, fontsize=9.6, color=theme["muted"], va="center")

    # 1: synthesize
    lane(2, 66.3, "1", "SYNTHESIZE", "a repository link becomes tools that are checked against the library itself")
    w, gap, y, h = 21, 5.25, 49.5, 13
    xs = [2 + i * (w + gap) for i in range(5)]
    top = [
        box(xs[0], y, w, h, "data", "Repository URL", "cloned at a recorded commit;\nnever built or installed"),
        box(xs[1], y, w, h, "data", "Scrape public API", "static AST scan:\nno repository code runs"),
        box(xs[2], y, w, h, "llm", "Propose tools", "picks functions by full path;\nunknown paths are dropped"),
        box(xs[3], y, w, h, "llm", "Write test, then tool", "two separate requests: the\ncode never sees the test"),
        box(xs[4], y, w, h, "run", "Verify in sandbox", "loads · MCP accepts it · runs ·\nmatches a direct library call"),
    ]
    for a, b in zip(top, top[1:]):
        arrow(a["r"], b["l"])
    arrow((top[4]["t"][0] - 4, y + h), (top[3]["t"][0] + 4, y + h), connectionstyle="arc3,rad=0.3")
    ax.text((top[3]["t"][0] + top[4]["t"][0]) / 2, y + h + 4.6, "on failure the error goes back: up to 3 repair rounds", fontsize=8.8, color=theme["muted"], ha="center", va="center")

    # the accepted tools feed stages 2 and 3
    tools = box(2, 4, 17, 33, "data", "MCP tool set", "one file per tool,\nserved in its own\nenvironment and\nsandbox")
    gutter = 43.5
    ax.plot([top[4]["b"][0], top[4]["b"][0], tools["t"][0]], [y, gutter, gutter], color=theme["muted"], lw=1.5, solid_capstyle="round")
    arrow((tools["t"][0], gutter), tools["t"])
    ax.text(top[4]["b"][0] - 1.5, gutter + 1.5, "accepted tools", fontsize=8.8, color=theme["muted"], ha="right", va="center")

    cw, cgap, x0, rh = 18.5, 3.5, 23.5, 13
    cx = [x0 + i * (cw + cgap) for i in range(4)]
    # 2: chain
    yb = 24
    lane(x0, yb + rh + 2.2, "2", "CHAIN", "which tool's output can feed which tool's input")
    row = [
        box(cx[0], yb, cw, rh, "llm", "Propose types", "names the kinds of values,\ne.g. VersionString"),
        box(cx[1], yb, cw, rh, "run", "Verify types", "values swapped between\nparameters; outputs fed\nto the tools that take them"),
        box(cx[2], yb, cw, rh, "ext", "ToolGym", "signature graph, live chain\ncheck, generation pipeline"),
        box(cx[3], yb, cw, rh, "data", "Synthetic traces", "tasks with a validated\nchain of tool calls"),
    ]
    arrow((19, yb + rh / 2), row[0]["l"])
    for a, b in zip(row, row[1:]):
        arrow(a["r"], b["l"])
    # 3: measure
    yc = 4
    lane(x0, yc + rh + 2.2, "3", "MEASURE", "can a model use the tools, and what does a run cost in tokens")
    evaluate = box(cx[0], yc, 3 * cw + 2 * cgap, rh, "ext", "Model with and without the tools",
                   "242 exercises whose answers come from the library's own test suite; an open model served with vLLM;\noptionally forced to call tools. Scoring uses only the answer, so any tool set can be compared.")
    model_traces = box(cx[3], yc, cw, rh, "data", "Model traces", "every request, with full\nmessages and token counts")
    arrow((19, yc + rh / 2), evaluate["l"])
    arrow(evaluate["r"], model_traces["l"])
    box(111.5, 4, 16.5, 33, "run", "Trace analysis", "what repeats in a\nrun, and how many\ntokens each\ncompression idea\nwould save\n\ntoken counts match\nthe server's exactly")
    arrow(row[3]["r"], (111.5, yb + rh / 2))
    arrow(model_traces["r"], (111.5, yc + rh / 2))

    # legend: identity is carried by the tag in each box as well as by color
    for i, (kind, label) in enumerate((("llm", "written by an LLM"), ("run", "checked by running code"), ("ext", "external system"), ("data", "data or static step"))):
        slot, tag = KINDS[kind]
        color = theme["line"] if slot is None else theme["series"][slot]
        fill = theme["neutral"] if slot is None else mix(color, theme["surface"], 0.13)
        lx = 23.5 + i * 22
        ax.add_patch(FancyBboxPatch((lx, 0.9), 2.2, 1.4, boxstyle="round,pad=0,rounding_size=0.35", fc=fill, ec=color, lw=1.4))
        ax.text(lx + 3.1, 1.6, label, fontsize=9, color=theme["muted"], va="center")
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)


# --- results ------------------------------------------------------------------------------------


def passed(path: str) -> tuple[int, int]:
    rows = [json.loads(line) for line in open(ROOT / "out" / "runs" / path)]
    rows = [r for r in rows if r["horizon"] == "short"]
    return sum(r["passed"] for r in rows), len(rows)


def rounded_end(ax, x0, x1, y, height, color, points=4.5):
    """A bar from x0 to x1 with a square start and a rounded data end. Needs final axes limits."""
    if x1 <= x0:
        return
    (ox, oy), (ux, uy) = ax.transData.transform([(0, 0), (1, 1)])
    radius = points * ax.figure.dpi / 72  # in pixels
    rx, ry = min(radius / abs(ux - ox), (x1 - x0) / 2), min(radius / abs(uy - oy), height / 2)
    lo, hi = y - height / 2, y + height / 2
    vertices = [(x0, lo), (x1 - rx, lo), (x1, lo), (x1, lo + ry), (x1, hi - ry), (x1, hi), (x1 - rx, hi), (x0, hi), (x0, lo)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(vertices, codes), fc=color, ec="none", zorder=3))


def style(ax, theme):
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["line"])
    ax.tick_params(axis="both", length=0, colors=theme["muted"], labelsize=10)
    ax.xaxis.grid(True, color=theme["line"], lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)


PARTS = [  # (label, keys in repetition.json)
    ("tool list", ["tool list"]),
    ("system prompt and task", ["system prompt and task", "end of prompt (start of the model's reply)"]),
    ("the model's earlier calls", ["the model's earlier calls"]),
    ("tool outputs", ["older tool outputs", "newest tool output"]),
]
SETTINGS = [  # (label, group in repetition.json)
    ("Short tasks, 21 hand-made tools\n(Qwen3-8B, 222 runs)", "qwen3-8b, tools: traces, tool choice: auto, short tasks"),
    ("Long tasks, 21 hand-made tools\n(known-good solutions, 20 runs)", "known-good, long tasks"),
    ("Long ToolGym chains, generated tools\n(6 tools offered per task, 12 runs)", "ToolGym chains, tools: toolgym-generated, long tasks"),
]


def results(theme: dict, path: pathlib.Path) -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.3), dpi=200, gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.62})
    fig.patch.set_facecolor(theme["surface"])
    fig.subplots_adjust(left=0.13, right=0.985, top=0.82, bottom=0.2)

    # (a) one measure, one series: a single hue, values as direct labels
    bars = [("Hand-made tools (21)", passed("qwen3-8b-tools-traces-short.jsonl")),
            ("No tools", passed("qwen3-8b-none.jsonl")),
            ("Generated tools (29)", passed("qwen3-8b-tools-generated-coder-60-short.jsonl")),
            ("Generated tools (22)", passed("qwen3-8b-tools-generated-coder-short.jsonl"))]
    style(a, theme)
    a.set_xlim(0, 100)
    a.set_ylim(-0.6, len(bars) - 0.4)
    a.invert_yaxis()
    a.set_yticks(range(len(bars)), [label for label, _ in bars], color=theme["ink"], fontsize=11)
    a.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    fig.canvas.draw()
    for i, (_, (ok, n)) in enumerate(bars):
        share = 100 * ok / n
        rounded_end(a, 0, share, i, 0.46, theme["series"][0])
        a.text(share + 1.5, i, f"{share:.0f}%", va="center", fontsize=11, fontweight="bold", color=theme["ink"])
    a.set_title("Exercises solved, by tool set", loc="left", fontsize=13, fontweight="bold", color=theme["ink"], pad=24)
    a.text(0, 1.035, "222 one-call tasks on pypa/packaging · model: Qwen3-8B · one run each", transform=a.transAxes, fontsize=9.5, color=theme["muted"])

    # (b) parts of a whole: stacked, hues in fixed order, a surface gap between segments
    data = json.load(open(ROOT / "out" / "traces" / "analysis" / "repetition.json"))
    style(b, theme)
    b.set_xlim(0, 100)
    b.set_ylim(-0.6, len(SETTINGS) - 0.4)
    b.invert_yaxis()
    b.set_yticks(range(len(SETTINGS)), [label for label, _ in SETTINGS], color=theme["ink"], fontsize=10.2)
    b.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    fig.canvas.draw()
    for i, (_, group) in enumerate(SETTINGS):
        parts = data[group]["parts"]
        total = sum(parts.values())
        left = 0.0
        for j, (label, keys) in enumerate(PARTS):
            share = 100 * sum(parts.get(k, 0) for k in keys) / total
            if j == len(PARTS) - 1:
                rounded_end(b, left, left + share, i, 0.46, theme["series"][j])
            else:
                b.add_patch(Rectangle((left, i - 0.23), share, 0.46, fc=theme["series"][j], ec="none", zorder=3))
            if j:
                b.plot([left, left], [i - 0.23, i + 0.23], color=theme["surface"], lw=2, zorder=4)  # the gap between segments
            if share >= 9:
                b.text(left + share / 2, i - 0.36, f"{share:.0f}%", ha="center", va="bottom", fontsize=9.5, color=theme["ink"])
            left += share
    b.set_title("What the prompt tokens of a run consist of", loc="left", fontsize=13, fontweight="bold", color=theme["ink"], pad=24)
    b.text(0, 1.035, "share of all prompt tokens over a run · counted with the model's own tokenizer", transform=b.transAxes, fontsize=9.5, color=theme["muted"])
    handles = [Rectangle((0, 0), 1, 1, fc=theme["series"][j]) for j in range(len(PARTS))]
    legend = b.legend(handles, [label for label, _ in PARTS], loc="upper right", bbox_to_anchor=(1.01, -0.13), ncol=4, frameon=False,
                      fontsize=9.6, handlelength=1.0, handleheight=1.0, columnspacing=1.4, handletextpad=0.5)
    for text in legend.get_texts():
        text.set_color(theme["muted"])
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)


if __name__ == "__main__":
    for name, theme in THEMES.items():
        pipeline(theme, DOCS / f"pipeline-{name}.png")
        results(theme, DOCS / f"results-{name}.png")
    print("wrote", ", ".join(p.name for p in sorted(DOCS.glob("*.png"))))
