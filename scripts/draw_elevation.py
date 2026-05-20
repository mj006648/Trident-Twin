"""Generate the Phase 5 Trident Twin Elevation View (side view from -Y).

Companion to docs/site-plan.png. The Site Plan shows the X-Y plane (top-down);
this Elevation shows the X-Z plane so the vertical stacking that a top view
cannot express becomes visible — most importantly:

  * Staging Shelves at z = 1.7 / 2.1 / 2.5 above Silver Lakehouse
  * Dataset Package vs. Workload Dock heights
  * Operator Desk and Customer Desk as low waist-height stations

Output: docs/elevation.png

Stdlib + matplotlib only. No Isaac Sim / pxr required.

Run:
    python3 scripts/draw_elevation.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parents[1] / "docs" / "elevation.png"

# (center_x, center_z, size_x, size_z, label, group)
# All values mirror scripts/create_scene.py. Heights = scale_z; centers = z.
ROOMS = [
    (-9.0, 0.7, 0.55, 0.38, "Dataset\nPkg 001", "dataset"),
    (-6.3, 0.5, 2.2, 1.0, "Bronze Lake\n(buckets)", "lake"),
    (-4.2, 0.18, 4.6, 0.12, "Accumulation Conveyor", "pipeline"),
    (-2.4, 0.6, 0.8, 1.2, "Explaining\n(Milvus)", "meta_e"),
    (0.8, 0.6, 0.8, 1.2, "Sharing\n(Redis)", "meta_s"),
    (2.8, 0.18, 3.8, 0.12, "To-Staging Conveyor", "pipeline"),
    (5.4, 0.8, 2.0, 1.6, "Silver Lakehouse\n(staged)", "lakehouse"),
    (5.4, 1.7, 2.3, 0.08, "Shelf 1 (z=1.7)", "shelf"),
    (5.4, 2.1, 2.3, 0.08, "Shelf 2 (z=2.1)", "shelf"),
    (5.4, 2.5, 2.3, 0.08, "Shelf 3 (z=2.5)", "shelf"),
    (1.4, 0.55, 1.0, 1.1, "System\nOperator", "operator"),
    (7.5, 0.55, 1.0, 1.1, "Customer\nDesk", "customer"),
    (9.2, 0.7, 0.7, 1.4, "Workload\nDocks\n(stacked\nbehind)", "workload"),
]

# 4 zones (X start, X end, label, color tint)
ZONES = [
    (-10.3, -5.0, "Lake Zone", "#3b8bb0"),
    (-5.0, 2.0, "Accumulation Zone", "#7a6fb0"),
    (2.0, 6.8, "Staging Zone", "#2faa55"),
    (6.8, 10.3, "Delivery Zone", "#c47433"),
]

COLORS = {
    "lake": "#bcd6e7",
    "pipeline": "#d8d8d8",
    "meta_e": "#bdd0f5",
    "meta_s": "#b9e0c6",
    "lakehouse": "#cde0bf",
    "shelf": "#a8c690",
    "operator": "#fbe5b6",
    "customer": "#f6c8a8",
    "workload": "#d8c4ee",
    "dataset": "#cccccc",
}

# Frame bounds
X_MIN, X_MAX = -11.0, 11.0
Z_MIN, Z_MAX = -0.4, 3.6

# Lakehouse envelope (same X span as Site Plan; vertical = floor to roof)
LH_X1, LH_X2 = -10.3, 10.3
LH_Z1, LH_Z2 = -0.15, 3.2

# Ground level
GROUND_Z = 0.0


def draw_grid(ax) -> None:
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 1), minor=True)
    ax.set_yticks([z / 2 for z in range(int(Z_MIN * 2), int(Z_MAX * 2) + 1)], minor=True)
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1, 2))
    ax.set_yticks([0, 1, 2, 3])
    ax.grid(which="minor", color="#eeeeee", linewidth=0.5)
    ax.grid(which="major", color="#cccccc", linewidth=0.7)
    ax.set_axisbelow(True)


def draw_ground(ax) -> None:
    ax.axhline(GROUND_Z, color="#444444", linewidth=1.0, zorder=2)
    for x in range(int(X_MIN) + 1, int(X_MAX), 1):
        ax.plot([x, x - 0.18], [GROUND_Z, GROUND_Z - 0.15],
                color="#888888", lw=0.6, zorder=2)


def draw_lakehouse_envelope(ax) -> None:
    env = mpatches.FancyBboxPatch(
        (LH_X1, LH_Z1), LH_X2 - LH_X1, LH_Z2 - LH_Z1,
        boxstyle="round,pad=0.0,rounding_size=0.2",
        facecolor="none", edgecolor="#222222",
        linewidth=2.2, linestyle=(0, (8, 3)), zorder=1.5,
    )
    ax.add_patch(env)
    ax.text(LH_X1 + 0.2, LH_Z2 - 0.05, "  Trident Lakehouse (elevation)",
            ha="left", va="top", fontsize=11, fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#222222", linewidth=1.0), zorder=2)


def draw_zone(ax, x_start, x_end, label, color) -> None:
    rect = mpatches.Rectangle(
        (x_start, LH_Z1 + 0.02), x_end - x_start, LH_Z2 - LH_Z1 - 0.04,
        facecolor=color, edgecolor="none", alpha=0.13, zorder=1,
    )
    ax.add_patch(rect)
    ax.text((x_start + x_end) / 2, LH_Z1 + 0.1, label,
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            color="#333333", zorder=4)


def draw_room(ax, cx, cz, w, h, label, group) -> None:
    rect = mpatches.Rectangle(
        (cx - w / 2, cz - h / 2), w, h,
        facecolor=COLORS[group], edgecolor="black", linewidth=1.2, zorder=3,
    )
    ax.add_patch(rect)
    font = 7.0 if w < 1.0 or h < 0.25 else 8.5
    if group == "shelf":
        ax.text(cx + w / 2 + 0.1, cz, label, ha="left", va="center",
                fontsize=7, style="italic", color="#444444", zorder=4)
    else:
        ax.text(cx, cz, label, ha="center", va="center", fontsize=font,
                fontweight="bold", zorder=4)


def draw_height_dim(ax, x, z1, z2, label) -> None:
    ax.plot([x, x], [z1, z2], color="#666666", lw=0.8, zorder=4)
    ax.plot([x - 0.08, x + 0.08], [z1, z1], color="#666666", lw=0.8, zorder=4)
    ax.plot([x - 0.08, x + 0.08], [z2, z2], color="#666666", lw=0.8, zorder=4)
    ax.text(x + 0.15, (z1 + z2) / 2, label, ha="left", va="center",
            fontsize=8, color="#444444", zorder=4)


def draw_scale_bar(ax) -> None:
    x0, z0 = X_MIN + 0.5, Z_MIN + 0.05
    ax.plot([x0, x0 + 2], [z0, z0], color="black", lw=2.0, zorder=10)
    ax.plot([x0, x0], [z0 - 0.05, z0 + 0.05], color="black", lw=0.8, zorder=10)
    ax.plot([x0 + 2, x0 + 2], [z0 - 0.05, z0 + 0.05], color="black", lw=0.8, zorder=10)
    ax.plot([x0 + 1, x0 + 1], [z0 - 0.04, z0 + 0.04], color="black", lw=0.6, zorder=10)
    ax.text(x0 + 1, z0 - 0.18, "0    1    2 m", ha="center", va="top",
            fontsize=8, zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=COLORS["lake"], edgecolor="black", label="Bronze Lake (buckets)"),
        mpatches.Patch(facecolor=COLORS["meta_e"], edgecolor="black", label="Explaining Metadata (Milvus)"),
        mpatches.Patch(facecolor=COLORS["meta_s"], edgecolor="black", label="Sharing Metadata (Redis)"),
        mpatches.Patch(facecolor=COLORS["lakehouse"], edgecolor="black", label="Silver Lakehouse"),
        mpatches.Patch(facecolor=COLORS["shelf"], edgecolor="black", label="Staging Shelves (z=1.7/2.1/2.5)"),
        mpatches.Patch(facecolor=COLORS["pipeline"], edgecolor="black", label="Conveyor / Pipeline"),
        mpatches.Patch(facecolor=COLORS["customer"], edgecolor="black", label="Customer Desk"),
        mpatches.Patch(facecolor=COLORS["operator"], edgecolor="black", label="System Operator Desk"),
        mpatches.Patch(facecolor=COLORS["workload"], edgecolor="black", label="Workload Dock"),
        Line2D([0], [0], color="#222222", lw=2.0, linestyle=(0, (8, 3)), label="Trident Lakehouse envelope"),
        Line2D([0], [0], color="#444444", lw=1.0, label="Ground level (z=0)"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=8.5, framealpha=1.0, edgecolor="#888888",
              title="Legend", title_fontsize=9)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Site Plan owns the metric-true aspect (1:1). Elevation deliberately
    # exaggerates Z so that 0.4 m shelf separation is readable. We do this
    # by NOT calling set_aspect("equal") and by giving the figure a tall
    # canvas relative to its data range.
    fig, ax = plt.subplots(figsize=(18, 8))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Z_MIN, Z_MAX)

    draw_grid(ax)
    draw_ground(ax)
    draw_lakehouse_envelope(ax)
    for x_start, x_end, label, color in ZONES:
        draw_zone(ax, x_start, x_end, label, color)
    for cx, cz, w, h, label, group in ROOMS:
        draw_room(ax, cx, cz, w, h, label, group)

    # Highlight the vertical staging stack on the left of the Silver block
    draw_height_dim(ax, 6.55, 0.0, 1.7, "1.7 m")
    draw_height_dim(ax, 6.85, 0.0, 2.1, "2.1 m")
    draw_height_dim(ax, 7.15, 0.0, 2.5, "2.5 m")

    draw_scale_bar(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin — Phase 5 Elevation View (Side, looking from -Y)\n"
        "Companion to Site Plan: vertical stacking of Staging Shelves and entity heights  ·  1 unit = 1 m  ·  matches PoC USD stage",
        fontsize=12, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=9)
    ax.set_ylabel("Z (m) — height ↑", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUT, dpi=180, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
