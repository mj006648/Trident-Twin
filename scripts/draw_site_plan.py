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

X_MIN, X_MAX = -30, 78
Y_MIN, Y_MAX = -12, 32

# (cx, cy, w, h, fill, edge, zone_no, zone_name)
ZONE_PADS = [
    # Control Tower: zone pad 없음, draw_control_tower로만 표시
    (-22,  0, 16,  8,  C_BRONZE_FILL,  C_BRONZE,  "Zone 1", "Data Ingest"),
    ( -4,  9, 21, 38,  C_BRONZE_FILL,  C_BRONZE,  "Zone 2", "Raw Bucket"),
    ( 13,  0, 12,  7,  C_SILVER_FILL,  C_SILVER,  "Zone 3", "Accumulation"),
    ( 29,  9, 21, 38,  C_SILVER_FILL,  C_SILVER,  "Zone 4", "Lakehouse"),
    ( 44, 10, 10, 11,  C_LOBBY_FILL,   C_LOBBY,   "Zone 0", "Data Search"),
    ( 59,9.5, 22, 20,  C_DELIVER_FILL, C_DELIVER, "Zone 5", "Delivery"),
]

# warehouse outlines + size label (cx, cy, w, h, color, size_label)
WAREHOUSES = [
    (-4,  9, 19, 32, C_BRONZE, "19×32×6m"),
    (29,  9, 19, 32, C_SILVER, "19×32×6m"),
]

# Lakehouse 내부 구분선 y=13.5
LH_DIVIDER_Y = 13.5

# Accumulation gates
GATES = [(7,"INGEST"),(10,"STAGE"),(13,"CLEAN"),(16,"TAG"),(19,"CATALOG")]

# Big Table
BIG_TABLE = (52, 9.5, 3.5, 10)  # cx, cy, w, h

# Raw Bucket 오른쪽 벽: x=4.5, Lakehouse 오른쪽 벽: x=38.5, Big Table 왼쪽: x=50.3
# Big Table: cx=52, cy=9.5, w=3.5, h=10 → left=50.3, right=53.7, top=14.5, bottom=4.5

# (x1,y1,x2,y2, color, label, loff)
CONVEYORS = [
    # Ingest belt
    (-17,  0.0, -12,  0.0, C_BRONZE, "Ingest Belt",     (0,  0.9)),
    # Accumulation belts (2 lanes)
    (  5, -0.7,  20, -0.7, C_SILVER, "",                (0,  0.0)),
    (  5,  0.7,  20,  0.7, C_SILVER, "",                (0,  0.0)),
    # Lakehouse Storage(하단) 오른쪽 벽(x=38.5, y=3) → Search Zone 아래 우회(y=3)
    # → Big Table 아래(x=50.3) 수직으로 올라와 Big Table 하단(y=4.5)에 연결
    (38.5,  3.0,  50.3,  3.0, C_SILVER, "Belt",                (4.5, -1.3)),
    (50.3,  3.0,  50.3,  4.5, C_SILVER, "",                    (0,    0.0)),
    # Lakehouse Staging(상단) 오른쪽 벽(x=38.5, y=21) → Search Zone 위로 우회(y=21)
    # → Big Table 오른쪽(x=50.3) 수직으로 내려와 Big Table 상단(y=14.5)에 연결
    (38.5, 21.0,  50.3, 21.0, C_GOLD,   "Belt",                (4.5,  1.3)),
    (50.3, 21.0,  50.3, 14.5, C_GOLD,   "",                    (0,    0.0)),
    # Big Table → AI/HPC/HPDA (딜리버리 벨트)
    (53.7,  6.0,  62,   6.0, C_DELIVER, "Belt (AI)",   (1.0, 0.7)),
    (53.7, 10.0,  62,  10.0, C_DELIVER, "Belt (HPC)",  (1.0, 0.7)),
    (53.7, 14.0,  62,  14.0, C_DELIVER, "Belt (HPDA)", (1.0, 0.7)),
]

TRUCKS = [
    (-20.5,  0, 7.0, 2.4, "#e63b3b", "Ingest"),
    ( 64,    6, 5.6, 2.2, "#27a040", "AI"),
    ( 64,   10, 4.8, 2.0, "#7d7f88", "HPC"),
    ( 64,   14, 5.0, 2.0, "#4a76d6", "HPDA"),
]


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, zone_no, zone_name):
    ax.add_patch(mpatches.Rectangle(
        (cx-w/2, cy-h/2), w, h,
        facecolor=fill, edgecolor=edge, linewidth=1.5, alpha=0.45, zorder=1))
    # zone label above pad
    ax.text(cx, cy+h/2+0.3, f"{zone_no}  {zone_name}",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=edge, zorder=2)


def draw_warehouse(ax, cx, cy, w, h, color, size_label):
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx-w/2, cy-h/2), w, h,
        boxstyle="round,pad=0,rounding_size=0.3",
        facecolor="white", edgecolor=color, linewidth=2.2, alpha=0.9, zorder=3))
    ax.text(cx, cy, size_label,
            ha="center", va="center", fontsize=9, color=color,
            fontweight="bold", zorder=4)


def draw_lakehouse_divider(ax):
    # Lakehouse 창고 내부 구분선: cx=29, w=19 → x: 19.5~38.5
    ax.plot([19.6, 38.4], [LH_DIVIDER_Y, LH_DIVIDER_Y],
            color=C_GOLD, lw=2.0, linestyle="--", zorder=7, alpha=1.0)
    # 상단 절반 (Staging) 배경
    ax.add_patch(mpatches.Rectangle(
        (19.6, LH_DIVIDER_Y), 18.8, 11.5,
        facecolor=C_GOLD_FILL, edgecolor="none", alpha=0.35, zorder=4))
    ax.text(29, 22.0, "Staging\n(Ready-to-use)",
            ha="center", va="center", fontsize=8, color="#78350f",
            fontweight="bold", zorder=8)
    ax.text(29, 7.0, "Storage\n(Iceberg Tables)",
            ha="center", va="center", fontsize=8, color="#334155",
            fontweight="bold", zorder=8)


def draw_big_table(ax, cx, cy, w, h):
    ax.add_patch(mpatches.Rectangle(
        (cx-w/2, cy-h/2), w, h,
        facecolor="#8a5a3a", edgecolor="#3c2410",
        linewidth=1.8, zorder=5))
    ax.text(cx, cy, "Big\nTable",
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white", zorder=6)


def draw_gate(ax, x, label):
    for xi in (x-0.25, x+0.25):
        ax.add_patch(mpatches.Rectangle(
            (xi-0.1, -1.6), 0.2, 3.2,
            facecolor="#fffbe6", edgecolor="#888800", linewidth=1.0, zorder=5))
    ax.plot([x-0.35, x+0.35], [2.0, 2.0], color="#888800", lw=2.5, zorder=6)
    ax.text(x, 2.5, label, ha="center", va="bottom", fontsize=6,
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
    ax.text(44, 9.9, "Search /\nSelection",
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
        mpatches.Patch(facecolor=C_BRONZE_FILL,  edgecolor=C_BRONZE,  label="Zone 1/2  Data Ingest / Raw Bucket"),
        mpatches.Patch(facecolor=C_SILVER_FILL,  edgecolor=C_SILVER,  label="Zone 3/4  Accumulation / Lakehouse"),
        mpatches.Patch(facecolor=C_GOLD_FILL,    edgecolor=C_GOLD,    label="Zone 4 (상단)  Staging"),
        mpatches.Patch(facecolor=C_LOBBY_FILL,   edgecolor=C_LOBBY,   label="Zone 0  Data Search"),
        mpatches.Patch(facecolor=C_DELIVER_FILL, edgecolor=C_DELIVER, label="Zone 5  Delivery"),
        Line2D([0],[0], color=C_BRONZE,  lw=4, label="Bronze conveyor"),
        Line2D([0],[0], color=C_SILVER,  lw=4, label="Silver conveyor"),
        Line2D([0],[0], color=C_DELIVER, lw=4, label="Dispatch conveyor"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9, framealpha=1.0, edgecolor="#888888",
              title="Legend", title_fontsize=10)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(26, 13))
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    ax.set_xticks(range(X_MIN, X_MAX+1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX+1, 5))
    ax.grid(which="major", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)

    for cx,cy,w,h,fill,edge,zno,zname in ZONE_PADS:
        draw_zone_pad(ax, cx,cy,w,h,fill,edge,zno,zname)

    for cx,cy,w,h,color,size_label in WAREHOUSES:
        draw_warehouse(ax, cx,cy,w,h,color,size_label)

    draw_lakehouse_divider(ax)

    for x1,y1,x2,y2,color,label,loff in CONVEYORS:
        draw_conveyor(ax, x1,y1,x2,y2,color,label,loff)

    for x,label in GATES:
        draw_gate(ax, x, label)

    draw_big_table(ax, *BIG_TABLE)
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
