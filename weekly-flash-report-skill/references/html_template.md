# HTML Template — S3 "Teal Thread" Design

This is the exact CSS and HTML structure for the Weekly Flash Report.
The S3 variant uses the original Fuego tan palette but threads teal accents through
KPI card tops, section header left borders, and the GM message border.

## Complete CSS

The CSS uses a two-part structure:
1. **Base CSS** — the core Fuego brand styles with red KPI borders and gold GM accents
2. **S3 Teal Thread overrides** — appended at the end, overriding specific rules with teal

This pattern is important because it keeps the base reusable for other color variants.

```css
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');

:root {
  --fuego-red: #DE3C00;
  --fuego-black: #352F2E;
  --fuego-charcoal: #232021;
  --fuego-gold: #A57E39;
  --fuego-tan: #DBCBBF;
  --fuego-teal: #86CAC7;
  --green: #2e7d5b;
  --green-bg: #e0f2eb;
  --red: #c13515;
  --red-bg: #fde8e3;
  --yellow: var(--fuego-gold);
  --yellow-bg: #faf2e4;
  --text-primary: #232021;
  --text-secondary: #7a706a;
  /* these get overridden per variant */
  --bg: #F4F0EC;
  --card-bg: #ffffff;
  --border: #d9cfc7;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Source Sans 3', 'Myriad Pro', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.report-container { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* ── HEADER (V5 Glowing Teal) ── */
.header {
  border-radius: 16px; padding: 32px 40px; color: #fff;
  margin-bottom: 24px; position: relative; overflow: hidden;
}
.header-b3 {
  background: var(--fuego-charcoal); text-align: center;
  padding: 44px 40px 38px; position: relative;
}
.header-b3-tag {
  display: inline-block; font-size: 11px; font-weight: 700;
  letter-spacing: 2.5px; text-transform: uppercase;
  padding: 4px 16px; border-radius: 4px; margin-bottom: 16px;
  background: rgba(134,202,199,0.15); color: var(--fuego-teal);
  border: 1px solid rgba(134,202,199,0.3);
}
.header-b3 h1 {
  font-size: 40px; font-weight: 800; letter-spacing: -1px;
  margin-bottom: 16px; text-shadow: 0 0 40px rgba(134,202,199,0.2);
}
.header-b3-meta {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; font-size: 14px; opacity: 0.75;
}
.header-b3-pill {
  font-size: 12px; font-weight: 600; letter-spacing: 0.5px;
  padding: 3px 12px; border-radius: 20px;
  border: 1px solid rgba(134,202,199,0.5); color: var(--fuego-teal);
  box-shadow: 0 0 8px rgba(134,202,199,0.15);
}
.header-b3-dot { color: var(--fuego-gold); font-size: 18px; }
.header-b3 .b3-bar-top, .header-b3 .b3-bar-bottom {
  position: absolute; left: 0; right: 0;
}
.header-b3 .b3-bar-top { top: 0; }
.header-b3 .b3-bar-bottom { bottom: 0; }
.b3-v5 .b3-bar-top {
  height: 3px; background: var(--fuego-teal);
  box-shadow: 0 0 12px rgba(134,202,199,0.6), 0 0 30px rgba(134,202,199,0.25);
}
.b3-v5 .b3-bar-bottom {
  height: 3px; background: var(--fuego-teal);
  box-shadow: 0 0 12px rgba(134,202,199,0.6), 0 0 30px rgba(134,202,199,0.25);
}

/* ── KPI CARDS ── */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card {
  background: var(--card-bg); border-radius: 12px; padding: 20px 24px;
  border: 1px solid var(--border); border-top: 3px solid var(--fuego-red);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.kpi-card .kpi-label {
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
}
.kpi-card .kpi-value {
  font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1.1;
}
.kpi-card .kpi-change {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; font-weight: 600; margin-top: 8px;
  padding: 2px 8px; border-radius: 6px;
}
.kpi-change.positive { color: var(--green); background: var(--green-bg); }
.kpi-change.negative { color: var(--red); background: var(--red-bg); }
.kpi-change.neutral { color: var(--yellow); background: var(--yellow-bg); }

/* ── SECTIONS ── */
.section {
  background: var(--card-bg); border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  margin-bottom: 24px; overflow: hidden;
}
.section-header {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 24px; border-bottom: 1px solid var(--border);
  background: #f9f6f3;
}
.section-header .icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.icon-sales { background: #fde8e3; color: var(--fuego-red); }
.icon-labor { background: #f4f0ec; color: var(--fuego-black); }
.icon-reviews { background: #faf2e4; color: var(--fuego-gold); }
.icon-catering { background: #e0f2eb; color: var(--green); }
.section-header h2 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.section-header .section-sub {
  font-size: 13px; color: var(--text-secondary); margin-left: auto;
}

/* ── TABLES ── */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th {
  padding: 10px 16px; text-align: right; font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary);
  border-bottom: 2px solid var(--border); white-space: nowrap;
}
thead th:first-child { text-align: left; }
tbody td {
  padding: 10px 16px; text-align: right;
  border-bottom: 1px solid #ede7e0; white-space: nowrap;
}
tbody td:first-child { text-align: left; font-weight: 600; color: var(--text-primary); }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #faf7f4; }
tbody tr.total-row { background: #f7f3ef; font-weight: 700; }
tbody tr.total-row td { border-top: 2px solid var(--border); }

/* ── PILLS ── */
.pill {
  display: inline-block; padding: 2px 8px; border-radius: 6px;
  font-weight: 600; font-size: 12px;
}
.pill-green { color: var(--green); background: var(--green-bg); }
.pill-red { color: var(--red); background: var(--red-bg); }
.pill-yellow { color: var(--yellow); background: var(--yellow-bg); }
.pill-neutral { color: var(--text-secondary); background: #ede7e0; }

/* ── GM MESSAGE ── */
.gm-message {
  background: linear-gradient(135deg, #f9f6f3, #f0ebe5);
  border: 1px solid var(--fuego-tan);
  border-left: 4px solid var(--fuego-gold);
  border-radius: 12px; padding: 20px 24px;
  margin-bottom: 24px; font-size: 14px;
  line-height: 1.7; color: var(--fuego-charcoal);
}
.gm-message .gm-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: var(--fuego-gold); margin-bottom: 8px;
}

/* ── LAYOUT ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.footer { text-align: center; padding: 16px; font-size: 11px; color: var(--text-secondary); }

@media print {
  body { background: #fff; }
  .report-container { padding: 0; }
  .section { break-inside: avoid; }
}

/* ── S3 "TEAL THREAD" OVERRIDES ──
   These override the base styles above to thread teal accents throughout.
   Append these AFTER the base CSS. */

:root {
  --bg: #F4F0EC;
  --card-bg: #ffffff;
  --border: #d9cfc7;
}

.kpi-card { border-top: 3px solid var(--fuego-teal); }
.section-header { background: #f9f6f3; border-left: 3px solid var(--fuego-teal); }
tbody tr:hover { background: #faf7f4; }
tbody tr.total-row { background: #f7f3ef; }
.gm-message { background: linear-gradient(135deg, #f9f6f3, #f0ebe5);
  border-left: 4px solid var(--fuego-teal); }
.gm-message .gm-label { color: #5a9e9b; }
.icon-labor { background: #e8f1f0; color: #4a8e8b; }
```

## HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weekly Flash Report – {location}</title>
<style>{CSS}</style>
</head>
<body>
<div class="report-container">

  <!-- HEADER -->
  <div class="header header-b3 b3-v5">
    <div class="b3-bar-top"></div>
    <div class="header-b-inner">
      <div class="header-b3-tag">WEEKLY FLASH REPORT</div>
      <h1>{location}</h1>
      <div class="header-b3-meta">
        <span class="header-b3-pill">Fuego Tortilla Grill</span>
        <span class="header-b3-dot">&bull;</span>
        <span>{week_long}</span>
      </div>
    </div>
    <div class="b3-bar-bottom"></div>
  </div>

  <!-- KPI CARDS -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Weekly Sales</div>
      <div class="kpi-value">{sales}</div>
      {kpi_badge(sss)}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Orders</div>
      <div class="kpi-value">{orders}</div>
      {kpi_badge(sst)}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Avg Ticket</div>
      <div class="kpi-value">{avg_ticket}</div>
      {kpi_badge(tkt_chg)}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Labor %</div>
      <div class="kpi-value">{labor_pct}%</div>
      <div class="kpi-change {labor_cls}">{labor_arrow} {labor_badge}</div>
    </div>
  </div>

  <!-- GM MESSAGE -->
  <div class="gm-message">
    <div class="gm-label">Message to General Manager</div>
    {gm_message}
  </div>

  <!-- SALES PERFORMANCE -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-sales">&#128202;</div>
      <h2>Sales Performance</h2>
      <div class="section-sub">Last 4 Weeks</div>
    </div>
    <table>
      <thead><tr>
        <th>Week</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th>
        <th>Avg Ticket</th><th>Tkt vs PY</th><th>Cat #</th><th>Cat $</th><th>Cat $ PY</th>
      </tr></thead>
      <tbody>{sales_rows}</tbody>
    </table>
  </div>

  <!-- TWO COLUMN: Reviews + Catering -->
  <div class="two-col">
    <div class="section">
      <div class="section-header">
        <div class="icon icon-reviews">&#11088;</div>
        <h2>Ratings &amp; Reviews</h2>
      </div>
      <table>
        <thead><tr>
          <th>Week</th><th>Google</th><th>#</th><th>Ovation</th><th>#</th><th>Yelp</th><th>#</th>
        </tr></thead>
        <tbody>{review_rows}</tbody>
      </table>
    </div>
    <div class="section">
      <div class="section-header">
        <div class="icon icon-catering">&#127919;</div>
        <h2>Catering</h2>
      </div>
      <table>
        <thead><tr>
          <th>Week</th><th>Orders</th><th>Cat $</th><th>Cat $ PY</th><th>vs PY</th>
        </tr></thead>
        <tbody>{catering_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- LABOR DAILY BREAKDOWN -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-labor">&#128101;</div>
      <h2>Labor | Last Week Daily Breakdown</h2>
      <div class="section-sub">{week_long}</div>
    </div>
    <table>
      <thead><tr>
        <th>Day</th><th>Sales</th><th>Guide Hrs</th><th>Sch Hrs</th><th>Actual Hrs</th>
        <th>vs Guide #</th><th>vs Guide %</th><th>Hrs vs Sch</th><th>Labor $</th>
        <th>Labor %</th><th>$ / Labor Hr</th>
      </tr></thead>
      <tbody>{labor_daily_rows}</tbody>
    </table>
  </div>

  <!-- LABOR TRENDS -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-labor">&#128200;</div>
      <h2>Labor Trends</h2>
      <div class="section-sub">Last 4 Weeks</div>
    </div>
    <table>
      <thead><tr>
        <th>Week</th><th>Sales</th><th>Guide Hrs</th><th>Sch Hrs</th><th>Actual Hrs</th>
        <th>vs Guide #</th><th>vs Guide %</th><th>Hrs vs Sch</th><th>Labor $</th>
        <th>Labor %</th><th>$ / Labor Hr</th>
      </tr></thead>
      <tbody>{labor_trends_rows}</tbody>
    </table>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Generated on {today} &middot; Fuego Tortilla Grill – {location} &middot; Data sourced from Chabi Analytics
  </div>

</div>
</body>
</html>
```

## Row Highlighting Rules

### Current Week Row (most recent)
- Add `style="background:#f5efe9;"` to `<tr>`
- Wrap cell values in `<strong>` tags (except pill cells which stay as-is)

### Monday Row (in labor daily)
- Add `style="opacity:0.5;"` to `<tr>`
- Show: Mon, $0, 0, —, {actual_hrs}, —, —, —, {labor_$}, —, —
- Monday is assumed closed/minimal operations

### Total Row (in labor daily)
- Add `class="total-row"` to `<tr>`
- Sums all 7 days for each column
