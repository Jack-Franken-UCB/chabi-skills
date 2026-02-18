---
name: upselling-by-server
description: >
  Generate standalone Upselling by Server reports for Fuego Tortilla Grill locations.
  Pulls trailing 14-day item-level and order-level data from Snowflake via Chabi Analytics,
  computes attachment rates per server within each dining category × daypart combination,
  scores servers relative to their segment peers, and produces branded HTML reports with
  actionable coaching insights. Reports cover all 8 segments: Dine In and Drive Thru
  crossed with Breakfast, Lunch, Dinner, and Late Night. Use this skill whenever the user
  asks about upselling, attachment rates, server performance on add-ons, suggestive selling
  metrics, or wants to know which servers need training. Also trigger when a user mentions
  "sales attachment", "add-on rate", "beverage attachment", "server scorecard", or "who's
  upselling well". Trigger even if user just says something casual like "how are my servers
  doing on upsells" or "who needs training on suggestive selling".
---

# Upselling by Server Report

This skill evaluates every server at Fuego Tortilla Grill locations on their ability to
attach add-on items (queso, guac, sides, desserts) and beverages (drinks, alcohol) to each
check. The critical design principle: servers are scored **relative to their own segment**
(dining category × daypart) — a breakfast drive-thru server isn't compared against a
dinner dine-in server, because the upselling opportunities are fundamentally different.

Reports are generated for **all 6 operational locations** by default, each as a separate
HTML file.

## Parameters

Before generating, confirm with the user or use defaults:

| Parameter | Default | Notes |
|-----------|---------|-------|
| Locations | All 6 | San Marcos, Waco, San Antonio, College Station, Burleson, Fayetteville |
| Trailing days | 14 | Days to look back from yesterday |
| Min checks | 20 | Exclude servers with fewer checks in a segment (insufficient data) |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |

## Segmentation: Dining Category × Daypart

Reports are organized into **8 segments**, sorted by daypart first:

1. Breakfast — Dine In
2. Breakfast — Drive Thru
3. Lunch — Dine In
4. Lunch — Drive Thru
5. Dinner — Dine In
6. Dinner — Drive Thru
7. Late Night — Dine In
8. Late Night — Drive Thru

Skip any segment that has no data or no servers meeting the min-checks threshold.

**Dining category mapping**: Use the `DINING_CATEGORY` field from ORDERS_REPORTS:
- "Dine In" → Dine In
- "Drive Thru" → Drive Thru
- "Takeout" → Include with Dine In (server interaction is similar)
- Exclude: "Catering", "3rd Party", "Delivery" (these are not server-influenced channels)

**Daypart mapping**: Use the `SERVICE` field from ORDERS_REPORTS:
- Breakfast, Lunch, Dinner, Late Night (as reported by Toast)

## Step 1: Pull Data from Snowflake

Run two queries via `Chabi Connectors:run_query`. The date range should be the trailing
14 days ending yesterday (today's data may be incomplete). Generate one set of queries
per location, or combine all locations into a single query if result size permits.

### Query A — Check Counts & Revenue per Server/Dining Category/Daypart

```sql
SELECT
  o.RESTAURANT_LOCATION,
  o.SERVER,
  o.SERVICE,
  o.DINING_CATEGORY,
  SUM(o.CHECK_COUNT) AS checks,
  SUM(o.AMOUNT) AS revenue,
  ROUND(SUM(o.AMOUNT) / NULLIF(SUM(o.CHECK_COUNT), 0), 2) AS avg_check
FROM CHABI_DBT.ORDERS_REPORTS o
WHERE o.BRAND = 'fuego-tortilla-grill'
  AND o.REPORT_DATE BETWEEN '{start_date}' AND '{end_date}'
  AND o.VOIDED = false
  AND o.DINING_CATEGORY IN ('Dine In', 'Drive Thru', 'Takeout')
  AND o.SERVER NOT IN (
    'default online ordering','Default Online Ordering',
    'Online Order','Online  Order ','Online  Host Village'
  )
  AND o.SERVER IS NOT NULL AND LENGTH(TRIM(o.SERVER)) > 0
GROUP BY 1, 2, 3, 4
HAVING SUM(o.CHECK_COUNT) >= {min_checks}
```

**Important**: Map `Takeout` to `Dine In` after the query for segmentation purposes.
This is done post-query because the server interaction model for takeout orders is
similar to dine-in (face-to-face upsell opportunity at the counter).

### Query B — Item Quantities by Upsell Category

```sql
SELECT
  isr.RESTAURANT_LOCATION,
  isr.SERVER,
  isr.SERVICE,
  isr.DINING_CATEGORY,
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
WHERE isr.BRAND = 'fuego-tortilla-grill'
  AND isr.REPORT_DATE BETWEEN '{start_date}' AND '{end_date}'
  AND isr.DINING_CATEGORY IN ('Dine In', 'Drive Thru', 'Takeout')
  AND isr.SERVER NOT IN (
    'default online ordering','Default Online Ordering',
    'Online Order','Online  Order ','Online  Host Village'
  )
  AND isr.SERVER IS NOT NULL AND LENGTH(TRIM(isr.SERVER)) > 0
GROUP BY 1, 2, 3, 4
```

**Note on query size**: If the combined query across all locations exceeds the result
display limit, run queries per-location (loop over the 6 locations). This is common
and expected.

Join A and B on `RESTAURANT_LOCATION + SERVER + SERVICE + DINING_CATEGORY`. If a server
appears in A but not B, their item counts are all zero (they had checks but sold nothing
in the mapped categories). After joining, remap `Takeout` rows to `Dine In` and
re-aggregate.

## Step 2: Compute Attachment Rates

For each server in each segment (dining_category × daypart):

```
category_rate = (category_qty / checks) * 100
food_addon_rate = (queso + guac + chips + sides + desserts) / checks * 100
bev_rate = (drinks + alcohol) / checks * 100
total_rate = food_addon_rate + bev_rate
```

Rates can exceed 100% — that means the server is averaging more than one of that item per
check, which is great.

**TOTAL rate** = food_addon_rate + bev_rate. This is the key combined metric displayed
as the color-coded TOTAL column in the report.

## Step 3: Segment-Relative Scoring

### Segment Benchmarks (weighted by check count)

For each segment (dining_category × daypart), compute weighted averages:

```
segment_avg_X = sum(server_X * server_checks) / sum(server_checks)
```

Compute for: food_addon, bev, total, queso, guac, sides, drinks, alcohol, dessert, avg_check.

### Percentile Ranking

Within each segment, rank servers on food_addon, bev, and avg_check:

```
percentile = (count of servers with LOWER value) / (total_servers - 1) * 100
```

If only 1 server in a segment, percentile defaults to 50.

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

1. **Top performers** (composite 75+ with 30+ checks) — Name them, their segment
   (e.g., "Lunch Drive Thru"), and what they excel at. These are the coaching role models.

2. **Training focus** (composite 25 or below with 30+ checks) — Name them, their segment,
   and specifically which categories they're weak on vs segment avg. Recommend pairing
   with a top performer during overlapping shifts.

3. **Systemic gaps** — If 50%+ of servers in a segment are below average on a category,
   it's likely a systemic issue (menu positioning, counter layout, lack of verbal prompts)
   rather than individual coaching. Call this out differently from individual training needs.

4. **Cross-channel comparisons** — Compare Dine In vs Drive Thru performance within the
   same daypart. Highlight significant differences (e.g., "Drive Thru breakfast servers
   average 35% food add-on rate vs 52% for Dine In — the window interaction limits
   suggestive selling opportunity"). This helps managers set realistic channel-specific targets.

5. **Standout categories** — Any server with a single category 15+ pts above segment avg
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

2. **Summary KPIs** — 4 cards: Total servers evaluated, Avg composite score, Best segment
   (highest avg total_rate), Biggest opportunity segment (lowest avg total_rate).

3. **Per-segment tables** — One section per segment, ordered:
   Breakfast Dine In → Breakfast Drive Thru → Lunch Dine In → Lunch Drive Thru →
   Dinner Dine In → Dinner Drive Thru → Late Night Dine In → Late Night Drive Thru.

   Skip segments with no data. Each has:
   - Segment header with daypart name + dining category, server count, check count, avg check
   - Benchmark row showing weighted averages
   - Table sorted by composite desc with columns:

     Server | Score | Grade | Checks | Avg Chk | Queso | Guac | Sides | Dessert | Food Total | Drinks | Alcohol | Bev Total | **TOTAL**

   - **Individual category pills**: green if 5+ pts above segment avg, red if 5+ below,
     neutral/yellow otherwise.
   - **TOTAL column** — Combined food + bev attachment rate. This column gets a
     **background color gradient** based on the value relative to the segment:
     - Dark green (#1B5E20) with white text: 15+ pts above segment avg
     - Medium green (#4CAF50) with white text: 5–14 pts above
     - Light green (#C8E6C9) with dark text: 0–4 pts above
     - Light red (#FFCDD2) with dark text: 0–4 pts below
     - Medium red (#E53935) with white text: 5–14 pts below
     - Dark red (#B71C1C) with white text: 15+ pts below

4. **AI Recap** — The actionable insights from Step 4, including cross-channel comparisons.

5. **Footer** — Generated date, Fuego Tortilla Grill – {Location}, Chabi Analytics attribution.

### Output

Generate one HTML report per location. Save to:
`upselling_{location_slug}_{start_date}_to_{end_date}.html`

where `location_slug` = location name lowercased, spaces → underscores.

Write the report as a Python script that generates the HTML, then execute it. This ensures
clean string interpolation and avoids template escaping issues.

When generating for all locations, loop and produce all 6 files, then present them to
the user together.
