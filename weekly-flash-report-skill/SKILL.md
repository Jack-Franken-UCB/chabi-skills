---
name: weekly-flash-report
description: >
  Generate a branded Weekly Flash Report for any Fuego Tortilla Grill location.
  Pulls the last 4 weeks of sales, catering, reviews, labor, and scheduled hours data
  from Snowflake via Chabi Analytics, computes labor guidelines, generates an AI-written
  GM message, and produces a polished HTML report with the S3 "Teal Thread" design.
  Use this skill whenever the user asks for a weekly flash, weekly report, flash report,
  weekly summary, store performance report, location weekly update, or GM report for
  any Fuego location. Also trigger when a user says something casual like "how did
  San Marcos do this week" or "pull the weekly numbers for College Station" or
  "generate the flash for Waco". Trigger for any request that involves summarizing
  a Fuego location's weekly performance across sales, labor, and reviews.
---

# Weekly Flash Report

This skill generates a single-page HTML report summarizing the most recent week's
performance for a Fuego Tortilla Grill location. The report covers sales, catering,
ratings/reviews, daily labor, and labor trends — all benchmarked against prior year
and internal labor guidelines. A short AI-written "Message to General Manager"
provides narrative context at the top.

## Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Location | *(ask user)* | Valid RESTAURANT_LOCATION values: San Marcos, Waco, San Antonio, College Station, Burleson, Fayetteville |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |
| Report week | Most recent completed Monday–Sunday week | Override with a specific Monday date if user asks for a past week |

If the user doesn't specify a location, ask them. If they don't specify a week,
use the most recent completed week (find the last Monday that is at least 7 days ago).

## Implementation Approach

Write a Python script that:
1. Queries all data from Snowflake via `Chabi_Analytics__run_query`
2. Processes results into Python data structures
3. Computes labor guidelines, KPIs, and pill formatting
4. Generates the complete HTML string
5. Saves to the outputs directory

This approach (Python script generating HTML) is the most reliable way to produce
the report because it avoids template escaping issues and allows clean arithmetic.

## Step 1: Pull Data from Snowflake

Run all queries via `Chabi_Analytics__run_query`. Run independent queries in parallel.
The report needs 4 weeks of data ending on the most recent completed Sunday.
Calculate the 4 week-start Mondays: `ws` (most recent), `ws-7d`, `ws-14d`, `ws-21d`.
The date range spans from `ws-21d` through `ws+6d` (the Sunday ending the most recent week).

**Critical note about ORDER_METRICS TIME_PERIOD_TO_DATE**:
- For `TIME_PERIOD_TYPE = 'week'`: AMOUNT is in rows where `TIME_PERIOD_TO_DATE = false`
- For `TIME_PERIOD_TYPE = 'day'`: AMOUNT is in rows where `TIME_PERIOD_TO_DATE = true`
This is counter-intuitive but verified. Getting this wrong will return all zeros.

### Query 1 — Weekly Sales (4 weeks + PY)

**Important**: Use `TIME_PERIOD_TYPE = 'week'` with `TIME_PERIOD_TO_DATE = false`.
In ORDER_METRICS, weekly aggregates live in the `week` period type with `to_date = false`.
(For daily granularity, use `TIME_PERIOD_TYPE = 'day'` with `TIME_PERIOD_TO_DATE = true`.)

```sql
SELECT
  TIME_PERIOD_VALUE AS week_start,
  SUM(AMOUNT) AS amount,
  SUM(AMOUNT_PREV_YEAR) AS amount_py,
  SUM(NET_AMOUNT) AS net_amount,
  SUM(ORDER_COUNT) AS orders,
  SUM(ORDER_COUNT_PREV_YEAR) AS orders_py,
  SUM(DISCOUNT_AMOUNT) AS discount
FROM CHABI_DBT.ORDER_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'week'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND TIME_PERIOD_TO_DATE = false
GROUP BY 1
ORDER BY 1 DESC
```

### Query 2 — Catering (current year, 4 weeks)

```sql
SELECT
  DATE_TRUNC('week', TIME_PERIOD_VALUE) AS week_start,
  SUM(AMOUNT) AS amount,
  SUM(ORDER_COUNT) AS orders
FROM CHABI_DBT.ORDER_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND DINING_CATEGORY = 'Catering'
  AND TIME_PERIOD_TO_DATE = true
GROUP BY 1
ORDER BY 1 DESC
```

### Query 3 — Catering Prior Year (4 weeks, shifted back 52 weeks)

```sql
SELECT
  DATEADD('week', 52, DATE_TRUNC('week', TIME_PERIOD_VALUE)) AS week_start,
  SUM(AMOUNT) AS amount,
  SUM(ORDER_COUNT) AS orders
FROM CHABI_DBT.ORDER_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day'
  AND TIME_PERIOD_VALUE BETWEEN DATEADD('week', -52, '{ws_minus_21}'::DATE)
                            AND DATEADD('week', -52, '{ws_plus_6}'::DATE)
  AND DINING_CATEGORY = 'Catering'
  AND TIME_PERIOD_TO_DATE = true
GROUP BY 1
ORDER BY 1 DESC
```

### Query 4 — Reviews (4 weeks, all sources)

```sql
SELECT
  DATE_TRUNC('week', FEEDBACK_DATE) AS week_start,
  'google' AS source,
  AVG(STARS) AS avg_rating,
  COUNT(*) AS review_count
FROM CHABI_DBT.GOOGLE_REVIEWS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND FEEDBACK_DATE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
GROUP BY 1, 2

UNION ALL

SELECT
  DATE_TRUNC('week', FEEDBACK_DATE) AS week_start,
  'ovation' AS source,
  AVG(STARS) AS avg_rating,
  COUNT(*) AS review_count
FROM CHABI_DBT.OVATION_SURVEY_REPORTS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND FEEDBACK_DATE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
GROUP BY 1, 2

UNION ALL

SELECT
  DATE_TRUNC('week', FEEDBACK_DATE) AS week_start,
  'yelp' AS source,
  AVG(STARS) AS avg_rating,
  COUNT(*) AS review_count
FROM CHABI_DBT.YELP_REVIEWS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND FEEDBACK_DATE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
GROUP BY 1, 2

ORDER BY 1 DESC, 2
```

### Query 5 — Daily Labor (hours + pay, all 4 weeks)

```sql
SELECT
  REPORT_DATE,
  SUM(TOTAL_HOURS) AS total_hours,
  SUM(TOTAL_PAY) AS total_pay
FROM CHABI_DBT.LABOR_REPORTS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND REPORT_DATE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
GROUP BY 1
ORDER BY 1
```

### Query 6 — Daily Sales (for guideline calculation)

**Important**: Use `TIME_PERIOD_TO_DATE = true` for daily granularity (this is where
AMOUNT lives for day-level rows in ORDER_METRICS).

```sql
SELECT
  TIME_PERIOD_VALUE AS report_date,
  SUM(AMOUNT) AS amount
FROM CHABI_DBT.ORDER_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND TIME_PERIOD_TO_DATE = true
GROUP BY 1
ORDER BY 1
```

### Query 7 — Scheduled Hours from 7shifts (all 4 weeks)

Scheduled hours come from the 7shifts scheduling system, not from LABOR_REPORTS.
The raw data is in `SEVEN_SHIFTS_DATA_FUEGO_TORTILLA_GRILL.SCHEDULED_HOURS_WAGES`.
Multiple file versions may exist per date, so you must deduplicate by selecting only
the latest file per restaurant+date (using `MAX_BY(_file, _modified)`).

Exclude management roles (GM, AM, KM) since their hours are handled separately
via the AGM adjustment in the guideline calculation.

```sql
WITH base AS (
  SELECT
    d._file,
    d._modified,
    d.date,
    d.location,
    d.regular_hours,
    d.role,
    m.RESTAURANT_NUMBER
  FROM SEVEN_SHIFTS_DATA_FUEGO_TORTILLA_GRILL.SCHEDULED_HOURS_WAGES d
  JOIN RESTAURANT_MAPPING.RESTAURANT_MAPPING_TABLE m
    ON d.location = m.SEVEN_SHIFTS_LOCATION
  JOIN CHABI_DBT.LOCATIONS l
    ON m.RESTAURANT_NUMBER = l.RESTAURANT_NUMBER
  WHERE l.restaurant_location = '{location}'
    AND d.date BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
    AND d.role NOT IN ('General Manager','Assistant Manager','Kitchen Manager')
),
latest_files AS (
  SELECT
    RESTAURANT_NUMBER,
    date,
    MAX_BY(_file, _modified) AS _file
  FROM base
  GROUP BY 1, 2
)
SELECT
  b.date AS report_date,
  SUM(b.regular_hours) AS scheduled_hours
FROM base b
INNER JOIN latest_files lf
  ON lf.RESTAURANT_NUMBER = b.RESTAURANT_NUMBER
  AND lf.date = b.date
  AND lf._file = b._file
GROUP BY 1
ORDER BY 1
```

**Note**: Mondays typically have no scheduled hours (closed day). If a day is missing
from the results, treat scheduled hours as 0 for that day.

## Step 2: Compute Labor Guidelines

The labor guideline system allocates weekly target hours based on weekly net sales,
then distributes them across days proportionally to each day's sales volume with
day-of-week adjustments.

### Guideline Lookup Table

```python
GUIDELINES_TABLE = {
    0: 0, 2100: 326, 20000: 345, 25000: 416, 26000: 431, 27000: 445,
    28000: 459, 29000: 474, 30000: 488, 35000: 559, 40000: 631,
    45000: 702, 50000: 744, 55000: 786, 60000: 828
}
```

Find the largest threshold that does not exceed the week's net sales. That value is
the base guideline hours.

### AGM Adjustment

Subtract 50 hours per week (AGM hours are pre-allocated and should not count against
the store's guideline).

### Day-of-Week Adjustments

After proportional distribution, add:

| Day | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|-----|-----|-----|-----|-----|-----|-----|-----|
| Adj | 0 | +8 | +3 | +3 | +3 | +3 | -20 |

### Distribution Algorithm

```python
def compute_daily_guideline(week_start, daily_sales_dict):
    rate = 54 / 3000
    days = [week_start + timedelta(days=i) for i in range(7)]

    # Monday (day 0 of week) gets 0 guideline hours
    raw = []
    for d in days:
        if d.weekday() == 0:  # Monday
            raw.append(0)
        else:
            s = daily_sales_dict.get(d, 0)
            if s <= 0:
                raw.append(0)
            elif s <= 3000:
                raw.append(s * rate)
            elif s <= 9000:
                raw.append(54 + (s - 3000) * rate)
            else:
                raw.append(54 + 6000 * rate + (s - 9000) * rate * 0.80)

    # Week net sales and total guideline
    week_net = sum(daily_sales_dict.get(d, 0) for d in days)
    total_guide = lookup_guide(week_net) - 50  # AGM adjustment
    total_raw = sum(raw) or 1

    DOW_ADJ = {0: 0, 1: 8, 2: 3, 3: 3, 4: 3, 5: 3, 6: -20}
    result = {}
    for i, d in enumerate(days):
        if d.weekday() == 0:
            result[d] = 0
        else:
            result[d] = max(0, (raw[i] / total_raw) * total_guide + DOW_ADJ.get(d.weekday(), 0))
    return result
```

## Step 3: Generate the GM Message

Write a concise paragraph (4–6 sentences) for the General Manager. Cover:

1. **Sales headline** — Total sales, SSS% direction, recent trend context
2. **Order growth** — SST%, traffic direction
3. **Avg ticket** — Current vs PY, upsell focus if below
4. **Labor** — Labor %, improvement vs prior week, actual vs guideline hours
5. **Over/under days** — Days that ran >2hrs over or under guideline
6. **Reviews** — Highlight scores from Google/Ovation/Yelp if available
7. **Closing** — Brief encouraging call to action

Tone: professional, concise, data-driven. Name actual numbers. One paragraph.

## Step 4: Format & Pill Helpers

Read `references/helpers.md` for the complete set of Python formatting helper functions
including: `fm()`, `fn()`, `fp()`, `pct_chg()`, `pill_sss()`, `pill_labor_diff()`,
`pill_labor_ratio()`, `pill_hrs_vs_sch()`, `pill_labor_pct()`, `pill_rating()`,
`kpi_badge()`, `wk_short()`, `wk_long()`.

## Step 5: Build the HTML

Read `references/html_template.md` for the complete CSS and HTML structure. The design
is the S3 "Teal Thread" variant — original Fuego tan palette with teal accents threading
through KPI card tops, section header left borders, GM message border, and labor icons.

Key S3 overrides from the base design:
- KPI cards: `border-top: 3px solid var(--fuego-teal)` (instead of red)
- Section headers: `border-left: 3px solid var(--fuego-teal)`
- GM message: `border-left: 4px solid var(--fuego-teal)` (instead of gold)
- GM label color: `#5a9e9b` (teal-ish)
- Labor icons: `background: #e8f1f0; color: #4a8e8b`

### Table Row Construction

**Current week highlighting**: The most recent week's row gets `style="background:#f5efe9;"`
and values wrapped in `<strong>` tags.

**Monday row**: Dimmed with `style="opacity:0.5;"`, shows $0 sales, 0 guide hrs,
"—" for scheduled, actual hours + pay only. All other cells show "—".

**Total row**: `class="total-row"`, summed across all 7 days.

## Step 6: Output

Save the generated HTML to:
```
weekly_flash_{location_slug}.html
```
where `location_slug` = location name lowercased, spaces replaced by underscores.

Write to the outputs directory and provide the user a link to view/download.
