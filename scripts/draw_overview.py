"""Generate a minimal, data-independent Trident-Twin conceptual overview."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "overview.png"

COLORS = {
    "raw": ("#b87333", "#ead1b8"),
    "acc": ("#64748b", "#e2e8f0"),
    "lake": ("#2563eb", "#dbeafe"),
    "stage": ("#d97706", "#ffedd5"),
    "search": ("#0891b2", "#cffafe"),
    "ai": ("#16a34a", "#dcfce7"),
    "delivery": ("#7c3aed", "#ddd6fe"),
}
DARK = "#0f172a"


def add_box(ax, x, y, w, h, title, key):
    edge, face = COLORS[key]
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.12",
        facecolor=face, edgecolor=edge, linewidth=2.0, zorder=3,
        path_effects=[pe.SimplePatchShadow(offset=(2, -2), alpha=0.12), pe.Normal()],
    ))
    ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=edge, zorder=4)


def arrow(ax, x1, y1, x2, y2, color=DARK, label=None, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.3,
                                mutation_scale=20, connectionstyle=f"arc3,rad={rad}"), zorder=2)
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.20, label,
                ha="center", va="center", fontsize=8.0, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor=color, alpha=0.95), zorder=6)


def draw_icons(ax):
    # Raw objects
    for i in range(5):
        ax.add_patch(mpatches.Rectangle((0.75 + (i % 3) * 0.28, 3.18 + (i // 3) * 0.24),
                                        0.18, 0.14, facecolor=COLORS["raw"][0], edgecolor="#7c2d12", zorder=6))
    # Three accumulation steps
    for i, color in enumerate(["#f59e0b", "#22c55e", "#06b6d4"]):
        ax.add_patch(mpatches.Circle((3.17 + i * 0.35, 3.38), 0.13, facecolor=color, edgecolor="white", zorder=6))
        ax.text(3.17 + i * 0.35, 3.38, str(i + 1), ha="center", va="center", fontsize=7, color="#111827", fontweight="bold", zorder=7)
    # Lakehouse table roles
    for i in range(6):
        edge, face = (COLORS["lake"][0], COLORS["lake"][1]) if i not in {2, 5} else ("#b45309", "#fef3c7")
        ax.add_patch(mpatches.Rectangle((5.70 + (i % 3) * 0.30, 3.18 + (i // 3) * 0.25),
                                        0.22, 0.16, facecolor=face, edgecolor=edge, zorder=6))
    # Staging bundle
    for i in range(3):
        ax.add_patch(mpatches.FancyBboxPatch((7.78, 3.52 - i * 0.22), 0.85, 0.10,
                                             boxstyle="round,pad=0.02,rounding_size=0.04",
                                             facecolor="#fed7aa", edgecolor=COLORS["stage"][0], zorder=6))
    # Search cards
    for i in range(3):
        ax.add_patch(mpatches.FancyBboxPatch((10.05, 3.52 - i * 0.25), 0.95, 0.14,
                                             boxstyle="round,pad=0.02,rounding_size=0.04",
                                             facecolor="white", edgecolor=COLORS["search"][0], zorder=6))
    # Delivery docks
    for i, color in enumerate([COLORS["ai"][0], "#64748b", "#2563eb"]):
        ax.add_patch(mpatches.Rectangle((12.35, 3.56 - i * 0.25), 0.52, 0.13,
                                        facecolor=color, edgecolor="#0f172a", zorder=6))


def main() -> None:
    fig, ax = plt.subplots(figsize=(15.5, 8.0))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 14, 6.2, facecolor="#f8fafc", edgecolor="none", zorder=0))
    ax.add_patch(mpatches.FancyBboxPatch((0.28, 0.44), 13.44, 4.95,
                                         boxstyle="round,pad=0.03,rounding_size=0.16",
                                         facecolor="white", edgecolor="#cbd5e1", linewidth=1.3, zorder=1))
    ax.text(7, 5.78, "Trident-Twin: Stable Digital Twin Flow",
            ha="center", va="center", fontsize=19, fontweight="bold", color=DARK)
    ax.text(7, 5.44,
            "The diagram is data-independent; live datasets and tables are injected by scene generation.",
            ha="center", va="center", fontsize=10.5, color="#475569")

    boxes = [
        (0.45, 2.35, 1.65, 2.1, "Raw\nBucket", "raw"),
        (2.55, 2.35, 1.65, 2.1, "3-Step\nAccum.", "acc"),
        (4.65, 2.35, 1.85, 2.1, "Lakehouse\nTables", "lake"),
        (6.95, 2.35, 1.85, 2.1, "Data\nStaging", "stage"),
        (9.25, 2.35, 1.85, 2.1, "Data\nSearch", "search"),
        (11.55, 2.35, 1.95, 2.1, "Gemma4 +\nDelivery", "delivery"),
    ]
    for box in boxes:
        add_box(ax, *box)
    for x in [2.10, 4.20, 6.50, 8.80, 11.10]:
        arrow(ax, x, 3.40, x + 0.34, 3.40)
    arrow(ax, 10.15, 2.25, 5.75, 1.20, COLORS["search"][0], "highlight", rad=-0.18)
    arrow(ax, 12.35, 2.25, 8.0, 1.15, COLORS["stage"][0], "save bundle", rad=-0.18)
    arrow(ax, 8.0, 2.25, 12.35, 1.05, COLORS["delivery"][0], "reuse", rad=0.18)
    draw_icons(ax)

    ax.add_patch(mpatches.FancyBboxPatch((1.2, 0.55), 11.6, 0.48,
                                         boxstyle="round,pad=0.03,rounding_size=0.10",
                                         facecolor=DARK, edgecolor=DARK, zorder=3))
    ax.text(7, 0.79,
            "Continuous: stream + light commands · On demand: search, data context, Gemma4, delivery · One-shot: scene regeneration",
            ha="center", va="center", fontsize=9.8, color="white", fontweight="bold", zorder=4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=170, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
