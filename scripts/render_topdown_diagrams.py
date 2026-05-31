"""Render 9 top-down schematic diagrams (overview + per-zone) as PNGs.

Reuses draw_site_plan.py's drawing primitives but renders into per-zone
axis windows so each PNG is a focused "top-down camera view" of that
zone. Output: docs/screenshots/<zone>.png

This is a matplotlib schematic — not a photo-real Isaac Sim render — and
exists because the headless Isaac Sim renderer in this environment
cannot acquire CUDA (driver/library mismatch + GUI already holding the
GPU). It still answers "what does each zone look like from straight
above" with labels and the metallic theme intact.

Run:
    python3 scripts/render_topdown_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Reuse all the shapes / colors / layout from the site plan.
from draw_site_plan import (
    ZONE_PADS, BUILDINGS, STATIONS, CONVEYORS, TRUCKS, BIG_TABLE, LOBBY,
    C_BRONZE, C_BRONZE_FILL, C_SILVER, C_SILVER_FILL, C_GOLD, C_GOLD_FILL,
    C_LOBBY, C_LOBBY_FILL, C_DELIVERY, C_DELIVERY_FILL, C_TOWER,
    draw_grid, draw_zone_pad, draw_building, draw_conveyor, draw_station,
    draw_truck, draw_big_table, draw_lobby_interior, draw_control_tower,
    draw_raw_inventory, draw_inventory_boxes, draw_staging_bundles,
    draw_search_decision_panel, draw_readiness_callouts,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"

# (slug, title, x_min, x_max, y_min, y_max, padding)
VIEWS = [
    ("00_overview",     "Overall — Data Readiness / Usage Optimization Map", -30, +72, -18, +35),
    ("01_ingest",       "Zone 1 INGEST (Bronze) — Raw Arrival",    -32, -12,  -7,  +7),
    ("02_raw_bucket",   "Zone 2 RAW BUCKET — Untagged Object Count", -16,  +8,  -10, +10),
    ("03_accumulation", "Zone 3 PIPELINE STEPS — Audit / Catalog / Schema / Tag / Index / Bundle / Serve",   0, +26, -8,  +8),
    ("04_lakehouse",    "Zone 4 LAKEHOUSE INVENTORY — Count + Tags + Readiness", +18, +40, -10, +10),
    ("05_staging",      "Zone 5 STAGING — Ready-to-use Bundles",   +18, +40, +12, +32),
    ("06_search",       "Zone 6 SEARCH — Intent, Candidate Highlight, Readiness Compare",  +37, +52,  +2, +18),
    ("07_delivery",     "Zone 7 DELIVERY — AI / HPC / HPDA Workload Packages", +46, +72,  +1, +18),
    ("08_tower",        "Zone 8 TOWER — Operator Readiness Monitor", -28, -16, +20, +32),
]


def draw_facility(ax) -> None:
    """Lay down every facility element on the given axis."""
    for cx, cy, w, h, fill, edge, label in ZONE_PADS:
        draw_zone_pad(ax, cx, cy, w, h, fill, edge, label)
    for cx, cy, w, h, color, label in BUILDINGS:
        draw_building(ax, cx, cy, w, h, color, label)
    draw_raw_inventory(ax)
    draw_inventory_boxes(ax)
    draw_staging_bundles(ax)
    for x1, y1, x2, y2, color, label, off in CONVEYORS:
        draw_conveyor(ax, x1, y1, x2, y2, color, label, off)
    for x, label in STATIONS:
        draw_station(ax, x, label)
    draw_big_table(ax, *BIG_TABLE)
    draw_lobby_interior(ax, *LOBBY)
    draw_search_decision_panel(ax)
    draw_control_tower(ax, -22, +25)
    draw_readiness_callouts(ax)
    for cx, cy, w, h, color, label in TRUCKS:
        draw_truck(ax, cx, cy, w, h, color, label)


def render_view(slug: str, title: str,
                x_min: int, x_max: int, y_min: int, y_max: int) -> None:
    width_m = x_max - x_min
    height_m = y_max - y_min
    # Keep aspect ratio but ensure figure has enough pixels for the long titles
    fig_w = min(22, max(14, width_m / 4))
    fig_h = fig_w * height_m / width_m
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    draw_grid(ax)
    draw_facility(ax)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("X (m)", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)
    plt.tight_layout()
    out = OUT_DIR / f"{slug}.png"
    plt.savefig(out, dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for slug, title, x_min, x_max, y_min, y_max in VIEWS:
        render_view(slug, title, x_min, x_max, y_min, y_max)


if __name__ == "__main__":
    main()
