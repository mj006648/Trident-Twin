"""Generate the Phase 5 Trident Twin Site Plan (top-down architectural view).

Output: docs/site-plan.png

Style: white background, thin black walls, light grey grid, dimension lines,
north arrow, scale bar, legend. Coordinates are 1:1 with PoC USD stage
(scripts/create_scene.py); 1 unit = 1 meter.

Stdlib + matplotlib only. No Isaac Sim / pxr required.

Run:
    python3 scripts/draw_site_plan.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parents[1] / "docs" / "site-plan.png"

# PoC stage coordinates (center_x, center_y, size_x, size_y, label, group)
# Source: scripts/create_scene.py, X axis = data flow.
ROOMS = [
    (-6.3, 0.0, 2.2, 2.0, "Bronze\nLake", "lake"),
    (-4.2, 0.0, 4.6, 0.18, "Accumulation Conveyor", "pipeline"),
    (-2.4, 0.0, 0.8, 1.4, "Explaining\nStation", "meta_e"),
    (0.8, 0.0, 0.8, 1.4, "Sharing\nStation", "meta_s"),
    (2.8, 0.0, 3.8, 0.18, "To-Lakehouse Conveyor", "pipeline"),
    (5.4, 0.0, 2.0, 2.2, "Silver\nLakehouse", "lakehouse"),
    (1.4, -2.4, 1.0, 0.7, "Operator\nDesk", "operator"),
    (7.8, -2.1, 0.7, 0.7, "HPC", "workload"),
    (8.8, -0.7, 0.7, 0.7, "M&S", "workload"),
    (8.8, 0.7, 0.7, 0.7, "AI", "workload"),
    (7.8, 2.1, 0.7, 0.7, "HPDA", "workload"),
    (-9.0, 0.0, 0.55, 0.38, "Dataset\nPkg 001", "dataset"),
]

# Staging shelves stack vertically over Silver Lakehouse — show as one annotation
SHELF_ANNOT = (5.4, 1.6, "Staging Shelves\n(z=1.7 / 2.1 / 2.5)")

COLORS = {
    "lake": "#bcd6e7",
    "pipeline": "#d8d8d8",
    "meta_e": "#bdd0f5",
    "meta_s": "#b9e0c6",
    "lakehouse": "#cde0bf",
    "operator": "#fbe5b6",
    "workload": "#d8c4ee",
    "dataset": "#cccccc",
}

# Site bounds (with margin)
X_MIN, X_MAX = -11.0, 11.0
Y_MIN, Y_MAX = -4.0, 4.2


def draw_grid(ax) -> None:
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 1), minor=True)
    ax.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1, 1), minor=True)
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 2))
    ax.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1, 2))
    ax.grid(which="minor", color="#eeeeee", linewidth=0.5)
    ax.grid(which="major", color="#cccccc", linewidth=0.7)
    ax.set_axisbelow(True)


def draw_room(ax, cx, cy, w, h, label, group) -> None:
    rect = mpatches.Rectangle(
        (cx - w / 2, cy - h / 2), w, h,
        facecolor=COLORS[group], edgecolor="black", linewidth=1.2, zorder=2,
    )
    ax.add_patch(rect)
    font = 8 if w < 1.0 or h < 0.3 else 9
    ax.text(cx, cy, label, ha="center", va="center", fontsize=font,
            fontweight="bold", zorder=3)


def draw_zone(ax, x_start, x_end, label, color) -> None:
    rect = mpatches.Rectangle(
        (x_start, Y_MIN + 0.1), x_end - x_start, Y_MAX - Y_MIN - 0.2,
        facecolor=color, edgecolor="none", alpha=0.18, zorder=1,
    )
    ax.add_patch(rect)
    ax.text((x_start + x_end) / 2, Y_MIN + 0.25, label,
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            color="#444444", zorder=4)


def draw_flow_arrow(ax, x1, x2, y, color, label) -> None:
    ax.annotate(
        "", xy=(x2, y), xytext=(x1, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, mutation_scale=22),
        zorder=5,
    )
    ax.text((x1 + x2) / 2, y + 0.18, label, ha="center", va="bottom",
            fontsize=9, color=color, fontweight="bold", zorder=6)


def draw_dimension(ax, x1, x2, y, label) -> None:
    ax.plot([x1, x2], [y, y], color="#666666", lw=0.8, zorder=4)
    ax.plot([x1, x1], [y - 0.12, y + 0.12], color="#666666", lw=0.8, zorder=4)
    ax.plot([x2, x2], [y - 0.12, y + 0.12], color="#666666", lw=0.8, zorder=4)
    ax.text((x1 + x2) / 2, y + 0.18, label, ha="center", va="bottom",
            fontsize=8, color="#444444", zorder=4)


def draw_north_arrow(ax) -> None:
    nx, ny = X_MAX - 0.8, Y_MAX - 0.8
    ax.annotate("", xy=(nx, ny + 0.5), xytext=(nx, ny - 0.3),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4,
                                mutation_scale=18), zorder=10)
    ax.text(nx, ny + 0.7, "N", ha="center", va="bottom",
            fontsize=11, fontweight="bold", zorder=10)
    ax.text(nx, ny - 0.55, "(data flow → +X)", ha="center", va="top",
            fontsize=7, color="#666666", zorder=10)


def draw_scale_bar(ax) -> None:
    x0, y0 = X_MIN + 0.5, Y_MIN + 0.4
    ax.plot([x0, x0 + 2], [y0, y0], color="black", lw=2.5, zorder=10)
    ax.plot([x0, x0], [y0 - 0.1, y0 + 0.1], color="black", lw=1.0, zorder=10)
    ax.plot([x0 + 2, x0 + 2], [y0 - 0.1, y0 + 0.1], color="black", lw=1.0, zorder=10)
    ax.plot([x0 + 1, x0 + 1], [y0 - 0.07, y0 + 0.07], color="black", lw=0.8, zorder=10)
    ax.text(x0 + 1, y0 - 0.25, "0    1    2 m", ha="center", va="top",
            fontsize=8, zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=COLORS["lake"], edgecolor="black", label="Lake (raw zone)"),
        mpatches.Patch(facecolor=COLORS["meta_e"], edgecolor="black", label="Explaining Metadata (Milvus)"),
        mpatches.Patch(facecolor=COLORS["meta_s"], edgecolor="black", label="Sharing Metadata (Redis)"),
        mpatches.Patch(facecolor=COLORS["lakehouse"], edgecolor="black", label="Lakehouse (staged)"),
        mpatches.Patch(facecolor=COLORS["pipeline"], edgecolor="black", label="Conveyor / Pipeline"),
        mpatches.Patch(facecolor=COLORS["workload"], edgecolor="black", label="Workload Dock"),
        mpatches.Patch(facecolor=COLORS["operator"], edgecolor="black", label="Operator Desk"),
        Line2D([0], [0], color="#00a0c8", lw=2.2, label="Accumulation flow (Cyan)"),
        Line2D([0], [0], color="#2faa55", lw=2.2, label="Delivery flow (Green)"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=8.5, framealpha=1.0, edgecolor="#888888",
              title="Legend", title_fontsize=9)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(18, 7))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")

    draw_grid(ax)

    # Phase zone bands (background tint)
    draw_zone(ax, -10.5, -3.5, "Accumulation Zone", "#00a0c8")
    draw_zone(ax, -3.5, 2.0, "Metadata Zone", "#7a6fb0")
    draw_zone(ax, 2.0, 6.8, "Lakehouse Zone", "#2faa55")
    draw_zone(ax, 6.8, 10.5, "Delivery Zone", "#9a5cd8")

    for cx, cy, w, h, label, group in ROOMS:
        draw_room(ax, cx, cy, w, h, label, group)

    ax.text(SHELF_ANNOT[0], SHELF_ANNOT[1], SHELF_ANNOT[2],
            ha="center", va="bottom", fontsize=7, style="italic",
            color="#555555", zorder=4)

    # Pipeline flow arrows
    draw_flow_arrow(ax, -8.4, -2.0, -1.2, "#00a0c8", "Accumulation")
    draw_flow_arrow(ax, 2.0, 6.5, -1.2, "#00a0c8", "→ Stage")
    draw_flow_arrow(ax, 6.5, 9.5, 1.3, "#2faa55", "Delivery →")

    # Dimensions (above the rooms, not overlapping zone labels)
    draw_dimension(ax, -9.0, 5.4, 3.55, "14.4 m  ·  Dataset → Silver Lakehouse (data flow span)")
    draw_dimension(ax, 5.4, 8.8, -3.05, "3.4 m  ·  Lakehouse → Workload Docks")

    draw_north_arrow(ax)
    draw_scale_bar(ax)
    draw_legend(ax)

    # Title block
    ax.set_title(
        "Trident-Twin — Phase 5 Site Plan (Top View)\n"
        "Accumulation & Delivery Pipeline · 1 unit = 1 m · coordinates match PoC USD stage",
        fontsize=12, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUT, dpi=180, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
