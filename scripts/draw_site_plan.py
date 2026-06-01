"""Generate the Trident-Twin Site Plan (top-down architectural view).

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

C_BRONZE  = "#b87333"; C_BRONZE_FILL  = "#e6c7a8"
C_SILVER  = "#9fa5ab"; C_SILVER_FILL  = "#dcdfe3"
C_GOLD    = "#d4a017"; C_GOLD_FILL    = "#f3dca8"
C_LOBBY   = "#2dcad0"; C_LOBBY_FILL   = "#bff0f2"
C_DELIVER = "#8862e0"; C_DELIVER_FILL = "#d9ccf5"
C_TOWER   = "#4a6b9c"

X_MIN, X_MAX = -30, 75
Y_MIN, Y_MAX = -12, 32

# (cx, cy, w, h, fill, edge, label)
ZONE_PADS = [
    (-22, 25,  6,  6,  "#c3d0e4",    C_TOWER,   "Control Tower"),
    (-22,  0, 16,  8,  C_BRONZE_FILL, C_BRONZE,  "TRUCK YARD"),
    ( -4,  9, 21, 38,  C_BRONZE_FILL, C_BRONZE,  "RAW BUCKET ZONE"),
    ( 13,  0, 12,  7,  C_SILVER_FILL, C_SILVER,  "ACCUMULATION ZONE"),
    ( 29,  9, 21, 38,  C_SILVER_FILL, C_SILVER,  "LAKEHOUSE ZONE"),
    ( 44, 10, 10, 11,  C_LOBBY_FILL,  C_LOBBY,   "SEARCH ZONE"),
    ( 59,9.5, 22, 20,  C_DELIVER_FILL,C_DELIVER, "DELIVERY ZONE"),
]

# warehouse outlines (cx, cy, w, h, color)
WAREHOUSES = [
    (-4,  9, 19, 32, C_BRONZE),
    (29,  9, 19, 32, C_SILVER),
]

# Accumulation gates x positions
GATES = [(7,"INGEST"),(10,"STAGE"),(13,"CLEAN"),(16,"TAG"),(19,"CATALOG")]

# (x1,y1,x2,y2, color, label, loff)
CONVEYORS = [
    (-17, 0.0, -12, 0.0, C_BRONZE, "Ingest Belt",        (0,  0.9)),
    (  5,-0.7,  20,-0.7, C_SILVER, "Main Line",           (0, -1.1)),
    (  5, 0.7,  20, 0.7, C_SILVER, "Express Line",        (0,  1.1)),
    ( 38, 0.0,  49, 0.0, C_SILVER, "",                    (0,  0.0)),
    ( 52, 6.0,  62, 6.0, C_DELIVER,"AI",                  (1.0,0.6)),
    ( 52,10.0,  62,10.0, C_DELIVER,"HPC",                 (1.0,0.6)),
    ( 52,14.0,  62,14.0, C_DELIVER,"HPDA",                (1.0,0.6)),
]

TRUCKS = [
    (-20.5, 0,  7.0,2.4,"#e63b3b","Ingest"),
    (64,    6,  5.6,2.2,"#27a040","AI"),
    (64,   10,  4.8,2.0,"#7d7f88","HPC"),
    (64,   14,  5.0,2.0,"#4a76d6","HPDA"),
]


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, label):
    ax.add_patch(mpatches.Rectangle(
        (cx-w/2, cy-h/2), w, h,
        facecolor=fill, edgecolor=edge, linewidth=1.5, alpha=0.45, zorder=1))
    ax.text(cx, cy+h/2+0.3, label,
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=edge, zorder=2)


def draw_warehouse(ax, cx, cy, w, h, color):
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx-w/2, cy-h/2), w, h,
        boxstyle="round,pad=0,rounding_size=0.3",
        facecolor="white", edgecolor=color, linewidth=2.2, alpha=0.9, zorder=3))


def draw_lakehouse_divider(ax):
    # 구분선: Lakehouse zone 내부 절반 (y=13.5)
    ax.plot([19.6, 38.4], [13.5, 13.5],
            color=C_GOLD, lw=1.4, linestyle="--", zorder=5, alpha=0.8)
    ax.text(29, 13.8, "Staging (Bookshelf)",
            ha="center", va="bottom", fontsize=8, color="#78350f",
            fontweight="bold", zorder=6)
    ax.text(29, 13.2, "Storage (Tables)",
            ha="center", va="top", fontsize=8, color="#334155",
            fontweight="bold", zorder=6)


def draw_raw_boxes(ax):
    # 대표 박스 몇 개만
    for x in [-8, -6.5, -5, -3.5, -2]:
        for y in [5.5, 7.0, 8.5]:
            ax.add_patch(mpatches.Rectangle(
                (x, y), 0.9, 0.65,
                facecolor=C_BRONZE, edgecolor="#6b3f1d",
                linewidth=0.7, alpha=0.7, zorder=6))


def draw_staging_boxes(ax):
    # 대표 골드 번들 박스
    for x in [22, 26, 30, 34]:
        for y in [18.5, 21.5, 24.5]:
            ax.add_patch(mpatches.FancyBboxPatch(
                (x-1.2, y-0.4), 2.4, 0.8,
                boxstyle="round,pad=0.04,rounding_size=0.1",
                facecolor=C_GOLD_FILL, edgecolor=C_GOLD,
                linewidth=1.0, zorder=6))


def draw_gate(ax, x, label):
    for yi in (-1.4, 1.4):
        ax.plot([x, x], [yi, yi+0.0], color="#888800", lw=0)  # invisible anchor
    # pillars
    for xi in (x-0.25, x+0.25):
        ax.add_patch(mpatches.Rectangle(
            (xi-0.1, -1.6), 0.2, 3.2,
            facecolor="#fffbe6", edgecolor="#888800", linewidth=1.0, zorder=5))
    # crossbar
    ax.plot([x-0.35, x+0.35], [2.0, 2.0], color="#888800", lw=2.5, zorder=6)
    ax.text(x, 2.4, label, ha="center", va="bottom", fontsize=6.5,
            fontweight="bold", color="#444400", zorder=7)


def draw_conveyor(ax, x1, y1, x2, y2, color, label, loff):
    ax.plot([x1,x2],[y1,y2], color=color, lw=4, solid_capstyle="round",
            zorder=4, alpha=0.85)
    if label:
        mx = (x1+x2)/2+loff[0]; my = (y1+y2)/2+loff[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                fontweight="bold", color=color, zorder=7,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor=color, linewidth=0.7, alpha=0.95))


def draw_truck(ax, cx, cy, w, h, color, label):
    ax.add_patch(mpatches.Rectangle(
        (cx-w/2, cy-h/2), w, h,
        facecolor=color, edgecolor="black", linewidth=1.0, alpha=0.8, zorder=6))
    ax.text(cx, cy, label, ha="center", va="center", fontsize=7.5,
            fontweight="bold", color="white", zorder=7)


def draw_search_panel(ax):
    ax.add_patch(mpatches.FancyBboxPatch(
        (40.2, 5.4), 7.6, 8.9,
        boxstyle="round,pad=0.05,rounding_size=0.16",
        facecolor="white", edgecolor=C_LOBBY, linewidth=1.6, zorder=6))
    ax.text(44, 10.0, "Search /\nSelection",
            ha="center", va="center", fontsize=9, color="#0e7490",
            fontweight="bold", zorder=7)


def draw_control_tower(ax):
    ax.add_patch(mpatches.Circle((-22, 25), 1.5,
                                  facecolor=C_TOWER, edgecolor="black",
                                  linewidth=1.2, zorder=5))
    ax.text(-22, 25, "Tower", ha="center", va="center", fontsize=7,
            color="white", fontweight="bold", zorder=6)


def draw_scale_bar(ax):
    x0, y0 = X_MIN+2, Y_MIN+2
    ax.plot([x0, x0+10],[y0,y0], color="black", lw=3, zorder=10)
    for xo in (0,5,10):
        ax.plot([x0+xo,x0+xo],[y0-0.5,y0+0.5], color="black", lw=1, zorder=10)
    ax.text(x0+5, y0-1.5, "0    5    10 m",
            ha="center", va="top", fontsize=9, zorder=10)


def draw_north_arrow(ax):
    nx, ny = X_MAX-6, Y_MAX-6
    ax.annotate("", xy=(nx,ny+2.5), xytext=(nx,ny-1.5),
                arrowprops=dict(arrowstyle="-|>", color="black",
                                lw=1.6, mutation_scale=22), zorder=10)
    ax.text(nx, ny+3, "N", ha="center", va="bottom",
            fontsize=12, fontweight="bold", zorder=10)
    ax.text(nx, ny-2.5, "(data flow → +X)",
            ha="center", va="top", fontsize=8, color="#666666", zorder=10)


def draw_legend(ax):
    handles = [
        mpatches.Patch(facecolor=C_BRONZE_FILL,  edgecolor=C_BRONZE,  label="RAW BUCKET ZONE"),
        mpatches.Patch(facecolor=C_SILVER_FILL,  edgecolor=C_SILVER,  label="LAKEHOUSE ZONE (Storage)"),
        mpatches.Patch(facecolor=C_GOLD_FILL,    edgecolor=C_GOLD,    label="LAKEHOUSE ZONE (Staging)"),
        mpatches.Patch(facecolor=C_LOBBY_FILL,   edgecolor=C_LOBBY,   label="SEARCH ZONE"),
        mpatches.Patch(facecolor=C_DELIVER_FILL, edgecolor=C_DELIVER, label="DELIVERY ZONE"),
        Line2D([0],[0], color=C_BRONZE,  lw=4, label="Bronze conveyor"),
        Line2D([0],[0], color=C_SILVER,  lw=4, label="Silver conveyor"),
        Line2D([0],[0], color=C_DELIVER, lw=4, label="Dispatch conveyor"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9, framealpha=1.0, edgecolor="#888888",
              title="Legend", title_fontsize=10)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(24, 13))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    ax.set_xticks(range(X_MIN, X_MAX+1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX+1, 5))
    ax.grid(which="major", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)

    for cx,cy,w,h,fill,edge,label in ZONE_PADS:
        draw_zone_pad(ax, cx, cy, w, h, fill, edge, label)

    for cx,cy,w,h,color in WAREHOUSES:
        draw_warehouse(ax, cx, cy, w, h, color)

    draw_lakehouse_divider(ax)
    draw_raw_boxes(ax)
    draw_staging_boxes(ax)

    for x1,y1,x2,y2,color,label,loff in CONVEYORS:
        draw_conveyor(ax, x1,y1,x2,y2,color,label,loff)

    for x,label in GATES:
        draw_gate(ax, x, label)

    draw_search_panel(ax)
    draw_control_tower(ax)

    for cx,cy,w,h,color,label in TRUCKS:
        draw_truck(ax, cx,cy,w,h,color,label)

    draw_scale_bar(ax)
    draw_north_arrow(ax)
    draw_legend(ax)

    ax.set_title(
        "Trident-Twin Site Plan  —  Data Readiness / Usage Optimization Map (Top View)\n"
        "1 unit = 1 m  ·  matches scripts/create_scene.py",
        fontsize=13, fontweight="bold", pad=12,
    )
    ax.set_xlabel("X (m)  —  data flow direction →", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, facecolor="white", bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
