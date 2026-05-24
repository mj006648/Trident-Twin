"""Generate the v11 Trident-Twin Site Plan (top-down architectural view).

3-stage metallic model: Bronze (Raw) → Silver (Pipeline + Lakehouse) → Gold
(Showcase). Three separate buildings (Raw / Lakehouse / Showcase), a
Lobby+SearchCounter plaza in the LH-SC corridor, one Big Consolidation
Table, and three straight outgoing belts to three delivery trucks.

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

# Floor pad color per zone (top-down)
ZONE_PADS = [
    # (cx, cy, w, h, fill, edge, label)
    (-22, +25, 6, 6, "#c3d0e4", C_TOWER, "Zone 9\nControl Tower"),
    (-22, 0, 14, 8, "#c8c8c8", "#666666", "Zone 1\nTruck Yard"),
    (-4, 0, 19, 14, C_BRONZE_FILL, C_BRONZE, "Zone 2  Raw Bucket  (Bronze)"),
    (13, 0, 16, 7, C_SILVER_FILL, C_SILVER, "Zone 3  Pipeline  (Silver)"),
    (29, 0, 19, 14, C_SILVER_FILL, C_SILVER, "Zone 4  Lakehouse  (Silver)"),
    (29, 22, 19, 14, C_GOLD_FILL, C_GOLD, "Zone 5  Showcase  (Gold)"),
    (44, 10, 10, 11, C_LOBBY_FILL, C_LOBBY, "Zone 0+7\nLobby + Search"),
    (59, 10, 22, 14, C_DELIVERY_FILL, C_DELIVERY, "Zone 8  Delivery Docks"),
]

# Warehouse outlines (cx, cy, w, h, color, label)
BUILDINGS = [
    (-4, 0, 17, 12, C_BRONZE, "Raw Bucket\n17×12×6m"),
    (29, 0, 17, 12, C_SILVER, "Lakehouse\n17×12×6m"),
    (29, 22, 17, 12, C_GOLD, "Showcase\n17×12×6m"),
]

# Pipeline stations
STATIONS = [
    (7.0, "3-1\nProbing"),
    (10.0, "3-2\nArchitect"),
    (13.0, "3-3\nIceberg"),
    (16.0, "3-4\nMilvus"),
    (19.0, "3-5\nRedis"),
]

# Conveyors — list of (x1, y1, x2, y2, color, label, label_offset)
CONVEYORS = [
    # Inbound (bronze)
    (-17.9, 0.0, -12.3, 0.0, C_BRONZE, "Inbound (Bronze)", (0, 0.6)),
    # Pipeline main + express (silver)
    (4.7, -0.7, 20.4, -0.7, C_SILVER, "Main Line (Silver, Full Mode)", (0, -0.8)),
    (4.7, 0.7, 20.4, 0.7, C_SILVER, "Express Line (Silver, Delta Mode)", (0, 0.8)),
    # Promotion (gold) – drawn as Y belt, shifted west to clear the STAGING label
    (23.0, 6.0, 23.0, 16.0, C_GOLD, "Promotion (Gold)\nLH → Showcase", (-1.7, 0)),
    # LH → Big Table (silver)
    (37.5, 0.0, 52.0, 0.0, C_SILVER, "LH belt (Silver)", (0, -0.8)),
    (52.0, 0.0, 52.0, 4.5, C_SILVER, "", (0, 0)),
    # SC → Big Table (gold)
    (37.5, 22.0, 52.0, 22.0, C_GOLD, "SC belt (Gold)", (0, 0.8)),
    (52.0, 22.0, 52.0, 15.5, C_GOLD, "", (0, 0)),
    # Big Table → 3 trucks (straight)
    (54.0, 6.0, 61.5, 6.0, C_DELIVERY, "→ AI", (1.0, 0.6)),
    (54.0, 10.0, 61.5, 10.0, C_DELIVERY, "→ HPC", (1.0, 0.6)),
    (54.0, 14.0, 61.5, 14.0, C_DELIVERY, "→ HPDA", (1.0, 0.6)),
]

# Trucks (cx, cy, w, h, color, label)
TRUCKS = [
    (-20.5, 0, 7.0, 2.4, "#e63b3b", "Inbound Truck"),
    (64, 6, 5.6, 2.2, "#27a040", "AI Truck"),
    (64, 10, 4.8, 2.0, "#7d7f88", "HPC Van"),
    (64, 14, 5.0, 2.0, "#4a76d6", "HPDA Van"),
]

# Big Consolidation Table
BIG_TABLE = (52, 10, 4, 11)

# Lobby+SC plaza interior elements
LOBBY = (44, 10, 7, 7)  # plaza outline (lighter)

# Site bounds
X_MIN, X_MAX = -30, 72
Y_MIN, Y_MAX = -18, 32


def draw_grid(ax) -> None:
    ax.set_xticks(range(X_MIN, X_MAX + 1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX + 1, 5))
    ax.grid(which="major", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, label) -> None:
    rect = mpatches.Rectangle(
        (cx - w / 2, cy - h / 2), w, h,
        facecolor=fill, edgecolor=edge, linewidth=1.3, alpha=0.55, zorder=1,
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


def draw_station(ax, x, label) -> None:
    rect = mpatches.Rectangle((x - 0.9, -1.5), 1.8, 3.0,
                              facecolor="#fffbe6", edgecolor="#888800",
                              linewidth=1.0, zorder=5)
    ax.add_patch(rect)
    ax.text(x, 0, label, ha="center", va="center", fontsize=7,
            fontweight="bold", color="#444400", zorder=6)


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


def draw_big_table(ax, cx, cy, w, h) -> None:
    rect = mpatches.Rectangle((cx - w / 2, cy - h / 2), w, h,
                              facecolor="#8a5a3a", edgecolor="#3c2410",
                              linewidth=1.8, zorder=5)
    ax.add_patch(rect)
    # Edge rails (south=silver, north=gold)
    ax.plot([cx - w / 2, cx + w / 2], [cy - h / 2 + 0.05, cy - h / 2 + 0.05],
            color=C_SILVER, lw=2.5, zorder=6)
    ax.plot([cx - w / 2, cx + w / 2], [cy + h / 2 - 0.05, cy + h / 2 - 0.05],
            color=C_GOLD, lw=2.5, zorder=6)
    ax.text(cx, cy, "Big\nConsolidation\nTable\n4×11m",
            ha="center", va="center", fontsize=8.5, fontweight="bold",
            color="white", zorder=7)


def draw_lobby_interior(ax, cx, cy, w, h) -> None:
    # Reception desk + search counter (long N-S desk in plaza center)
    ax.plot([cx, cx], [cy - 1.7, cy + 1.7], color="#0d6e72",
            lw=8, solid_capstyle="round", zorder=5)
    ax.text(cx, cy, "Search\nCounter", ha="center", va="center",
            fontsize=7, color="white", fontweight="bold", zorder=6)


def draw_control_tower(ax, cx, cy) -> None:
    ax.add_patch(mpatches.Circle((cx, cy), 1.4, facecolor=C_TOWER,
                                  edgecolor="black", linewidth=1.2, zorder=5))
    ax.text(cx, cy, "Tower", ha="center", va="center", fontsize=7,
            color="white", fontweight="bold", zorder=6)


def draw_north_arrow(ax) -> None:
    nx, ny = X_MAX - 4, Y_MAX - 4
    ax.annotate("", xy=(nx, ny + 2.5), xytext=(nx, ny - 1.5),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.6,
                                mutation_scale=22), zorder=10)
    ax.text(nx, ny + 3, "N", ha="center", va="bottom",
            fontsize=12, fontweight="bold", zorder=10)
    ax.text(nx, ny - 2.5, "(data flow → +X)", ha="center", va="top",
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
                       label="Silver stage (Pipeline + Lakehouse)"),
        mpatches.Patch(facecolor=C_GOLD_FILL, edgecolor=C_GOLD,
                       label="Gold stage (Showcase)"),
        mpatches.Patch(facecolor=C_LOBBY_FILL, edgecolor=C_LOBBY,
                       label="Lobby + Search Counter"),
        mpatches.Patch(facecolor=C_DELIVERY_FILL, edgecolor=C_DELIVERY,
                       label="Delivery Yard"),
        Line2D([0], [0], color=C_BRONZE, lw=4, label="Bronze conveyor"),
        Line2D([0], [0], color=C_SILVER, lw=4, label="Silver conveyor"),
        Line2D([0], [0], color=C_GOLD, lw=4, label="Gold conveyor"),
        Line2D([0], [0], color=C_DELIVERY, lw=4, label="Dispatch conveyor"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9, framealpha=1.0, edgecolor="#888888",
              title="Legend (v11)", title_fontsize=10)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(22, 11))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")

    draw_grid(ax)

    for cx, cy, w, h, fill, edge, label in ZONE_PADS:
        draw_zone_pad(ax, cx, cy, w, h, fill, edge, label)

    for cx, cy, w, h, color, label in BUILDINGS:
        draw_building(ax, cx, cy, w, h, color, label)

    for x1, y1, x2, y2, color, label, off in CONVEYORS:
        draw_conveyor(ax, x1, y1, x2, y2, color, label, off)

    for x, label in STATIONS:
        draw_station(ax, x, label)

    draw_big_table(ax, *BIG_TABLE)
    draw_lobby_interior(ax, *LOBBY)
    draw_control_tower(ax, -22, +25)

    for cx, cy, w, h, color, label in TRUCKS:
        draw_truck(ax, cx, cy, w, h, color, label)

    draw_north_arrow(ax)
    draw_scale_bar(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin v11 Site Plan (Top View)\n"
        "3-stage metallic flow: Bronze (Raw) → Silver (Pipeline + Lakehouse) → Gold (Showcase) → Big Consolidation Table → AI/HPC/HPDA dock trucks\n"
        "1 unit = 1 m  ·  matches scripts/create_scene.py",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
