---
name: upselling-by-server
description: >
  Generate standalone Upselling by Server reports for Fuego Tortilla Grill locations.
  Pulls trailing 14-day item-level and order-level data from Snowflake via Chabi Analytics,
  computes attachment rates per server within each Channel × Daypart segment, ranks servers
  by Total Upsell % (Food Add-On + Bev), and produces branded HTML reports with STORE AVG
  and COMPANY AVG benchmarks ranked in-place alongside servers. Includes an AI coaching
  recap with up to 4 top performers and 4 training focus servers written in natural language.
  Use this skill whenever the user asks about upselling, attachment rates, server performance
  on add-ons, suggestive selling metrics, or wants to know which servers need training.
  Also trigger when a user mentions "sales attachment", "add-on rate", "beverage attachment",
  "server scorecard", or "who's upselling well". Trigger even if user just says something
  casual like "how are my servers doing on upsells" or "who needs training on suggestive selling".
---

# Upselling by Server Report

This skill evaluates every server at Fuego Tortilla Grill locations on their ability to
attach add-on items (queso, guac, sides, desserts) and beverages (drinks, alcohol) to each
check. The critical design principle: servers are scored **relative to their own segment**
(Channel × Daypart) — a breakfast drive-thru server isn't compared against a dinner dine-in
server, because the upselling opportunities are fundamentally different.

Reports are generated for **all 6 operational locations** by default, each as a separate
HTML file. Every table includes **STORE AVG** and **COMPANY AVG** rows ranked in their
natural position alongside servers, so managers can instantly see where their store and the
company as a whole fall in the distribution.

## Parameters

Before generating, confirm with the user or use defaults:

| Parameter | Default | Notes |
|-----------|---------|-------|
| Locations | All 6 | San Marcos, Waco, San Antonio, College Station, Burleson, Fayetteville |
| Trailing days | 14 | Days to look back from yesterday |
| Min checks | 21 | Exclude server-segments with 20 or fewer checks (use `HAVING SUM(CHECK_COUNT) > 20`) |
| Brand | fuego-tortilla-grill | Only Fuego supported currently |

## Segmentation: Channel × Daypart

Reports are organized into **up to 8 segments**, ordered daypart-first:

1. Dine In — Breakfast
2. Drive Thru — Breakfast
3. Dine In — Lunch
4. Drive Thru — Lunch
5. Dine In — Dinner
6. Drive Thru — Dinner
7. Dine In — Late Night
8. Drive Thru — Late Night

Skip any segment that has no qualifying data.

**Channel filter**: Use `DINING_CATEGORY IN ('Dine In', 'Drive Thru')` only.
Exclude Takeout, Catering, 3rd Party, and Delivery — these are not server-influenced channels.

**Daypart**: Use the `SERVICE` field. Filter `WHERE SERVICE IS NOT NULL` to avoid orphan rows.

## Step 1: Pull Data from Snowflake

### Recommended: Single Combined Query

Pull all locations at once with a LEFT JOIN to get order data and item data together.
This ensures company-wide averages can be computed from the same dataset.

```sql
SELECT
  o.RESTAURANT_LOCATION, TRIM(o.SERVER) AS SERVER, o.DINING_CATEGORY, o.SERVICE,
  SUM(o.CHECK_COUNT) AS checks,
  ROUND(SUM(o.AMOUNT), 2) AS revenue,
  ROUND(SUM(o.AMOUNT) / NULLIF(SUM(o.CHECK_COUNT), 0), 2) AS avg_check,
  COALESCE(SUM(iq.queso), 0) AS queso,
  COALESCE(SUM(iq.guac), 0) AS guac,
  COALESCE(SUM(iq.chips), 0) AS chips,
  COALESCE(SUM(iq.sides), 0) AS sides,
  COALESCE(SUM(iq.drinks), 0) AS drinks,
  COALESCE(SUM(iq.alcohol), 0) AS alcohol,
  COALESCE(SUM(iq.desserts), 0) AS desserts
FROM (
  SELECT RESTAURANT_LOCATION, SERVER, DINING_CATEGORY, SERVICE,
    SUM(CHECK_COUNT) AS CHECK_COUNT, SUM(AMOUNT) AS AMOUNT
  FROM CHABI_DBT.ORDERS_REPORTS
  WHERE BRAND = 'fuego-tortilla-grill'
    AND REPORT_DATE BETWEEN '{start_date}' AND '{end_date}'
    AND VOIDED = false
    AND DINING_CATEGORY IN ('Dine In', 'Drive Thru')
    AND SERVICE IS NOT NULL
    AND SERVER NOT IN (
      'default online ordering', 'Default Online Ordering',
      'Online Order', 'Online  Order ', 'Online  Host Village'
    )
    AND SERVER IS NOT NULL AND LENGTH(TRIM(SERVER)) > 0
  GROUP BY 1, 2, 3, 4
  HAVING SUM(CHECK_COUNT) > 20
) o
LEFT JOIN (
  SELECT isr.RESTAURANT_LOCATION, TRIM(isr.SERVER) AS SERVER,
    isr.DINING_CATEGORY, isr.SERVICE,
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
    AND isr.DINING_CATEGORY IN ('Dine In', 'Drive Thru')
    AND isr.SERVICE IS NOT NULL
    AND isr.SERVER NOT IN (
      'default online ordering', 'Default Online Ordering',
      'Online Order', 'Online  Order ', 'Online  Host Village'
    )
    AND isr.SERVER IS NOT NULL AND LENGTH(TRIM(isr.SERVER)) > 0
  GROUP BY 1, 2, 3, 4
) iq ON o.RESTAURANT_LOCATION = iq.RESTAURANT_LOCATION
  AND TRIM(o.SERVER) = iq.SERVER
  AND o.DINING_CATEGORY = iq.DINING_CATEGORY
  AND o.SERVICE = iq.SERVICE
GROUP BY 1, 2, 3, 4
ORDER BY 1, 4, 3, 2
```

**Note on result size**: If the combined query result is truncated by the MCP tool's row
limit, use `LISTAGG` to concatenate rows into a pipe-delimited string, or run per-location.
Typical total is ~275 rows across all 6 locations. If using LISTAGG, parse the pipe-delimited
output back into structured data in Python.

## Step 2: Compute Rates

For each server-segment row:

```
food_addon = (queso + guac + chips + sides + desserts) / checks * 100
bev_rate   = (drinks + alcohol) / checks * 100
total_upsell = food_addon + bev_rate
```

Also compute individual category rates for the detail columns:
```
queso_rate   = queso / checks * 100
guac_rate    = guac / checks * 100
sides_rate   = sides / checks * 100
desserts_rate = desserts / checks * 100
drinks_rate  = drinks / checks * 100
alcohol_rate = alcohol / checks * 100
```

Rates can exceed 100% (more than one item per check — that's great).

## Step 3: Compute Benchmarks

### STORE AVG (per location per segment)

For each (location, channel, daypart) segment, compute **check-weighted** averages:

```
store_avg_X = sum(server_X * server_checks) / sum(server_checks)
store_avg_total_upsell = store_avg_food_addon + store_avg_bev_rate
store_avg_checks = sum(server_checks)
```

Compute for all metrics: food_addon, bev_rate, avg_check, and each individual category rate.

### COMPANY AVG (across all locations per segment)

For each (channel, daypart) segment across ALL locations:

```
company_avg_X = sum(server_X * server_checks) / sum(server_checks)  -- all locations
company_avg_total_upsell = company_avg_food_addon + company_avg_bev_rate
company_avg_checks = sum(server_checks)  -- all locations
```

**Important**: Company averages MUST be computed from ALL locations' data, not just the
current report's location. This is why the single combined query approach is preferred.

## Step 4: Grade Servers

### Percentile Ranking by Total Upsell

Within each segment (for a given location), rank servers by `total_upsell`:

```
total_pct = (count of servers with LOWER total_upsell) / (total_servers - 1) * 100
```

If only 1 server in a segment, percentile defaults to 50.

### Grade Labels (based on total_upsell percentile)

| Percentile | Label | Styling |
|------------|-------|---------|
| 80–100 | ★ Star | Solid dark green badge (#1a7a3a), white text |
| 60–79 | Strong | Light green bg (#d4edda) |
| 40–59 | Average | Gold/yellow bg (#fff3cd) |
| 20–39 | Below Avg | Orange bg (#ffe0cc) |
| 0–19 | Needs Work | Red bg (#f8d7da) |

## Step 5: Build the Table — Ranked with Benchmarks In-Place

This is the key differentiator of this report. Tables are sorted by `total_upsell`
descending, and the **STORE AVG** and **COMPANY AVG** rows are inserted at their natural
ranked position alongside servers.

### Algorithm:

```python
entries = []
for server in segment_servers:
    entries.append(('server', server['total_upsell'], server))
entries.append(('store', store_avg['total_upsell'], store_avg))
entries.append(('company', company_avg['total_upsell'], company_avg))
entries.sort(key=lambda x: -x[1])  # descending by total_upsell
```

Then render each entry:
- `server` → normal row with pill-colored rates
- `store` → highlighted teal callout row (class `avg-store`)
- `company` → highlighted gold callout row (class `avg-company`)

This lets a GM instantly see: "4 servers above store avg, 2 below, and we're above/below
the company benchmark."

### Table Columns

```
Server | Total | Grade | Checks | Avg Chk | Queso | Guac | Sides | Dessert | Food Add-On | Drinks | Alcohol | Bev Total
```

- **Total** = `total_upsell` formatted as `{value:.0f}%` (bold, large font)
- **Grade** = pill badge from Step 4
- **Individual category pills**: green if 5+ pts above store avg, red if 5+ pts below,
  yellow/neutral otherwise
- **STORE AVG row**: shows `total_upsell` in the Total column, dashes for Score/Grade,
  store total checks, and raw % values (no pills)
- **COMPANY AVG row**: same format, different highlight color

## Step 6: Build AI Coaching Recap

The recap uses **natural language paragraphs** (not bullet points). Be specific with
names, segments, and numbers. Maximum of:

- **4 Top Performers** (total_upsell percentile ≥ 75 AND checks ≥ 30)
- **4 Training Focus** (total_upsell percentile ≤ 25 AND checks ≥ 30)

Sorted by total_upsell descending for top, ascending for training.

### Top Performers format:

> **{Server}** stands out in *{Channel} {Daypart}* ({checks} checks). They're delivering
> a food add-on rate of {X}% (well above the {Y}% avg), and a beverage attachment of {X}%
> vs the {Y}% norm.

Only include specific callouts where the server is 5+ pts above store avg. If no specific
standout, use: "Consistently strong across all categories."

### Training Focus format:

> **{Server}** has room to grow in *{Channel} {Daypart}* ({checks} checks). Their food
> add-on sits at {X}% vs the {Y}% avg, and bev attachment is {X}% vs {Y}%. Consider
> pairing them with a top performer during overlapping shifts.

Only include specific callouts where the server is 5+ pts below store avg.

**Do NOT include**: Daypart-level gaps, standout categories, cross-channel comparisons,
or systemic gap analysis. Keep the recap focused on actionable individual coaching.

## Step 7: Generate HTML Report

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

1. **Header** — Dark charcoal background, "Upselling by Server" title, location name in
   teal, date range in tan. Glowing teal bar style (3px teal borders top/bottom with
   box-shadow glow).

2. **Summary KPIs** — 4 cards with teal top border:
   - Strongest Food Add-On section (name + rate)
   - Biggest Food Add-On Opportunity section (name + rate)
   - Strongest Bev Rate section (name + rate)
   - Biggest Bev Opportunity section (name + rate)

   Section values are check-weighted averages for that segment. Format section names as
   "{Channel} {Daypart}" (e.g., "Dine In Dinner").

3. **Per-segment tables** — One section per segment, ordered daypart-first:
   Dine In Breakfast → Drive Thru Breakfast → Dine In Lunch → Drive Thru Lunch →
   Dine In Dinner → Drive Thru Dinner → Dine In Late Night → Drive Thru Late Night.

   Skip segments with no data. Each has:
   - Dark charcoal header bar with icon (🍽️ Dine In, 🚗 Drive Thru), daypart name,
     server count, check count, avg check
   - Table with all servers + STORE AVG + COMPANY AVG ranked by Total (descending)
   - **No separate benchmark bar** — benchmarks are in the table itself

4. **AI Coaching Recap** — Bordered left with teal accent. Contains Top Performers (max 4)
   and Training Focus (max 4) sections with natural language paragraphs.

5. **Footer** — Generated date, "Fuego Tortilla Grill — {Location}", Chabi Analytics.

### Callout Row Styling

```css
/* STORE AVG — teal theme */
tr.avg-store {
  background: #dff0ef;
  border-top: 2px solid var(--fuego-teal);
  border-bottom: 2px solid var(--fuego-teal);
}
tr.avg-store td { font-weight: 700; color: var(--fuego-charcoal); font-size: 13px; }
tr.avg-store .sn { color: var(--fuego-teal); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
tr.avg-store:hover { background: #dff0ef; }  /* no hover change */

/* COMPANY AVG — gold theme */
tr.avg-company {
  background: #eae6dc;
  border-top: 2px solid #cec7b8;
  border-bottom: 2px solid #cec7b8;
}
tr.avg-company td { font-weight: 700; color: #555; font-size: 13px; }
tr.avg-company .sn { color: #A57E39; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
tr.avg-company:hover { background: #eae6dc; }
```

### Pill Colors

```css
.pill-green  { background: #d4edda; color: #155724; }  /* 5+ pts above store avg */
.pill-red    { background: #f8d7da; color: #721c24; }  /* 5+ pts below store avg */
.pill-yellow { background: #fff3cd; color: #856404; }  /* within ±5 pts */
```

### Output

Generate one HTML report per location. Save to:
`upselling_by_server_{location_slug}_{start_date}_to_{end_date}.html`

Write the report as a **Python script** that generates the HTML, then execute it. This
ensures clean string interpolation and avoids template escaping issues.

When generating for all locations, process all 6 in a single script run (required to
compute company averages correctly), then present all files to the user together.
