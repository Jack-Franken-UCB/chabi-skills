---
name: system-weekly-flash
description: >
  Generate a Fuego Tortilla Grill system-wide Weekly Flash Report covering all locations.
  Pulls 4 weeks of sales, labor, reviews, catering, and upselling data from Snowflake via
  Chabi Analytics, computes labor guidelines, ranks all stores in rack-and-stack tables,
  generates AI insights verified against the data, and produces a branded PDF.
  Use this skill when the user asks for a system report, overall Fuego report, all-locations
  summary, system flash, or brand-level weekly performance. Also trigger for requests like
  "how did Fuego do this week overall" or "give me the system view".
---

# System Weekly Flash Report

This skill generates a system-wide performance report for Fuego Tortilla Grill covering
all locations. The report includes system KPIs, 4-week trends, and rack-and-stack rankings
for Sales, Labor, Reviews, and Catering — each with AI-generated insights that are
**programmatically verified** against the underlying data before inclusion.

## Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Week ending | Most recent Saturday | The Saturday ending the reporting week (Mon-Sun) |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |
| Trailing weeks | 4 | Number of weeks to show in trends |

Determine the report week automatically: find the most recent completed week (Monday–Sunday)
before today's date. The report week is the most recent full week ending on a Sunday.

## IMPORTANT: Read Reference Files First

Before writing any code, read these reference files:
- `references/helpers.md` — Python helpers, guideline computation, data processing
- `references/html_template.md` — CSS template, HTML structure, component patterns

## Step 1: Identify Locations and Date Range

Available Fuego locations (query LOCATIONS table if unsure):
- Burleson, College Station, Fayetteville, San Antonio, San Marcos, Waco

Comp vs Non-Comp stores:
- **Comp stores** have prior-year data (AMOUNT_PREV_YEAR > 0 in ORDER_METRICS)
- **Non-comp stores** (new stores) show N/A for SSS%, SST%, and Ticket Change
- System-level SSS/SST is computed from **comp stores only**

Compute 4 week-start dates (Mondays) working backwards from the report week.

## Step 2: Pull Data from Snowflake

Run all queries via `Chabi_Analytics__run_query`. All tables are in `CHABI_DBT` schema.

### Query 1 — Weekly Sales (ORDER_METRICS)

```sql
SELECT
  RESTAURANT_LOCATION, TIME_PERIOD_VALUE,
  AMOUNT, AMOUNT_PREV_YEAR, NET_AMOUNT,
  ORDER_COUNT, ORDER_COUNT_PREV_YEAR, DISCOUNT_AMOUNT
FROM CHABI_DBT.ORDER_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'week'
  AND TIME_PERIOD_VALUE IN ({week_starts_csv})
  AND TIME_PERIOD_TO_DATE = false
  AND VOIDED = false
ORDER BY RESTAURANT_LOCATION, TIME_PERIOD_VALUE
```

### Query 2 — Catering Current Year

```sql
SELECT
  RESTAURANT_LOCATION, TIME_PERIOD_VALUE,
  SUM(AMOUNT) AS amount, SUM(ORDER_COUNT) AS orders
FROM CHABI_DBT.ORDER_METRICS
WHERE BRAND = 'fuego-tortilla-grill'
  AND TIME_PERIOD_TYPE = 'day_dow'
  AND TIME_PERIOD_VALUE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
  AND DINING_CATEGORY = 'Catering'
  AND VOIDED = false
GROUP BY 1, 2
```

Note: Aggregate catering by week after pulling (group by location + week_start).

### Query 3 — Catering Prior Year

Same as Query 2 but shift dates back 52 weeks (364 days) for prior year comparison.
Only comp stores will have data.

### Query 4 — Reviews (3 sources)

```sql
-- Google
SELECT RESTAURANT_LOCATION, REVIEW_DATE, AVG(STARS) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.GOOGLE_REVIEWS
WHERE BRAND = 'fuego-tortilla-grill'
  AND REVIEW_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1, 2

-- Ovation
SELECT RESTAURANT_LOCATION, SURVEY_DATE, AVG(SURVEY_RATING) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.OVATION_SURVEY_REPORTS
WHERE BRAND = 'fuego-tortilla-grill'
  AND SURVEY_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1, 2

-- Yelp
SELECT RESTAURANT_LOCATION, REVIEW_DATE, AVG(STARS) AS avg_rating, COUNT(*) AS cnt
FROM CHABI_DBT.YELP_REVIEWS
WHERE BRAND = 'fuego-tortilla-grill'
  AND REVIEW_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1, 2
```

Aggregate by location + week_start + source.

### Query 5 — Daily Labor (LABOR_METRICS)

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

### Query 6 — Daily Sales (ORDER_METRICS, day_dow)

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

### Query 7 — Scheduled Hours (SEVEN_SHIFTS_DATA)

```sql
SELECT
  RESTAURANT_LOCATION, SHIFT_DATE,
  SUM(REGULAR_HOURS) + SUM(COALESCE(OT_HOURS, 0)) AS scheduled_hours
FROM CHABI_DBT.SEVEN_SHIFTS_DATA
WHERE BRAND = 'fuego-tortilla-grill'
  AND SHIFT_DATE BETWEEN '{earliest_monday}' AND '{latest_sunday}'
GROUP BY 1, 2
ORDER BY 1, 2
```

### Query 8 — AGM Hours

**IMPORTANT:** This table is NOT in CHABI_DBT. It lives in its own schema, uses display-name
brands (not slugs), text-format dates (M/D/YYYY), and `STORE_LISTING` as the location column.

```sql
SELECT STORE_LISTING AS RESTAURANT_LOCATION,
       START_DATE, END_DATE, DAILY_HOURS, WEEKLY_HOURS
FROM LABOR_AGM_HOURS.LABOR_AGM_HOURS_TABLE
WHERE BRAND = 'Fuego Tortilla Grill'
ORDER BY STORE_LISTING, START_DATE
```

**Date parsing note:** START_DATE and END_DATE are TEXT columns in `M/D/YYYY` format.
Parse them to proper dates before using in guideline computation. Each row defines a
date range and the AGM weekly hours applicable during that range. Always query the live
table — do NOT hardcode AGM values, as they change week-to-week during new-store ramp-downs.

### Query 9 — Labor Guidelines

**IMPORTANT:** This table is NOT in CHABI_DBT. It lives in its own schema and uses
display-name brands (not slugs).

```sql
SELECT WEEKLY_NET_SALES_THRESHOLD, WEEKLY_TOTAL_HOURS
FROM LABOR_GUIDELINES.LABOR_GUIDELINES_TABLE
WHERE BRAND = 'Fuego Tortilla Grill'
ORDER BY WEEKLY_NET_SALES_THRESHOLD
```

### Query 10 — Upselling Attachment Rates (trailing 14 days)

```sql
-- Query A: Check counts per location
SELECT
  o.RESTAURANT_LOCATION,
  SUM(o.CHECK_COUNT) AS checks,
  ROUND(SUM(o.AMOUNT) / NULLIF(SUM(o.CHECK_COUNT), 0), 2) AS avg_check
FROM CHABI_DBT.ORDERS_REPORTS o
WHERE o.BRAND = 'fuego-tortilla-grill'
  AND o.REPORT_DATE BETWEEN '{14_days_ago}' AND '{latest_sunday}'
  AND o.VOIDED = false
  AND o.DINING_CATEGORY NOT IN ('Catering')
  AND o.SERVER NOT IN ('default online ordering','Default Online Ordering','Online Order','Online  Order ','Online  Host Village')
  AND o.SERVER IS NOT NULL AND LENGTH(TRIM(o.SERVER)) > 0
GROUP BY 1

-- Query B: Item quantities by upsell category per location
SELECT
  isr.RESTAURANT_LOCATION,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Queso' THEN isr.qty ELSE 0 END) AS queso,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Guacamole' THEN isr.qty ELSE 0 END) AS guac,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Chips and Salsa' THEN isr.qty ELSE 0 END) AS chips,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Sides' THEN isr.qty ELSE 0 END) AS sides,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Drinks' THEN isr.qty ELSE 0 END) AS drinks,
  SUM(CASE WHEN m.mapped_menu_subgroup IN ('Margaritas and Beer') THEN isr.qty ELSE 0 END) AS alcohol,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Desserts' THEN isr.qty ELSE 0 END) AS desserts
FROM CHABI_DBT.ITEM_SELECTION_REPORTS isr
INNER JOIN MENU_MAP.MENU_MAP_TABLE m
  ON m.toast_menu_group = isr.menu_group AND m.toast_menu = isr.menu AND m.toast_menu_item = isr.menu_item
WHERE isr.BRAND = 'fuego-tortilla-grill'
  AND isr.REPORT_DATE BETWEEN '{14_days_ago}' AND '{latest_sunday}'
  AND isr.DINING_CATEGORY NOT IN ('Catering')
  AND isr.SERVER NOT IN ('default online ordering','Default Online Ordering','Online Order','Online  Order ','Online  Host Village')
  AND isr.SERVER IS NOT NULL AND LENGTH(TRIM(isr.SERVER)) > 0
GROUP BY 1
```

Compute per-location: `food_addon_rate = (queso+guac+chips+sides+desserts)/checks*100`,
`bev_rate = (drinks+alcohol)/checks*100`, `queso_rate = queso/checks*100`.

## Step 3: Compute KPIs

### Per-Location Current Week KPIs

For each location, from the current week's data:

| KPI | Formula | Notes |
|-----|---------|-------|
| Sales | AMOUNT from ORDER_METRICS | |
| SSS % | (CY - PY) / PY × 100 | Comp stores only; N/A for non-comp |
| Orders | ORDER_COUNT | |
| SST % | (CY orders - PY orders) / PY orders × 100 | Comp stores only |
| Avg Ticket | Sales / Orders | |
| Ticket Change | pct_chg(CY ticket, PY ticket) | Comp stores only |
| Labor Hours | Sum of daily PAYABLE_HOURS for the week | |
| Labor Pay | Sum of daily TOTAL_PAY for the week | |
| Labor % | Labor Pay / Sales × 100 | |
| Guideline Hours | See guideline algorithm in helpers.md | |
| vs Guide # | Actual Hours - Guideline Hours | |
| vs Guide % | Actual Hours / Guideline Hours × 100 | |
| Scheduled Hours | Sum of daily scheduled from 7Shifts | |
| SPLH | Sales / Labor Hours | Sales Per Labor Hour |
| Catering $ | From catering query | |
| Reviews | Weighted avg across Google/Ovation/Yelp | Weight by count |

### System Totals

- **System Sales/Orders**: Sum all locations
- **SSS/SST** (system-level): Sum comp stores only, compute % change vs sum of comp PY
- **System Avg Ticket**: System Sales / System Orders (all locations)
- **System Ticket Change**: Comp CY ticket vs comp PY ticket
- **System Labor**: Sum all locations' hours, pay, guidelines
- **System Catering**: Sum all locations

### 4-Week Trends

Compute the above for each of the 4 trailing weeks. SSS/SST always comp-only.

### Per-Location 4-Week History

Store each location's KPIs for all 4 weeks. This powers the AI callout context.
Structure as `loc_weekly[location][week_index]` with all KPIs.

## Step 4: Build Rack & Stack Rankings

### Sales R&S — Ranked by Sales (highest = #1)

Columns: Rank, Location, Sales, SSS %, Orders, SST %, Avg Ticket, Tkt Chg, Catering, Basis
- Non-comp stores show N/A pills for SSS/SST/Tkt Chg with "Non-Comp" basis
- System total row at bottom

### Labor R&S — Ranked by vs Guide % (lowest = #1)

Columns: Rank, Location, Sales, Guide Hrs, Sch Hrs, Actual Hrs, vs Guide #, vs Guide %, Labor %, SPLH
- Guide/Sch/Actual hrs rounded to whole numbers
- System total row at bottom

### Reviews R&S — Ranked by Weighted Avg Rating (highest = #1)

Columns: Rank, Location, Google, #, Ovation, #, Yelp, #, Wtd Avg, Total #

### Catering R&S — Ranked by Catering $ (highest = #1)

Columns: Rank, Location, Orders, Cat $, Cat $ PY, vs PY

## Step 5: Generate AI Insights (with Verification Loop)

**THIS IS THE MOST CRITICAL STEP.** AI insights must be generated programmatically
from the computed data, then verified. Never hardcode numbers.

### 5a. Build a Verification Data Dictionary

Create a flat dictionary mapping every location to every computed metric. Example:

```python
verify_data = {}
for loc in LOCATIONS:
    d = loc_data[loc]
    verify_data[f"{loc}_sales"] = d["amount"]
    verify_data[f"{loc}_sss"] = d["sss"]
    verify_data[f"{loc}_sst"] = d["sst"]
    verify_data[f"{loc}_labor_pct"] = d["labor_pct"]
    verify_data[f"{loc}_vs_guide_pct"] = d["vs_guide_pct"]
    verify_data[f"{loc}_avg_tkt"] = d["avg_tkt"]
    verify_data[f"{loc}_labor_hrs"] = d["labor_hrs"]
    verify_data[f"{loc}_guide_hrs"] = d["guide_total"]
    verify_data[f"{loc}_splh"] = d["amount"] / d["labor_hrs"] if d["labor_hrs"] else 0
    verify_data[f"{loc}_cat_amt"] = d["cat_amt"]
    verify_data[f"{loc}_food_addon_rate"] = upselling[loc]["food_addon_rate"]
    verify_data[f"{loc}_queso_rate"] = upselling[loc]["queso_rate"]
    verify_data[f"{loc}_bev_rate"] = upselling[loc]["bev_rate"]
    # 4-week history
    for wi, ws_i in enumerate(WEEK_STARTS):
        verify_data[f"{loc}_w{wi}_sales"] = loc_weekly[loc][wi]["amount"]
        verify_data[f"{loc}_w{wi}_labor_pct"] = loc_weekly[loc][wi]["labor_pct"]
        verify_data[f"{loc}_w{wi}_cat_amt"] = loc_weekly[loc][wi].get("cat_amt", 0)
    # Reviews 4-week
    for wi, ws_i in enumerate(WEEK_STARTS):
        for src in ["google", "ovation", "yelp"]:
            verify_data[f"{loc}_w{wi}_{src}_r"] = reviews[loc][ws_i].get(src, {}).get("avg")
```

### 5b. Generate Callouts Programmatically

Each callout is built from the `loc_data`, `loc_weekly`, and `upselling` dictionaries
using f-strings that reference computed values directly. **Never type a number literally.**

Example pattern:
```python
# CORRECT — references computed data
f"San Antonio's food add-on rate is {upselling['San Antonio']['food_addon_rate']:.1f}%"

# WRONG — hardcoded number
f"San Antonio's food add-on rate is 23.9%"
```

### Callout Content Guidelines

**Sales Callout** should cover:
- Which comp store(s) have positive/negative SSS and their 4-week trajectory
- Transaction trends (SST) — separate from ticket trends
- Ticket gap analysis using REAL upselling data (queso attach, food addon rate, bev rate)
- New store momentum with 4-week sales trajectory
- Do NOT mention College Station's high revenue share (it's obvious)

**Labor Callout** should cover:
- Who ran tightest/loosest to guide and WHY (e.g., AGM allowances)
- 4-week labor % trajectory for notable stores
- Schedule-vs-actual gaps and what they might indicate
- Whether running under guide might be hurting sales (connect to SSS/SST)

**Reviews Callout** should cover:
- 4-week trends (improving/declining), not just current week
- Platform divergence (Google vs Ovation) and what it signals
- Survey volume and its impact on data reliability

**Catering Callout** should cover:
- 4-week catering trajectories (show the progression)
- Correct PY comparisons (verify direction: up or down!)
- Penetration rate (catering as % of store sales)
- New store catering development

### 5c. Verification Loop

After generating each callout string, run it through the verifier:

```python
MAX_VERIFICATION_ROUNDS = 3

def verify_callout(callout_name, callout_text, verify_data, loc_data, loc_weekly, upselling):
    """
    Parse numerical claims from callout text and verify against data.
    Returns (is_valid, errors_list).
    """
    errors = []

    # Extract all numerical claims: "X is Y%" or "X at Y%" or "$X" or "Y orders"
    # For each location mentioned, check that attributed metrics match

    for loc in LOCATIONS:
        if loc not in callout_text and f"<strong>{loc}</strong>" not in callout_text:
            continue

        # Check labor % claims
        import re
        # Pattern: "{location}...{number}% labor" or "labor...{number}%"
        # Find all percentages near the location name
        # This is fuzzy — look for any percentage within ~100 chars of location mention

        loc_region_start = callout_text.find(loc)
        if loc_region_start == -1:
            loc_region_start = callout_text.find(f"<strong>{loc}</strong>")
        if loc_region_start == -1:
            continue

        # Get text window around location mention (300 chars forward)
        window = callout_text[loc_region_start:loc_region_start + 400]

        # Check for labor % (e.g., "14.0%" near "labor")
        if "labor" in window.lower() or "%" in window:
            pct_matches = re.findall(r'(\d+\.\d+)%', window)
            for pct_str in pct_matches:
                pct_val = float(pct_str)
                # Check if this matches any known metric for this location
                actual_labor = verify_data.get(f"{loc}_labor_pct")
                actual_guide = verify_data.get(f"{loc}_vs_guide_pct")
                actual_sss = verify_data.get(f"{loc}_sss")
                actual_sst = verify_data.get(f"{loc}_sst")
                actual_food = verify_data.get(f"{loc}_food_addon_rate")
                actual_queso = verify_data.get(f"{loc}_queso_rate")
                actual_bev = verify_data.get(f"{loc}_bev_rate")

                known_values = {
                    "labor_pct": actual_labor,
                    "vs_guide_pct": actual_guide,
                    "sss": actual_sss,
                    "sst": actual_sst,
                    "food_addon_rate": actual_food,
                    "queso_rate": actual_queso,
                    "bev_rate": actual_bev,
                }
                # Also check 4-week history
                for wi in range(4):
                    known_values[f"w{wi}_labor_pct"] = verify_data.get(f"{loc}_w{wi}_labor_pct")

                # Does this percentage match ANY known value (within 0.15 tolerance)?
                matched = False
                for key, actual in known_values.items():
                    if actual is not None and abs(pct_val - abs(actual)) < 0.15:
                        matched = True
                        break
                if not matched and pct_val > 1:  # ignore trivial matches
                    errors.append(
                        f"[{callout_name}] {loc}: claimed {pct_val}% not found in known metrics. "
                        f"Known: labor={actual_labor:.1f}%, guide={actual_guide:.1f}%, "
                        f"sss={actual_sss}, sst={actual_sst}"
                    )

        # Check dollar amounts
        dollar_matches = re.findall(r'\$([0-9,]+(?:\.\d+)?)', window)
        for d_str in dollar_matches:
            d_val = float(d_str.replace(',', ''))
            if d_val < 10:  # skip tiny amounts like $4.09 ticket gaps
                continue
            # Check against known dollar values
            actual_sales = verify_data.get(f"{loc}_sales", 0)
            actual_cat = verify_data.get(f"{loc}_cat_amt", 0)
            actual_tkt = verify_data.get(f"{loc}_avg_tkt", 0)
            known_dollars = [actual_sales, actual_cat, actual_tkt]
            # Also 4-week sales/cat
            for wi in range(4):
                known_dollars.append(verify_data.get(f"{loc}_w{wi}_sales", 0))
                known_dollars.append(verify_data.get(f"{loc}_w{wi}_cat_amt", 0))
            # Check within 5% tolerance for large numbers, exact for small
            matched = any(
                abs(d_val - v) / max(v, 1) < 0.05 if v > 100 else abs(d_val - v) < 5
                for v in known_dollars if v
            )
            if not matched and d_val > 100:
                errors.append(
                    f"[{callout_name}] {loc}: claimed ${d_val:,.0f} not found in known values. "
                    f"Known: sales={actual_sales:,.0f}, cat={actual_cat:,.0f}"
                )

    return (len(errors) == 0, errors)

# Run verification loop
for round_num in range(MAX_VERIFICATION_ROUNDS):
    all_valid = True
    all_errors = []

    for name, text in [("sales", sales_callout), ("labor", labor_callout),
                        ("reviews", reviews_callout), ("catering", catering_callout)]:
        valid, errors = verify_callout(name, text, verify_data, loc_data, loc_weekly, upselling)
        if not valid:
            all_valid = False
            all_errors.extend(errors)

    if all_valid:
        print(f"✓ All AI insights verified on round {round_num + 1}")
        break
    else:
        print(f"✗ Round {round_num + 1}: {len(all_errors)} errors found:")
        for e in all_errors:
            print(f"  {e}")
        # REGENERATE the offending callouts using correct data
        # ... rebuild callouts from verify_data ...
        print(f"  → Regenerating callouts from verified data...")

if not all_valid:
    print("⚠ Could not fully verify after max rounds. Using best available.")
```

### 5d. Regeneration Strategy

When verification fails:
1. Identify which callout(s) have errors
2. For each error, look up the CORRECT value from `verify_data`
3. Rebuild the callout string using ONLY `verify_data` lookups
4. Re-run verification
5. After MAX_VERIFICATION_ROUNDS, use whatever is cleanest

**Critical rule**: The regenerated callout must use f-string references to the data
dictionaries, never literal numbers. Example:

```python
labor_callout = (
    f"<strong>{best_guide_loc}</strong> ran tightest to guide at "
    f"{verify_data[f'{best_guide_loc}_vs_guide_pct']:.1f}%..."
)
```

## Step 6: Build HTML Report

Read `references/html_template.md` for the full CSS and HTML structure.

The report has these sections in order:
1. **Header** — "System Weekly Flash Report", "Fuego Tortilla Grill", "All 6 Locations", date range
2. **KPI Cards** (5) — System Sales, System Orders, Avg Ticket, System Labor %, Catering
3. **System Summary** — GM-style narrative paragraph
4. **System Performance Trends** — 4-week table with:
   Week, Sales, SSS%, Orders, SST%, Avg Tkt, Guide Hrs (whole), Actual Hrs (whole),
   vs Guide #, vs Guide %, Labor %, SPLH, Catering, Cat PY
5. **Sales Rack & Stack** — table + AI Insight callout below
6. **Labor Rack & Stack** — table + AI Insight callout below
7. **Reviews Rack & Stack** — table + AI Insight callout below
8. **Catering Rack & Stack** — table + AI Insight callout below
9. **Footer**

### Design Notes
- Use the S3 "Teal Thread" design (see html_template.md for CSS)
- Page 1 should have comfortable spacing — larger KPI cards, generous GM message padding
- Rank pills: 1st=solid green, 2nd=light green, 3rd=gold, last=red, middle=gray
- Metric pills: green=good, red=bad, yellow=neutral (thresholds vary by metric)
- Guide/Sch/Actual hrs in both Trends and Labor R&S rounded to **whole numbers**
- Report can span multiple pages — use CSS `break-inside: avoid` on sections

## Step 7: Generate PDF

```python
# Write HTML
with open(html_path, "w") as f:
    f.write(html)

# Convert to PDF via headless Chrome
subprocess.run([
    "google-chrome", "--headless", "--no-sandbox", "--disable-gpu",
    f"--print-to-pdf={pdf_path}",
    "--print-to-pdf-no-header", "--no-pdf-header-footer",
    f"file://{html_path}"
], capture_output=True, text=True, timeout=30)

# Copy to outputs
shutil.copy(pdf_path, output_path)
```

Output filename: `Weekly Flash - Fuego System - {month} {day} – {end_day}, {year}.pdf`

## Guideline Computation Algorithm

See `references/helpers.md` for the complete algorithm. Key points:
- Uses LABOR_GUIDELINES_TABLE for interpolated lookup
- Partial week detection: days_with_sales < 6 (Fuego closed Mondays)
- Partial week: per-day projection, lookup independently, split evenly
- Full week: proportional allocation with linear weighting, knee at $9K
- DOW adjustments: Mon=0, Tue=+8, Wed/Thu/Fri/Sat=+3, Sun=-20
- AGM hours: added per operating day only (daily = weekly / 6)
- Zero-sales guard: if lookup=0, day gets 0 total
