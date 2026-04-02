"""
chart_generator.py
------------------
Generates a 4-panel KPI dashboard saved as PNG files to the output/charts directory.
Charts are also stitched into a single dashboard image.
"""

import os
import logging
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")               # headless — no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

log = logging.getLogger(__name__)

# ── Colour palette ──────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#0d1117",
    "surface":   "#161b22",
    "border":    "#30363d",
    "text":      "#e6edf3",
    "muted":     "#8b949e",
    "green":     "#3fb950",
    "yellow":    "#d29922",
    "red":       "#f85149",
    "blue":      "#58a6ff",
    "purple":    "#bc8cff",
}

BAR_COLORS = [PALETTE["blue"], PALETTE["green"], PALETTE["purple"],
              PALETTE["yellow"], PALETTE["red"]]


def _apply_dark_style(ax, title: str = "") -> None:
    """Apply consistent dark-mode styling to an Axes."""
    ax.set_facecolor(PALETTE["surface"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=9)
    ax.xaxis.label.set_color(PALETTE["muted"])
    ax.yaxis.label.set_color(PALETTE["muted"])
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["border"])
    ax.set_title(title, color=PALETTE["text"], fontsize=11, fontweight="bold", pad=10)
    ax.title.set_fontfamily("monospace")


# ── Chart 1: Monthly on-time delivery trend ─────────────────────────────────

def chart_monthly_trend(df: pd.DataFrame, ax: plt.Axes) -> None:
    monthly = (
        df.groupby("month")
        .agg(total=("order_id", "count"), on_time=("is_on_time", "sum"))
        .reset_index()
    )
    monthly["rate"] = monthly["on_time"] / monthly["total"] * 100
    months_short = [m[-5:] for m in monthly["month"]]   # "01-01" → last 5 chars

    ax.plot(months_short, monthly["rate"], color=PALETTE["green"],
            linewidth=2.5, marker="o", markersize=5, zorder=3)
    ax.fill_between(months_short, monthly["rate"], alpha=0.15, color=PALETTE["green"])
    ax.axhline(monthly["rate"].mean(), color=PALETTE["yellow"], linewidth=1,
               linestyle="--", label=f"Avg {monthly['rate'].mean():.1f}%")
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8, facecolor=PALETTE["bg"], edgecolor=PALETTE["border"],
              labelcolor=PALETTE["muted"])
    _apply_dark_style(ax, "📈  Monthly On-Time Delivery Rate")


# ── Chart 2: On-time rate by warehouse ─────────────────────────────────────

def chart_warehouse_performance(df: pd.DataFrame, ax: plt.Axes) -> None:
    wh = (
        df.groupby("warehouse")
        .agg(total=("order_id", "count"), on_time=("is_on_time", "sum"))
        .reset_index()
    )
    wh["rate"] = wh["on_time"] / wh["total"] * 100
    wh = wh.sort_values("rate")
    short_names = [w.split("-")[0] for w in wh["warehouse"]]

    colors = [PALETTE["red"] if r < 70 else PALETTE["yellow"] if r < 80 else PALETTE["green"]
              for r in wh["rate"]]

    bars = ax.barh(short_names, wh["rate"], color=colors, edgecolor=PALETTE["border"],
                   linewidth=0.5, height=0.6)
    for bar, val in zip(bars, wh["rate"]):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", color=PALETTE["text"], fontsize=9)
    ax.set_xlim(0, 110)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    _apply_dark_style(ax, "🏭  On-Time Rate by Warehouse")


# ── Chart 3: Avg cost per order by category ─────────────────────────────────

def chart_cost_by_category(df: pd.DataFrame, ax: plt.Axes) -> None:
    cat = (
        df.groupby("product_category")["cost_lkr"]
        .mean()
        .reset_index()
        .sort_values("cost_lkr")
    )

    bars = ax.barh(cat["product_category"], cat["cost_lkr"],
                   color=BAR_COLORS[:len(cat)],
                   edgecolor=PALETTE["border"], linewidth=0.5, height=0.6)
    for bar, val in zip(bars, cat["cost_lkr"]):
        ax.text(val + 100, bar.get_y() + bar.get_height() / 2,
                f"LKR {val:,.0f}", va="center", color=PALETTE["text"], fontsize=8)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
    ax.set_xlabel("Avg Cost (LKR ×1000)")
    _apply_dark_style(ax, "💰  Avg Cost per Order by Category")


# ── Chart 4: Order volume by month (stacked status) ────────────────────────

def chart_order_volume(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = (
        df.groupby(["month", "delivery_status"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    months_short = [m[-5:] for m in pivot["month"]]
    status_colors = {
        "Delivered":  PALETTE["green"],
        "Delayed":    PALETTE["yellow"],
        "In Transit": PALETTE["blue"],
        "Cancelled":  PALETTE["red"],
    }
    bottom = pd.Series([0] * len(pivot))
    for status, color in status_colors.items():
        if status in pivot.columns:
            ax.bar(months_short, pivot[status], bottom=bottom,
                   color=color, label=status, edgecolor=PALETTE["bg"], linewidth=0.3)
            bottom += pivot[status]

    ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("Orders")
    ax.legend(fontsize=8, facecolor=PALETTE["bg"], edgecolor=PALETTE["border"],
              labelcolor=PALETTE["muted"], loc="upper left")
    _apply_dark_style(ax, "📦  Monthly Order Volume by Status")


# ── Dashboard assembly ──────────────────────────────────────────────────────

def generate_dashboard(df: pd.DataFrame, kpis: dict, charts_dir: str) -> None:
    """
    Render a 2×2 KPI dashboard and save individual + combined PNGs.

    Args:
        df:         Cleaned orders DataFrame.
        kpis:       KPI dict from calculate_kpis().
        charts_dir: Directory to save PNG files.
    """
    charts_path = Path(charts_dir)
    charts_path.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 10), facecolor=PALETTE["bg"])
    gs  = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.30,
                   left=0.07, right=0.97, top=0.90, bottom=0.08)

    axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(2)]
    for ax in axes:
        ax.set_facecolor(PALETTE["surface"])

    chart_monthly_trend(df, axes[0])
    chart_warehouse_performance(df, axes[1])
    chart_cost_by_category(df, axes[2])
    chart_order_volume(df, axes[3])

    # Header
    overall = kpis["overall"]
    fig.suptitle(
        f"Supply Chain KPI Dashboard   |   "
        f"On-Time: {overall['on_time_rate_pct']}%   "
        f"Orders: {overall['total_orders']:,}   "
        f"Avg Cost: LKR {overall['avg_cost_per_order']:,.0f}",
        color=PALETTE["text"], fontsize=13, fontweight="bold",
        fontfamily="monospace",
    )

    dashboard_path = charts_path / "kpi_dashboard.png"
    fig.savefig(str(dashboard_path), dpi=150, bbox_inches="tight",
                facecolor=PALETTE["bg"])
    plt.close(fig)
    log.info(f"  Dashboard saved → {dashboard_path}")

    # Save each chart individually as well
    chart_fns = [
        ("monthly_trend",          chart_monthly_trend),
        ("warehouse_performance",  chart_warehouse_performance),
        ("cost_by_category",       chart_cost_by_category),
        ("order_volume",           chart_order_volume),
    ]
    for name, fn in chart_fns:
        fig_single, ax_single = plt.subplots(figsize=(8, 5), facecolor=PALETTE["bg"])
        ax_single.set_facecolor(PALETTE["surface"])
        fn(df, ax_single)
        out = charts_path / f"{name}.png"
        fig_single.savefig(str(out), dpi=120, bbox_inches="tight",
                           facecolor=PALETTE["bg"])
        plt.close(fig_single)
        log.info(f"  Chart saved → {out}")
