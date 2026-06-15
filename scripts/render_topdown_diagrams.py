"""Render current top-down schematic diagrams for the README.

Outputs docs/screenshots/00_overview.png through 08_tower.png. These are
schematic documentation views, not Isaac renderer captures; actual scene camera
captures are produced by scripts/capture_overview.py.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from draw_site_plan import X_MIN, X_MAX, Y_MIN, Y_MAX, draw_facility, draw_grid

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"

# (slug, title, x_min, x_max, y_min, y_max)
VIEWS = [
    ("00_overview", "Overall — current Trident Twin layout", X_MIN, X_MAX, Y_MIN, Y_MAX),
    ("01_ingest", "Internal Intake / Truck Yard — not exposed as Portal camera", -29, -13, -6, 6),
    ("02_raw_bucket", "Raw Bucket Zone — dataset slots generated from live raw_bucket entities", -15.5, 7.5, -5, 26.5),
    ("03_accumulation", "Accumulation Zone — STEP 1 / STEP 2 / STEP 3 live ingest animation", 3.5, 22.5, -6.5, 6.5),
    ("04_lakehouse", "Lakehouse Zone — actual data/metadata tables in matching raw slots", 18, 40, -4, 18),
    ("05_staging", "Data Staging Zone — Dataset Basket reuse bundles on display tables", 18, 40, 17, 28.5),
    ("06_search", "Search Zone — query, candidates, selected tables, Gemma trigger", 38.5, 50.5, 3.0, 17.0),
    ("07_delivery", "Delivery Zone — Big Table to AI / HPC / HPDA buses", 48, 74, 0, 18),
    ("08_tower", "Control Tower Zone — operator/viewer anchor", -28, -16, 18, 30),
]


def render_view(slug: str, title: str, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
    width_m = x_max - x_min
    height_m = y_max - y_min
    fig_w = min(22, max(9, width_m / 4))
    fig_h = max(5.2, fig_w * height_m / width_m)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    draw_grid(ax)
    draw_facility(ax)
    ax.set_title(title, fontsize=12.5, fontweight="bold", pad=10)
    ax.set_xlabel("X (m)", fontsize=8.5)
    ax.set_ylabel("Y (m)", fontsize=8.5)
    plt.tight_layout()
    out = OUT_DIR / f"{slug}.png"
    plt.savefig(out, dpi=170, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for view in VIEWS:
        render_view(*view)


if __name__ == "__main__":
    main()
