---
name: weekly-flash-report
description: >
  Generate a branded Weekly Flash Report for any Fuego Tortilla Grill location.
  Pulls the last 4 weeks of sales, catering, reviews, labor, and scheduled hours data
  from Snowflake via Chabi Analytics, computes labor guidelines, generates an AI-written
  GM message, and produces a polished single-page portrait PDF report with the S3
  "Teal Thread" design. The report is generated as HTML first (to leverage full CSS
  styling), then converted to a pixel-perfect PDF using headless Chrome with CSS
  @page directives controlling orientation and margins.
  Use this skill whenever the user asks for a weekly flash, weekly report, flash report,
  weekly summary, store performance report, location weekly update, or GM report for
  any Fuego location. Also trigger when a user says something casual like "how did
  San Marcos do this week" or "pull the weekly numbers for College Station" or
  "generate the flash for Waco". Trigger for any request that involves summarizing
  a Fuego location's weekly performance across sales, labor, and reviews.
---

# Weekly Flash Report

This skill generates a single-page portrait PDF report summarizing the most recent
week's performance for a Fuego Tortilla Grill location. The report covers sales,
catering, ratings/reviews, daily labor, and labor trends — all benchmarked against
prior year and internal labor guidelines. A short AI-written "Message to General
Manager" provides narrative context at the top. The report is built as HTML first
(to leverage the full S3 "Teal Thread" CSS design), then converted to a pixel-perfect
PDF using headless Chrome with CSS @page directives.

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
5. Converts the HTML to PDF using headless Chrome
6. Saves the PDF to the outputs directory

This approach (Python → HTML → PDF via headless Chrome) is the most reliable way to
produce a pixel-perfect PDF because Chrome renders the full CSS exactly as a browser
would, preserving grid layouts, background colors, pills, fonts, and all visual styling.
The CSS @page directive controls page size, orientation, and margins directly in the
stylesheet rather than via Playwright API options.

## Step 1: Pull Data from Snowflake

Run all queries via `Chabi_Analytics__run_query`. Run independent queries in parallel.
The report needs 4 weeks of data ending on the most recent completed Sunday.
Calculate the 4 week-start Mondays: `ws` (most recent), `ws-7d`, `ws-14d`, `ws-21d`.
The date range spans from `ws-21d` through `ws+6d` (the Sunday ending the most recent week).

**Critical note about ORDER_METRICS TIME_PERIOD_TO_DATE**:
- For `TIME_PERIOD_TYPE = 'week'`: AMOUNT is in rows where `TIME_PERIOD_TO_DATE = false`
- For `TIME_PERIOD_TYPE = 'day'`: AMOUNT is in rows where `TIME_PERIOD_TO_DATE = true`
This is counter-intuitive but verified. Getting this wrong will return all zeros.

**Critical note about VOIDED orders**:
- ALL queries against ORDER_METRICS must include `AND VOIDED = false`
- Voided orders carry $0 in AMOUNT but still count in ORDER_COUNT
- Failing to filter voids inflates order counts, deflates avg ticket, and skews SST%

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
  AND VOIDED = false
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
  AND VOIDED = false
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
  AND VOIDED = false
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

### Query 5 — Daily Labor (payable hours + pay, all 4 weeks)

**Important**: Use `PAYABLE_HOURS` (not `TOTAL_HOURS`) from `LABOR_METRICS` with
`TIME_PERIOD_TYPE = 'day'` and `TIME_PERIOD_TO_DATE = true`. PAYABLE_HOURS excludes
unpaid break time and matches the corporate labor dashboard exactly. Using TOTAL_HOURS
from LABOR_REPORTS will overcount by ~2% due to included break time.

```sql
SELECT
  TIME_PERIOD_VALUE AS report_date,
  SUM(PAYABLE_HOURS) AS payable_hours,
  SUM(TOTAL_PAY) AS total_pay
FROM CHABI_DBT.LABOR_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND TIME_PERIOD_TO_DATE = true
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
  AND VOIDED = false
GROUP BY 1
ORDER BY 1
```

### Query 7 — Scheduled Hours from 7shifts (all 4 weeks)

Scheduled hours come from the 7shifts scheduling system, not from LABOR_REPORTS.
The raw data is in `SEVEN_SHIFTS_DATA_FUEGO_TORTILLA_GRILL.SCHEDULED_HOURS_WAGES`.
Multiple file versions may exist per date, so you must deduplicate by selecting only
the latest file per restaurant+date (using `MAX_BY(_file, _modified)`).

**Critical**: Use the latest-file-per-date approach (not shift-level dedup). Each
7shifts file export is a complete snapshot of the schedule for that date. Deduping
by individual shift fields (in_time, out_time, role) across all files retains stale
shifts from older exports when schedules change, inflating hours by ~20%.

Exclude management roles (GM, AM, KM) since their hours are not included in the
guideline calculation.

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

### Guideline Lookup — Interpolation

**Important**: Use linear interpolation between thresholds, NOT floor lookup.
The corporate dashboard interpolates, so floor lookup will undercount by ~5-10 hours
per week. Do NOT subtract AGM hours — the corporate system does not apply an AGM
adjustment.

```python
def lookup_guide(net_sales):
    """Interpolate between guideline thresholds."""
    thresholds = sorted(GUIDELINES_TABLE.items())
    if net_sales <= 0:
        return 0
    lower_t, lower_h = thresholds[0]
    for i, (t, h) in enumerate(thresholds):
        if t > net_sales:
            lower_t, lower_h = thresholds[i - 1]
            upper_t, upper_h = t, h
            frac = (net_sales - lower_t) / (upper_t - lower_t)
            return lower_h + frac * (upper_h - lower_h)
        lower_t, lower_h = t, h
    return thresholds[-1][1]
```

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

    # Week net sales and total guideline — NO AGM subtraction
    week_net = sum(daily_sales_dict.get(d, 0) for d in days)
    total_guide = lookup_guide(week_net)
    total_raw = sum(raw) or 1

    DOW_ADJ = {0: 0, 1: 8, 2: 3, 3: 3, 4: 3, 5: 3, 6: -20}
    result = {}
    for i, d in enumerate(days):
        if d.weekday() == 0:
            result[d] = 0
        else:
            result[d] = max(0, (raw[i] / total_raw) * total_guide + DOW_ADJ.get(d.weekday(), 0))
    return result, total_guide, week_net
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

**Portrait A4 layout**: The report uses a compact CSS design optimized for portrait A4.
All sizing (fonts, padding, margins) is scaled down from the base design to fit the
full report on a single page. The CSS includes a `@page` directive that controls
page size and orientation directly — no need for Playwright margin/orientation options.

**Full-page distribution**: The `.report-container` uses `display: flex` with
`justify-content: space-between` and `min-height: 100vh` to evenly distribute all
sections from top to bottom of the page. Sections have no bottom margins — flexbox
handles all spacing.

**No box shadows**: Sections and KPI cards have no `box-shadow` for a cleaner look.

## Step 6: Output as PDF

The report is generated as HTML first (to leverage the full CSS design), then converted
to a pixel-perfect PDF using headless Chrome.

### 6a. Save the intermediate HTML

Save the generated HTML to a temporary file in the working directory:
```python
html_path = f"/home/claude/weekly_flash_{location_slug}.html"
with open(html_path, "w") as f:
    f.write(html_string)
```
where `location_slug` = location name lowercased, spaces replaced by underscores.

### 6b. Convert HTML to PDF with headless Chrome

Use headless Chrome directly (not Playwright) to print the HTML to PDF. The CSS @page
directive handles page size, orientation, and margins, so no API-level options are
needed for those. This approach is more reliable than Playwright for `file://` URLs.

```bash
google-chrome --headless --no-sandbox --disable-gpu \
  --print-to-pdf=/path/to/output.pdf \
  --print-to-pdf-no-header \
  --no-pdf-header-footer \
  file:///path/to/input.html
```

The CSS @page directive in the HTML controls the layout:
```css
@page {
  size: A4 portrait;
  margin: 0.2in 0.2in;
}
```

**Key settings:**
- `--print-to-pdf-no-header` and `--no-pdf-header-footer` — removes Chrome's default
  header/footer (page numbers, URL, date)
- `print-color-adjust: exact` in the CSS `@media print` block preserves all background
  colors, pills, header gradients, and teal accents
- The CSS `@page { size: A4 portrait; margin: 0.2in; }` controls page size and margins
  directly — tight margins maximize space for the data-dense tables

### 6c. Deliver the PDF

The output filename must follow this convention, with all words title-cased:
```
Weekly Flash - {Location} - {date_range}.pdf
```
where `{date_range}` is the short week range, e.g. `Feb 9 – 15, 2026`.

```python
import shutil
week_end = week_start + timedelta(days=6)
date_range = f"{week_start.strftime('%b %-d')} – {week_end.strftime('%-d')}, {week_end.year}"
filename = f"Weekly Flash - {location} - {date_range}".title() + ".pdf"
output_path = f"/mnt/user-data/outputs/{filename}"
shutil.copy(pdf_path, output_path)
```

The HTML intermediate file can be kept in `/home/claude/` for debugging but is
not delivered to the user.
