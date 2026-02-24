# Helper Functions Reference

## Formatting Helpers

```python
def fm(v, d=0):
    """Format as money."""
    if v is None or v == 0: return "$0"
    return f"${v:,.{d}f}"

def fn(v, d=0):
    """Format number with commas."""
    if v is None: return "—"
    return f"{v:,.{d}f}"

def fp(v, d=1):
    """Format as percentage."""
    return f"{v:,.{d}f}%" if v else "—"

def pct_chg(current, prior):
    """Percentage change. Returns None if prior is 0."""
    return ((current - prior) / prior) * 100 if prior else None
```

## Pill Rendering Helpers

```python
def pill_sss(v):
    """Green if positive, red if negative, neutral if None."""
    if v is None: return '<span class="pill pill-neutral">N/A</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-green" if v >= 0 else "pill-red"
    return f'<span class="pill {cls}">{sign}{v:.1f}%</span>'

def pill_labor_diff(v):
    """Hours vs guide difference pill."""
    if v is None: return '<span class="pill pill-neutral">—</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-red" if v > 0.5 else ("pill-green" if v < -0.5 else "pill-yellow")
    return f'<span class="pill {cls}">{sign}{v:.1f}</span>'

def pill_labor_ratio(actual, guide):
    """Actual/Guide % pill. Under 100 = green, over = red."""
    if not guide: return '<span class="pill pill-neutral">—</span>'
    r = (actual / guide) * 100
    cls = "pill-red" if r > 100.5 else ("pill-green" if r < 99.5 else "pill-yellow")
    return f'<span class="pill {cls}">{r:.1f}%</span>'

def pill_labor_pct(v):
    """Labor % pill. Under 25 = green, 25-30 = yellow, over 30 = red."""
    if not v: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v < 25 else ("pill-yellow" if v < 30 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}%</span>'

def pill_rating(v):
    """Review rating pill. 4+ = green, 3-4 = yellow, under 3 = red."""
    if v is None: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v >= 4 else ("pill-yellow" if v >= 3 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}</span>'
```

## Rank Helpers

```python
def rank_items(loc_data, key, reverse=True):
    """Return list of (loc, value, rank). reverse=True = highest is #1."""
    items = [(loc, loc_data[loc].get(key, 0) or 0) for loc in LOCATIONS]
    items.sort(key=lambda x: x[1], reverse=reverse)
    return [(loc, val, i+1) for i, (loc, val) in enumerate(items)]

def rank_suffix(r):
    if r == 1: return "1st"
    elif r == 2: return "2nd"
    elif r == 3: return "3rd"
    else: return f"{r}th"

def rank_cls(r, total=6):
    if r == 1: return "rank-1"
    elif r == 2: return "rank-2"
    elif r == 3: return "rank-3"
    elif r == total: return "rank-last"
    else: return "rank-mid"

def kpi_badge(v, suffix="vs PY"):
    if v is None: return f'<div class="kpi-change neutral">N/A {suffix}</div>'
    cls = "positive" if v >= 0 else "negative"
    arrow = "&#9650;" if v >= 0 else "&#9660;"
    sign = "+" if v >= 0 else ""
    return f'<div class="kpi-change {cls}">{arrow} {sign}{v:.1f}% {suffix}</div>'
```

## Guideline Computation

### Algorithm Overview

1. Build `GUIDELINES_TABLE` from LABOR_GUIDELINES_TABLE query (threshold → hours mapping)
2. For each location and week, compute daily guidelines

### Lookup Function

```python
def lookup_guide(net_sales, GUIDELINES_TABLE):
    """Interpolate guideline hours from the lookup table."""
    thresholds = sorted(GUIDELINES_TABLE.items())
    if net_sales <= 0: return 0
    for i, (t, h) in enumerate(thresholds):
        if t > net_sales:
            lower_t, lower_h = thresholds[i - 1]
            frac = (net_sales - lower_t) / (t - lower_t)
            return lower_h + frac * (h - lower_h)
    return thresholds[-1][1]  # cap at max
```

### AGM Hours

```python
def get_agm_daily_hours(location, day, agm_data):
    """Get AGM adjustment hours for a location on a given day."""
    for loc, start, end, daily_h, weekly_h in agm_data:
        if loc == location and start <= day <= end:
            return weekly_h / 6  # 6 operating days (closed Mondays)
    return 0
```

### Daily Guideline Computation

```python
def compute_daily_guideline(week_start, daily_sales_dict, location, agm_data, GUIDELINES_TABLE):
    """
    Compute daily labor guidelines for a week.

    Returns: (daily_dict, total_hours, week_net_sales)

    Key rules:
    - DAYS_OPEN = 6 (closed Mondays)
    - Partial week (days_with_sales < 6): project each day independently
    - Full week: proportional allocation with knee at $9K
    - DOW adjustments always applied
    - AGM hours added per operating day
    - Zero-sales days get 0 (no DOW, no AGM)
    """
    DAYS_OPEN = 6
    DOW_ADJ = {0: 0, 1: 8, 2: 3, 3: 3, 4: 3, 5: 3, 6: -20}
    rate = 54 / 3000  # proportional rate

    days = [week_start + timedelta(days=i) for i in range(7)]
    days_with_sales = sum(1 for d in days if daily_sales_dict.get(d, 0) > 0)
    is_partial = days_with_sales < DAYS_OPEN
    result = {}

    if is_partial:
        # Each day projects independently
        for d in days:
            day_s = daily_sales_dict.get(d, 0)
            if d.weekday() == 0 or day_s <= 0:
                result[d] = 0
            else:
                proj = day_s * DAYS_OPEN
                lkp = lookup_guide(proj, GUIDELINES_TABLE)
                if lkp <= 0:
                    result[d] = 0
                else:
                    agm = get_agm_daily_hours(location, d, agm_data)
                    result[d] = lkp / DAYS_OPEN + DOW_ADJ.get(d.weekday(), 0) + agm
    else:
        # Full week: proportional allocation
        week_net = sum(daily_sales_dict.get(d, 0) for d in days)
        total_guide = lookup_guide(week_net, GUIDELINES_TABLE)

        # Compute raw weights with knee at $9K
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
            ds = daily_sales_dict.get(d, 0)
            if d.weekday() == 0 or ds <= 0:
                result[d] = 0
            else:
                agm = get_agm_daily_hours(location, d, agm_data)
                result[d] = (raw[i] / total_raw) * total_guide + DOW_ADJ.get(d.weekday(), 0) + agm

    return result, sum(result.values()), sum(daily_sales_dict.get(d, 0) for d in days)
```

## Data Organization

### Weekly Sales Dictionary

```python
# Structure: weekly_sales[location][week_start_date] = {
#   "amount": float, "amount_py": float, "net_amount": float,
#   "orders": int, "orders_py": int, "discount": float
# }
weekly_sales = defaultdict(dict)
```

### Daily Labor Dictionary

```python
# Structure: daily_labor[location][date] = {"hours": float, "pay": float}
daily_labor = defaultdict(dict)
```

### Reviews Dictionary

```python
# Structure: reviews[location][week_start_date][source] = {"avg": float, "count": int}
reviews = defaultdict(lambda: defaultdict(dict))
```

### Upselling Dictionary

```python
# Structure: upselling[location] = {
#   "checks": int, "avg_check": float,
#   "queso_rate": float, "guac_rate": float, "food_addon_rate": float,
#   "bev_rate": float, "drinks_rate": float, "alcohol_rate": float
# }
upselling = {}
```

### Per-Location Weekly History

```python
# Structure: loc_weekly[location][week_index] = {
#   "amount": float, "orders": int, "labor_pct": float,
#   "cat_amt": float, "google_r": float, "ovation_r": float, ...
# }
# week_index 0 = current week, 1 = prior week, etc.
loc_weekly = defaultdict(dict)
```
