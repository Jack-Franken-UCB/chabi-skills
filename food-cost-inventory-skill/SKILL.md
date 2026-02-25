---
name: food-cost-inventory
description: >
  Generate a branded Food Cost & Inventory Report for any Fuego Tortilla Grill location.
  Pulls the latest weekly MarginEdge data from Snowflake, computes actual vs theoretical
  food cost by category and item, identifies top variance offenders with inventory equation
  breakdowns, benchmarks against all locations, and produces a polished HTML report with
  prioritized action items including specific MarginEdge fix steps.
  Use this skill whenever the user asks about food cost, inventory variance, MarginEdge
  analysis, actual vs theoretical, COGS, food cost percentage, inventory recount,
  waste analysis, or wants to know which items are causing food cost problems.
  Also trigger when a user says something casual like "how's food cost at Waco",
  "what's driving variance this week", "pull the MarginEdge report for San Marcos",
  "which items should we recount", or "food cost breakdown by category".
  Trigger for any request involving food cost analysis, inventory variance, or
  MarginEdge data for any Fuego location.
---

# Food Cost & Inventory Report

This skill generates a comprehensive HTML report analyzing food cost and inventory
variance for a Fuego Tortilla Grill location using MarginEdge data. The report
covers actual vs theoretical food cost, category breakdowns, item-level variance
analysis, inventory equation diagnostics, system-wide location benchmarks,
Pareto analysis, and prioritized action items with MarginEdge-specific fix steps.

## Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Location | *(ask user)* | MarginEdge names: "Fuego Tortilla Grill - Waco Baylor", "Fuego Tortilla Grill - San Marcos", "Fuego Tortilla Grill - San Antonio", "Fuego Tortilla Grill - College Station", "Fuego Tortilla Grill - Burleson", "Fuego Tortilla Grill - Fayetteville" |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |
| Report week | Most recent completed week | Use PERIOD_START_DATE from MarginEdge data |

## Data Source

MarginEdge data is in: `MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE`

**Critical: Deduplication Required** — Multiple file versions may exist per location/period.
Always filter to the latest file using `MAX_BY(_FILE, _MODIFIED)` per RESTAURANT_NAME + PERIOD_START_DATE.

## Step 1: Pull Data from Snowflake

Run all queries via `Chabi Connectors:run_query`. Run independent queries in parallel.

### Query 1 — Find Latest Period and File

```sql
SELECT DISTINCT RESTAURANT_NAME, PERIOD_START_DATE, PERIOD_END_DATE,
  MAX_BY(_FILE, _MODIFIED) AS latest_file
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
GROUP BY 1, 2, 3
ORDER BY PERIOD_START_DATE DESC, RESTAURANT_NAME
LIMIT 12
```

Use the most recent PERIOD_START_DATE for the target location.

### Query 2 — Item-Level Detail for Target Location

```sql
WITH latest AS (
  SELECT MAX_BY(_FILE, _MODIFIED) AS _file
  FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
  WHERE RESTAURANT_NAME = '{restaurant_name}'
    AND PERIOD_START_DATE = '{period_start}'
)
SELECT
  CATEGORY_TYPE, CATEGORY_NAME, PRODUCT_NAME,
  ROUND(ACTUAL_COST_PERCENT * 100, 1) as actual_pct,
  ROUND(TARGET_COST_PERCENT * 100, 1) as target_pct,
  ROUND(USED_VALUE, 2) as used_value,
  ROUND(SOLD_REVENUE, 2) as sold_revenue,
  ROUND(VARIANCE_VALUE, 2) as variance_val,
  ROUND(VARIANCE_UNITS, 1) as variance_units,
  PRODUCT_UNIT_UNIT as unit,
  ROUND(STARTING_COUNT, 1) as start_count,
  ROUND(ENDING_COUNT, 1) as end_count,
  ROUND(PURCHASED_UNITS, 1) as purchased,
  ROUND(USED_UNITS, 1) as used_units,
  ROUND(SOLD_UNITS, 1) as sold_units,
  ROUND(UNIT_PRICE, 2) as unit_price,
  WASTED_UNITS, WASTED_VALUE
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE t
JOIN latest l ON t._FILE = l._file
WHERE RESTAURANT_NAME = '{restaurant_name}'
  AND PERIOD_START_DATE = '{period_start}'
  AND USED_VALUE > 0
ORDER BY ABS(VARIANCE_VALUE) DESC
LIMIT 25
```

### Query 3 — Category-Level Summary for Target Location

```sql
WITH latest AS (
  SELECT MAX_BY(_FILE, _MODIFIED) AS _file
  FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
  WHERE RESTAURANT_NAME = '{restaurant_name}'
    AND PERIOD_START_DATE = '{period_start}'
)
SELECT
  CATEGORY_TYPE, CATEGORY_NAME,
  SUM(USED_VALUE) as total_used,
  SUM(SOLD_REVENUE) as total_revenue,
  SUM(VARIANCE_VALUE) as total_variance,
  AVG(ACTUAL_COST_PERCENT) as avg_actual_pct,
  AVG(TARGET_COST_PERCENT) as avg_target_pct
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE t
JOIN latest l ON t._FILE = l._file
WHERE RESTAURANT_NAME = '{restaurant_name}'
  AND PERIOD_START_DATE = '{period_start}'
GROUP BY 1, 2
ORDER BY total_used DESC
```

### Query 4 — Overall Summary for Target Location

```sql
WITH latest AS (
  SELECT MAX_BY(_FILE, _MODIFIED) AS _file
  FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
  WHERE RESTAURANT_NAME = '{restaurant_name}'
    AND PERIOD_START_DATE = '{period_start}'
)
SELECT
  SUM(STARTING_VALUE) as starting_inv,
  SUM(PURCHASED_VALUE) as purchased,
  SUM(USED_VALUE) as used,
  SUM(ENDING_VALUE) as ending_inv,
  SUM(SOLD_REVENUE) as revenue,
  SUM(VARIANCE_VALUE) as variance,
  SUM(WASTED_VALUE) as waste
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE t
JOIN latest l ON t._FILE = l._file
WHERE RESTAURANT_NAME = '{restaurant_name}'
  AND PERIOD_START_DATE = '{period_start}'
```

### Query 5 — 4-Week Trend for Target Location

```sql
WITH latest_files AS (
  SELECT PERIOD_START_DATE, MAX_BY(_FILE, _MODIFIED) AS _file
  FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
  WHERE RESTAURANT_NAME = '{restaurant_name}'
    AND PERIOD_START_DATE >= DATEADD('week', -3, '{period_start}'::DATE)
  GROUP BY 1
)
SELECT
  t.PERIOD_START_DATE, t.PERIOD_END_DATE,
  SUM(t.USED_VALUE) as total_used,
  SUM(t.SOLD_REVENUE) as total_revenue,
  CASE WHEN SUM(t.SOLD_REVENUE) > 0 THEN ROUND(SUM(t.USED_VALUE)/SUM(t.SOLD_REVENUE)*100,1) ELSE 0 END as food_cost_pct,
  SUM(t.VARIANCE_VALUE) as total_variance
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE t
JOIN latest_files l ON t.PERIOD_START_DATE = l.PERIOD_START_DATE AND t._FILE = l._file
WHERE RESTAURANT_NAME = '{restaurant_name}'
GROUP BY 1, 2
ORDER BY 1 DESC
```

### Query 6 — All Locations Comparison (Same Week)

```sql
WITH latest_files AS (
  SELECT RESTAURANT_NAME, MAX_BY(_FILE, _MODIFIED) AS _file
  FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE
  WHERE PERIOD_START_DATE = '{period_start}'
  GROUP BY 1
)
SELECT
  t.RESTAURANT_NAME,
  SUM(t.USED_VALUE) as total_used,
  SUM(t.SOLD_REVENUE) as total_revenue,
  CASE WHEN SUM(t.SOLD_REVENUE) > 0 THEN ROUND(SUM(t.USED_VALUE)/SUM(t.SOLD_REVENUE)*100,1) ELSE 0 END as food_cost_pct,
  SUM(t.VARIANCE_VALUE) as total_variance
FROM MARGIN_EDGE_FUEGO_TORTILLA_GRILL.MARGIN_EDGE_FUEGO_TORTILLA_GRILL_TABLE t
JOIN latest_files l ON t.RESTAURANT_NAME = l.RESTAURANT_NAME AND t._FILE = l._file
WHERE t.PERIOD_START_DATE = '{period_start}'
GROUP BY 1
ORDER BY food_cost_pct ASC
```

## Step 2: Analyze Data & Generate Insights

### Variance Root Cause Classification

For each top variance item, classify the likely root cause:

1. **Inventory Miscount** — Used units >> Sold units AND ending count seems low relative
   to (starting + purchased). Suggest: "Recount in walk-in, weigh on scale."

2. **Recipe Mapping Error** — Item shows $0 revenue but high used value, OR a companion
   item shows $0 used but high revenue. Suggest: "Fix recipe mapping in MarginEdge."

3. **Waste/Spoilage** — Item has high perishability (produce, dairy) AND actual cost % >>
   target % AND wasted_value = 0. Suggest: "Start logging waste in MarginEdge."

4. **Portioning** — Moderate gap between used and sold units for high-volume items.
   Suggest: "Audit portion sizes, post portion photos at station."

5. **Recipe Not Linked** — Item shows 100% usage with $0 revenue (used in prep items
   not connected to POS). Suggest: "Add as ingredient to MarginEdge recipes."

### Fix Impact Simulation

Calculate simulated food cost % after each fix:
```
adjusted_used = total_used - (recoverable_variance_from_fix)
adjusted_food_cost_pct = adjusted_used / total_revenue * 100
```

Show as stacked horizontal bars: Current → after each fix → Target.

## Step 3: Generate GM Message

Write using the **Headline → Story → Ask** framework:

- **Headline**: One sentence, biggest number, red flag
- **Story**: 3-4 sentences — what drove it, is it sales or usage, location ranking, what's working
- **Ask**: One specific action with a deadline, bolded

## Step 4: Build the HTML Report

The report has these sections in order:

1. **Header** — Brand, location badge, period
2. **GM Message** — Headline/Story/Ask with teal-topped card
3. **Annualized Impact** — Red gradient banner: weekly variance × 52
4. **Fix Impact Simulator** — Horizontal bars showing FC% after each fix
5. **KPI Cards** — Actual %, COGS, Variance, Ending Inventory (4-card grid)
6. **Inventory Flow** — Start + Purchased − Used = Ending (node visualization)
7. **Category Scorecard** — 🔴🟡🟢 quick-scan grid (8 categories)
8. **Location Comparison** — 6-card grid, highlight target location
9. **Variance Pareto** — Stacked bar with legend
10. **Inventory Equation Cards** — Top 3 offenders, full equation + diagnostic question
11. **4-Week Trend** — FC% and variance, 4-card grid
12. **Category Table** — Used, Revenue, Actual%, Target%, Gap, Variance
13. **Item Variance Table** — Top 12 with unit detail (used/sold/var units)
14. **What's Working Well** — Top 4 positive items, 2-column grid
15. **Action Plan** — P1–P5 checklist with MarginEdge click-paths and impact badges

### Design System

Fuego brand palette with teal accents (S3 "Teal Thread"):
- `--brown: #4a3728` (header), `--teal: #4a8e8b` (accents), `--tan: #f5efe9` (backgrounds)
- `--red: #c0392b` (negative), `--green: #1e8449` (positive), `--orange: #d4780a` (warning)
- Font: DM Sans (Google Fonts) + JetBrains Mono for tabular numbers
- Pill badges: colored background + text for status indicators
- Cards with `border-top: 3px solid var(--teal)` for KPI cards
- Section headers with `border-left: 3px solid var(--teal)`
- Alternating table row stripes for readability
- Action items with left border color-coded by priority + empty checkbox squares

Read `references/html_template.md` for the complete CSS and HTML reference if available.

## Step 5: Output

Save as: `food_cost_{location_slug}.html`

Write to outputs directory and present to user.
