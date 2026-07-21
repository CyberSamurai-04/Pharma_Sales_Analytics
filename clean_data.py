"""
Cleans the raw Kaggle pharma sales CSVs and writes tidy versions to data/cleaned/.

Run:  python clean_data.py
"""

import os
import pandas as pd

RAW_DIR = os.path.join("data", "raw", "archive")
CLEAN_DIR = os.path.join("data", "cleaned")

DRUG_COLS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]

# The files don't all use the same date format, so keep it explicit per file.
FILES = {
    "salesdaily.csv": ("sales_daily", "%m/%d/%Y"),
    "saleshourly.csv": ("sales_hourly", "%m/%d/%Y %H:%M"),
    "salesweekly.csv": ("sales_weekly", "%m/%d/%Y"),
    "salesmonthly.csv": ("sales_monthly", "%Y-%m-%d"),
}


def load_raw(filename, date_format):
    df = pd.read_csv(os.path.join(RAW_DIR, filename))
    df = df.rename(columns={"datum": "date", "Weekday Name": "weekday"})
    df["date"] = pd.to_datetime(df["date"], format=date_format)
    return df


def clean(df, name):
    """Standard cleaning pass. Prints what it actually changed."""
    before = len(df)

    # A missing quantity means nothing was dispensed, not that the value is
    # unknown -- so zero is the honest fill, not a mean.
    missing = int(df[DRUG_COLS].isna().sum().sum())
    if missing:
        df[DRUG_COLS] = df[DRUG_COLS].fillna(0)

    df = df.drop_duplicates()
    dupe_rows = before - len(df)

    dupe_dates = int(df["date"].duplicated().sum())
    if dupe_dates:
        df = df.drop_duplicates(subset="date", keep="first")

    df = df.sort_values("date").reset_index(drop=True)

    print(f"  {name:<14} rows {before} -> {len(df)}  "
          f"| nulls filled: {missing}  "
          f"| dupe rows: {dupe_rows}  "
          f"| dupe dates: {dupe_dates}")
    return df


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)

    print(f"Reading raw files from {RAW_DIR}\n")
    cleaned = {}
    for filename, (name, date_format) in FILES.items():
        df = load_raw(filename, date_format)
        cleaned[name] = clean(df, name)

    print(f"\nWriting to {CLEAN_DIR}")
    for name, df in cleaned.items():
        path = os.path.join(CLEAN_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"  {name}.csv  ({len(df):,} rows, {len(df.columns)} cols)")

    daily = cleaned["sales_daily"]
    print(f"\nDate range: {daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}")
    print("Done.")


if __name__ == "__main__":
    main()
