"""Generate the current Trident-Twin site plan schematic.

Output:
    docs/site-plan.png
    docs/site-plan-v2.png

The schematic follows the June 2026 implementation: raw/lakehouse slots are
paired, Accumulation is shown as three conceptual steps, Data Staging is a
Dataset Basket-like area, and selected bundles flow through the Big Table to
AI/HPC/HPDA delivery.
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

C_BRONZE = "#b87333"
C_BRONZE_FILL = "#ead1b8"
C_SILVER = "#64748b"
C_SILVER_FILL = "#e2e8f0"
C_DATA = "#60a5fa"
C_DATA_FILL = "#dbeafe"
C_META = "#fbbf24"
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

# (cx, cy, w, h, fill, edge, label)
ZONE_PADS = [
    (-22, 0, 14, 7, C_BRONZE_FILL, C_BRONZE, "Truck Yard / Internal Intake"),
    (-4, 11, 20, 30, C_BRONZE_FILL, C_BRONZE, "Raw Bucket Zone"),
    (13, 0, 15, 7, C_SILVER_FILL, C_SILVER, "Accumulation Zone · 3 steps"),
    (29, 7, 20, 20, C_DATA_FILL, C_SILVER, "Lakehouse Zone"),
    (29, 22.5, 20, 9, C_STAGE_FILL, C_STAGE, "Data Staging Zone"),
    (44, 10, 10, 12, C_SEARCH_FILL, C_SEARCH, "Search Zone"),
    (61, 9.5, 22, 18, C_DELIVERY_FILL, C_DELIVERY, "Delivery Zone"),
]

# (cx, cy, w, h, color, label)
BUILDINGS = [
    (-4, 11, 18.5, 28, C_BRONZE, "Raw dataset slots"),
    (29, 7, 18.5, 18, C_SILVER, "Iceberg tables by raw slot"),
    (29, 22.5, 18.5, 7, C_STAGE, "Dataset Basket / reuse staging"),
]

# Accumulation step sections: (x0, x1, label, sublabel, color)
STATIONS = [
    (5.6, 10.15, "STEP 1", "ingest + profile", "#f59e0b"),
    (10.15, 15.05, "STEP 2", "catalog + link", "#22c55e"),
    (15.05, 19.6, "STEP 3", "ready + manifest", "#06b6d4"),
]

# (x1, y1, x2, y2, color, label, off)
CONVEYORS = [
    (-18.0, 0.0, -13.0, 0.0, C_BRONZE, "intake", (0, 0.8)),
    (4.8, -0.8, 20.0, -0.8, C_SILVER, "live ingest box", (0, -1.1)),
    (4.8, 0.8, 20.0, 0.8, C_SILVER, "", (0, 0)),
    # Lakehouse and staging outputs bypass Search Zone and enter the Big Table.
    (38.5, 5.0, 48.8, 5.0, C_SILVER, "lakehouse copy", (2.5, -1.0)),
    (48.8, 5.0, 48.8, 9.5, C_SILVER, "", (0, 0)),
    (48.8, 9.5, 50.2, 9.5, C_SILVER, "", (0, 0)),
    (38.5, 22.5, 49.4, 22.5, C_STAGE, "staged bundle", (2.7, 1.0)),
    (49.4, 22.5, 49.4, 14.5, C_STAGE, "", (0, 0)),
    (49.4, 14.5, 50.2, 14.5, C_STAGE, "", (0, 0)),
    (53.8, 6.0, 68.5, 6.0, C_AI, "AI bus", (0, -0.9)),
    (53.8, 9.5, 68.5, 9.5, C_HPC, "HPC", (0, 0.85)),
    (53.8, 13.0, 68.5, 13.0, C_HPDA, "HPDA", (0, 0.85)),
]

TRUCKS = [
    (-20.8, 0.0, 5.8, 2.2, "#ef4444", "raw"),
    (70.0, 6.0, 4.8, 2.0, C_AI, "AI"),
    (70.0, 9.5, 4.8, 2.0, C_HPC, "HPC"),
    (70.0, 13.0, 4.8, 2.0, C_HPDA, "HPDA"),
]

BIG_TABLE = (52.0, 9.5, 3.6, 10.2)
LOBBY = (44.0, 10.0, 7.2, 8.2)

RAW_SLOTS = [
    ("icu_ehr_tabular_v1", -9.8, 18.2),
    ("icu_waveform_mixed_v1", -3.9, 18.2),
    ("icu_imaging_mixed_v1", 2.0, 18.2),
    ("sepsis_cohort", -9.8, 11.0),
    ("lactate_results", -3.9, 11.0),
    ("radiology_reports", 2.0, 11.0),
    ("antibiotic_events", -9.8, 3.8),
    ("vitals", -3.9, 3.8),
    ("labs", 2.0, 3.8),
]

LAKEHOUSE_SLOTS = [
    ("icu_ehr_tabular_v1", 24.0, 11.4, ["patient", "icu_stay", "chartevents", "diagnoses", "trident_manifest", "trident_tables"]),
    ("icu_waveform_mixed_v1", 30.0, 11.4, ["waveform_samples", "waveform_segments", "signal_quality", "trident_manifest"]),
    ("icu_imaging_mixed_v1", 36.0, 11.4, ["image_manifest", "radiology_reports", "dicom_series", "trident_manifest"]),
    ("sepsis_cohort", 24.0, 4.0, ["sepsis_cohort", "lactate_results", "vasopressors", "trident_manifest"]),
    ("antibiotic_events", 30.0, 4.0, ["antibiotic_events", "med_orders", "trident_tables"]),
    ("labs", 36.0, 4.0, ["lab_results", "specimens", "trident_manifest"]),
]

STAGED_BUNDLES = [
    ("sepsis bundle", 23.0, 22.5, ["sepsis_cohort", "lactate_results"]),
    ("imaging Q&A", 29.0, 22.5, ["image_manifest", "radiology_reports"]),
    ("multi-dataset", 35.0, 22.5, ["labs", "vitals", "med_orders"]),
]


def draw_grid(ax) -> None:
    ax.set_xticks(range(X_MIN, X_MAX + 1, 5))
    ax.set_yticks(range(Y_MIN, Y_MAX + 1, 5))
    ax.grid(which="major", color="#e2e8f0", linewidth=0.65)
    ax.set_axisbelow(True)


def draw_zone_pad(ax, cx, cy, w, h, fill, edge, label) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.45",
        facecolor=fill, edgecolor=edge, linewidth=1.6, alpha=0.50, zorder=1,
    ))
    ax.text(cx, cy + h / 2 + 0.38, label, ha="center", va="bottom",
            fontsize=9.5, color=edge, fontweight="bold", zorder=8)


def draw_building(ax, cx, cy, w, h, color, label) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.28",
        facecolor="white", edgecolor=color, linewidth=2.0, alpha=0.92, zorder=3,
    ))
    ax.text(cx, cy + h / 2 - 0.95, label, ha="center", va="top",
            fontsize=8.3, color=color, fontweight="bold", zorder=8)


def draw_conveyor(ax, x1, y1, x2, y2, color, label, off=(0, 0)) -> None:
    ax.plot([x1, x2], [y1, y2], color=color, lw=4.6, solid_capstyle="round", alpha=0.82, zorder=4)
    if label:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], label,
                ha="center", va="center", fontsize=7.2, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=color, alpha=0.96), zorder=9)


def draw_station(ax, x0, x1, label, sublabel, color) -> None:
    ax.add_patch(mpatches.Rectangle((x0, -3.15), x1 - x0, 6.3,
                                    facecolor=color, edgecolor="white", linewidth=1.2,
                                    alpha=0.18, zorder=2))
    ax.plot([x0, x0], [-3.15, 3.15], color="#475569", lw=1.0, alpha=0.45, zorder=4)
    ax.text((x0 + x1) / 2, 2.28, label, ha="center", va="center",
            fontsize=9.5, color="#111827", fontweight="bold", zorder=9)
    ax.text((x0 + x1) / 2, 1.36, sublabel, ha="center", va="center",
            fontsize=6.8, color="#334155", zorder=9)


def draw_raw_inventory(ax) -> None:
    for name, x, y in RAW_SLOTS:
        ax.add_patch(mpatches.FancyBboxPatch((x - 2.55, y - 2.05), 5.1, 3.65,
                                             boxstyle="round,pad=0.02,rounding_size=0.10",
                                             facecolor="#fff7ed", edgecolor=C_BRONZE,
                                             linewidth=1.1, alpha=0.92, zorder=5))
        ax.text(x, y + 1.05, name, ha="center", va="center", fontsize=5.5,
                color="#7c2d12", fontweight="bold", zorder=7)
        for i in range(5):
            bx = x - 1.65 + (i % 3) * 1.05
            by = y - 0.95 + (i // 3) * 0.75
            ax.add_patch(mpatches.Rectangle((bx, by), 0.72, 0.45,
                                            facecolor=C_BRONZE, edgecolor="#7c2d12",
                                            linewidth=0.8, alpha=0.86, zorder=6))


def draw_table_crate(ax, x, y, label, meta=False, scale=1.0) -> None:
    face = C_META_FILL if meta else C_DATA_FILL
    edge = "#b45309" if meta else "#1d4ed8"
    ax.add_patch(mpatches.FancyBboxPatch((x - 0.42 * scale, y - 0.30 * scale), 0.84 * scale, 0.60 * scale,
                                         boxstyle="round,pad=0.01,rounding_size=0.04",
                                         facecolor=face, edgecolor=edge, linewidth=0.8, zorder=7))
    # Use table names, small and black, matching current scene intent.
    short = label if len(label) <= 15 else label[:14] + "…"
    ax.text(x, y, short, ha="center", va="center", fontsize=3.9 * scale,
            color="#111827", fontweight="bold", zorder=8)


def draw_inventory_boxes(ax) -> None:
    for ns, cx, cy, tables in LAKEHOUSE_SLOTS:
        ax.add_patch(mpatches.FancyBboxPatch((cx - 2.65, cy - 2.55), 5.3, 4.7,
                                             boxstyle="round,pad=0.02,rounding_size=0.10",
                                             facecolor="#f8fafc", edgecolor=C_SILVER,
                                             linewidth=1.1, alpha=0.96, zorder=5))
        ax.text(cx, cy + 1.78, ns, ha="center", va="center", fontsize=4.9,
                color="#111827", fontweight="bold", zorder=8)
        for i, table in enumerate(tables[:8]):
            tx = cx - 1.55 + (i % 4) * 1.03
            ty = cy + 0.62 - (i // 4) * 0.92
            meta = table.startswith("trident_") or table in {"trident_manifest", "trident_tables"}
            # individual support table under every crate
            ax.add_patch(mpatches.Rectangle((tx - 0.48, ty - 0.42), 0.96, 0.08,
                                            facecolor="#94a3b8", edgecolor="#475569",
                                            linewidth=0.4, zorder=6))
            draw_table_crate(ax, tx, ty, table, meta=meta, scale=0.90)


def draw_staging_bundles(ax) -> None:
    # Empty long display tables first.
    for y in (20.6, 22.5, 24.4):
        ax.add_patch(mpatches.FancyBboxPatch((20.4, y - 0.30), 17.2, 0.60,
                                             boxstyle="round,pad=0.01,rounding_size=0.08",
                                             facecolor="#fed7aa", edgecolor=C_STAGE,
                                             linewidth=1.0, alpha=0.60, zorder=5))
    for title, x, y, items in STAGED_BUNDLES:
        ax.add_patch(mpatches.FancyBboxPatch((x - 2.2, y - 0.72), 4.4, 1.35,
                                             boxstyle="round,pad=0.02,rounding_size=0.10",
                                             facecolor="#fff7ed", edgecolor=C_STAGE,
                                             linewidth=1.2, zorder=6))
        ax.text(x, y + 0.38, title, ha="center", va="center", fontsize=5.8,
                color="#7c2d12", fontweight="bold", zorder=8)
        ax.text(x, y - 0.20, " + ".join(items[:2]) + ("…" if len(items) > 2 else ""),
                ha="center", va="center", fontsize=4.7, color="#111827", zorder=8)


def draw_search_decision_panel(ax) -> None:
    x, y, w, h = 40.6, 6.4, 6.8, 7.2
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                                         boxstyle="round,pad=0.04,rounding_size=0.18",
                                         facecolor="white", edgecolor=C_SEARCH,
                                         linewidth=1.7, zorder=6))
    ax.text(x + w / 2, y + h - 0.9, "Data Search", ha="center", va="center",
            fontsize=8.5, color=C_SEARCH, fontweight="bold", zorder=8)
    rows = [("sepsis data", "sepsis_cohort"), ("lactate", "lactate_results"), ("imaging", "image_manifest")]
    for i, (q, table) in enumerate(rows):
        yy = y + h - 2.0 - i * 1.35
        ax.add_patch(mpatches.FancyBboxPatch((x + 0.45, yy - 0.42), w - 0.9, 0.8,
                                             boxstyle="round,pad=0.02,rounding_size=0.08",
                                             facecolor="#ecfeff", edgecolor="#67e8f9", linewidth=0.8, zorder=7))
        ax.text(x + 0.75, yy + 0.12, q, ha="left", va="center", fontsize=5.3,
                color="#155e75", fontweight="bold", zorder=8)
        ax.text(x + 0.75, yy - 0.16, table, ha="left", va="center", fontsize=5.0,
                color="#111827", zorder=8)
    ax.text(x + w / 2, y + 0.65, "highlight → Gemma4 → delivery", ha="center", va="center",
            fontsize=5.5, color="#155e75", fontweight="bold", zorder=8)


def draw_big_table(ax, cx, cy, w, h) -> None:
    ax.add_patch(mpatches.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                         boxstyle="round,pad=0.02,rounding_size=0.12",
                                         facecolor="#8b5e34", edgecolor="#3f2a16",
                                         linewidth=1.8, zorder=6))
    ax.text(cx, cy, "Big\nTable", ha="center", va="center", fontsize=8.5,
            color="white", fontweight="bold", zorder=8)


def draw_lobby_interior(ax, cx, cy, w, h) -> None:
    # Kept for render_topdown compatibility. Search UI is drawn separately.
    pass


def draw_control_tower(ax, cx=-22, cy=25) -> None:
    ax.add_patch(mpatches.Circle((cx, cy), 1.55, facecolor=C_TOWER,
                                  edgecolor="#0f172a", linewidth=1.2, zorder=6))
    ax.text(cx, cy, "Control\nTower", ha="center", va="center", fontsize=6.5,
            color="white", fontweight="bold", zorder=8)
    ax.add_patch(mpatches.Rectangle((cx - 0.45, cy - 5.0), 0.9, 4.0,
                                    facecolor="#94a3b8", edgecolor="#334155", zorder=5))


def draw_readiness_callouts(ax) -> None:
    ax.text(18.6, -5.6, "Live Start: accumulation boxes only\nafter real ingest/event polling",
            ha="center", va="center", fontsize=7.0, color="#334155",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=C_SILVER, alpha=0.95), zorder=9)
    ax.text(54.5, 18.0, "Ask Gemma4 with Selection:\ncopy → Big Table → AI Bus",
            ha="center", va="center", fontsize=7.0, color="#4c1d95",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=C_DELIVERY, alpha=0.95), zorder=9)


def draw_truck(ax, cx, cy, w, h, color, label) -> None:
    ax.add_patch(mpatches.FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                         boxstyle="round,pad=0.02,rounding_size=0.14",
                                         facecolor=color, edgecolor="#0f172a",
                                         linewidth=1.0, alpha=0.88, zorder=7))
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
    ax.text(nx, ny - 2.2, "data flow → +X", ha="center", va="top", fontsize=8, color="#475569", zorder=10)


def draw_legend(ax) -> None:
    handles = [
        mpatches.Patch(facecolor=C_BRONZE_FILL, edgecolor=C_BRONZE, label="Raw Bucket / intake"),
        mpatches.Patch(facecolor=C_SILVER_FILL, edgecolor=C_SILVER, label="3-step accumulation"),
        mpatches.Patch(facecolor=C_DATA_FILL, edgecolor=C_SILVER, label="Lakehouse data tables"),
        mpatches.Patch(facecolor=C_META_FILL, edgecolor="#b45309", label="Metadata/catalog tables"),
        mpatches.Patch(facecolor=C_STAGE_FILL, edgecolor=C_STAGE, label="Data Staging / Dataset Basket"),
        mpatches.Patch(facecolor=C_SEARCH_FILL, edgecolor=C_SEARCH, label="Search Zone"),
        mpatches.Patch(facecolor=C_DELIVERY_FILL, edgecolor=C_DELIVERY, label="Delivery"),
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
        "Trident-Twin Site Plan — Raw/Lakehouse/Data Staging/Search/Gemma Delivery Flow\n"
        "June 2026 layout · raw/lakehouse slots are generated from twin-hub entities; live events animate only when Start Live is active",
        fontsize=13.5, fontweight="bold", pad=14,
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
