---
name: upselling-by-server
description: >
  Generate a standalone Upselling by Server report for any Fuego Tortilla Grill location.
  Pulls trailing 14-day item-level and order-level data from Snowflake via Chabi Analytics,
  computes attachment rates per server within each daypart, scores servers relative to their
  daypart peers, and produces a branded HTML report with actionable coaching insights.
  Use this skill whenever the user asks about upselling, attachment rates, server performance
  on add-ons, suggestive selling metrics, or wants to know which servers need training.
  Also trigger when a user mentions "sales attachment", "add-on rate", "beverage attachment",
  "server scorecard", or "who's upselling well". Trigger even if user just says something
  casual like "how are my servers doing on upsells" or "who needs training on suggestive selling".
---

# Upselling by Server Report

This skill evaluates every server at a Fuego Tortilla Grill location on their ability to
attach add-on items (queso, guac, sides, desserts) and beverages (drinks, alcohol) to each
check. The critical design principle: servers are scored **relative to their own daypart** —
a breakfast server isn't penalized for lower alcohol numbers than a dinner server, because
breakfast simply doesn't have the same alcohol opportunity.

## Parameters

Before generating, confirm with the user or use defaults:

| Parameter | Default | Notes |
|-----------|---------|-------|
| Location | *(ask)* | Valid RESTAURANT_LOCATION (e.g., "San Marcos", "College Station") |
| Trailing days | 14 | Days to look back from yesterday |
| Min checks | 10 | Exclude servers with fewer checks (insufficient data) |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |

Available locations: San Marcos, Waco, San Antonio, College Station, Burleson, Fayetteville.

## Step 1: Pull Data from Snowflake

Run two queries via `Chabi_Analytics__run_query`. The date range should end yesterday
(today's data may be incomplete). Run both queries in parallel if possible.

### Query A — Check Counts & Revenue per Server/Daypart

```sql
SELECT
  o.SERVER,
  o.SERVICE,
  SUM(o.CHECK_COUNT) AS checks,
  SUM(o.AMOUNT) AS revenue,
  ROUND(SUM(o.AMOUNT) / NULLIF(SUM(o.CHECK_COUNT), 0), 2) AS avg_check
FROM CHABI_DBT.ORDERS_REPORTS o
WHERE o.RESTAURANT_LOCATION = '{location}'
  AND o.BRAND = 'fuego-tortilla-grill'
  AND o.REPORT_DATE BETWEEN '{start_date}' AND '{end_date}'
  AND o.VOIDED = false
  AND o.DINING_CATEGORY NOT IN ('Catering')
  AND o.SERVER NOT IN (
    'default online ordering','Default Online Ordering',
    'Online Order','Online  Order ','Online  Host Village'
  )
  AND o.SERVER IS NOT NULL AND LENGTH(TRIM(o.SERVER)) > 0
GROUP BY 1, 2
HAVING SUM(o.CHECK_COUNT) >= {min_checks}
```

### Query B — Item Quantities by Upsell Category

```sql
SELECT
  isr.SERVER,
  isr.SERVICE,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Queso' THEN isr.qty ELSE 0 END) AS queso,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Guacamole' THEN isr.qty ELSE 0 END) AS guac,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Chips and Salsa' THEN isr.qty ELSE 0 END) AS chips,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Sides' THEN isr.qty ELSE 0 END) AS sides,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Drinks' THEN isr.qty ELSE 0 END) AS drinks,
  SUM(CASE WHEN m.mapped_menu_subgroup IN ('Margaritas and Beer') THEN isr.qty ELSE 0 END) AS alcohol,
  SUM(CASE WHEN m.mapped_menu_subgroup = 'Desserts' THEN isr.qty ELSE 0 END) AS desserts
FROM CHABI_DBT.ITEM_SELECTION_REPORTS isr
INNER JOIN MENU_MAP.MENU_MAP_TABLE m
  ON m.toast_menu_group = isr.menu_group
  AND m.toast_menu = isr.menu
  AND m.toast_menu_item = isr.menu_item
WHERE isr.RESTAURANT_LOCATION = '{location}'
  AND isr.BRAND = 'fuego-tortilla-grill'
  AND isr.REPORT_DATE BETWEEN '{start_date}' AND '{end_date}'
  AND isr.DINING_CATEGORY NOT IN ('Catering')
  AND isr.SERVER NOT IN (
    'default online ordering','Default Online Ordering',
    'Online Order','Online  Order ','Online  Host Village'
  )
  AND isr.SERVER IS NOT NULL AND LENGTH(TRIM(isr.SERVER)) > 0
GROUP BY 1, 2
```

Join A and B on `SERVER + SERVICE`. If a server appears in A but not B, their item counts
are all zero (they had checks but sold nothing in the mapped categories).

## Step 2: Compute Attachment Rates

For each server in each daypart:

```
category_rate = (category_qty / checks) * 100
food_addon_rate = (queso + guac + chips + sides + desserts) / checks * 100
bev_rate = (drinks + alcohol) / checks * 100
```

Rates can exceed 100% — that means the server is averaging more than one of that item per
check, which is great.

## Step 3: Daypart-Relative Scoring

### Daypart Benchmarks (weighted by check count)

For each daypart, compute weighted averages:

```
daypart_avg_X = sum(server_X * server_checks) / sum(server_checks)
```

Compute for: food_addon, bev, queso, guac, sides, drinks, alcohol, dessert, avg_check.

### Percentile Ranking

Within each daypart, rank servers on food_addon, bev, and avg_check:

```
percentile = (count of servers with LOWER value) / (total_servers - 1) * 100
```

If only 1 server in a daypart, percentile defaults to 50.

### Composite Score

```
composite = 0.50 * food_addon_percentile + 0.30 * bev_percentile + 0.20 * avg_check_percentile
```

Weights reflect controllability: food add-ons are the most coachable behavior, beverages
are the next biggest lever, and avg check captures overall selling effectiveness.

### Grade Labels

| Score | Label | Styling |
|-------|-------|---------|
| 80–100 | ★ Star | Solid green badge, white text |
| 60–79 | Strong | Light green bg |
| 40–59 | Average | Gold/yellow bg |
| 20–39 | Below Avg | Orange bg |
| 0–19 | Needs Work | Red bg |

## Step 4: Build Actionable AI Recap

The recap is the most important part. Name names. Be specific. Group by:

1. **Top performers** (composite 75+ with 30+ checks) — Name them, their daypart, and
   what they excel at. These are the coaching role models.

2. **Training focus** (composite 25 or below with 30+ checks) — Name them, their daypart,
   and specifically which categories they're weak on vs daypart avg. Recommend pairing
   with a top performer during overlapping shifts.

3. **Daypart-specific gaps** — If 50%+ of servers in a daypart are below average on a
   category, it's likely a systemic issue (menu positioning, counter layout, lack of
   prompts) rather than individual coaching. Call this out differently.

4. **Standout categories** — Any server with a single category 15+ pts above daypart avg
   deserves a callout — they might have a technique worth sharing.

Format the recap as a bulleted list with bold server names and specific numbers.

## Step 5: Generate HTML Report

### Branding

```css
:root {
  --fuego-red: #DE3C00;
  --fuego-black: #352F2E;
  --fuego-charcoal: #232021;
  --fuego-gold: #A57E39;
  --fuego-tan: #DBCBBF;
  --fuego-teal: #86CAC7;
}
font-family: 'Source Sans 3' (import from Google Fonts)
```

### Report Layout

1. **Header** — Dark charcoal background, location name, "Upselling by Server" title,
   date range. Use the glowing teal bar style (3px teal bars top/bottom with box-shadow glow).

2. **Summary KPIs** — 4 cards: Total servers evaluated, Avg composite score, Best daypart
   (highest avg food_addon), Biggest opportunity daypart (lowest avg food_addon).

3. **Per-daypart tables** — One section per daypart (Breakfast, Lunch, Dinner, Late Night).
   Skip dayparts with no data. Each has:
   - Daypart header with name, server count, check count, avg check
   - Benchmark row showing weighted averages
   - Table sorted by composite desc with columns:
     Server | Score | Grade | Checks | Avg Chk | Queso | Guac | Sides | Dessert | Food Add-On | Drinks | Alcohol | Bev Total
   - Pill colors: green if 5+ pts above daypart avg, red if 5+ below, yellow otherwise.

4. **AI Recap** — The actionable insights from Step 4.

5. **Footer** — Generated date, Fuego Tortilla Grill – {Location}, Chabi Analytics attribution.

### Output Path

Save to: `upselling_by_server_{location_slug}_{start_date}_to_{end_date}.html`

where `location_slug` = location name lowercased, spaces → underscores.

Write the report as a Python script that generates the HTML, then execute it. This ensures
clean string interpolation and avoids template escaping issues.
