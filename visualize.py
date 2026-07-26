"""
Builds the portfolio charts from the SQLite database.

Reads through the same queries that sql_queries.py prints, so the charts and the
terminal output can't drift apart. Charts go to visualizations/ as PNGs.

Run:  python sql_queries.py   (first, to build the db)
      python visualize.py
"""

import os
import matplotlib
matplotlib.use("Agg")  # writing files, no interactive window needed

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from sql_queries import QUERIES, connect

OUT_DIR = "visualizations"

# Muted corporate palette. Blue carries the data, orange is the one accent,
# everything structural (grid, axis, labels) sits well behind it.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
ORANGE = "#eb6834"

thousands = FuncFormatter(lambda x, _: f"{x:,.0f}")


def set_style():
    """One look for every chart."""
    sns.set_theme(style="white")
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_SOFT,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def title_block(ax, title, subtitle):
    """Bold headline with a quieter line of context underneath."""
    ax.set_title(title, fontsize=14, fontweight="600", color=INK,
                 loc="left", pad=26)
    ax.text(0, 1.035, subtitle, transform=ax.transAxes,
            fontsize=9.5, color=INK_SOFT, va="bottom")


def footnote(fig, text):
    fig.text(0.01, -0.02, text, fontsize=8, color=INK_MUTED, ha="left")


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"  {name}")


# --------------------------------------------------------------------------- #
# Chart 1 -- which categories actually move
# --------------------------------------------------------------------------- #

def chart_top_categories(conn):
    df = pd.read_sql_query(QUERIES["top_categories"], conn).sort_values("total_units")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["drug_name"], df["total_units"], color=BLUE, height=0.62)

    # Value at the end of each bar -- eight bars is few enough to label them all.
    span = df["total_units"].max()
    for name, units, pct in zip(df["drug_name"], df["total_units"], df["pct_of_total"]):
        ax.text(units + span * 0.012, name, f"{units:,.0f}   ({pct:.1f}%)",
                va="center", fontsize=9, color=INK_SOFT)

    ax.set_xlim(0, span * 1.18)
    ax.xaxis.set_major_formatter(thousands)
    ax.set_xlabel("Units sold")
    ax.set_ylabel("")
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)

    title_block(
        ax,
        "Pyrazolones and Anilides account for half of all units sold",
        "Total units by drug category, Jan 2014 - Oct 2019",
    )
    footnote(fig, "Source: Kaggle pharma sales data. Categories labelled by ATC classification.")
    save(fig, "01_top_drug_categories.png")


# --------------------------------------------------------------------------- #
# Chart 2 -- the trend, with the noise smoothed out
# --------------------------------------------------------------------------- #

def chart_monthly_trend(conn):
    df = pd.read_sql_query(QUERIES["moving_average"], conn)

    # The data stops on 8 October 2019, so that last month is only a week long
    # and plots as a cliff. Cut it rather than ship a misleading chart.
    df = df[df["month"] < "2019-10"].copy()
    df["month"] = pd.to_datetime(df["month"])

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(df["month"], df["units"], color=BLUE, linewidth=1.4, alpha=0.55,
            label="Monthly units")
    ax.plot(df["month"], df["moving_avg_3m"], color=ORANGE, linewidth=2.4,
            label="3-month moving average")

    # Label the trend line where it ends instead of relying on the legend alone.
    last = df.iloc[-1]
    ax.annotate(f"{last['moving_avg_3m']:,.0f}",
                xy=(last["month"], last["moving_avg_3m"]),
                xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9, fontweight="600", color=ORANGE)

    ax.yaxis.set_major_formatter(thousands)
    ax.set_xlabel("")
    ax.set_ylabel("Units sold per month")
    ax.set_ylim(0, df["units"].max() * 1.12)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="lower left", fontsize=9, ncol=2)

    title_block(
        ax,
        "Sales swing on a hard seasonal cycle, peaking every winter",
        "Total monthly units with a 3-month moving average, Jan 2014 - Sep 2019",
    )
    footnote(fig, "October 2019 excluded: the source data ends on the 8th, so the month is incomplete.")
    save(fig, "02_monthly_sales_trend.png")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    set_style()

    conn = connect()
    try:
        print(f"Writing charts to {OUT_DIR}/")
        chart_top_categories(conn)
        chart_monthly_trend(conn)
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
