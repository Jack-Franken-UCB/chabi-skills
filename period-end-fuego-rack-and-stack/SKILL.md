---
name: period-end-fuego-rack-and-stack
description: >
  Generate a Fuego Tortilla Grill multi-week consolidated Rack & Stack report.
  Pulls trailing N weeks (default 4) of sales, labor, reviews, catering, and
  scheduling data from Snowflake via Chabi Analytics, computes labor guidelines,
  ranks all stores across multiple dimensions, generates AI insights verified
  against the data, and produces a branded HTML/PDF report.
  Use this skill whenever the user asks for a period-end report, consolidated
  report, rack-and-stack, multi-week summary, monthly rollup, 4-week report,
  trailing period performance, or system-level performance comparison across
  Fuego locations. Also trigger for "how did Fuego do this month", "compare
  all locations for the last 4 weeks", "period-end rack and stack", or
  "give me the consolidated view across stores".
---

# Period-End Fuego Rack & Stack Report

This skill generates a multi-week consolidated performance report for Fuego
Tortilla Grill covering all locations. The report aggregates N weeks (default 4)
of data and ranks locations across Sales, Labor, Reviews, and Catering — each
with AI-generated insights **programmatically verified** against the underlying data.

## Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Period end | Most recent Saturday | The Sunday ending the most recent complete week |
| Trailing weeks | 4 | Number of weeks to consolidate |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |

Determine the report period automatically: find the most recent completed week
(Monday–Sunday) before today, then work back N weeks from that Monday.

## IMPORTANT: Read Reference Files First

Before writing any code, read these reference files:
- `references/helpers.md` — Python helpers, guideline computation, AGM data, data processing
- `references/html_template.md` — CSS template, HTML structure, component patterns

## Step 1: Identify Locations and Date Range

Available Fuego locations (query LOCATIONS table if unsure):
- Burleson, College Station, Fayetteville, San Antonio, San Marcos, Waco

Comp vs Non-Comp stores:
- **Comp stores** have prior-year data (AMOUNT_PREV_YEAR > 0)
- **Non-comp stores** (new stores) show N/A for SSS%, SST%, and Ticket Change
- System-level SSS/SST is computed from **comp stores only**

Compute N week-start dates (Mondays) working backwards from the report week.

## Step 2: Pull Data from Snowflake

Run all queries via `Chabi_Analytics__run_query`. All tables are in `CHABI_DBT` schema
unless otherwise noted.

### CRITICAL: Use `day_dow` for Prior-Year Comparisons

**Always use `TIME_PERIOD_TYPE = 'day_dow'`** for any query involving prior-year
comparisons (AMOUNT_PREV_YEAR, ORDER_COUNT_PREV_YEAR). The `day_dow` type aligns
PY data by day-of-week (Mon-to-Mon, Tue-to-Tue, etc.) which is the correct comp
methodology for restaurant operations.

Using `TIME_PERIOD_TYPE = 'day'` with `TIME_PERIOD_TO_DATE = true` aligns by
calendar date, which produces slightly different (incorrect) PY totals — typically
off by $1K-$5K systemwide. This was a hard-won lesson.

### Query 1 — Weekly Sales (ORDER_METRICS, day_dow aggregated to weeks)

```sql
SELECT
  RESTAURANT_LOCATION,
  DATE_TRUNC('week', TIME_PERIOD_VALUE) AS week_start,
  SUM(AMOUNT) AS amount,
  SUM(AMOUNT_PREV_YEAR) AS amount_py,
  SUM(ORDER_COUNT) AS orders,
  SUM(ORDER_COUNT_PREV_YEAR) AS orders_py,
  SUM(DISCOUNT_AMOUNT) AS discount
FROM CHABI_DBT.ORDER_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
  AND VOIDED = false
  AND RESTAURANT_LOCATION IN ({locations_csv})
GROUP BY 1, 2
ORDER BY 1, 2
```

This returns CY/PY sales, orders, and discounts per location per week with proper
day-of-week alignment.

### Query 2 — Daily Sales (for guideline computation)

```sql
SELECT
  RESTAURANT_LOCATION, TIME_PERIOD_VALUE, SUM(NET_AMOUNT) AS net_amount
FROM CHABI_DBT.ORDER_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
  AND VOIDED = false
GROUP BY 1, 2
ORDER BY 1, 2
```

Daily sales are needed for the guideline computation algorithm (see helpers.md).

### Query 3 — Daily Labor (LABOR_METRICS, day_dow)

```sql
SELECT
  RESTAURANT_LOCATION, TIME_PERIOD_VALUE,
  SUM(PAYABLE_HOURS) AS hours, SUM(TOTAL_PAY) AS pay
FROM CHABI_DBT.LABOR_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1, 2
ORDER BY 1, 2
```

### Query 4 — Scheduled Hours (Seven Shifts)

**IMPORTANT:** This table is NOT in CHABI_DBT. It lives in brand-specific schemas.
Use `MAX_BY(_file, _modified)` to pick the latest file per (location, date).
Exclude management roles. Use `RESTAURANT_MAPPING.RESTAURANT_MAPPING_TABLE` for
location mapping. Apply a 6AM business-day boundary for cross-midnight shifts.

Reference: See Metabase Card #769 or the weekly-consolidated-report skill for
the full scheduled hours query.

### Query 5 — Catering CY

```sql
SELECT
  RESTAURANT_LOCATION, DATE_TRUNC('week', TIME_PERIOD_VALUE) AS week_start,
  SUM(AMOUNT) AS amount, SUM(ORDER_COUNT) AS orders
FROM CHABI_DBT.ORDER_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
  AND DINING_CATEGORY = 'Catering'
  AND VOIDED = false
GROUP BY 1, 2
```

### Query 6 — Catering PY

Same as Query 5 but shift dates back 364 days (52 weeks).

### Query 7 — Reviews (3 sources)

```sql
-- Google
SELECT RESTAURANT_LOCATION, AVG(STARS) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.GOOGLE_REVIEWS
WHERE BRAND = 'fuego-tortilla-grill'
  AND REVIEW_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1

-- Ovation
SELECT RESTAURANT_LOCATION, AVG(SURVEY_RATING) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.OVATION_SURVEY_REPORTS
WHERE BRAND = 'fuego-tortilla-grill'
  AND SURVEY_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1

-- Yelp
SELECT RESTAURANT_LOCATION, AVG(STARS) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.YELP_REVIEWS
WHERE BRAND = 'fuego-tortilla-grill'
  AND REVIEW_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1
```

Aggregate all reviews across the full period (no weekly breakdown needed for
the rack & stack — just location-level averages and counts).

## Step 3: Compute Metrics

### Per-Location Per-Week

For each location and each week:
1. **Sales**: amount, amount_py, orders, orders_py, discount from Query 1
2. **SSS/SST**: `(CY - PY) / PY * 100` for comp stores; N/A for non-comp
3. **Avg Ticket**: `amount / orders`; ticket change vs PY for comp stores
4. **Labor**: Sum daily hours and pay from Query 3
5. **Scheduled Hours**: Sum daily scheduled from Query 4
6. **Guideline Hours**: Use `compute_daily_guideline()` from helpers.md with daily sales
7. **Labor %**: `pay / amount * 100`
8. **SPLH**: `amount / hours`
9. **vs Guide**: `actual_hours - guide_hours` (number and percent)
10. **Catering**: amount and orders from Query 5

### N-Week Aggregates (per location)

Sum all weekly values across the trailing period:
- Total amount, amount_py, orders, orders_py
- Total labor hours, pay, guideline hours, scheduled hours
- Total catering amount, orders, PY amount
- SSS/SST computed on the totals (comp stores only)
- Avg ticket on the totals
- Reviews: weighted average across Google, Ovation, Yelp by count

### System Totals

- **System sales/orders**: Sum all locations
- **System SSS/SST**: Compute from comp stores only (CY comp total vs PY comp total)
- **System avg ticket**: system_amount / system_orders
- **Ticket change**: comp CY ticket vs comp PY ticket
- **System labor %**: system_pay / system_amount * 100
- **System SPLH**: system_amount / system_hours

## Step 4: Rank Locations

Four rack & stack tables, each ranked by a different metric:

| Section | Ranked By | Direction |
|---------|-----------|-----------|
| Sales | 4-Wk Total Sales ($) | Highest first |
| Labor | vs Guide % | Lowest first (closest to guide = best) |
| Reviews | Weighted Avg Rating | Highest first |
| Catering | 4-Wk Catering $ | Highest first |

## Step 5: Generate AI Insights

Each rack & stack section includes an AI Insight callout with data-backed
observations. Guidelines:

1. Lead with the standout performer and cite specific numbers
2. Highlight trends (weekly trajectories) where notable
3. Call out areas of concern with context (e.g., new store ramp, AGM adjustments)
4. Keep to 3-5 sentences per section
5. **All numbers in callouts must be verifiable** from the computed data

## Step 6: Build HTML Report

Follow the S3 "Teal Thread" design from `references/html_template.md`.

### Report Structure

1. **Header**: Dark charcoal with teal glow bars, report title, location count, date range
2. **KPI Cards** (5 across): System Sales, System Orders, Avg Ticket, System Labor %, Catering
3. **System Summary**: GM-style narrative paragraph with key data points
4. **System Performance Trends**: Weekly breakdown table (newest week first) with:
   - Sales, SSS%, Orders, SST%, Avg Ticket
   - Guide Hrs, Sch Hrs, Actual Hrs, vs Guide #, vs Guide %, Labor%, SPLH
   - Catering
   - 4-week total row at bottom
5. **Sales Rack & Stack**: Ranked table + AI Insight callout
   - Columns: Rank, Location, 4-Wk Sales, SSS%, Orders, SST%, Avg Ticket, Tkt Chg, Catering, Basis
6. **Labor Rack & Stack**: Ranked table + AI Insight callout
   - Columns: Rank, Location, 4-Wk Sales, Guide Hrs, Sch Hrs, Actual Hrs, vs Guide #, vs Guide %, Labor%, SPLH
7. **Reviews Rack & Stack**: Ranked table + AI Insight callout
   - Columns: Rank, Location, Google, #, Ovation, #, Yelp, #, Wtd Avg, Total #
8. **Catering Rack & Stack**: Ranked table + AI Insight callout
   - Columns: Rank, Location, Orders, Cat $, Cat $ PY, vs PY
9. **Footer**: Generated date, brand name, data source

### Pill Thresholds

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| SSS/SST % | ≥ 0% | — | < 0% |
| Labor % | < 25% | 25-30% | > 30% |
| vs Guide # | < 0 (under) | ≈ 0 | > 0 (over) |
| vs Guide % | < 99.5% | 99.5-100.5% | > 100.5% |
| Rating | ≥ 4.5 | 4.0-4.4 | < 4.0 |
| Rank | 1st solid green, 2nd light green, 3rd gold | Middle gray | Last red |

### Formatting

- Money: `fm(value)` for whole dollars, `fm(value, 2)` for SPLH/avg ticket
- Hours: `fn(value, 0)` — rounded to whole numbers
- Percentages: One decimal place
- N/A for non-comp SSS/SST/ticket change

## Step 7: Generate PDF

Use WeasyPrint (or Chrome headless if available) to render the HTML to PDF.
Save both HTML and PDF to `/mnt/user-data/outputs/`.

Filename pattern:
```
Period End - Fuego Rack & Stack - {period_description}.pdf
Period End - Fuego Rack & Stack - {period_description}.html
```

## Reference Implementation

A complete working Python implementation is available at
`references/reference_implementation.py`. This contains all data processing,
guideline computation, HTML generation, and output — ready to run after
substituting fresh query results for the hardcoded data arrays.
