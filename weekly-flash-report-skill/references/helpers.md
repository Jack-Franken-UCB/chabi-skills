# Python Helper Functions

Copy these functions exactly into the generation script. They handle all number formatting,
pill/badge generation, and date formatting for the report.

```python
from datetime import datetime, timedelta, date

def fm(v, d=0):
    """Format as money. $0 for zero/None."""
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
    """Percent change. Returns None if prior is 0."""
    return ((current - prior) / prior) * 100 if prior else None

def pill_sss(v):
    """SSS/SST percentage pill — green positive, red negative."""
    if v is None: return '<span class="pill pill-neutral">N/A</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-green" if v >= 0 else "pill-red"
    return f'<span class="pill {cls}">{sign}{v:.1f}%</span>'

def pill_labor_diff(v):
    """vs Guide # pill — green if under guideline, red if over."""
    if v is None: return '<span class="pill pill-neutral">—</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-red" if v > 0.5 else ("pill-green" if v < -0.5 else "pill-yellow")
    return f'<span class="pill {cls}">{sign}{v:.1f}</span>'

def pill_labor_ratio(actual, guide):
    """vs Guide % pill — actual/guide as percentage."""
    if not guide: return '<span class="pill pill-neutral">—</span>'
    r = (actual / guide) * 100
    cls = "pill-red" if r > 100.5 else ("pill-green" if r < 99.5 else "pill-yellow")
    return f'<span class="pill {cls}">{r:.1f}%</span>'

def pill_hrs_vs_sch(v):
    """Hours vs Scheduled pill — green if under, red if over."""
    if v is None: return '<span class="pill pill-neutral">—</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-green" if v < -0.5 else ("pill-red" if v > 0.5 else "pill-yellow")
    return f'<span class="pill {cls}">{sign}{v:.1f}</span>'

def pill_labor_pct(v):
    """Labor % pill — green <25%, yellow 25-30%, red >30%."""
    if not v: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v < 25 else ("pill-yellow" if v < 30 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}%</span>'

def pill_rating(v):
    """Review rating pill — green >=4, yellow 3-4, red <3."""
    if v is None: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v >= 4 else ("pill-yellow" if v >= 3 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}</span>'

def kpi_badge(v, suffix="vs PY"):
    """KPI change badge for the header cards."""
    if v is None: return f'<div class="kpi-change neutral">N/A {suffix}</div>'
    cls = "positive" if v >= 0 else "negative"
    arrow = "&#9650;" if v >= 0 else "&#9660;"
    sign = "+" if v >= 0 else ""
    return f'<div class="kpi-change {cls}">{arrow} {sign}{v:.1f}% {suffix}</div>'

def wk_short(w):
    """Short week label: 'Feb 9'"""
    return w.strftime("%b %-d")

def wk_long(w):
    """Long week label: 'February 9 – 15, 2026'"""
    e = w + timedelta(days=6)
    return f"{w.strftime('%B %-d')} – {e.strftime('%-d')}, {e.year}"
```
