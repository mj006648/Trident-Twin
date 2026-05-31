"""Generate the Trident-Twin conceptual overview.

The overview is intentionally product-oriented rather than architectural:
it frames the twin as a Data Readiness / Usage Optimization map, not a
generic 3D warehouse visualization.

Output: overview.png

Run:
    python3 scripts/draw_overview.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "overview.png"

C_BRONZE = "#b87333"
C_BRONZE_FILL = "#ead1b8"
C_SILVER = "#64748b"
C_SILVER_FILL = "#e2e8f0"
C_GOLD = "#d4a017"
C_GOLD_FILL = "#fde68a"
C_SEARCH = "#0891b2"
C_SEARCH_FILL = "#cffafe"
C_DELIVERY = "#7c3aed"
C_DELIVERY_FILL = "#ddd6fe"
C_OK = "#16a34a"
C_WARN = "#f59e0b"
C_BAD = "#ef4444"
C_PURPLE = "#8b5cf6"
C_RED = "#f43f5e"
C_GREEN = "#22c55e"


def add_box(ax, xy, w, h, title, subtitle, face, edge, fontsize=12):
    x, y = xy
    box = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=face,
        edgecolor=edge,
        linewidth=2.2,
        zorder=3,
        path_effects=[pe.SimplePatchShadow(offset=(2, -2), alpha=0.16), pe.Normal()],
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=edge, zorder=4)
    ax.text(x + w / 2, y + h * 0.33, subtitle, ha="center", va="center",
            fontsize=9, color="#334155", zorder=4, linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color="#334155", label=None, rad=0.0):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=2.4,
            mutation_scale=22,
            connectionstyle=f"arc3,rad={rad}",
        ),
        zorder=2,
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.22, label,
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=color,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                          edgecolor=color, linewidth=0.8, alpha=0.95),
                zorder=5)


def draw_raw_boxes(ax):
    for i, (x, y) in enumerate([(0.55, 3.7), (0.85, 3.4), (1.15, 3.65), (1.35, 3.32)]):
        ax.add_patch(mpatches.Rectangle((x, y), 0.28, 0.22,
                                        facecolor=C_BRONZE, edgecolor="#6b3f1d",
                                        linewidth=1.0, zorder=6))
    ax.text(1.15, 3.18, "raw objects\nmetadata: none", ha="center",
            va="top", fontsize=8, color="#78350f", fontweight="bold")


def draw_inventory(ax):
    # Three namespace/component shelves with compact table crates.
    shelves = [
        (4.82, 3.90, "camera", 7, C_OK),
        (4.82, 3.45, "lidar", 5, C_WARN),
        (4.82, 3.00, "weather", 3, C_BAD),
    ]
    for sx, sy, label, n, quality_color in shelves:
        ax.plot([sx, sx + 1.55], [sy - 0.05, sy - 0.05], color="#475569", lw=2.0, zorder=6)
        ax.text(sx - 0.18, sy + 0.04, label, ha="right", va="center",
                fontsize=8, fontweight="bold", color="#334155", zorder=6)
        for i in range(n):
            x = sx + 0.08 + (i % 7) * 0.18
            y = sy + 0.02 + (i // 7) * 0.18
            ax.add_patch(mpatches.Rectangle((x, y), 0.13, 0.13,
                                            facecolor="#f8fafc", edgecolor=C_SILVER,
                                            linewidth=0.9, zorder=6))
            if i < 3:
                ax.add_patch(mpatches.Circle((x + 0.12, y + 0.13), 0.035,
                                             facecolor=C_PURPLE, edgecolor="white",
                                             linewidth=0.4, zorder=7))
            if i in (1, 3):
                ax.add_patch(mpatches.Circle((x + 0.04, y + 0.13), 0.035,
                                             facecolor=C_RED, edgecolor="white",
                                             linewidth=0.4, zorder=7))
        ax.add_patch(mpatches.Circle((sx + 1.47, sy + 0.09), 0.08,
                                     facecolor=quality_color, edgecolor="white",
                                     linewidth=1.0, zorder=8))
    ax.text(5.55, 2.65, "count + tags + readiness\nnot just storage",
            ha="center", va="center", fontsize=8, color="#334155",
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor=C_SILVER, alpha=0.95), zorder=8)


def draw_bundles(ax):
    bundles = [
        (7.45, 3.82, "camera+lidar", "AI fit 92%"),
        (7.45, 3.35, "weather+gps", "HPDA fit 78%"),
        (7.45, 2.88, "hot basket", "last used 2h"),
    ]
    for x, y, title, sub in bundles:
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), 1.35, 0.32,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor="#fffbeb", edgecolor=C_GOLD, linewidth=1.6, zorder=6))
        ax.text(x + 0.67, y + 0.20, title, ha="center", va="center",
                fontsize=8, fontweight="bold", color="#78350f", zorder=7)
        ax.text(x + 0.67, y + 0.08, sub, ha="center", va="center",
                fontsize=7, color="#92400e", zorder=7)


def draw_search_panel(ax):
    ax.add_patch(mpatches.FancyBboxPatch(
        (9.9, 3.0), 1.55, 1.15,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        facecolor="white", edgecolor=C_SEARCH, linewidth=1.8, zorder=6))
    ax.text(10.675, 3.93, "User intent", ha="center", va="center",
            fontsize=8, color=C_SEARCH, fontweight="bold", zorder=7)
    ax.text(10.675, 3.70, '"camera + lidar"', ha="center", va="center",
            fontsize=9, color="#0f172a", fontweight="bold", zorder=7)
    ax.text(10.675, 3.43, "highlight candidates\ncompare readiness\npick bundle",
            ha="center", va="center", fontsize=7.5, color="#334155",
            linespacing=1.25, zorder=7)
    for i, txt in enumerate(["quality ✓", "policy ✓", "cache !"]):
        col = [C_OK, C_OK, C_WARN][i]
        ax.text(10.1 + i * 0.43, 3.08, txt, ha="center", va="center",
                fontsize=6.5, color=col, fontweight="bold", zorder=7)


def draw_delivery(ax):
    docks = [("AI", "#22c55e"), ("HPC", "#64748b"), ("HPDA", "#2563eb")]
    for i, (label, color) in enumerate(docks):
        x = 12.40
        y = 3.82 - i * 0.42
        ax.add_patch(mpatches.Rectangle((x, y), 0.78, 0.28,
                                        facecolor=color, edgecolor="#0f172a",
                                        linewidth=1.0, alpha=0.85, zorder=6))
        ax.text(x + 0.39, y + 0.14, label, ha="center", va="center",
                fontsize=8, color="white", fontweight="bold", zorder=7)
    ax.text(12.78, 2.73, "URI / SQL / Spark\nsnippet ready",
            ha="center", va="center", fontsize=8, color="#4c1d95",
            fontweight="bold", zorder=7)


def main() -> None:
    fig, ax = plt.subplots(figsize=(15.5, 8.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.8)
    ax.axis("off")

    # Background bands
    ax.add_patch(mpatches.Rectangle((0, 0), 14, 6.8, facecolor="#f8fafc", edgecolor="none", zorder=0))
    ax.add_patch(mpatches.FancyBboxPatch((0.25, 0.45), 13.5, 5.4,
                                         boxstyle="round,pad=0.03,rounding_size=0.16",
                                         facecolor="white", edgecolor="#cbd5e1",
                                         linewidth=1.3, zorder=1))

    ax.text(7, 6.35, "Trident-Twin: Data Readiness / Usage Optimization Twin",
            ha="center", va="center", fontsize=20, fontweight="bold",
            color="#0f172a")
    ax.text(7, 6.02,
            "See what data is ready, why it is searchable, and how it can be delivered to AI / HPC / HPDA workloads.",
            ha="center", va="center", fontsize=11, color="#475569")

    add_box(ax, (0.45, 2.35), 1.9, 2.6, "RAW INTAKE", "objects arrive\nunknown schema\nlow usability",
            C_BRONZE_FILL, C_BRONZE)
    add_box(ax, (2.75, 2.35), 1.9, 2.6, "REFINE", "schema detect\nIceberg table\nquality check",
            "#f1f5f9", C_SILVER)
    add_box(ax, (5.05, 2.35), 1.95, 2.6, "INVENTORY", "namespace/table\ncomponent volume\nreadiness bars",
            C_SILVER_FILL, C_SILVER)
    add_box(ax, (7.35, 2.35), 1.95, 2.6, "STAGING", "hot datasets\nrecommended bundles\nDataset Basket",
            C_GOLD_FILL, C_GOLD)
    add_box(ax, (9.65, 2.35), 1.95, 2.6, "SEARCH", "intent → candidates\nreadiness compare\nfast selection",
            C_SEARCH_FILL, C_SEARCH)
    add_box(ax, (11.95, 2.35), 1.9, 2.6, "DELIVERY", "AI / HPC / HPDA\nURI · SQL · Spark\nworkload-ready",
            C_DELIVERY_FILL, C_DELIVERY)

    for x in [2.35, 4.65, 7.0, 9.3, 11.6]:
        arrow(ax, x, 3.65, x + 0.38, 3.65)
    arrow(ax, 6.05, 2.30, 8.30, 1.20, C_GOLD, "curate likely-use bundles", rad=0.18)
    arrow(ax, 10.65, 2.30, 6.25, 1.20, C_SEARCH, "search highlights inventory", rad=-0.18)

    draw_raw_boxes(ax)
    draw_inventory(ax)
    draw_bundles(ax)
    draw_search_panel(ax)
    draw_delivery(ax)

    # Bottom value statement
    ax.add_patch(mpatches.FancyBboxPatch((1.0, 0.55), 12.0, 0.42,
                                         boxstyle="round,pad=0.03,rounding_size=0.1",
                                         facecolor="#0f172a", edgecolor="#0f172a",
                                         linewidth=1.0, zorder=3))
    ax.text(7, 0.76,
            "Twin value = faster data choice: volume + pipeline steps + readiness bars + workload fit in one spatial map",
            ha="center", va="center", fontsize=10.5, color="white",
            fontweight="bold", zorder=4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
