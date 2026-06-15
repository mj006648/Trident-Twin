"""Generate a generic Trident-Twin site plan schematic.

This diagram is intentionally data-independent. It must show stable zones,
flows, and roles only; dataset/table names belong to live scene generation and
actual screenshots, not to the reusable architecture diagram.

Output:
    docs/site-plan.png
    docs/site-plan-v2.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "docs" / "site-plan.png"
OUT_V2 = BASE / "docs" / "site-plan-v2.png"

C_RAW = "#b87333"
C_RAW_FILL = "#ead1b8"
C_ACC = "#64748b"
C_ACC_FILL = "#e2e8f0"
C_DATA = "#2563eb"
C_DATA_FILL = "#dbeafe"
C_META = "#b45309"
C_META_FILL = "#fef3c7"
C_STAGE = "#d97706"
C_STAGE_FILL = "#ffedd5"
C_SEARCH = "#0891b2"
C_SEARCH_FILL = "#cffafe"
C_DELIVERY = "#7c3aed"
C_DELIVERY_FILL = "#ddd6fe"
C_TOWER = "#334155"
C_AI = "#16a34a"
C_HPC = "#64748b"
C_HPDA = "#2563eb"

X_MIN, X_MAX = -30, 76
Y_MIN, Y_MAX = -12, 34

ZONE_PADS = [
    (-22, 0, 14, 7, C_RAW_FILL, C_RAW, "Intake"),
    (-4, 11, 20, 30, C_RAW_FILL, C_RAW, "Raw Bucket Zone"),
    (13, 0, 15, 7, C_ACC_FILL, C_ACC, "Accumulation Zone"),
    (29, 7, 20, 20, C_DATA_FILL, C_ACC, "Lakehouse Zone"),
    (29, 22.5, 20, 9, C_STAGE_FILL, C_STAGE, "Data Staging Zone"),
    (44, 10, 10, 12, C_SEARCH_FILL, C_SEARCH, "Search Zone"),
    (61, 9.5, 22, 18, C_DELIVERY_FILL, C_DELIVERY, "Delivery Zone"),
]

BUILDINGS = [
    (-4, 11, 18.5, 28, C_RAW),
    (29, 7, 18.5, 18, C_ACC),
    (29, 22.5, 18.5, 7, C_STAGE),
]

STATIONS = [
    (5.6, 10.15, "1", "#f59e0b"),
    (10.15, 15.05, "2", "#22c55e"),
    (15.05, 19.6, "3", "#06b6d4"),
]

CONVEYORS = [
    (-18.0, 0.0, -13.0, 0.0, C_RAW, "", (0, 0)),
    (4.8, -0.8, 20.0, -0.8, C_ACC, "", (0, 0)),
    (4.8, 0.8, 20.0, 0.8, C_ACC, "", (0, 0)),
    (38.5, 5.0, 48.8, 5.0, C_ACC, "", (0, 0)),
    (48.8, 5.0, 48.8, 9.5, C_ACC, "", (0, 0)),
    (48.8, 9.5, 50.2, 9.5, C_ACC, "", (0, 0)),
    (38.5, 22.5, 49.4, 22.5, C_STAGE, "", (0, 0)),
    (49.4, 22.5, 49.4, 14.5, C_STAGE, "", (0, 0)),
    (49.4, 14.5, 50.2, 14.5, C_STAGE, "", (0, 0)),
    (53.8, 6.0, 68.5, 6.0, C_AI, "", (0, 0)),
    (53.8, 9.5, 68.5, 9.5, C_HPC, "", (0, 0)),
    (53.8, 13.0, 68.5, 13.0, C_HPDA, "", (0, 0)),
]

TRUCKS = [
    (-20.8, 0.0, 5.8, 2.2, "#ef4444", ""),
    (70.0, 6.0, 4.8, 2.0, C_AI, "AI"),
    (70.0, 9.5, 4.8, 2.0, C_HPC, "HPC"),
    (70.0, 13.0, 4.8, 2.0, C_HPDA, "HPDA"),
]

BIG_TABLE = (52.0, 9.5, 3.6, 10.2)


def draw_grid(ax) -> None:
    ax.set_xticks(range(X_MIN, X_MAX + 1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX + 1, 5))
    ax.grid(which="major", color="#e2e8f0", linewidth=0.55)
    ax.set_axisbelow(True)


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, label) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.42",
        facecolor=fill, edgecolor=edge, linewidth=1.55, alpha=0.48, zorder=1,
    ))
    ax.text(cx, cy + h / 2 + 0.45, label, ha="center", va="bottom",
            fontsize=10.5, color=edge, fontweight="bold", zorder=8)


def draw_building(ax, cx, cy, w, h, color) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.24",
        facecolor="white", edgecolor=color, linewidth=1.9, alpha=0.90, zorder=3,
    ))


def draw_conveyor(ax, x1, y1, x2, y2, color, label="", off=(0, 0)) -> None:
    ax.plot([x1, x2], [y1, y2], color=color, lw=4.5, solid_capstyle="round", alpha=0.80, zorder=4)


def draw_station(ax, x0, x1, label, color) -> None:
    ax.add_patch(mpatches.Rectangle((x0, -3.15), x1 - x0, 6.3,
                                    facecolor=color, edgecolor="white", linewidth=1.2,
                                    alpha=0.16, zorder=2))
    ax.plot([x0, x0], [-3.15, 3.15], color="#475569", lw=1.0, alpha=0.42, zorder=4)
    ax.text((x0 + x1) / 2, 0.0, label, ha="center", va="center",
            fontsize=17, color="#111827", fontweight="bold", zorder=9)


def draw_raw_inventory(ax) -> None:
    xs = [-9.8, -4.0, 1.8]
    ys = [18.2, 11.0, 3.8]
    for y in ys:
        for x in xs:
            ax.add_patch(mpatches.FancyBboxPatch((x - 2.35, y - 1.8), 4.7, 3.3,
                                                 boxstyle="round,pad=0.02,rounding_size=0.10",
                                                 facecolor="#fff7ed", edgecolor=C_RAW,
                                                 linewidth=1.0, alpha=0.90, zorder=5))
            for i in range(5):
                bx = x - 1.40 + (i % 3) * 0.95
                by = y - 0.86 + (i // 3) * 0.72
                ax.add_patch(mpatches.Rectangle((bx, by), 0.66, 0.42,
                                                facecolor=C_RAW, edgecolor="#7c2d12",
                                                linewidth=0.7, alpha=0.82, zorder=6))
    ax.text(-4.0, 24.4, "dataset slots", ha="center", va="center",
            fontsize=7.8, color="#7c2d12", fontweight="bold", zorder=9)


def draw_table_crate(ax, x, y, meta=False, scale=1.0) -> None:
    face = C_META_FILL if meta else C_DATA_FILL
    edge = C_META if meta else C_DATA
    ax.add_patch(mpatches.Rectangle((x - 0.45 * scale, y - 0.42 * scale), 0.90 * scale, 0.08 * scale,
                                    facecolor="#94a3b8", edgecolor="#475569", linewidth=0.35, zorder=6))
    ax.add_patch(mpatches.FancyBboxPatch((x - 0.38 * scale, y - 0.22 * scale), 0.76 * scale, 0.44 * scale,
                                         boxstyle="round,pad=0.01,rounding_size=0.035",
                                         facecolor=face, edgecolor=edge, linewidth=0.8, zorder=7))


def draw_inventory_boxes(ax) -> None:
    xs = [24.0, 30.0, 36.0]
    ys = [11.4, 4.0]
    for y in ys:
        for x in xs:
            ax.add_patch(mpatches.FancyBboxPatch((x - 2.45, y - 2.25), 4.9, 4.15,
                                                 boxstyle="round,pad=0.02,rounding_size=0.10",
                                                 facecolor="#f8fafc", edgecolor=C_ACC,
                                                 linewidth=1.0, alpha=0.95, zorder=5))
            for i in range(8):
                tx = x - 1.45 + (i % 4) * 0.96
                ty = y + 0.70 - (i // 4) * 0.92
                draw_table_crate(ax, tx, ty, meta=(i in {2, 5}), scale=0.88)
    ax.text(30.0, 15.9, "data + metadata tables", ha="center", va="center",
            fontsize=7.8, color="#334155", fontweight="bold", zorder=9)


def draw_staging_bundles(ax) -> None:
    for y in (20.6, 22.5, 24.4):
        ax.add_patch(mpatches.FancyBboxPatch((20.4, y - 0.30), 17.2, 0.60,
                                             boxstyle="round,pad=0.01,rounding_size=0.08",
                                             facecolor="#fed7aa", edgecolor=C_STAGE,
                                             linewidth=1.0, alpha=0.60, zorder=5))
    for i, (x, y) in enumerate([(23.5, 22.5), (29.0, 22.5), (34.5, 22.5)]):
        ax.add_patch(mpatches.FancyBboxPatch((x - 1.55, y - 0.58), 3.1, 1.05,
                                             boxstyle="round,pad=0.02,rounding_size=0.10",
                                             facecolor="#fff7ed", edgecolor=C_STAGE,
                                             linewidth=1.2, zorder=6))
        for j in range(3):
            draw_table_crate(ax, x - 0.65 + j * 0.65, y - 0.02, meta=(j == 2), scale=0.55)
    ax.text(29.0, 25.65, "saved bundles", ha="center", va="center",
            fontsize=7.8, color="#7c2d12", fontweight="bold", zorder=9)


def draw_search_decision_panel(ax) -> None:
    x, y, w, h = 40.6, 6.4, 6.8, 7.2
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                                         boxstyle="round,pad=0.04,rounding_size=0.18",
                                         facecolor="white", edgecolor=C_SEARCH,
                                         linewidth=1.7, zorder=6))
    ax.text(x + w / 2, y + h - 1.15, "search", ha="center", va="center",
            fontsize=10.5, color=C_SEARCH, fontweight="bold", zorder=8)
    for i in range(4):
        yy = y + h - 2.35 - i * 1.0
        ax.add_patch(mpatches.FancyBboxPatch((x + 0.75, yy - 0.24), w - 1.5, 0.48,
                                             boxstyle="round,pad=0.02,rounding_size=0.06",
                                             facecolor="#ecfeff", edgecolor="#67e8f9", linewidth=0.75, zorder=7))
    ax.text(x + w / 2, y + 0.72, "select → ask", ha="center", va="center",
            fontsize=7.2, color="#155e75", fontweight="bold", zorder=8)


def draw_big_table(ax, cx, cy, w, h) -> None:
    ax.add_patch(mpatches.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                         boxstyle="round,pad=0.02,rounding_size=0.12",
                                         facecolor="#8b5e34", edgecolor="#3f2a16",
                                         linewidth=1.8, zorder=6))
    ax.text(cx, cy, "Big\nTable", ha="center", va="center", fontsize=8.5,
            color="white", fontweight="bold", zorder=8)


def draw_lobby_interior(ax, *args, **kwargs) -> None:
    pass


def draw_control_tower(ax, cx=-22, cy=25) -> None:
    ax.add_patch(mpatches.Circle((cx, cy), 1.55, facecolor=C_TOWER,
                                  edgecolor="#0f172a", linewidth=1.2, zorder=6))
    ax.text(cx, cy, "Tower", ha="center", va="center", fontsize=7.2,
            color="white", fontweight="bold", zorder=8)
    ax.add_patch(mpatches.Rectangle((cx - 0.45, cy - 5.0), 0.9, 4.0,
                                    facecolor="#94a3b8", edgecolor="#334155", zorder=5))


def draw_readiness_callouts(ax) -> None:
    ax.text(13.0, -5.45, "Start Live animates ingest progress", ha="center", va="center",
            fontsize=7.4, color="#334155",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor=C_ACC, alpha=0.95), zorder=9)
    ax.text(57.0, 18.0, "Gemma ask triggers copy + delivery", ha="center", va="center",
            fontsize=7.4, color="#4c1d95",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor=C_DELIVERY, alpha=0.95), zorder=9)


def draw_truck(ax, cx, cy, w, h, color, label="") -> None:
    ax.add_patch(mpatches.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                         boxstyle="round,pad=0.02,rounding_size=0.14",
                                         facecolor=color, edgecolor="#0f172a",
                                         linewidth=1.0, alpha=0.88, zorder=7))
    if label:
        ax.text(cx, cy, label, ha="center", va="center", fontsize=7.5,
                color="white", fontweight="bold", zorder=8)


def draw_scale_bar(ax) -> None:
    x0, y0 = X_MIN + 2, Y_MIN + 2
    ax.plot([x0, x0 + 10], [y0, y0], color="#111827", lw=3, zorder=10)
    for tick in (0, 5, 10):
        ax.plot([x0 + tick, x0 + tick], [y0 - 0.45, y0 + 0.45], color="#111827", lw=1, zorder=10)
    ax.text(x0 + 5, y0 - 1.25, "0    5    10 m", ha="center", va="top", fontsize=8.5, zorder=10)


def draw_north_arrow(ax) -> None:
    nx, ny = X_MAX - 6, Y_MAX - 6
    ax.annotate("", xy=(nx, ny + 2.6), xytext=(nx, ny - 1.4),
                arrowprops=dict(arrowstyle="-|>", color="#111827", lw=1.7, mutation_scale=22), zorder=10)
    ax.text(nx, ny + 3.1, "N", ha="center", va="bottom", fontsize=12, fontweight="bold", zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=C_RAW_FILL, edgecolor=C_RAW, label="Raw slots"),
        mpatches.Patch(facecolor=C_DATA_FILL, edgecolor=C_DATA, label="Data table"),
        mpatches.Patch(facecolor=C_META_FILL, edgecolor=C_META, label="Metadata table"),
        mpatches.Patch(facecolor=C_STAGE_FILL, edgecolor=C_STAGE, label="Staged bundle"),
        Line2D([0], [0], color=C_AI, lw=4, label="AI bus"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=8.8, framealpha=1.0, edgecolor="#94a3b8", title="Legend", title_fontsize=10)


def draw_facility(ax) -> None:
    for pad in ZONE_PADS:
        draw_zone_pad(ax, *pad)
    for building in BUILDINGS:
        draw_building(ax, *building)
    draw_raw_inventory(ax)
    draw_inventory_boxes(ax)
    draw_staging_bundles(ax)
    for station in STATIONS:
        draw_station(ax, *station)
    for conveyor in CONVEYORS:
        draw_conveyor(ax, *conveyor)
    draw_big_table(ax, *BIG_TABLE)
    draw_search_decision_panel(ax)
    draw_control_tower(ax)
    draw_readiness_callouts(ax)
    for truck in TRUCKS:
        draw_truck(ax, *truck)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(27, 13.5))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    draw_grid(ax)
    draw_facility(ax)
    draw_scale_bar(ax)
    draw_north_arrow(ax)
    draw_legend(ax)
    ax.set_title(
        "Trident-Twin Generic Site Plan — Stable Zones and Flows",
        fontsize=14, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)
    plt.tight_layout()
    for out in (OUT, OUT_V2):
        plt.savefig(out, dpi=160, facecolor="white", bbox_inches="tight")
        print(f"wrote {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
