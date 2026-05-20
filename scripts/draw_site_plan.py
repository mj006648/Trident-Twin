"""Generate the Phase 5 Trident Twin Site Plan (top-down architectural view).

4-Zone model: Lake / Accumulation / Staging / Delivery. All four zones live
inside a single Trident Lakehouse outline; Lake is NOT a separate building,
it is the no-metadata-yet area of the same Lakehouse.

Output: docs/site-plan.png

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
    (-9.0, 0.0, 0.55, 0.38, "Dataset\nPkg 001", "dataset"),
    (-6.3, 0.0, 2.2, 2.0, "Bronze\nLake\n(buckets)", "lake"),
    (-4.2, 0.0, 4.6, 0.18, "Accumulation Conveyor", "pipeline"),
    (-2.4, 0.0, 0.8, 1.4, "Explaining\nStation\n(Milvus)", "meta_e"),
    (0.8, 0.0, 0.8, 1.4, "Sharing\nStation\n(Redis)", "meta_s"),
    (2.8, 0.0, 3.8, 0.18, "To-Staging Conveyor", "pipeline"),
    (5.4, 0.0, 2.0, 2.2, "Silver\nLakehouse\n(staged)", "lakehouse"),
    (1.4, -2.4, 1.0, 0.7, "System\nOperator", "operator"),
    (8.3, 3.0, 1.0, 0.7, "Customer\nDesk", "customer"),
    (7.8, -2.1, 0.7, 0.7, "HPC", "workload"),
    (8.8, -0.7, 0.7, 0.7, "M&S", "workload"),
    (8.8, 0.7, 0.7, 0.7, "AI", "workload"),
    (7.8, 2.1, 0.7, 0.7, "HPDA", "workload"),
]

SHELF_ANNOT = (5.4, 1.6, "Staging Shelves\n(z=1.7 / 2.1 / 2.5)")

COLORS = {
    "lake": "#bcd6e7",
    "pipeline": "#d8d8d8",
    "meta_e": "#bdd0f5",
    "meta_s": "#b9e0c6",
    "lakehouse": "#cde0bf",
    "operator": "#fbe5b6",
    "customer": "#f6c8a8",
    "workload": "#d8c4ee",
    "dataset": "#cccccc",
}

# 4 zones (X start, X end, label, tint color)
ZONES = [
    (-10.3, -5.0, "Lake Zone", "#3b8bb0"),
    (-5.0, 2.0, "Accumulation Zone", "#7a6fb0"),
    (2.0, 6.8, "Staging Zone", "#2faa55"),
    (6.8, 10.3, "Delivery Zone", "#c47433"),
]

# Site bounds
X_MIN, X_MAX = -11.0, 11.0
Y_MIN, Y_MAX = -4.0, 4.2

# Trident Lakehouse outer envelope (encloses ALL four zones)
LH_X1, LH_X2 = -10.3, 10.3
LH_Y1, LH_Y2 = -3.4, 3.5


def draw_grid(ax) -> None:
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 1), minor=True)
    ax.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1, 1), minor=True)
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 2))
    ax.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1, 2))
    ax.grid(which="minor", color="#eeeeee", linewidth=0.5)
    ax.grid(which="major", color="#cccccc", linewidth=0.7)
    ax.set_axisbelow(True)


def draw_lakehouse_envelope(ax) -> None:
    env = mpatches.FancyBboxPatch(
        (LH_X1, LH_Y1), LH_X2 - LH_X1, LH_Y2 - LH_Y1,
        boxstyle="round,pad=0.0,rounding_size=0.25",
        facecolor="none", edgecolor="#222222",
        linewidth=2.2, linestyle=(0, (8, 3)), zorder=1.5,
    )
    ax.add_patch(env)
    ax.text(LH_X1 + 0.2, LH_Y2 - 0.05, "  Trident Lakehouse",
            ha="left", va="top", fontsize=12, fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#222222", linewidth=1.0), zorder=2)


def draw_room(ax, cx, cy, w, h, label, group) -> None:
    rect = mpatches.Rectangle(
        (cx - w / 2, cy - h / 2), w, h,
        facecolor=COLORS[group], edgecolor="black", linewidth=1.2, zorder=3,
    )
    ax.add_patch(rect)
    font = 7.5 if w < 1.0 or h < 0.3 else 8.5
    ax.text(cx, cy, label, ha="center", va="center", fontsize=font,
            fontweight="bold", zorder=4)


def draw_zone(ax, x_start, x_end, label, color) -> None:
    rect = mpatches.Rectangle(
        (x_start, LH_Y1 + 0.05), x_end - x_start, LH_Y2 - LH_Y1 - 0.1,
        facecolor=color, edgecolor="none", alpha=0.15, zorder=1,
    )
    ax.add_patch(rect)
    ax.text((x_start + x_end) / 2, LH_Y1 + 0.18, label,
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            color="#333333", zorder=4)


def draw_flow_arrow(ax, x1, y1, x2, y2, color, label, label_offset=(0, 0.18)) -> None:
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, mutation_scale=22),
        zorder=5,
    )
    mx, my = (x1 + x2) / 2 + label_offset[0], (y1 + y2) / 2 + label_offset[1]
    ax.text(mx, my, label, ha="center", va="bottom",
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
        mpatches.Patch(facecolor=COLORS["lake"], edgecolor="black", label="Bronze Lake (buckets)"),
        mpatches.Patch(facecolor=COLORS["meta_e"], edgecolor="black", label="Explaining Metadata (Milvus)"),
        mpatches.Patch(facecolor=COLORS["meta_s"], edgecolor="black", label="Sharing Metadata (Redis)"),
        mpatches.Patch(facecolor=COLORS["lakehouse"], edgecolor="black", label="Silver Lakehouse / Shelves"),
        mpatches.Patch(facecolor=COLORS["pipeline"], edgecolor="black", label="Conveyor / Pipeline"),
        mpatches.Patch(facecolor=COLORS["customer"], edgecolor="black", label="Customer Desk"),
        mpatches.Patch(facecolor=COLORS["operator"], edgecolor="black", label="System Operator Desk"),
        mpatches.Patch(facecolor=COLORS["workload"], edgecolor="black", label="Workload Dock (AI/HPC/HPDA/M&S)"),
        Line2D([0], [0], color="#222222", lw=2.0, linestyle=(0, (8, 3)), label="Trident Lakehouse envelope"),
        Line2D([0], [0], color="#00a0c8", lw=2.2, label="Accumulation pipeline (upstream)"),
        Line2D([0], [0], color="#c47433", lw=2.2, label="Delivery pipeline (downstream)"),
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
    draw_lakehouse_envelope(ax)

    for x_start, x_end, label, color in ZONES:
        draw_zone(ax, x_start, x_end, label, color)

    for cx, cy, w, h, label, group in ROOMS:
        draw_room(ax, cx, cy, w, h, label, group)

    ax.text(SHELF_ANNOT[0], SHELF_ANNOT[1], SHELF_ANNOT[2],
            ha="center", va="bottom", fontsize=7, style="italic",
            color="#555555", zorder=4)

    # Accumulation pipeline (upstream): Lake -> Accumulation -> Staging
    draw_flow_arrow(ax, -8.4, -1.2, -2.0, -1.2, "#00a0c8",
                    "Accumulation: Lake -> attach metadata", label_offset=(0, 0.18))
    draw_flow_arrow(ax, 2.0, -1.2, 6.5, -1.2, "#00a0c8",
                    "-> Staging shelves", label_offset=(0, 0.18))

    # Delivery pipeline (downstream): Customer Desk -> shelves OR metadata -> docks
    draw_flow_arrow(ax, 7.8, 2.95, 6.5, 1.2, "#c47433",
                    "Customer query -> Shelf pickup", label_offset=(-0.6, 0.1))
    draw_flow_arrow(ax, 8.3, 2.6, 8.3, 1.2, "#c47433",
                    "-> Workload Dock", label_offset=(1.1, -0.05))

    # Dimensions
    draw_dimension(ax, -9.0, 5.4, 3.7, "14.4 m  ·  Dataset → Silver Lakehouse (data flow span)")
    draw_dimension(ax, 5.4, 8.8, -3.7, "3.4 m  ·  Lakehouse → Workload Docks")

    draw_north_arrow(ax)
    draw_scale_bar(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin — Phase 5 Site Plan (Top View, 4-Zone Model)\n"
        "Lake · Accumulation · Staging · Delivery all live inside one Trident Lakehouse  ·  1 unit = 1 m  ·  matches PoC USD stage",
        fontsize=12, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUT, dpi=180, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
