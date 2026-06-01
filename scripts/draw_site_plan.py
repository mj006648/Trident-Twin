"""Generate the Trident-Twin Site Plan (top-down architectural view).

Data Readiness / Usage Optimization model: Bronze (Raw) → Silver
(Refinement + Lakehouse Inventory/Staging) → Search/Selection → AI/HPC/HPDA Delivery.

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

# ---------------------------------------------------------------------------
# Metallic theme colors (mirror create_scene.py "metal_*" materials)
# ---------------------------------------------------------------------------
C_BRONZE = "#b87333"
C_BRONZE_FILL = "#e6c7a8"
C_SILVER = "#9fa5ab"
C_SILVER_FILL = "#dcdfe3"
C_GOLD = "#d4a017"
C_GOLD_FILL = "#f3dca8"
C_LOBBY = "#2dcad0"
C_LOBBY_FILL = "#bff0f2"
C_DELIVERY = "#8862e0"
C_DELIVERY_FILL = "#d9ccf5"
C_TOWER = "#4a6b9c"
C_OK = "#16a34a"
C_WARN = "#f59e0b"
C_BAD = "#ef4444"
C_PURPLE = "#8b5cf6"
C_RED = "#f43f5e"
C_GREEN = "#22c55e"

# Site bounds (per spec)
X_MIN, X_MAX = -30, 75
Y_MIN, Y_MAX = -12, 32

# ---------------------------------------------------------------------------
# Zone pads — (cx, cy, w, h, fill, edge, label)
# Coordinates match create_scene.py zone centers.
# ---------------------------------------------------------------------------
ZONE_PADS = [
    (-22, 25, 6, 6, "#c3d0e4", C_TOWER, "Zone 7\nControl Tower"),
    (-22, 0, 16, 8, C_BRONZE_FILL, C_BRONZE, "Zone 1\nTruck Yard"),
    (-4, 9, 21, 38, C_BRONZE_FILL, C_BRONZE, "Zone 2\nRaw Bucket (Bronze)"),
    (13, 0, 12, 7, C_SILVER_FILL, C_SILVER, "Zone 3\nAccumulation"),
    (29, 9, 21, 38, C_SILVER_FILL, C_SILVER, "Zone 4\nLakehouse (Silver/Gold)"),
    (44, 10, 10, 11, C_LOBBY_FILL, "#222222", "Zone 5\nSearch + Select"),
    (59, 9.5, 22, 20, C_DELIVERY_FILL, C_DELIVERY, "Zone 6\nWorkload Delivery"),
]

# Warehouse outlines (cx, cy, w, h, color, label)
BUILDINGS = [
    (-4, 9, 19, 32, C_BRONZE, "Raw Bucket\n19×32×6m"),
    (29, 9, 19, 32, C_SILVER, "Lakehouse\n19×32×6m"),
]

# Gates in Accumulation Zone (x position, label)
# Each gate straddles both pipeline belts (y=-0.7 and y=+0.7)
GATES = [
    (7,  "INGEST"),
    (10, "STAGE"),
    (13, "CLEAN"),
    (16, "TAG"),
    (19, "CATALOG"),
]

# Conveyors — list of (x1, y1, x2, y2, color, label, label_offset)
CONVEYORS = [
    # Ingest belt (bronze): x=-17 ~ -12, y=0
    (-17, 0.0, -12, 0.0, C_BRONZE, "Ingest Belt", (0, 0.9)),
    # Pipeline belts (silver): x=5 ~ 20
    (5, -0.7, 20, -0.7, C_SILVER, "Main Line (Full Mode)", (0, -1.0)),
    (5,  0.7, 20,  0.7, C_SILVER, "Express Line (Delta Mode)", (0, 1.0)),
    # LH -> Search: x=38 ~ 49, y=0
    (38, 0.0, 49, 0.0, C_SILVER, "LH -> Search", (0, -1.0)),
    # Delivery outbound x=52~62
    (52, 6.0,  62, 6.0,  C_DELIVERY, "-> AI",   (1.0, 0.6)),
    (52, 10.0, 62, 10.0, C_DELIVERY, "-> HPC",  (1.0, 0.6)),
    (52, 14.0, 62, 14.0, C_DELIVERY, "-> HPDA", (1.0, 0.6)),
]

# Trucks (cx, cy, w, h, color, label)
TRUCKS = [
    (-20.5, 0, 7.0, 2.4, "#e63b3b", "Ingest Truck"),
    (64, 6,  5.6, 2.2, "#27a040", "AI Truck"),
    (64, 10, 4.8, 2.0, "#7d7f88", "HPC Truck"),
    (64, 14, 5.0, 2.0, "#4a76d6", "HPDA Truck"),
]

# Lobby / Search panel
LOBBY = (44, 10, 7, 7)


def draw_grid(ax) -> None:
    ax.set_xticks(range(X_MIN, X_MAX + 1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX + 1, 5))
    ax.grid(which="major", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, label) -> None:
    rect = mpatches.Rectangle(
        (cx - w / 2, cy - h / 2), w, h,
        facecolor=fill, edgecolor=edge, linewidth=1.3, alpha=0.45, zorder=1,
    )
    ax.add_patch(rect)
    ax.text(cx, cy + h / 2 + 0.4, label,
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=edge, zorder=2)


def draw_building(ax, cx, cy, w, h, color, label) -> None:
    rect = mpatches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.3",
        facecolor="white", edgecolor=color, linewidth=2.4, zorder=3,
    )
    ax.add_patch(rect)
    ax.text(cx, cy, label, ha="center", va="center", fontsize=10,
            fontweight="bold", color=color, zorder=4,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="none", alpha=0.85))


def draw_gate(ax, x, label) -> None:
    """Draw a gate at x straddling the two pipeline belts (y=-0.7, y=+0.7).

    Gate shape: two vertical pillars at (x-0.15, x+0.15), spanning y=-1.5 to y=+1.5,
    with a horizontal crossbar at y=0.
    """
    pillar_left  = x - 0.18
    pillar_right = x + 0.18
    y_bot, y_top = -1.5, 1.5
    # Left pillar
    ax.add_patch(mpatches.Rectangle(
        (pillar_left - 0.12, y_bot), 0.24, y_top - y_bot,
        facecolor="#fffbe6", edgecolor="#888800", linewidth=1.0, zorder=5))
    # Right pillar
    ax.add_patch(mpatches.Rectangle(
        (pillar_right - 0.12, y_bot), 0.24, y_top - y_bot,
        facecolor="#fffbe6", edgecolor="#888800", linewidth=1.0, zorder=5))
    # Crossbar
    ax.plot([pillar_left - 0.12, pillar_right + 0.12], [0, 0],
            color="#888800", lw=2.5, zorder=6)
    ax.text(x, y_top + 0.3, label, ha="center", va="bottom", fontsize=7,
            fontweight="bold", color="#444400", zorder=7)


def draw_raw_inventory(ax) -> None:
    """Show raw objects as untagged brown boxes in Raw Bucket Zone."""
    # Raw Bucket: cx=-4, cy=9, sx=19, sy=32 -> interior y: -7 ~ 25
    positions = [
        (-8.2, 5.0), (-7.2, 5.0), (-6.2, 5.0), (-5.2, 5.0), (-4.2, 5.0),
        (-8.2, 6.2), (-7.2, 6.2), (-6.2, 6.2), (-5.2, 6.2),
        (-2.0, 5.0), (-1.0, 5.0), (0.0, 5.0), (1.0, 5.0),
    ]
    for x, y in positions:
        ax.add_patch(mpatches.Rectangle((x, y), 0.7, 0.55,
                                        facecolor=C_BRONZE, edgecolor="#6b3f1d",
                                        linewidth=0.7, alpha=0.75, zorder=6))
    ax.text(-4, 2.5, "Raw object count\nmetadata: none",
            ha="center", va="center", fontsize=7.5, fontweight="bold",
            color="#78350f", zorder=7,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor=C_BRONZE, alpha=0.92))


def draw_metadata_tag(ax, x, y, color, label="") -> None:
    ax.add_patch(mpatches.Circle((x, y), 0.12, facecolor=color,
                                 edgecolor="white", linewidth=0.5, zorder=8))
    if label:
        ax.text(x + 0.18, y + 0.05, label, ha="left", va="center",
                fontsize=5.8, color=color, fontweight="bold", zorder=9)


def draw_inventory_boxes(ax) -> None:
    """Show Lakehouse inventory density — lower half of Lakehouse (y=0~13).

    Lakehouse zone: cx=29, cy=9, sx=19, sy=32
    Storage table area: y=0 ~ 13 (lower half).
    """
    rows = [
        ("camera",  2.5, 7, C_OK),
        ("lidar",   4.5, 5, C_WARN),
        ("weather", 6.5, 4, C_BAD),
        ("gps",     8.5, 3, C_OK),
    ]
    x0 = 22.2
    for label, y, count, quality_color in rows:
        ax.plot([21.5, 36.3], [y - 0.35, y - 0.35],
                color="#475569", lw=1.6, zorder=6)
        ax.text(21.8, y + 0.35, label, ha="left", va="center",
                fontsize=7.5, fontweight="bold", color="#334155", zorder=7)
        for i in range(count):
            x = x0 + 1.25 + i * 1.15
            ax.add_patch(mpatches.Rectangle((x, y - 0.05), 0.72, 0.52,
                                            facecolor="#f8fafc", edgecolor=C_SILVER,
                                            linewidth=0.9, zorder=7))
            if i < 3:
                draw_metadata_tag(ax, x + 0.62, y + 0.45, C_PURPLE, "" if i else "semantic")
            if i in (1, 3):
                draw_metadata_tag(ax, x + 0.14, y + 0.45, C_RED, "" if i != 1 else "location")
        ax.add_patch(mpatches.Circle((35.8, y + 0.25), 0.25,
                                     facecolor=quality_color, edgecolor="white",
                                     linewidth=1.0, zorder=8))
    ax.text(29, 0.0, "Inventory = table count + volume + tags + readiness\n(schema · quality · lineage · semantic · location · policy)",
            ha="center", va="center", fontsize=7.5, color="#334155",
            fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                      edgecolor=C_SILVER, alpha=0.95))


def draw_staging_bundles(ax) -> None:
    """Show curated ready-to-use bundles in Lakehouse upper half (y=14~26).

    Lakehouse zone: cx=29, cy=9, sx=19, sy=32
    Staging/bookshelf area: y=14 ~ 27 (upper half).
    """
    bundles = [
        (22.0, 22.0, "camera+lidar", "AI fit 92%"),
        (26.0, 22.0, "weather+gps", "HPDA fit 78%"),
        (30.0, 22.0, "hot basket", "used 2h ago"),
        (34.0, 22.0, "materialized\ncollection", "policy OK"),
        (24.0, 18.5, "semantic\ncandidate", "confidence high"),
        (29.0, 18.5, "joined\nbundle", "quality 0.88"),
        (34.0, 18.5, "cache-warm\nbundle", "Redis hot"),
    ]
    for x, y, title, sub in bundles:
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 1.35, y - 0.55), 2.7, 1.1,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor="#fffbeb", edgecolor=C_GOLD,
            linewidth=1.3, zorder=7))
        ax.text(x, y + 0.16, title, ha="center", va="center",
                fontsize=6.8, fontweight="bold", color="#78350f", zorder=8)
        ax.text(x, y - 0.30, sub, ha="center", va="center",
                fontsize=5.9, color="#92400e", zorder=8)
    # Divider line between storage (lower) and staging (upper)
    ax.plot([19.5, 38.5], [13.5, 13.5], color=C_GOLD,
            lw=1.5, linestyle="--", zorder=6, alpha=0.7)
    ax.text(29, 14.2, "-- Staging (Bookshelf) --", ha="center", va="bottom",
            fontsize=7.5, color="#78350f", fontweight="bold", zorder=7)
    ax.text(29, 13.0, "-- Storage (Tables) --", ha="center", va="top",
            fontsize=7.5, color="#334155", fontweight="bold", zorder=7)


def draw_search_decision_panel(ax) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (40.2, 5.4), 7.6, 8.9,
        boxstyle="round,pad=0.05,rounding_size=0.16",
        facecolor="white", edgecolor=C_LOBBY,
        linewidth=1.6, zorder=6))
    ax.text(44, 13.35, "Search / Selection", ha="center", va="center",
            fontsize=8.5, color="#0e7490", fontweight="bold", zorder=7)
    ax.text(44, 12.35, '"camera + lidar"', ha="center", va="center",
            fontsize=8, color="#0f172a", fontweight="bold", zorder=7)
    for i, (txt, col) in enumerate([
        ("highlight\ncandidates", C_LOBBY),
        ("compare\nreadiness", C_OK),
        ("explain\nmissing tags", C_WARN),
        ("pick\nbundle", C_GOLD),
    ]):
        ax.add_patch(mpatches.FancyBboxPatch(
            (41.0 + (i % 2) * 3.15, 9.3 - (i // 2) * 2.1), 2.5, 1.35,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor="#f8fafc", edgecolor=col, linewidth=1.1, zorder=7))
        ax.text(42.25 + (i % 2) * 3.15, 9.98 - (i // 2) * 2.1, txt,
                ha="center", va="center", fontsize=6.7, color=col,
                fontweight="bold", zorder=8)


def draw_readiness_callouts(ax) -> None:
    callouts = [
        (13, -5.0, "Gates: INGEST/STAGE/CLEAN/TAG/CATALOG\naccumulation before pipeline", C_SILVER),
        (43.5, 2.1, "Twin value:\nfaster choice, not just 3D view", C_LOBBY),
        (59.0, 1.5, "Delivery outputs:\nURI · SQL · Spark snippet", C_DELIVERY),
    ]
    for x, y, txt, col in callouts:
        ax.text(x, y, txt, ha="center", va="center", fontsize=7.2,
                color=col, fontweight="bold", zorder=9,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor=col, linewidth=1.0, alpha=0.95))


def draw_conveyor(ax, x1, y1, x2, y2, color, label, label_offset) -> None:
    ax.plot([x1, x2], [y1, y2], color=color, lw=4.5,
            solid_capstyle="round", zorder=4, alpha=0.85)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=8, fontweight="bold", color=color, zorder=7,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                          edgecolor=color, linewidth=0.8, alpha=0.95))


def draw_truck(ax, cx, cy, w, h, color, label) -> None:
    rect = mpatches.Rectangle((cx - w / 2, cy - h / 2), w, h,
                              facecolor=color, edgecolor="black",
                              linewidth=1.0, alpha=0.75, zorder=6)
    ax.add_patch(rect)
    ax.text(cx, cy, label, ha="center", va="center", fontsize=7.5,
            fontweight="bold", color="white", zorder=7)


def draw_lobby_interior(ax, cx, cy, w, h) -> None:
    ax.plot([cx, cx], [cy - 1.7, cy + 1.7], color="#0d6e72",
            lw=8, solid_capstyle="round", zorder=5)
    ax.text(cx, cy, "Intent\nCounter", ha="center", va="center",
            fontsize=7, color="#111111", fontweight="bold", zorder=6)


def draw_control_tower(ax, cx, cy) -> None:
    ax.add_patch(mpatches.Circle((cx, cy), 1.4, facecolor=C_TOWER,
                                  edgecolor="black", linewidth=1.2, zorder=5))
    ax.text(cx, cy, "Tower", ha="center", va="center", fontsize=7,
            color="white", fontweight="bold", zorder=6)


def draw_north_arrow(ax) -> None:
    nx, ny = X_MAX - 5, Y_MAX - 5
    ax.annotate("", xy=(nx, ny + 2.5), xytext=(nx, ny - 1.5),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.6,
                                mutation_scale=22), zorder=10)
    ax.text(nx, ny + 3, "N", ha="center", va="bottom",
            fontsize=12, fontweight="bold", zorder=10)
    ax.text(nx, ny - 2.5, "(data flow -> +X)", ha="center", va="top",
            fontsize=8, color="#666666", zorder=10)


def draw_scale_bar(ax) -> None:
    x0, y0 = X_MIN + 2, Y_MIN + 2
    ax.plot([x0, x0 + 10], [y0, y0], color="black", lw=3.0, zorder=10)
    for x_off in (0, 5, 10):
        ax.plot([x0 + x_off, x0 + x_off], [y0 - 0.5, y0 + 0.5],
                color="black", lw=1.0, zorder=10)
    ax.text(x0 + 5, y0 - 1.4, "0       5       10 m",
            ha="center", va="top", fontsize=9, zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=C_BRONZE_FILL, edgecolor=C_BRONZE,
                       label="Bronze stage (Raw)"),
        mpatches.Patch(facecolor=C_SILVER_FILL, edgecolor=C_SILVER,
                       label="Silver/Gold stage (Lakehouse)"),
        mpatches.Patch(facecolor=C_LOBBY_FILL, edgecolor=C_LOBBY,
                       label="Search / Selection Counter"),
        mpatches.Patch(facecolor=C_DELIVERY_FILL, edgecolor=C_DELIVERY,
                       label="Workload Delivery Yard"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=C_PURPLE,
               markersize=8, label="Milvus semantic tag"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=C_RED,
               markersize=8, label="Redis location/share tag"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=C_OK,
               markersize=8, label="Readiness / policy OK"),
        Line2D([0], [0], color=C_BRONZE, lw=4, label="Bronze conveyor"),
        Line2D([0], [0], color=C_SILVER, lw=4, label="Silver conveyor"),
        Line2D([0], [0], color=C_DELIVERY, lw=4, label="Dispatch conveyor"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9, framealpha=1.0, edgecolor="#888888",
              title="Legend (Data Readiness)", title_fontsize=10)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(24, 13))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")

    draw_grid(ax)

    for cx, cy, w, h, fill, edge, label in ZONE_PADS:
        draw_zone_pad(ax, cx, cy, w, h, fill, edge, label)

    for cx, cy, w, h, color, label in BUILDINGS:
        draw_building(ax, cx, cy, w, h, color, label)

    draw_raw_inventory(ax)
    draw_inventory_boxes(ax)
    draw_staging_bundles(ax)

    for x1, y1, x2, y2, color, label, off in CONVEYORS:
        draw_conveyor(ax, x1, y1, x2, y2, color, label, off)

    for x, label in GATES:
        draw_gate(ax, x, label)

    draw_lobby_interior(ax, *LOBBY)
    draw_search_decision_panel(ax)
    draw_control_tower(ax, -22, 25)

    for cx, cy, w, h, color, label in TRUCKS:
        draw_truck(ax, cx, cy, w, h, color, label)

    draw_readiness_callouts(ax)
    draw_north_arrow(ax)
    draw_scale_bar(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin Site Plan -- Data Readiness / Usage Optimization Map (Top View)\n"
        "Bronze raw objects -> Silver/Gold Lakehouse (storage + staging) -> Search/Selection -> AI/HPC/HPDA delivery\n"
        "1 unit = 1 m  .  matches scripts/create_scene.py",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) -- data flow direction ->", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
