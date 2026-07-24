"""
Builds the SQLite database from data/cleaned/ and runs the analysis queries.

Everything analytical lives in SQL here rather than pandas -- the point of this
stage is the query layer, so grouping, ranking, LAG() and the moving average
window are all done by the database. Pandas only reads the results back for
display.

visualize.py imports QUERIES from this module so the charts run off exactly the
same SQL that gets printed here.

Run:  python sql_queries.py
"""

import os
import sqlite3
import pandas as pd

DB_PATH = "pharma_sales.db"
CLEAN_DIR = os.path.join("data", "cleaned")

# csv name -> table name
TABLES = {
    "sales_daily": "sales_daily",
    "sales_weekly": "sales_weekly",
    "sales_monthly": "sales_monthly",
    "sales_hourly": "sales_hourly",
    "sales_long": "sales_long",
    "drug_categories": "dim_drug",
}


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #

TOP_CATEGORIES = """
SELECT
    d.drug_name,
    d.drug_group,
    ROUND(SUM(s.units), 1)                                          AS total_units,
    ROUND(100.0 * SUM(s.units) / (SELECT SUM(units) FROM sales_long), 2) AS pct_of_total,
    RANK() OVER (ORDER BY SUM(s.units) DESC)                        AS sales_rank
FROM sales_long s
JOIN dim_drug d ON d.atc_code = s.atc_code
GROUP BY d.atc_code, d.drug_name, d.drug_group
ORDER BY total_units DESC
"""

MONTHLY_TREND = """
WITH monthly AS (
    SELECT
        strftime('%Y-%m', date) AS month,
        SUM(units)              AS units
    FROM sales_long
    GROUP BY strftime('%Y-%m', date)
)
SELECT
    month,
    ROUND(units, 1)                                          AS units,
    ROUND(LAG(units) OVER (ORDER BY month), 1)               AS prev_month,
    ROUND(units - LAG(units) OVER (ORDER BY month), 1)       AS change,
    ROUND(100.0 * (units - LAG(units) OVER (ORDER BY month))
          / LAG(units) OVER (ORDER BY month), 1)             AS pct_change
FROM monthly
ORDER BY month
"""

# 2019 stops on 8 October, so a straight full-year comparison would show every
# category "collapsing" by roughly a quarter. Restricting every year to Jan-Oct
# keeps the comparison like-for-like.
YOY_GROWTH = """
WITH ytd AS (
    SELECT
        s.atc_code,
        d.drug_name,
        s.year,
        SUM(s.units) AS units
    FROM sales_long s
    JOIN dim_drug d ON d.atc_code = s.atc_code
    WHERE s.month <= 10
    GROUP BY s.atc_code, d.drug_name, s.year
),
compared AS (
    SELECT
        drug_name,
        year,
        units,
        LAG(units) OVER (PARTITION BY atc_code ORDER BY year) AS prev_units
    FROM ytd
)
SELECT
    drug_name,
    year,
    ROUND(units, 1)                                     AS ytd_units,
    ROUND(prev_units, 1)                                AS prev_ytd_units,
    ROUND(100.0 * (units - prev_units) / prev_units, 1) AS yoy_pct
FROM compared
WHERE prev_units IS NOT NULL
ORDER BY drug_name, year
"""

MOVING_AVERAGE = """
WITH monthly AS (
    SELECT
        strftime('%Y-%m', date) AS month,
        SUM(units)              AS units
    FROM sales_long
    GROUP BY strftime('%Y-%m', date)
)
SELECT
    month,
    ROUND(units, 1) AS units,
    ROUND(AVG(units) OVER (
        ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 1) AS moving_avg_3m,
    ROUND(units - AVG(units) OVER (
        ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 1) AS vs_trend
FROM monthly
ORDER BY month
"""

QUERIES = {
    "top_categories": TOP_CATEGORIES,
    "monthly_trend": MONTHLY_TREND,
    "yoy_growth": YOY_GROWTH,
    "moving_average": MOVING_AVERAGE,
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def connect():
    return sqlite3.connect(DB_PATH)


def build_database(conn):
    """Load every cleaned CSV into the database, replacing whatever was there."""
    print(f"Building {DB_PATH}")
    for csv_name, table in TABLES.items():
        df = pd.read_csv(os.path.join(CLEAN_DIR, f"{csv_name}.csv"))
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  {table:<15} {len(df):>7,} rows")

    # sales_long carries most of the analysis, so give it something to seek on.
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_long_date ON sales_long(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_long_code ON sales_long(atc_code)")
    conn.commit()


def run_query(conn, sql, title, tail=None):
    """Run a query, print it as a table, and hand back the full result."""
    df = pd.read_sql_query(sql, conn)

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)

    shown = df.tail(tail) if tail else df
    print(shown.to_string(index=False, na_rep="-"))
    if tail and len(df) > tail:
        print(f"\n({len(df)} rows total, showing the last {tail})")

    return df


def main():
    conn = connect()
    try:
        build_database(conn)

        run_query(
            conn,
            TOP_CATEGORIES,
            "1. Top selling drug categories (whole period, 2014-2019)",
        )
        run_query(
            conn,
            MONTHLY_TREND,
            "2. Monthly sales trend with month-over-month change",
            tail=12,
        )
        run_query(
            conn,
            YOY_GROWTH,
            "3. Year-over-year growth by category (Jan-Oct like-for-like)",
        )
        run_query(
            conn,
            MOVING_AVERAGE,
            "4. Monthly sales against a 3-month moving average",
            tail=12,
        )

        print("\nDone.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
