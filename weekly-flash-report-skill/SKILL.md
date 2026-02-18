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

**Critical note about ORDER_METRICS TIME_PERIOD_TYPE for daily data**:
- Prefer `TIME_PERIOD_TYPE = 'day_dow'` for all daily queries. It does NOT require
  a `TIME_PERIOD_TO_DATE` filter.
- The `'day'` period type can silently drop low-sales days (e.g., a $160 day absent
  from `'day'` but present in `'day_dow'`). This causes partial-week detection to fail
  and guideline hours to be severely miscalculated.
- For `TIME_PERIOD_TYPE = 'week'`: do NOT filter on `TIME_PERIOD_TO_DATE`. The weekly
  total is split across `true` and `false` rows — both must be summed.

**Critical note about VOIDED orders**:
- ALL queries against ORDER_METRICS must include `AND VOIDED = false`
- Voided orders carry $0 in AMOUNT but still count in ORDER_COUNT
- Failing to filter voids inflates order counts, deflates avg ticket, and skews SST%

### Query 1 — Weekly Sales (4 weeks + PY)

**Important**: Use `TIME_PERIOD_TYPE = 'week'` and do NOT filter on `TIME_PERIOD_TO_DATE`.
The weekly aggregate is split across two rows: `TIME_PERIOD_TO_DATE = false` (most of the
week) and `TIME_PERIOD_TO_DATE = true` (the partial/MTD portion). Both must be summed to
get the correct weekly total. Filtering to only `false` will undercount sales significantly.
(For daily granularity, always use `TIME_PERIOD_TYPE = 'day_dow'` — see general note above.)

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
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND DINING_CATEGORY = 'Catering'
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
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN DATEADD('week', -52, '{ws_minus_21}'::DATE)
                            AND DATEADD('week', -52, '{ws_plus_6}'::DATE)
  AND DINING_CATEGORY = 'Catering'
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
`TIME_PERIOD_TYPE = 'day_dow'`. PAYABLE_HOURS excludes unpaid break time and matches
the corporate labor dashboard exactly. Using TOTAL_HOURS from LABOR_REPORTS will
overcount by ~2% due to included break time.

```sql
SELECT
  TIME_PERIOD_VALUE AS report_date,
  SUM(PAYABLE_HOURS) AS payable_hours,
  SUM(TOTAL_PAY) AS total_pay
FROM CHABI_DBT.LABOR_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
GROUP BY 1
ORDER BY 1
```

### Query 6 — Daily Sales (for guideline calculation)

**Important**: Use `TIME_PERIOD_TYPE = 'day_dow'` (NOT `'day'`). The `day` type can
miss low-sales days (e.g., Fayetteville Tue $160 was absent from `day` results but
present in `day_dow`). `day_dow` does not require a `TIME_PERIOD_TO_DATE` filter.

```sql
SELECT
  TIME_PERIOD_VALUE AS report_date,
  SUM(NET_AMOUNT) AS amount
FROM CHABI_DBT.ORDER_METRICS
WHERE RESTAURANT_LOCATION = '{location}'
  AND BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{ws_minus_21}' AND '{ws_plus_6}'
  AND VOIDED = false
GROUP BY 1
ORDER BY 1
```

### Query 7 — Scheduled Hours (from 7shifts)

**Important**: Include both `REGULAR_HOURS` and `OT_HOURS` (overtime). OT hours can
be significant on weekends (e.g., Fayetteville Sun = 41.5 OT hrs). Omitting OT_HOURS
will undercount scheduled hours by 3–5% at high-volume or new locations.

```sql
WITH base AS (
  SELECT d._file, d._modified, d.date, d.location,
         d.regular_hours, COALESCE(d.ot_hours, 0) AS ot_hours,
         d.role, m.RESTAURANT_NUMBER
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
  SELECT RESTAURANT_NUMBER, date, MAX_BY(_file, _modified) AS _file
  FROM base GROUP BY 1, 2
)
SELECT b.date AS report_date,
  SUM(b.regular_hours) + SUM(b.ot_hours) AS scheduled_hours
FROM base b
INNER JOIN latest_files lf
  ON lf.RESTAURANT_NUMBER = b.RESTAURANT_NUMBER
 AND lf.date = b.date
 AND lf._file = b._file
GROUP BY 1 ORDER BY 1
```

### Query 8 — AGM Hours

```sql
SELECT store_listing AS location,
       start_date::date AS start_date,
       end_date::date AS end_date,
       daily_hours,
       weekly_hours
FROM LABOR_AGM_HOURS.LABOR_AGM_HOURS_TABLE
WHERE store_listing = '{location}'
ORDER BY start_date
```

### Query 9 — Labor Guidelines Table

**Important**: Pull the full latest guidelines from the database instead of hardcoding.
The table extends well beyond $60K for high-volume locations like College Station ($130K+/week).
Hardcoding a partial table will cap guidelines at 828 hours, severely undercounting.

```sql
WITH guidelines AS (
  SELECT
    weekly_net_sales_threshold AS threshold,
    weekly_total_hours AS hours,
    start_date::date AS start_date
  FROM LABOR_GUIDELINES.LABOR_GUIDELINES_TABLE
  WHERE brand = 'Fuego Tortilla Grill'
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY weekly_net_sales_threshold
    ORDER BY start_date DESC
  ) = 1
)
SELECT threshold, hours FROM guidelines
WHERE hours > 0
  AND (threshold % 5000 = 0 OR threshold IN (2100, 18800))
ORDER BY threshold
```

This returns ~80 rows at $5K intervals. Build a dict and interpolate between thresholds.
Alternatively, embed the known breakpoints:

```python
GUIDELINES_TABLE = {
    0: 0, 2100: 326, 18800: 328, 20000: 345,
    25000: 416, 30000: 488, 35000: 559, 40000: 631, 45000: 702,
    50000: 744, 55000: 786, 60000: 828, 65000: 870, 70000: 912,
    75000: 953, 80000: 995, 85000: 1037, 90000: 1079, 95000: 1120,
    100000: 1162, 105000: 1204, 110000: 1246, 115000: 1287, 120000: 1329,
    125000: 1371, 130000: 1413, 135000: 1454, 140000: 1496, 145000: 1538,
    150000: 1580, 155000: 1621, 160000: 1663, 165000: 1705, 170000: 1747,
    175000: 1788, 180000: 1830, 185000: 1872, 190000: 1914, 195000: 1956,
    200000: 1997,
}
```

## Step 2: Compute Labor Guidelines

### Guideline Lookup (interpolation)

**Important**: Use linear interpolation between thresholds, NOT floor lookup.
The corporate dashboard interpolates, so floor lookup will undercount by ~5-10 hours
per week.

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

### Distribution Algorithm (with AGM adjustment)

Two modes depending on whether the week is complete:

#### PARTIAL WEEK (`days_with_sales < days_open`)

Triggered by store closures (e.g., MLK weekend, weather, new store soft-open)
where the number of days with sales > 0 is less than `days_open` (6 for Fuego).

- Each operating day's sales is projected to a full week: `projected_weekly = daily_sales × days_open`
- Look up guideline hours for that projected weekly sales independently per day
- Daily allocation = `weekly_total_hours / days_open` (even split)
- **Zero-lookup guard**: if projected sales too low for any guideline (lookup = 0),
  the day gets **0 total hours** — no DOW adjustment, no AGM either
- DOW + AGM adjustments applied only to days with lookup > 0

```python
# Partial week example — Burleson Jan 19 (5 of 6 days operating):
# Tue $3,299 × 6 = $19,792 → lookup 341 → 341/6 = 56.8 + DOW(8) = 64.8
# Sat $18.75 × 6 = $112.50 → lookup 0   → 0 (no DOW, no AGM)
```

#### FULL WEEK (`days_with_sales >= days_open`)

Uses **full proportional allocation** — the entire `weekly_total_hours` is
distributed by weight. This matches the updated Card 274 SQL.

```python
def compute_daily_guideline(week_start, daily_sales_dict, location=None):
    DAYS_OPEN = 6  # Fuego closed Mondays
    DOW_ADJ = {0: 0, 1: 8, 2: 3, 3: 3, 4: 3, 5: 3, 6: -20}
    rate = 54 / 3000  # hours per dollar for weighting
    days = [week_start + timedelta(days=i) for i in range(7)]

    days_with_sales = sum(1 for d in days if daily_sales_dict.get(d, 0) > 0)
    is_partial = days_with_sales < DAYS_OPEN
    week_net = sum(daily_sales_dict.get(d, 0) for d in days)

    result = {}
    agm_total = 0

    if is_partial:
        for d in days:
            day_sales = daily_sales_dict.get(d, 0)
            if d.weekday() == 0 or day_sales <= 0:
                result[d] = 0
            else:
                projected_weekly = day_sales * DAYS_OPEN
                day_lookup = lookup_guide(projected_weekly)
                if day_lookup <= 0:
                    result[d] = 0  # No DOW or AGM when lookup = 0
                else:
                    daily_hrs = day_lookup / DAYS_OPEN
                    agm_hrs = get_agm_daily_hours(location, d) if location else 0
                    result[d] = daily_hrs + DOW_ADJ.get(d.weekday(), 0) + agm_hrs
                    agm_total += agm_hrs
    else:
        total_guide = lookup_guide(week_net)
        raw = []
        for d in days:
            if d.weekday() == 0:
                raw.append(0)
            else:
                s = daily_sales_dict.get(d, 0)
                if s <= 0: raw.append(0)
                elif s <= 9000: raw.append(s * rate)
                else: raw.append(9000 * rate + (s - 9000) * rate * 0.80)
        total_raw = sum(raw) or 1
        for i, d in enumerate(days):
            day_sales = daily_sales_dict.get(d, 0)
            if d.weekday() == 0 or day_sales <= 0:
                result[d] = 0
            else:
                base = (raw[i] / total_raw) * total_guide + DOW_ADJ.get(d.weekday(), 0)
                agm_hrs = get_agm_daily_hours(location, d) if location else 0
                result[d] = base + agm_hrs
                agm_total += agm_hrs

    guide_total = sum(result.values())
    return result, guide_total, week_net
```

### Key design decisions in the guideline algorithm

1. **Partial vs full week detection**: Count days with sales > 0. If fewer than
   `days_open` (6 for Fuego), use per-day projection. Otherwise full proportional.

2. **Partial week per-day projection**: Each day projected independently to a full
   week (`daily_sales × days_open`), guideline looked up per that projection, then
   split evenly (`weekly_total_hours / days_open`). If the lookup returns 0 (projected
   sales below minimum threshold ~$2,100), the day gets 0 total — no DOW, no AGM.

3. **Full proportional allocation**: `(weight / sum_weights) * weekly_total_hours`
   distributes the FULL lookup amount to operating days only. No flat base per day.

4. **Linear weighting from $0**: The weight formula ramps linearly from $0 (not
   from $3K). This smooths distribution across days. The knee at $9K and 0.80
   multiplier above provide diminishing returns for very high-sales days.

5. **Zero-sales guard**: If `day_sales <= 0`, guideline = 0 for that day — no base
   hours, no DOW adjustment, no AGM hours. This matters for partial opening weeks
   at new locations (e.g., Fayetteville's first week).

6. **AGM hours added per operating day**: AGM daily hours from `LABOR_AGM_HOURS_TABLE`
   are added ONLY to days with sales > 0 and lookup > 0. `DAILY_HOURS = WEEKLY_HOURS / 6`
   (Fuego closed Mondays).

**Validation reference points** (Feb 9, 2026 week — full week):
- Burleson: ~523 hrs (no AGM)
- College Station: ~1,485 hrs (includes +50 AGM weekly)
- Fayetteville: ~828 hrs (includes +200 AGM weekly)
- San Antonio: ~714 hrs (no AGM)
- San Marcos: ~702 hrs (includes -50 AGM weekly)
- Waco: ~748 hrs (no AGM)

**Validation reference points** (Jan 19, 2026 week — partial week, store closures):
- Burleson: ~287 hrs (5 of 6 days operating, Sat=$18.75 → lookup=0 → 0 hrs)
- Fayetteville: ~646 hrs (4 of 6 days operating + AGM)
- Waco: ~475 hrs (full week — 7 days had sales ≥ days_open)
- San Antonio: ~559 hrs (full week)
- San Marcos: ~548 hrs (full week)

## Step 3: KPI Cards — Prior Year vs Trailing 4-Week Average

For locations **with prior year data**, compute SSS%, SST%, and ticket change vs PY
as normal (badge text: "vs PY").

For locations **without prior year data** (new stores where `amount_py == 0`), compare
the current week against the **trailing 4-week average** of the prior 3 weeks in the
data range. Badge text: "vs T4W Avg".

```python
if has_py:
    sss = pct_chg(cw_amount, cw_py)
    sst = pct_chg(cw_orders, cw_orders_py)
    kpi_suffix = "vs PY"
else:
    prior_weeks = [w for w in week_starts[1:] if w in loc_weekly]
    trail_amt = sum(loc_weekly[w]["amount"] for w in prior_weeks) / len(prior_weeks)
    trail_orders = sum(loc_weekly[w]["orders"] for w in prior_weeks) / len(prior_weeks)
    sss = pct_chg(cw_amount, trail_amt)
    sst = pct_chg(cw_orders, trail_orders)
    kpi_suffix = "vs T4W Avg"
```

## Step 4: Generate the GM Message

Write a concise paragraph (4–6 sentences) for the General Manager. Cover:

1. **Sales headline** — Total sales, SSS% direction, recent trend context
   - For PY stores: "up/down X% vs prior year"
   - For new stores: "up/down X% vs trailing 4-week avg"
2. **Order growth** — SST% (or "vs T4W" for new stores), traffic direction
3. **Avg ticket** — Current vs comparison baseline
4. **Labor** — Labor %, improvement vs prior week, actual vs guideline hours
5. **Over/under days** — Days that ran >2hrs over or under guideline
6. **Reviews** — Highlight scores from Google/Ovation/Yelp if available
7. **Closing** — Brief encouraging call to action

Tone: professional, concise, data-driven. Name actual numbers. One paragraph.

## Step 5: Format & Pill Helpers

Read `references/helpers.md` for the complete set of Python formatting helper functions
including: `fm()`, `fn()`, `fp()`, `pct_chg()`, `pill_sss()`, `pill_labor_diff()`,
`pill_labor_ratio()`, `pill_hrs_vs_sch()`, `pill_labor_pct()`, `pill_rating()`,
`kpi_badge()`, `wk_short()`, `wk_long()`.

## Step 6: Build the HTML

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

## Step 7: Output as PDF

The report is generated as HTML first (to leverage the full CSS design), then converted
to a pixel-perfect PDF using headless Chrome.

### 7a. Save the intermediate HTML

Save the generated HTML to a temporary file in the working directory:
```python
html_path = f"/home/claude/weekly_flash_{location_slug}.html"
with open(html_path, "w") as f:
    f.write(html_string)
```
where `location_slug` = location name lowercased, spaces replaced by underscores.

### 7b. Convert HTML to PDF with headless Chrome

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

### 7c. Deliver the PDF

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
