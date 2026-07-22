"""
Cleans the raw Kaggle pharma sales CSVs and writes tidy versions to data/cleaned/.

The four raw files are the same eight drug categories aggregated at different
granularities (hourly / daily / weekly / monthly). Annoyingly they don't all use
the same date format, so each one gets parsed explicitly.

Run:  python clean_data.py
"""

import os
import pandas as pd

RAW_DIR = os.path.join("data", "raw", "archive")
CLEAN_DIR = os.path.join("data", "cleaned")

# The column headers in the raw files are ATC codes. Nobody reading a chart
# knows what "N02BE" means, so keep a lookup and ship it as a dimension table.
ATC_CODES = {
    "M01AB": ("Acetic acid derivatives", "Anti-inflammatory / Antirheumatic"),
    "M01AE": ("Propionic acid derivatives", "Anti-inflammatory / Antirheumatic"),
    "N02BA": ("Salicylic acid derivatives", "Analgesics / Antipyretics"),
    "N02BE": ("Pyrazolones and Anilides", "Analgesics / Antipyretics"),
    "N05B": ("Anxiolytics", "Psycholeptics"),
    "N05C": ("Hypnotics and sedatives", "Psycholeptics"),
    "R03": ("Obstructive airway disease drugs", "Respiratory"),
    "R06": ("Antihistamines for systemic use", "Respiratory"),
}

DRUG_COLS = list(ATC_CODES)

# filename -> (output name, date format)
FILES = {
    "salesdaily.csv": ("sales_daily", "%m/%d/%Y"),
    "saleshourly.csv": ("sales_hourly", "%m/%d/%Y %H:%M"),
    "salesweekly.csv": ("sales_weekly", "%m/%d/%Y"),
    "salesmonthly.csv": ("sales_monthly", "%Y-%m-%d"),
}


def load_raw(filename, date_format):
    """Read one raw CSV and get the date column into a real datetime."""
    df = pd.read_csv(os.path.join(RAW_DIR, filename))
    df = df.rename(columns={"datum": "date", "Weekday Name": "weekday"})
    df["date"] = pd.to_datetime(df["date"], format=date_format)
    return df


def clean(df, name):
    """Standard cleaning pass. Prints what it actually changed."""
    before = len(df)

    # salesdaily has an "Hour" column holding values like 248 and 276 -- it's a
    # leftover sum from however the file was generated, not an hour of the day.
    # The hourly file has a genuine one, so only drop it here.
    if name == "sales_daily" and "Hour" in df.columns:
        df = df.drop(columns=["Hour"])

    # Year/Month are already in the raw files but we re-derive them from the
    # parsed date below, so drop them rather than carry two sets of the same
    # thing in different capitalisation.
    df = df.drop(columns=[c for c in ("Year", "Month") if c in df.columns])

    # A missing quantity here means nothing was dispensed, not that the value is
    # unknown -- so zero is the honest fill, not a mean or a forward fill.
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


def add_date_parts(df):
    """Year / month / quarter columns so the SQL layer doesn't have to derive them."""
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["quarter"] = df["date"].dt.quarter
    return df


def to_long(daily):
    """
    Melt the wide daily table into date / atc_code / units.

    Eight columns of drug codes is fine for a spreadsheet but painful to query --
    every "top category" question turns into eight UNIONs. Long format fixes that.
    """
    long_df = daily.melt(
        id_vars="date",
        value_vars=DRUG_COLS,
        var_name="atc_code",
        value_name="units",
    )
    long_df["year"] = long_df["date"].dt.year
    long_df["month"] = long_df["date"].dt.month
    return long_df.sort_values(["date", "atc_code"]).reset_index(drop=True)


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)

    print(f"Reading raw files from {RAW_DIR}\n")
    cleaned = {}
    for filename, (name, date_format) in FILES.items():
        df = load_raw(filename, date_format)
        cleaned[name] = clean(df, name)

    for name in cleaned:
        cleaned[name] = add_date_parts(cleaned[name])

    cleaned["sales_long"] = to_long(cleaned["sales_daily"])

    # Dimension table for joining readable names onto the ATC codes.
    cleaned["drug_categories"] = pd.DataFrame(
        [(code, name, group) for code, (name, group) in ATC_CODES.items()],
        columns=["atc_code", "drug_name", "drug_group"],
    )

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
