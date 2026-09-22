"""Render all three README share figures with identical physical geometry."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/fwbench-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "results/forecast-model-usage.json").read_text())
ROWS = DATA["models"]
CALLS = {r["model"]: r for r in json.loads(
    (ROOT / "results/tool-call-composition.json").read_text())["models"]}
MODEL_COLORS = ["#879DB4", "#485F7A", "#A295B0", "#A2B5A2", "#C6B69C"]
MODEL_LABELS = ["Bolt Tiny", "Chronos-2", "TimesFM 2.5", "Classical", "Other / invalid"]
TOOL_GROUPS = [
    ("Inspect", ["catalog", "history", "inspect_series"], "#8199B0"),
    ("Quote / budget", ["quote_forecast", "budget_status"], "#CBD4DC"),
    ("Forecast", ["forecast_and_plan"], "#92839B"),
    ("Classical", ["classical_plan", "hourly_history_plan"], "#9BB09F"),
    ("Replay", ["replay_forecast"], "#CBBB9D"),
]
plt.rcdefaults()
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 8,
                     "pdf.fonttype": 42, "svg.fonttype": "none"})
geometry = {}


def render(kind):
    """Only the values, legend text/colors and axis captions vary across panels."""
    fig, ax = plt.subplots(figsize=(3.4, 2.65), dpi=300)
    fig.subplots_adjust(left=.265, right=.90, top=.81, bottom=.16)
    is_tool = kind == "tool-call-composition"
    colors = [g[2] for g in TOOL_GROUPS] if is_tool else MODEL_COLORS
    labels = [g[0] for g in TOOL_GROUPS] if is_tool else MODEL_LABELS
    for i, row in enumerate(ROWS):
        if is_tool:
            record = CALLS[row["model"]]
            total = record["total_calls"]
            values = [sum(record["calls_by_tool"].get(k, 0) for k in g[1])
                      for g in TOOL_GROUPS]
            count = f'{record["mean_calls"]:.2f}' if record["mean_calls"] >= .01 else '<.01'
        else:
            record = row[kind]
            total = sum(record.values())
            values = [record.get(k, 0) for k in DATA["backends"]]
            count = f"{total:,}"
        left = 0
        for value, color in zip(values, colors):
            width = 100 * value / total if total else 0
            ax.barh(i, width, left=left, color=color, height=.7)
            left += width
        if not total:
            ax.text(2, i, "N/A", va="center", color="#777777", fontsize=8.3)
        ax.text(103, i, count, va="center", fontsize=8.3)
    for y in [2.5, 7.5]:
        ax.axhline(y, color="#C8CCD0", lw=.4, zorder=0)
    # Explicit limits prevent autoscaling from changing row positions across plots.
    ax.set(xlim=(0, 100), ylim=(11.935, -.935), xticks=[0, 50, 100])
    names = [r["label"].replace("GPT-6 Astra", "Astra").replace("Qwen3.6", "Q3.6")
             .replace("Gemma 4", "Gemma") for r in ROWS]
    ax.set_yticks(range(len(ROWS)), names, fontsize=8.3)
    xlabel = "Share of tool calls (%)" if is_tool else "Share of forecast requests (%)"
    ax.set_xlabel(xlabel, fontsize=8.7, labelpad=2)
    ax.tick_params(axis="y", length=0, pad=3)
    ax.tick_params(axis="x", length=2, labelsize=7.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.text(115, -1, "Calls/case" if is_tool else "Requests", ha="right", fontsize=7.7)
    fig.legend([Patch(facecolor=c) for c in colors], labels, loc="upper center", ncol=3,
               frameon=False, bbox_to_anchor=(.51, 1.01), fontsize=7.8,
               handlelength=1, columnspacing=.7)
    name = kind if is_tool else f"forecast-model-{kind}"
    fig.canvas.draw()
    geometry[name] = {
        "canvas_px": list(fig.canvas.get_width_height()),
        "axes_bounds_px": list(ax.get_window_extent().bounds),
        "bar_start_end_px": ax.transData.transform([[0, 0], [100, 0]]).tolist(),
        "row_label_pt": 8.3, "count_pt": 8.3, "legend_pt": 7.8,
        "tick_pt": 7.8, "axis_label_pt": 8.7, "readme_width_px": 640,
    }
    for ext in ["png", "svg", "pdf"]:
        fig.savefig(ROOT / f"docs/assets/{name}-aligned.{ext}", dpi=300, bbox_inches=None)
    plt.close(fig)


for kind in ["tool-call-composition", "requested", "returned"]:
    render(kind)
(ROOT / "provenance/readme-share-geometry.json").write_text(
    json.dumps(geometry, indent=2) + "\n")
