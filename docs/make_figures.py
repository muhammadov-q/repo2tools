"""Draw the README figures, on a white background like figures in a paper.

    uv run --with matplotlib python docs/make_figures.py

architecture.png  the system, drawn like a paper's architecture figure
results.png         (a) exercises solved per tool set, from out/runs/;
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
}
plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def mix(color: str, surface: str, share: float) -> tuple:
    a, b = matplotlib.colors.to_rgb(color), matplotlib.colors.to_rgb(surface)
    return tuple(share * x + (1 - share) * y for x, y in zip(a, b))


# --- pipeline diagram, in the style of a paper's architecture figure -----------------------------

NAVY = "#1f2a44"
PASTEL = {"panel": "#d9def5", "mint": "#c9f0ea", "blue_sq": "#c5d3f2", "block": "#8ea5e0", "pink_sq": "#f6c9d6", "pink": "#f2b6c1",
          "green_sq": "#cfe8c9", "orange": "#f8cfa9", "gray": "#efefef", "peach": "#fbe0d0", "light_blue": "#dce8f7",
          "mid_blue": "#9dbbe3", "bar": "#b7c7e6", "red": "#d6455d", "lilac": "#e3d5f5"}


def architecture(path: pathlib.Path) -> None:
    fig = plt.figure(figsize=(12.6, 8.1), dpi=220)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 126)
    ax.set_ylim(0, 81)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def block(x, y, w, h, color, label="", size=10.5, bold=True, rotation=0, radius=1.0, edge=None, lw=0.0, text_color="black", z=3):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}", fc=color, ec=edge or color, lw=lw, zorder=z))
        if label:
            ax.text(x + w / 2, y + h / 2, label, fontsize=size, fontweight="bold" if bold else "normal", ha="center", va="center",
                    rotation=rotation, color=text_color, zorder=z + 1, linespacing=1.25)

    def container(x, y, w, h, fill="white", radius=3.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}", fc=fill, ec=NAVY, lw=1.3, ls=(0, (6, 3)), zorder=1))

    def squares(x, y, n, color, vertical=False, size=2.0, gap=0.75, dark=False):
        """n small squares in a dashed frame; returns the frame (x, y, w, h)."""
        pad = 0.6
        w = size + 2 * pad if vertical else n * size + (n - 1) * gap + 2 * pad
        h = n * size + (n - 1) * gap + 2 * pad if vertical else size + 2 * pad
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=NAVY, lw=1.0, ls=(0, (2.5, 1.8)), zorder=3))
        for i in range(n):
            sx, sy = (x + pad, y + pad + i * (size + gap)) if vertical else (x + pad + i * (size + gap), y + pad)
            ax.add_patch(Rectangle((sx, sy), size, size, fc=color, ec=NAVY, lw=1.0, zorder=4))
        return x, y, w, h

    def arrow(a, b, color="black", dashed=False, lw=1.25, head=True):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>" if head else "-", mutation_scale=11, lw=lw, color=color,
                                     ls=(0, (4, 2.5)) if dashed else "-", shrinkA=0, shrinkB=0, zorder=5))

    def line(points, color="black", dashed=False, lw=1.25, head=True):
        xs, ys = zip(*points[:-1] if head else points)
        ax.plot(list(xs) + ([] if head else []), list(ys), color=color, lw=lw, ls=(0, (4, 2.5)) if dashed else "-", zorder=5, solid_capstyle="butt")
        if head:
            arrow(points[-2], points[-1], color=color, dashed=dashed, lw=lw)

    def plus(x, y, r=1.15):
        ax.add_patch(plt.Circle((x, y), r, fc="white", ec="black", lw=1.2, zorder=6))
        ax.plot([x - r * 0.6, x + r * 0.6], [y, y], color="black", lw=1.2, zorder=7)
        ax.plot([x, x], [y - r * 0.6, y + r * 0.6], color="black", lw=1.2, zorder=7)

    def code_tile(x, y, w, h, accent):
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec="#b9bfd6", lw=0.7, zorder=3))
        rows = [(0.0, 0.55, accent), (0.12, 0.7, "#9aa0b4"), (0.12, 0.45, "#9aa0b4"), (0.24, 0.5, "#c7cad6"), (0.12, 0.62, "#9aa0b4"), (0.0, 0.4, accent), (0.12, 0.66, "#c7cad6")]
        for i, (indent, length, color) in enumerate(rows):
            yy = y + h - 1.0 - i * (h - 1.6) / (len(rows) - 1)
            ax.plot([x + 0.7 + indent * w, x + 0.7 + (indent + length) * (w - 1.4)], [yy, yy], color=color, lw=1.6, solid_capstyle="round", zorder=4)

    # ---- input ---------------------------------------------------------------------------------
    block(1, 45, 27, 27, PASTEL["panel"], radius=0.3)
    for (tx, ty), accent in zip([(2.6, 60.2), (15.2, 60.2), (2.6, 49.6), (15.2, 49.6)], ["#3b6fd6", "#e2603a", "#2f9e77", "#8b5bd6"]):
        code_tile(tx, ty, 11.2, 9.6, accent)
    ax.text(14.5, 47.2, "Repository", fontsize=12, fontweight="bold", ha="center", va="center", zorder=4)
    arrow((29.5, 58.5), (33, 58.5))

    # ---- tool synthesis ------------------------------------------------------------------------
    ax.text(57, 76.6, "Tool Synthesis", fontsize=13.5, ha="center", va="center")
    container(34.5, 41.5, 45, 32.5)
    for i in range(3):  # stacked cards
        ax.add_patch(Rectangle((37.2 + (2 - i) * 1.0, 51.5 + (2 - i) * 1.0), 9.2, 9.2, fc=PASTEL["mint"], ec=NAVY, lw=1.1, zorder=3 + i))
    ax.text(41.8, 56.1, "AST\nscan", fontsize=10.5, ha="center", va="center", zorder=7, linespacing=1.15)
    arrow((49.2, 57.5), (51.6, 57.5))
    f = squares(52.2, 46.2, 8, PASTEL["blue_sq"], vertical=True)
    arrow((f[0] + f[2] + 0.6, 57.5), (58.6, 57.5))
    block(59.2, 46.5, 5.6, 22, PASTEL["block"], "LLM Generator", rotation=-90, size=10.5, radius=1.2)
    arrow((65.4, 57.5), (67.8, 57.5))
    c = squares(68.4, 46.2, 8, PASTEL["pink_sq"], vertical=True)
    ax.text(f[0] + f[2] / 2, 44.2, "public\nfunctions", fontsize=7.6, ha="center", va="center", color="#333333", linespacing=1.1)
    ax.text(c[0] + c[2] / 2, 44.2, "candidate\ntools", fontsize=7.6, ha="center", va="center", color="#333333", linespacing=1.1)
    arrow((c[0] + c[2] + 0.8, 57.5), (88.6, 57.5))

    # ---- verification --------------------------------------------------------------------------
    block(89, 55, 22, 5, PASTEL["pink"], "Sandbox Verifier", radius=1.0)
    g = squares(91.3, 47.2, 5, PASTEL["green_sq"], size=2.2, gap=1.2)
    for i in range(5):
        gx = g[0] + 0.6 + 1.1 + i * 3.4
        arrow((gx, g[1] + g[3]), (gx, 54.8), lw=1.1)
    ax.text(g[0] + g[2] / 2, 45.6, "sample inputs", fontsize=7.6, ha="center", va="center", color="#333333")
    arrow((100, 60.2), (100, 63.3))
    block(86, 63.5, 28, 4.6, PASTEL["orange"], "loads · MCP · runs · = library call", size=9.4, bold=False, radius=0.8, edge="#5a4632", lw=0.9)
    arrow((100, 68.3), (100, 71.3), dashed=True)
    block(86, 71.5, 28, 8, PASTEL["orange"], "Verified MCP Tool Set\n(one tool per function)", size=10.8, bold=False, radius=1.6, edge=NAVY, lw=1.3)
    # repair loop: failed checks go back to the generator
    line([(89, 56.2), (84.5, 56.2), (84.5, 39.4), (62, 39.4), (62, 46.3)], color=PASTEL["red"], dashed=True)
    ax.text(73.2, 38.0, "error fed back: up to 3 repair rounds", fontsize=7.8, ha="center", va="center", color=PASTEL["red"])
    # accepted tools go down to the lower panel
    line([(114, 75.5), (121.5, 75.5), (121.5, 35.2)], dashed=True)
    ax.text(122.6, 56, "accepted tools", fontsize=7.8, rotation=-90, ha="center", va="center", color="#333333")

    # ---- chaining and measurement ---------------------------------------------------------------
    container(1, 0.8, 124, 34.2, fill=PASTEL["gray"], radius=4.0)
    ax.text(3.8, 30.6, "Chaining & Measurement", fontsize=16.5, ha="left", va="center", zorder=3)

    arrow((2.6, 8.2), (5.2, 8.2))
    cube = [(5.8, 6.0), (7.9, 6.0), (7.9, 10.6), (5.8, 10.6)]
    ax.add_patch(plt.Polygon(cube, fc="#aab4cc", ec=NAVY, lw=1.0, zorder=3))
    ax.add_patch(plt.Polygon([(7.9, 6.0), (9.5, 7.6), (9.5, 12.2), (7.9, 10.6)], fc="#7d89a6", ec=NAVY, lw=1.0, zorder=3))
    ax.add_patch(plt.Polygon([(5.8, 10.6), (7.9, 10.6), (9.5, 12.2), (7.4, 12.2)], fc="#c9d0e2", ec=NAVY, lw=1.0, zorder=3))
    ax.text(7.6, 13.6, "tools", fontsize=7.6, ha="center", va="center", color="#333333")
    arrow((9.9, 8.2), (12.6, 8.2))
    block(13, 5.6, 16.5, 5.2, PASTEL["peach"], "Type Proposal\n(LLM)", size=9.6)
    line([(29.5, 8.2), (33.6, 8.2)])
    block(34, 5.6, 19.5, 5.2, PASTEL["light_blue"], "Pairwise Parameter\nCheck", size=9.4)
    line([(31.3, 8.2), (31.3, 4.0), (62.5, 4.0), (62.5, 8.2), (65.2, 8.2)])
    block(65.6, 5.6, 19.5, 5.2, PASTEL["mid_blue"], "Output → Consumer\nCheck", size=9.4)
    block(34, 14.4, 51.1, 4.2, PASTEL["bar"], "Execution-Checked Type Links", size=10.2, radius=0.8, edge=NAVY, lw=1.0)
    arrow((43.7, 10.9), (43.7, 14.2))
    arrow((75.3, 10.9), (75.3, 14.2))
    p1, p2 = (43.7, 22.4), (75.3, 22.4)
    arrow((p1[0], 18.7), (p1[0], p1[1] - 1.25))
    arrow((p2[0], 18.7), (p2[0], p2[1] - 1.25))
    plus(*p1)
    plus(*p2)
    ax.text(p1[0] + 2.0, p1[1], r"$T^{\,kept}_{param}$", fontsize=10, va="center")
    ax.text(p2[0] + 2.0, p2[1], r"$T^{\,kept}_{out}$", fontsize=10, va="center")
    # the proposal is combined with what the checks leave standing
    line([(21, 10.9), (21, 22.4), (p1[0] - 1.25, 22.4)], color=PASTEL["red"], lw=1.1)
    line([(37.5, 22.4), (37.5, 20.5), (68.5, 20.5), (68.5, 22.4), (p2[0] - 1.25, 22.4)], color=PASTEL["red"], lw=1.1)
    s1 = squares(p1[0] - 4.4, 26.2, 3, PASTEL["blue_sq"], size=2.1, gap=0.9)
    s2 = squares(p2[0] - 4.4, 26.2, 3, PASTEL["mid_blue"], size=2.1, gap=0.9)
    arrow((p1[0], p1[1] + 1.2), (p1[0], s1[1]))
    arrow((p2[0], p2[1] + 1.2), (p2[0], s2[1]))
    # typed tools go to ToolGym
    block(91.5, 24.4, 13.2, 6.8, PASTEL["pink"], "ToolGym", size=10.4, radius=1.0)
    ax.text(98.1, 22.9, "chain sampling + validation", fontsize=7.4, ha="center", va="center", color="#333333")
    line([(s1[0] + s1[2] / 2, s1[1] + s1[3]), (s1[0] + s1[2] / 2, 32.6), (87.5, 32.6), (87.5, 28.9), (91.3, 28.9)], dashed=True, lw=1.1)
    line([(s2[0] + s2[2], 27.8), (87.5, 27.8)], dashed=True, lw=1.1, head=False)
    line([(87.5, 27.8), (91.3, 27.8)], dashed=True, lw=1.1)
    t1 = squares(108.2, 23.6, 3, PASTEL["pink_sq"], vertical=True, size=1.9, gap=0.7)
    arrow((104.9, 27.8), (t1[0] - 0.2, 27.8))
    # the tools are also given to a model, on exercises with known answers
    block(91.5, 5.6, 13.2, 6.8, PASTEL["lilac"], "LLM Agent\n± Tools", size=9.8, radius=1.0)
    ax.text(98.1, 4.2, "242 exercises, known answers", fontsize=7.4, ha="center", va="center", color="#333333")
    line([(7.6, 5.9), (7.6, 2.4), (88.5, 2.4), (88.5, 9.0), (91.3, 9.0)])
    t2 = squares(108.2, 4.8, 3, PASTEL["green_sq"], vertical=True, size=1.9, gap=0.7)
    arrow((104.9, 9.0), (t2[0] - 0.2, 9.0))
    ax.text(t1[0] + t1[2] / 2, 21.9, "synthetic\ntraces", fontsize=7.2, ha="center", va="center", color="#333333", linespacing=1.1)
    ax.text(t2[0] + t2[2] / 2, 14.3, "model\ntraces", fontsize=7.2, ha="center", va="center", color="#333333", linespacing=1.1)
    block(114.6, 6.4, 8.2, 23.4, PASTEL["orange"], "Trace Analysis", rotation=-90, size=10.4, radius=1.2, edge=NAVY, lw=1.1)
    arrow((t1[0] + t1[2] + 0.2, 27.8), (114.4, 27.8))
    arrow((t2[0] + t2[2] + 0.2, 9.0), (114.4, 9.0))

    fig.savefig(path, facecolor="white")
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
    architecture(DOCS / "architecture.png")
    results(THEMES["light"], DOCS / "results.png")
    print("wrote", ", ".join(p.name for p in sorted(DOCS.glob("*.png"))))
