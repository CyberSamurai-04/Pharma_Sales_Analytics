# Building the Power BI dashboard

This folder has everything needed to build a real Power BI dashboard on top of
the same data the Python/SQL analysis uses — a proper star schema, not a raw
export.

## What's here

| File | Rows | Role |
|---|---|---|
| `fact_sales.csv` | 16,848 | Fact table — Date, ATCCode, Units |
| `dim_drug.csv` | 8 | Dimension — ATCCode, DrugName, DrugGroup |
| `dim_date.csv` | 2,191 | Dimension — one row per calendar day, **2014-01-01 to 2019-12-31** |

`dim_date` deliberately covers full calendar years, not just the days that have
sales (the real data stops 8 Oct 2019). Power BI's time-intelligence functions
(`SAMEPERIODLASTYEAR`, `DATESINPERIOD`) need every date present and contiguous —
gaps at year boundaries silently produce wrong YoY numbers, which is a common
mistake worth avoiding on purpose here.

## Step 1 — Import

Open Power BI Desktop → **Get Data → Text/CSV** → import all three files from
this folder.

## Step 2 — Build the relationships

Go to **Model view**. Drag to create:

- `fact_sales[Date]` → `dim_date[Date]` — many-to-one, single direction
- `fact_sales[ATCCode]` → `dim_drug[ATCCode]` — many-to-one, single direction

## Step 3 — Mark the date table

Select `dim_date` → **Table tools → Mark as date table** → choose the `Date`
column. This is required, not optional — `SAMEPERIODLASTYEAR` and
`DATESINPERIOD` silently return wrong results without it.

While in the model, fix two sort orders that are a common Power BI gotcha:

- `dim_date[MonthName]` → **Column tools → Sort by column** → `Month`
- `dim_date[WeekdayName]` → **Column tools → Sort by column** → `Weekday`

Without this, "April, August, December…" sorts alphabetically instead of
chronologically on any chart that uses the name instead of the number.

## Step 4 — Measures

Create a new measure (**Table tools → New measure**) for each of these,
against `fact_sales`:

```dax
Total Units = SUM(fact_sales[Units])
```

```dax
% of Total =
DIVIDE(
    [Total Units],
    CALCULATE([Total Units], ALL(dim_drug))
)
```

```dax
Prior Year Units = CALCULATE([Total Units], SAMEPERIODLASTYEAR(dim_date[Date]))

YoY % =
DIVIDE([Total Units] - [Prior Year Units], [Prior Year Units])
```

```dax
3M Moving Avg =
VAR CurrentDate = MAX(dim_date[Date])
VAR TrailingMonths =
    CALCULATETABLE(
        SUMMARIZE(dim_date, dim_date[YearMonth], "MonthlyTotal", [Total Units]),
        DATESINPERIOD(dim_date[Date], CurrentDate, -3, MONTH)
    )
RETURN
    AVERAGEX(TrailingMonths, [MonthlyTotal])
```

**Sanity-check this last one before trusting it** — I wrote it against known
DAX patterns but couldn't execute it myself. Put it on a line chart at month
grain and confirm April 2019 reads **≈1,900.0** and September 2019 reads
**≈1,563.8** — those are the verified values from the SQL version of this same
calculation (`sql_queries.py`, query 4). If it doesn't match, the simpler,
zero-DAX fallback is: right-click the line chart → **Analytics** pane → add a
**Trend line** set to a 3-period moving average — a native Power BI feature,
no formula to get wrong.

## Step 5 — Build three pages

**Page 1 — Overview**
- 4 KPI cards: `[Total Units]`, `DISTINCTCOUNT(dim_drug[ATCCode])`, min/max of
  `dim_date[Date]` (filtered to dates with sales), `[% of Total]` for the top
  category
- Bar chart: `Total Units` by `DrugName`, sorted descending
- Slicers: `dim_date[Year]`, `dim_drug[DrugGroup]`

**Page 2 — Trend & Seasonality**
- Line chart: `Total Units` and `3M Moving Avg` by `dim_date[YearMonth]`
- A second visual with `WeekdayName` (sorted) on the axis and `Total Units` —
  this reproduces the weekday-effect finding from the Methodology page

**Page 3 — Year-over-Year**
- Matrix: `dim_date[Year]` on rows, `dim_drug[DrugName]` on columns,
  `[YoY %]` as the value, conditional formatting → colour scale (red → white →
  blue) — this is the interactive version of the static heatmap chart

## Step 6 — Save

**Save As** → `pharma_sales_dashboard.pbix`, into this same `powerbi/` folder.

Once it's built, send me a screenshot or export — I'll wire a Power BI section
into the Results page on the site, the same way the three static charts are in
there now.
