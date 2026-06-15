"""Generate the current Trident-Twin conceptual overview.

Output: overview.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "overview.png"

C_RAW = "#b87333"
C_RAW_FILL = "#ead1b8"
C_ACC = "#64748b"
C_ACC_FILL = "#e2e8f0"
C_LAKE = "#2563eb"
C_LAKE_FILL = "#dbeafe"
C_STAGE = "#d97706"
C_STAGE_FILL = "#ffedd5"
C_SEARCH = "#0891b2"
C_SEARCH_FILL = "#cffafe"
C_AI = "#16a34a"
C_AI_FILL = "#dcfce7"
C_DELIVERY = "#7c3aed"
C_DELIVERY_FILL = "#ddd6fe"
C_DARK = "#0f172a"


def add_box(ax, x, y, w, h, title, lines, face, edge, fs=12):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.12",
        facecolor=face, edgecolor=edge, linewidth=2.0, zorder=3,
        path_effects=[pe.SimplePatchShadow(offset=(2, -2), alpha=0.13), pe.Normal()],
    ))
    ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=edge, zorder=4)
    ax.text(x + w / 2, y + h * 0.37, lines, ha="center", va="center",
            fontsize=8.8, color="#334155", linespacing=1.25, zorder=4)


def arrow(ax, x1, y1, x2, y2, color=C_DARK, label=None, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2,
                                mutation_scale=20, connectionstyle=f"arc3,rad={rad}"), zorder=2)
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.20, label,
                ha="center", va="center", fontsize=7.8, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor=color, alpha=0.95), zorder=6)


def draw_mini_raw(ax):
    for i, name in enumerate(["icu_ehr", "waveform", "imaging", "sepsis"]):
        x = 0.72 + (i % 2) * 0.58
        y = 3.36 - (i // 2) * 0.38
        ax.add_patch(mpatches.Rectangle((x, y), 0.42, 0.25, facecolor=C_RAW, edgecolor="#7c2d12", zorder=6))
        ax.text(x + 0.21, y - 0.08, name, ha="center", va="top", fontsize=5.5, color="#7c2d12", zorder=6)


def draw_mini_lake(ax):
    samples = [("sepsis_cohort", False), ("lactate_results", False), ("trident_manifest", True), ("image_manifest", False), ("radiology_reports", False)]
    for i, (name, meta) in enumerate(samples):
        x = 5.92 + (i % 3) * 0.48
        y = 3.47 - (i // 3) * 0.38
        edge = "#1d4ed8" if not meta else "#b45309"
        face = "#dbeafe" if not meta else "#fef3c7"
        ax.add_patch(mpatches.Rectangle((x, y), 0.38, 0.24, facecolor=face, edgecolor=edge, zorder=6))
        ax.text(x + 0.19, y + 0.12, name[:8], ha="center", va="center", fontsize=4.4, color="#111827", zorder=7)


def draw_mini_staging(ax):
    for y in (3.62, 3.24, 2.86):
        ax.add_patch(mpatches.FancyBboxPatch((7.65, y), 1.25, 0.22,
                                             boxstyle="round,pad=0.02,rounding_size=0.05",
                                             facecolor="#fed7aa", edgecolor=C_STAGE, linewidth=1, zorder=6))
    ax.add_patch(mpatches.FancyBboxPatch((7.78, 3.31), 0.95, 0.40,
                                         boxstyle="round,pad=0.02,rounding_size=0.06",
                                         facecolor="#fff7ed", edgecolor=C_STAGE, linewidth=1, zorder=7))
    ax.text(8.25, 3.51, "sepsis", ha="center", va="center", fontsize=6.0, color="#7c2d12", fontweight="bold", zorder=8)
    ax.text(8.25, 3.33, "cohort+lactate", ha="center", va="center", fontsize=4.8, color="#111827", zorder=8)


def draw_mini_search(ax):
    ax.add_patch(mpatches.FancyBboxPatch((9.85, 3.0), 1.45, 0.95,
                                         boxstyle="round,pad=0.02,rounding_size=0.07",
                                         facecolor="white", edgecolor=C_SEARCH, linewidth=1.4, zorder=6))
    ax.text(10.58, 3.76, "sepsis data", ha="center", va="center", fontsize=6.4, color=C_SEARCH, fontweight="bold", zorder=7)
    for i, txt in enumerate(["sepsis_cohort", "lactate_results", "antibiotic_events"]):
        ax.text(10.02, 3.50 - i * 0.20, txt, ha="left", va="center", fontsize=5.1, color="#111827", zorder=7)


def draw_mini_ai(ax):
    ax.add_patch(mpatches.FancyBboxPatch((12.10, 3.35), 0.86, 0.50,
                                         boxstyle="round,pad=0.02,rounding_size=0.08",
                                         facecolor=C_AI_FILL, edgecolor=C_AI, linewidth=1.4, zorder=6))
    ax.text(12.53, 3.60, "Gemma4", ha="center", va="center", fontsize=6.5, color=C_AI, fontweight="bold", zorder=7)
    for i, label in enumerate(["AI", "HPC", "HPDA"]):
        y = 3.0 - i * 0.27
        ax.add_patch(mpatches.Rectangle((12.18, y), 0.70, 0.18, facecolor=[C_AI, "#64748b", "#2563eb"][i], edgecolor="#0f172a", zorder=6))
        ax.text(12.53, y + 0.09, label, ha="center", va="center", fontsize=5.1, color="white", fontweight="bold", zorder=7)


def main() -> None:
    fig, ax = plt.subplots(figsize=(15.5, 8.6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.8)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 14, 6.8, facecolor="#f8fafc", edgecolor="none", zorder=0))
    ax.add_patch(mpatches.FancyBboxPatch((0.28, 0.44), 13.44, 5.43,
                                         boxstyle="round,pad=0.03,rounding_size=0.16",
                                         facecolor="white", edgecolor="#cbd5e1", linewidth=1.3, zorder=1))
    ax.text(7, 6.35, "Trident-Twin: Lakehouse Digital Twin for Search-to-AI Workflows",
            ha="center", va="center", fontsize=18.5, fontweight="bold", color=C_DARK)
    ax.text(7, 6.02,
            "Scene generation mirrors live raw/table inventory; Portal interactions animate only selected events, not heavy continuous scans.",
            ha="center", va="center", fontsize=10.4, color="#475569")

    add_box(ax, 0.45, 2.35, 1.65, 2.55, "RAW\nBUCKET", "live raw_bucket\nnamespace slots", C_RAW_FILL, C_RAW, fs=11.0)
    add_box(ax, 2.55, 2.35, 1.65, 2.55, "3-STEP\nACCUM.", "Step 1 profile\nStep 2 catalog/link\nStep 3 manifest", C_ACC_FILL, C_ACC, fs=10.5)
    add_box(ax, 4.65, 2.35, 1.85, 2.55, "LAKEHOUSE\nZONE", "actual data +\nmetadata tables", C_LAKE_FILL, C_LAKE, fs=10.8)
    add_box(ax, 6.95, 2.35, 1.85, 2.55, "DATA\nSTAGING", "Dataset Basket\nreusable bundles", C_STAGE_FILL, C_STAGE, fs=10.8)
    add_box(ax, 9.25, 2.35, 1.85, 2.55, "DATA\nSEARCH", "single/multi select\nhighlight tables", C_SEARCH_FILL, C_SEARCH, fs=10.8)
    add_box(ax, 11.55, 2.35, 1.95, 2.55, "GEMMA4 +\nDELIVERY", "bounded data context\nBig Table → AI bus", C_DELIVERY_FILL, C_DELIVERY, fs=10.5)

    for x in [2.10, 4.20, 6.50, 8.80, 11.10]:
        arrow(ax, x, 3.62, x + 0.34, 3.62)
    arrow(ax, 10.25, 2.28, 5.65, 1.18, C_SEARCH, "search highlights tables", rad=-0.18)
    arrow(ax, 12.45, 2.28, 8.0, 1.12, C_STAGE, "successful asks become staged bundles", rad=-0.18)
    arrow(ax, 8.00, 2.28, 12.35, 1.10, C_DELIVERY, "reuse bundle → ask again", rad=0.18)

    draw_mini_raw(ax)
    draw_mini_lake(ax)
    draw_mini_staging(ax)
    draw_mini_search(ax)
    draw_mini_ai(ax)

    ax.add_patch(mpatches.FancyBboxPatch((0.95, 0.55), 12.1, 0.48,
                                         boxstyle="round,pad=0.03,rounding_size=0.10",
                                         facecolor=C_DARK, edgecolor=C_DARK, zorder=3))
    ax.text(7, 0.79,
            "Continuous: WebRTC + lightweight commands. On demand: search, Lakehouse samples, Gemma4, delivery animation. One-shot: scene regeneration.",
            ha="center", va="center", fontsize=10.0, color="white", fontweight="bold", zorder=4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=170, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
