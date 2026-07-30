"""
Builds a Power BI-ready star schema from the cleaned data: a fact table, a drug
dimension, and a proper date dimension (full calendar years, not just the days
that happen to have sales -- Power BI's time intelligence functions need every
date in the range, weekends and gaps included, or SAMEPERIODLASTYEAR silently
returns wrong numbers on the missing days).

Run:  python build_powerbi_extract.py
"""

import os
import pandas as pd

CLEAN_DIR = os.path.join("..", "data", "cleaned")
OUT_DIR = "."


def build_fact():
    long_df = pd.read_csv(os.path.join(CLEAN_DIR, "sales_long.csv"), parse_dates=["date"])
    fact = long_df[["date", "atc_code", "units"]].rename(
        columns={"date": "Date", "atc_code": "ATCCode", "units": "Units"}
    )
    return fact.sort_values(["Date", "ATCCode"]).reset_index(drop=True)


def build_dim_drug():
    drugs = pd.read_csv(os.path.join(CLEAN_DIR, "drug_categories.csv"))
    return drugs.rename(columns={
        "atc_code": "ATCCode", "drug_name": "DrugName", "drug_group": "DrugGroup",
    })


def build_dim_date(min_date, max_date):
    """One row per calendar day, full years on both ends, so SAMEPERIODLASTYEAR
    and friends always have a matching prior-year date to compare against."""
    start = pd.Timestamp(year=min_date.year, month=1, day=1)
    end = pd.Timestamp(year=max_date.year, month=12, day=31)
    dates = pd.date_range(start, end, freq="D")

    dim = pd.DataFrame({"Date": dates})
    dim["Year"] = dim["Date"].dt.year
    dim["Quarter"] = dim["Date"].dt.quarter
    dim["QuarterLabel"] = "Q" + dim["Quarter"].astype(str) + " " + dim["Year"].astype(str)
    dim["Month"] = dim["Date"].dt.month
    dim["MonthName"] = dim["Date"].dt.strftime("%B")
    dim["MonthShort"] = dim["Date"].dt.strftime("%b")
    dim["YearMonth"] = dim["Date"].dt.strftime("%Y-%m")
    dim["Day"] = dim["Date"].dt.day
    dim["Weekday"] = dim["Date"].dt.weekday + 1  # 1 = Monday ... 7 = Sunday
    dim["WeekdayName"] = dim["Date"].dt.strftime("%A")
    dim["IsWeekend"] = dim["Weekday"].isin([6, 7])
    return dim


def main():
    fact = build_fact()
    dim_drug = build_dim_drug()
    dim_date = build_dim_date(fact["Date"].min(), fact["Date"].max())

    fact.to_csv(os.path.join(OUT_DIR, "fact_sales.csv"), index=False)
    dim_drug.to_csv(os.path.join(OUT_DIR, "dim_drug.csv"), index=False)
    dim_date.to_csv(os.path.join(OUT_DIR, "dim_date.csv"), index=False)

    print(f"fact_sales.csv   {len(fact):>7,} rows   {fact['Date'].min():%Y-%m-%d} to {fact['Date'].max():%Y-%m-%d}")
    print(f"dim_drug.csv     {len(dim_drug):>7,} rows")
    print(f"dim_date.csv     {len(dim_date):>7,} rows   {dim_date['Date'].min():%Y-%m-%d} to {dim_date['Date'].max():%Y-%m-%d}")
    print("\nRelationships to build in Power BI:")
    print("  fact_sales[Date]    -> dim_date[Date]     (many-to-one)")
    print("  fact_sales[ATCCode] -> dim_drug[ATCCode]  (many-to-one)")


if __name__ == "__main__":
    main()
