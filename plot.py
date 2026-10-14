"""Charts of the education wealth gap, SCF 1989-2025, drawn in the style of
The Economist's charts.

Reads the CSVs written by estimates.py (running it first if they are missing)
and writes:

* figures/wealth_gap_education.png   the gap over time, all families
* figures/wealth_gap_by_age.png      the gap within age groups of the head

Shaded bands are 95% confidence intervals (sampling + imputation error).

Usage: python plot.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

import estimates
from estimates import AGE_GROUPS, BY_AGE_CSV, GROUPS, OVERALL_CSV
from get_data import YEARS

ROOT = Path(__file__).parent

# Economist-style palette and furniture.
RED_TAG = "#E3120B"
COLORS = {"college": "#006BA2", "hs_or_less": "#DB444B"}
LABELS = {"college": "College degree", "hs_or_less": "High school or less"}
RATIO_COLOR = "#006BA2"
REFERENCE = "#758D99"
GRID = "#B7C6CF"
TEXT = "#0C0C0C"
TEXT_2 = "#595959"
BAND_ALPHA = 0.18
SOURCE = "Source: Federal Reserve Board, Survey of Consumer Finances"

plt.rcParams.update({
    # Arial first: matplotlib reads only the regular face of macOS's Helvetica .ttc files.
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"],
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def econ_axis(ax, label_years=(1989, 2001, 2013, 2025), y_labels=True):
    """Horizontal gridlines only, y labels on the right, dark baseline, small x ticks."""
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", length=0, labelsize=9, colors=TEXT, pad=2,
                   labelright=y_labels)
    ax.set_xticks(YEARS, minor=True)
    ax.set_xticks(label_years)
    ax.tick_params(axis="x", which="both", direction="out", color=TEXT, labelsize=9,
                   labelcolor=TEXT)
    ax.tick_params(axis="x", which="major", length=5)
    ax.tick_params(axis="x", which="minor", length=3)
    ax.set_xlim(YEARS[0] - 1, YEARS[-1] + 1)


def econ_frame(fig, title, subtitle, note):
    """Red rule and tag at the top-left, bold title, subtitle, source line."""
    fig.add_artist(plt.Line2D([0.012, 0.988], [0.995, 0.995], color=RED_TAG,
                              linewidth=1.2, transform=fig.transFigure))
    fig.add_artist(Rectangle((0.012, 0.955), 0.035, 0.035, color=RED_TAG,
                             transform=fig.transFigure, linewidth=0))
    fig.text(0.012, 0.935, title, fontsize=15, fontweight="bold", color=TEXT, va="top")
    fig.text(0.012, 0.885, subtitle, fontsize=11, color=TEXT, va="top")
    fig.text(0.012, 0.012, f"{note}\n{SOURCE}", fontsize=8.5, color=TEXT_2, va="bottom",
             linespacing=1.4)


def panel_title(ax, text):
    ax.set_title(text, loc="left", fontsize=10.5, fontweight="bold", color=TEXT, pad=10)


def band_line(ax, x, mid, lo, hi, color, **kw):
    ax.fill_between(x, lo, hi, color=color, alpha=BAND_ALPHA, linewidth=0)
    ax.plot(x, mid, color=color, linewidth=2.2, solid_capstyle="round", **kw)


def plot_overall(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.6),
                                   gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.22})
    x = df["year"]

    for group in GROUPS:
        k = lambda s: df[f"median_{group}{s}"] / 1e3
        band_line(ax1, x, k(""), k("_lo"), k("_hi"), COLORS[group])
    econ_axis(ax1)
    ax1.set_ylim(0, 600)
    ax1.set_yticks(range(0, 601, 100))
    panel_title(ax1, "Median net worth, $'000")
    ax1.text(2006, 545, LABELS["college"], color=COLORS["college"], fontsize=10,
             fontweight="bold", ha="center")
    ax1.text(2006, 125, LABELS["hs_or_less"], color=COLORS["hs_or_less"], fontsize=10,
             fontweight="bold", ha="center")

    band_line(ax2, x, df["median_ratio"], df["median_ratio_lo"], df["median_ratio_hi"],
              RATIO_COLOR)
    econ_axis(ax2)
    ax2.set_ylim(0, 9)
    ax2.set_yticks(range(0, 10, 1))
    panel_title(ax2, "Ratio, college to high school or less")
    # Label the first and last values just above the line, inside the plot area.
    for i, dx, ha in [(0, 0.6, "left"), (len(df) - 1, -0.6, "right")]:
        r = df["median_ratio"].iloc[i]
        ax2.text(x.iloc[i] + dx, r + 0.3, f"{r:.1f}", ha=ha, va="bottom", fontsize=10,
                 fontweight="bold", color=RATIO_COLOR)

    econ_frame(
        fig,
        "Degrees of separation",
        "United States, families by education of household head, 2025 prices",
        "Note: shaded areas show 95% confidence intervals. "
        "Household head is the SCF reference person.",
    )
    fig.subplots_adjust(left=0.012, right=0.955, top=0.76, bottom=0.14)
    return fig


def plot_by_age(by_age, overall):
    fig, axes = plt.subplots(2, len(AGE_GROUPS), figsize=(15, 7.4), sharex=True,
                             gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.32,
                                          "wspace": 0.28})
    ratio_top = 18
    for col, (code, label) in enumerate(AGE_GROUPS.items()):
        d = by_age[by_age["agecl"] == code]
        x = d["year"]
        top, bottom = axes[0, col], axes[1, col]

        for group in GROUPS:
            k = lambda s: d[f"median_{group}{s}"] / 1e3
            band_line(top, x, k(""), k("_lo"), k("_hi"), COLORS[group])
        econ_axis(top, label_years=(1989, 2007, 2025))
        top.set_ylim(0, None)
        top.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
        panel_title(top, "Under 35" if code == 1 else label)

        bottom.plot(overall["year"], overall["median_ratio"], color=REFERENCE,
                    linewidth=1.2, linestyle=(0, (3, 2)))
        band_line(bottom, x, d["median_ratio"], d["median_ratio_lo"], d["median_ratio_hi"],
                  RATIO_COLOR)
        econ_axis(bottom, label_years=(1989, 2007, 2025), y_labels=(col == len(AGE_GROUPS) - 1))
        bottom.set_ylim(0, ratio_top)
        bottom.set_yticks(range(0, ratio_top + 1, 3))
        r = d["median_ratio"].to_numpy()
        bottom.text(0.03, 0.95, f"1989: {r[0]:.1f}\n2025: {r[-1]:.1f}",
                    transform=bottom.transAxes, va="top", fontsize=9, color=TEXT)

    econ_frame(
        fig,
        "Middle-aged divergence",
        "United States, families by education and age of household head, 2025 prices",
        "Note: shaded areas show 95% confidence intervals. Panels hold roughly 60–650 "
        "sampled families each, so single surveys are noisy.",
    )
    fig.subplots_adjust(left=0.012, right=0.965, top=0.72, bottom=0.11)

    # Row labels and a key, Economist-style: plain text, colored where it names a series.
    # Placed from the laid-out axes so they sit just above each row.
    top_y = axes[0, 0].get_position().y1 + 0.065
    ratio_y = axes[1, 0].get_position().y1 + 0.03
    fig.text(0.012, top_y, "Median net worth, $'000 (scale differs by panel):",
             fontsize=10.5, color=TEXT, fontweight="bold")
    fig.text(0.255, top_y, LABELS["college"], fontsize=10.5, color=COLORS["college"],
             fontweight="bold")
    fig.text(0.335, top_y, LABELS["hs_or_less"], fontsize=10.5,
             color=COLORS["hs_or_less"], fontweight="bold")
    fig.text(0.012, ratio_y, "Ratio, college to high school or less (same scale):",
             fontsize=10.5, color=TEXT, fontweight="bold")
    fig.text(0.272, ratio_y, "– – all ages", fontsize=10.5, color=REFERENCE)
    return fig


def main():
    if not (OVERALL_CSV.exists() and BY_AGE_CSV.exists()):
        estimates.main()
    overall = pd.read_csv(OVERALL_CSV)
    by_age = pd.read_csv(BY_AGE_CSV)
    out = ROOT / "figures"
    out.mkdir(exist_ok=True)
    for name, fig in [("wealth_gap_education.png", plot_overall(overall)),
                      ("wealth_gap_by_age.png", plot_by_age(by_age, overall))]:
        fig.savefig(out / name, dpi=200)
        print(f"Wrote figures/{name}")


if __name__ == "__main__":
    main()
