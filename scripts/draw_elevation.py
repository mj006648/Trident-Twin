"""Generate the Trident-Twin Data Readiness Elevation View (side view from -Y).

Companion to docs/site-plan.png. The Site Plan shows the X-Y plane;
this Elevation shows the X-Z plane so vertical stacking becomes visible.

Side view from -Y looking north. The main data flow at Y=0 (Raw → Pipeline →
Lakehouse → Big Table → AI truck row) is the primary subject. Showcase and
the HPC/HPDA trucks sit at Y=+22 / Y=+10 / Y=+14 respectively and are
indicated with offset annotation rather than drawn in their occluded
positions.

Output: docs/elevation.png

Stdlib + matplotlib only.

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

# Metallic theme colors
C_BRONZE = "#b87333"
C_BRONZE_FILL = "#e6c7a8"
C_SILVER = "#9fa5ab"
C_SILVER_FILL = "#dcdfe3"
C_GOLD = "#d4a017"
C_GOLD_FILL = "#f3dca8"
C_LOBBY = "#2dcad0"
C_DELIVERY = "#8862e0"

# ---------------------------------------------------------------------------
# Buildings (side view): cx, cz_floor, w, h, edge_color, fill_color, label
# ---------------------------------------------------------------------------
# Heights are real z (m). Warehouses are 6m tall, on a floor pad ~0.1m thick.
BUILDINGS = [
    (-4, 0.1, 17, 6.0, C_BRONZE, C_BRONZE_FILL, "Raw Bucket\n(Bronze warehouse)"),
    (29, 0.1, 17, 6.0, C_SILVER, C_SILVER_FILL, "Lakehouse Inventory\n(table crates + tags)"),
]

# Showcase shown as DASHED behind LH (Y=+22) — annotation only
SHOWCASE_GHOST = (29, 0.1, 17, 6.0, "Staging / Ready Bundles — curated shelf at Y=+22")

# Pipeline stations (5)
STATIONS = [
    (7.0, "3-1\nProbing"),
    (10.0, "3-2\nArchitect"),
    (13.0, "3-3\nIceberg\ntable"),
    (16.0, "3-4\nSemantic\ntag"),
    (19.0, "3-5\nLocation\ntag"),
]
STATION_H = 3.0  # canopy height

# Conveyors (X-axis belts at z=0.7) — (x1, x2, color, label)
CONVEYORS_X = [
    (-17.9, -12.3, C_BRONZE, "Inbound (Bronze)"),
    (4.7, 20.4, C_SILVER, "Pipeline belts (Silver)"),
    (37.5, 52.0, C_SILVER, "Inventory candidates"),
    (54.0, 61.5, C_DELIVERY, "Workload package"),
]

# Big Table (cx, cz_floor, w, table_top_h, leg_h)
BIG_TABLE = (52, 0.1, 4, 0.10, 0.80)

# Inbound truck (cx, cz_floor, body parts)
# Trailer: cx=-20.5, body z=0.95 to 3.55, length 5
# Cab: cx=-22.5, body z=0.95 to 3.15, length 2
INBOUND_TRUCK = {
    "trailer": (-20.5, 0.95, 5.0, 2.6, "#e63b3b"),
    "cab": (-22.5, 0.95, 2.0, 2.2, "#e63b3b"),
    "wheels": [(-18.5, 0, 0.5), (-22.5, 0, 0.5)],  # (cx, cz_bottom, radius)
}

# AI delivery truck (rear at X=62, cab to +X side)
AI_TRUCK = {
    "body": (63.9, 0.95, 3.8, 2.2, "#27a040"),     # body west of cab
    "cab": (66.6, 0.95, 1.4, 1.6, "#27a040"),       # cab east of body
    "wheels": [(62.8, 0, 0.42), (66.6, 0, 0.42)],
}

# Control Tower (at X=-22, side view shows tall structure)
TOWER = {
    "base": (-22, 0.1, 3.2, 1.1, "#888888"),
    "shaft": (-22, 1.2, 1.0, 9.0, "#444444"),
    "deck": (-22, 10.2, 3.8, 2.0, "#3a5d8f"),
    "antenna": (-22, 12.2, 0.12, 1.6, "#222222"),
    "tip_y": 14.0,
}

# Frame bounds
X_MIN, X_MAX = -28, 72
Z_MIN, Z_MAX = -1.0, 14.5


def draw_grid(ax) -> None:
    ax.set_xticks(range(X_MIN, X_MAX + 1, 5))
    ax.set_yticks(range(int(Z_MIN), int(Z_MAX) + 1, 1))
    ax.grid(which="major", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


def draw_ground(ax) -> None:
    ax.axhline(0, color="#444444", linewidth=1.2, zorder=2)
    for x in range(X_MIN + 2, X_MAX, 4):
        ax.plot([x, x - 0.5], [0, -0.4], color="#888888", lw=0.6, zorder=2)


def draw_building(ax, cx, cz, w, h, edge, fill, label) -> None:
    rect = mpatches.FancyBboxPatch(
        (cx - w / 2, cz), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.3",
        facecolor=fill, edgecolor=edge, linewidth=2.4, alpha=0.4, zorder=3,
    )
    ax.add_patch(rect)
    # Frame lines for steel structure feel
    ax.plot([cx - w / 2, cx + w / 2], [cz + h, cz + h],
            color=edge, lw=2.0, zorder=4)
    ax.plot([cx - w / 2, cx - w / 2], [cz, cz + h],
            color=edge, lw=2.0, zorder=4)
    ax.plot([cx + w / 2, cx + w / 2], [cz, cz + h],
            color=edge, lw=2.0, zorder=4)
    ax.text(cx, cz + h * 0.55, label, ha="center", va="center", fontsize=10,
            fontweight="bold", color=edge, zorder=5,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="none", alpha=0.85))


def draw_showcase_ghost(ax) -> None:
    cx, cz, w, h, note = SHOWCASE_GHOST
    rect = mpatches.FancyBboxPatch(
        (cx - w / 2, cz + 6.5), w, h,  # offset up for visual separation
        boxstyle="round,pad=0.0,rounding_size=0.3",
        facecolor=C_GOLD_FILL, edgecolor=C_GOLD, linewidth=1.8,
        linestyle=(0, (8, 4)), alpha=0.35, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(cx, cz + 6.5 + h / 2, note, ha="center", va="center",
            fontsize=9, style="italic", color=C_GOLD, fontweight="bold",
            zorder=3)


def draw_station(ax, x, label) -> None:
    # Steel canopy
    ax.plot([x - 0.9, x - 0.9, x + 0.9, x + 0.9],
            [0.1, 0.1 + STATION_H, 0.1 + STATION_H, 0.1],
            color=C_SILVER, lw=1.6, zorder=4)
    ax.add_patch(mpatches.Rectangle(
        (x - 0.9, 0.1), 1.8, STATION_H,
        facecolor="#fffbe6", edgecolor="none", alpha=0.5, zorder=3))
    ax.text(x, 0.1 + STATION_H * 0.55, label,
            ha="center", va="center", fontsize=7, fontweight="bold",
            color="#444400", zorder=5)


def draw_conveyor(ax, x1, x2, color, label) -> None:
    z_top = 0.7
    # Belt surface
    ax.plot([x1, x2], [z_top, z_top], color=color, lw=5.0,
            solid_capstyle="round", zorder=4)
    # Support legs
    leg_h = 0.6
    n_legs = max(2, int((x2 - x1) / 2.5))
    for i in range(n_legs + 1):
        x = x1 + i * ((x2 - x1) / n_legs)
        ax.plot([x, x], [0, z_top - 0.03], color=color, lw=1.0,
                alpha=0.6, zorder=3)
    # Label
    mx = (x1 + x2) / 2
    ax.text(mx, z_top + 0.45, label, ha="center", va="bottom",
            fontsize=8, fontweight="bold", color=color, zorder=6,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor=color, linewidth=0.8, alpha=0.95))


def draw_big_table(ax) -> None:
    cx, cz_floor, w, top_h, leg_h = BIG_TABLE
    # Table top
    ax.add_patch(mpatches.Rectangle(
        (cx - w / 2, cz_floor + leg_h), w, top_h,
        facecolor="#8a5a3a", edgecolor="#3c2410", linewidth=1.4, zorder=5))
    # Legs (just 2 visible in side view)
    for x in (cx - w / 2 + 0.15, cx + w / 2 - 0.15):
        ax.plot([x, x], [cz_floor, cz_floor + leg_h],
                color="#3c2410", lw=2.4, zorder=5)
    ax.text(cx, cz_floor + leg_h + 0.5, "Big Table\nz_top=0.85m",
            ha="center", va="bottom", fontsize=7, fontweight="bold",
            color="#3c2410", zorder=6)


def draw_truck_body(ax, cx, cz, w, h, color) -> None:
    ax.add_patch(mpatches.Rectangle(
        (cx - w / 2, cz), w, h,
        facecolor=color, edgecolor="black", linewidth=1.0, zorder=6))


def draw_wheel(ax, cx, cz_bottom, r) -> None:
    ax.add_patch(mpatches.Circle((cx, cz_bottom + r), r,
                                  facecolor="#1a1a1a", edgecolor="black",
                                  linewidth=0.8, zorder=7))


def draw_inbound_truck(ax) -> None:
    t = INBOUND_TRUCK["trailer"]
    c = INBOUND_TRUCK["cab"]
    draw_truck_body(ax, *t)
    draw_truck_body(ax, *c)
    for wx, wz, r in INBOUND_TRUCK["wheels"]:
        draw_wheel(ax, wx, wz, r)
    ax.text(t[0], t[1] + t[3] + 0.4, "Inbound\nTruck",
            ha="center", va="bottom", fontsize=8, fontweight="bold",
            color="#e63b3b", zorder=8)


def draw_ai_truck(ax) -> None:
    b = AI_TRUCK["body"]
    c = AI_TRUCK["cab"]
    draw_truck_body(ax, *b)
    draw_truck_body(ax, *c)
    for wx, wz, r in AI_TRUCK["wheels"]:
        draw_wheel(ax, wx, wz, r)
    ax.text(b[0], b[1] + b[3] + 0.4, "AI Truck\n(rear ←  cab →)",
            ha="center", va="bottom", fontsize=8, fontweight="bold",
            color="#27a040", zorder=8)


def draw_tower(ax) -> None:
    # Base
    bx, bz, bw, bh, bc = TOWER["base"]
    ax.add_patch(mpatches.Rectangle((bx - bw / 2, bz), bw, bh,
                                     facecolor=bc, edgecolor="black",
                                     linewidth=1.0, zorder=5))
    # Shaft
    sx, sz, sw, sh, sc = TOWER["shaft"]
    ax.add_patch(mpatches.Rectangle((sx - sw / 2, sz), sw, sh,
                                     facecolor=sc, edgecolor="black",
                                     linewidth=1.0, zorder=5))
    # Deck
    dx, dz, dw, dh, dc = TOWER["deck"]
    ax.add_patch(mpatches.Rectangle((dx - dw / 2, dz), dw, dh,
                                     facecolor=dc, edgecolor="black",
                                     linewidth=1.2, alpha=0.7, zorder=6))
    # Antenna
    ax.plot([sx, sx], [dz + dh, TOWER["tip_y"]],
            color="#222222", lw=2.0, zorder=7)
    ax.add_patch(mpatches.Circle((sx, TOWER["tip_y"]), 0.18,
                                  facecolor="red", edgecolor="black",
                                  linewidth=0.8, zorder=8))
    ax.text(bx, TOWER["tip_y"] + 0.4, "Control\nTower",
            ha="center", va="bottom", fontsize=8, fontweight="bold",
            color="#3a5d8f", zorder=9)



def draw_readiness_layers(ax) -> None:
    # Small table crates inside the inventory warehouse, with colored tags.
    for i, x in enumerate([24.0, 25.4, 26.8, 28.2, 29.6, 31.0, 32.4, 33.8]):
        y = 1.0 + (i % 3) * 0.75
        ax.add_patch(mpatches.Rectangle((x - 0.35, y), 0.7, 0.45,
                                        facecolor="#f8fafc", edgecolor=C_SILVER,
                                        linewidth=0.9, zorder=7))
        tag_color = ["#8b5cf6", "#f43f5e", "#16a34a"][i % 3]
        ax.add_patch(mpatches.Circle((x + 0.30, y + 0.42), 0.09,
                                     facecolor=tag_color, edgecolor="white",
                                     linewidth=0.5, zorder=8))
    ax.text(29, 5.65, "Inventory exposes:\ncount · volume · tags · readiness",
            ha="center", va="center", fontsize=8, color=C_SILVER,
            fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor=C_SILVER, alpha=0.95))

    ax.text(44, 4.2, "Search does not just view the twin:\nit highlights candidates and missing metadata",
            ha="center", va="center", fontsize=8, color=C_LOBBY,
            fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                      edgecolor=C_LOBBY, alpha=0.95))

    ax.text(57.5, 3.9, "Delivery = URI / SQL / Spark snippet\nfor AI · HPC · HPDA",
            ha="center", va="center", fontsize=8, color=C_DELIVERY,
            fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                      edgecolor=C_DELIVERY, alpha=0.95))

def draw_height_dim(ax, x, z1, z2, label) -> None:
    ax.plot([x, x], [z1, z2], color="#666666", lw=0.8, zorder=4)
    ax.plot([x - 0.3, x + 0.3], [z1, z1], color="#666666", lw=0.8, zorder=4)
    ax.plot([x - 0.3, x + 0.3], [z2, z2], color="#666666", lw=0.8, zorder=4)
    ax.text(x + 0.5, (z1 + z2) / 2, label, ha="left", va="center",
            fontsize=8, color="#444444", zorder=4)


def draw_scale_bar(ax) -> None:
    x0, z0 = X_MIN + 2, Z_MIN + 0.3
    ax.plot([x0, x0 + 10], [z0, z0], color="black", lw=3.0, zorder=10)
    for x_off in (0, 5, 10):
        ax.plot([x0 + x_off, x0 + x_off], [z0 - 0.18, z0 + 0.18],
                color="black", lw=1.0, zorder=10)
    ax.text(x0 + 5, z0 - 0.55, "0       5       10 m",
            ha="center", va="top", fontsize=9, zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=C_BRONZE_FILL, edgecolor=C_BRONZE,
                       label="Bronze stage (Raw)"),
        mpatches.Patch(facecolor=C_SILVER_FILL, edgecolor=C_SILVER,
                       label="Silver stage (Refinement + Inventory)"),
        mpatches.Patch(facecolor=C_GOLD_FILL, edgecolor=C_GOLD,
                       label="Gold stage (Ready bundles) — Y=+22, drawn dashed offset"),
        Line2D([0], [0], color=C_BRONZE, lw=4, label="Bronze conveyor"),
        Line2D([0], [0], color=C_SILVER, lw=4, label="Silver conveyor"),
        Line2D([0], [0], color=C_DELIVERY, lw=4, label="Dispatch conveyor"),
        Line2D([0], [0], color="#444444", lw=1.2, label="Ground (z=0)"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9, framealpha=1.0, edgecolor="#888888",
              title="Legend (Readiness Elevation)", title_fontsize=10)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Elevation deliberately uses non-equal aspect for readability.
    fig, ax = plt.subplots(figsize=(22, 8))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Z_MIN, Z_MAX)

    draw_grid(ax)
    draw_ground(ax)

    # Showcase ghost first (behind everything)
    draw_showcase_ghost(ax)

    # Buildings
    for cx, cz, w, h, edge, fill, label in BUILDINGS:
        draw_building(ax, cx, cz, w, h, edge, fill, label)

    # Pipeline stations
    for x, label in STATIONS:
        draw_station(ax, x, label)

    # Conveyors
    for x1, x2, color, label in CONVEYORS_X:
        draw_conveyor(ax, x1, x2, color, label)

    draw_readiness_layers(ax)

    # Big Table
    draw_big_table(ax)

    # Trucks
    draw_inbound_truck(ax)
    draw_ai_truck(ax)

    # Control Tower
    draw_tower(ax)

    # Height dimensions on Lakehouse
    draw_height_dim(ax, 39, 0, 6.1, "6.0 m\nwarehouse")
    draw_height_dim(ax, 22, 0, 3.1, "3.0 m\nstation canopy")

    draw_scale_bar(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin Data Readiness Elevation View (Side, looking from -Y)\n"
        "Raw boxes become table crates with metadata tags; Staging is a ready-to-use curated shelf, not a second warehouse.\n"
        "Vertical exaggeration applied for clarity  ·  matches scripts/create_scene.py",
        fontsize=12, fontweight="bold", pad=14,
    )
    ax.set_xlabel("X (m) — data flow direction →", fontsize=10)
    ax.set_ylabel("Z (m) — height ↑", fontsize=10)

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
