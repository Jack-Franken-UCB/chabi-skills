# HTML Template Reference

## S3 "Teal Thread" CSS

```css
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');
:root {
  --fuego-red: #DE3C00; --fuego-black: #352F2E; --fuego-charcoal: #232021;
  --fuego-gold: #A57E39; --fuego-tan: #DBCBBF; --fuego-teal: #86CAC7;
  --green: #2e7d5b; --green-bg: #e0f2eb; --red: #c13515; --red-bg: #fde8e3;
  --yellow: var(--fuego-gold); --yellow-bg: #faf2e4;
  --text-primary: #232021; --text-secondary: #7a706a;
  --bg: #F4F0EC; --card-bg: #ffffff; --border: #d9cfc7;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Source Sans 3','Myriad Pro',-apple-system,BlinkMacSystemFont,sans-serif;
  background: var(--bg); color: var(--text-primary); line-height: 1.4;
  -webkit-font-smoothing: antialiased; font-size: 11px;
}
```

## Layout

```css
.report-container {
  max-width: 100%; margin: 0 auto; padding: 10px;
  display: flex; flex-direction: column; gap: 12px;
}
```

## Header — Dark Charcoal with Teal Glow Bars

```css
.header { border-radius: 10px; padding: 12px 20px; color: #fff; position: relative; overflow: hidden; }
.header-b3 { background: var(--fuego-charcoal); text-align: center; padding: 24px 20px 20px; position: relative; }
.header-b3-tag {
  display: inline-block; font-size: 8px; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; padding: 2px 10px; border-radius: 3px; margin-bottom: 8px;
  background: rgba(134,202,199,0.15); color: var(--fuego-teal); border: 1px solid rgba(134,202,199,0.3);
}
.header-b3 h1 {
  font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 8px;
  text-shadow: 0 0 40px rgba(134,202,199,0.2);
}
.header-b3-meta { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 11px; opacity: 0.75; }
.header-b3-pill { font-size: 9px; font-weight: 600; padding: 2px 8px; border-radius: 14px; border: 1px solid rgba(134,202,199,0.5); color: var(--fuego-teal); }
.header-b3-dot { color: var(--fuego-gold); font-size: 14px; }
.header-b3 .b3-bar-top, .header-b3 .b3-bar-bottom { position: absolute; left: 0; right: 0; }
.header-b3 .b3-bar-top { top: 0; } .header-b3 .b3-bar-bottom { bottom: 0; }
.b3-v5 .b3-bar-top { height: 2px; background: var(--fuego-teal); box-shadow: 0 0 12px rgba(134,202,199,0.6); }
.b3-v5 .b3-bar-bottom { height: 2px; background: var(--fuego-teal); box-shadow: 0 0 12px rgba(134,202,199,0.6); }
```

## KPI Cards — 5 across with generous padding

```css
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.kpi-card {
  background: var(--card-bg); border-radius: 8px; padding: 12px 14px;
  border: 1px solid var(--border); border-top: 3px solid var(--fuego-teal);
}
.kpi-card .kpi-label {
  font-size: 9px; font-weight: 500; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}
.kpi-card .kpi-value { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.kpi-card .kpi-change {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 9px; font-weight: 600; margin-top: 6px; padding: 2px 8px; border-radius: 4px;
}
.kpi-change.positive { color: var(--green); background: var(--green-bg); }
.kpi-change.negative { color: var(--red); background: var(--red-bg); }
.kpi-change.neutral { color: var(--yellow); background: var(--yellow-bg); }
```

## GM Message / System Summary

```css
.gm-message {
  background: linear-gradient(135deg, #f9f6f3, #f0ebe5);
  border: 1px solid var(--fuego-tan); border-left: 4px solid var(--fuego-teal);
  border-radius: 8px; padding: 14px 18px; font-size: 10.5px; line-height: 1.6;
}
.gm-message .gm-label {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #5a9e9b; margin-bottom: 6px;
}
```

## Sections (Tables)

```css
.section { background: var(--card-bg); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
.section-header {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-bottom: 1px solid var(--border); background: #f9f6f3;
  border-left: 3px solid var(--fuego-teal);
}
.section-header .icon {
  width: 22px; height: 22px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; font-size: 11px;
}
.icon-sales { background: #fde8e3; color: var(--fuego-red); }
.icon-labor { background: #e8f1f0; color: #4a8e8b; }
.icon-reviews { background: #faf2e4; color: var(--fuego-gold); }
.icon-catering { background: #e0f2eb; color: var(--green); }
.section-header h2 { font-size: 11px; font-weight: 700; }
.section-header .section-sub { font-size: 8px; color: var(--text-secondary); margin-left: auto; }
```

## Tables

```css
table { width: 100%; border-collapse: collapse; font-size: 10px; }
thead th {
  padding: 6px 7px; text-align: right; font-weight: 600; font-size: 8px;
  text-transform: uppercase; letter-spacing: 0.3px; color: var(--text-secondary);
  border-bottom: 2px solid var(--border); white-space: nowrap;
}
thead th:first-child { text-align: left; }
tbody td { padding: 6px 7px; text-align: right; border-bottom: 1px solid #ede7e0; white-space: nowrap; }
tbody td:first-child { text-align: left; font-weight: 600; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #faf7f4; }
tbody tr.total-row { background: #f7f3ef; font-weight: 700; }
tbody tr.total-row td { border-top: 2px solid var(--border); }
tbody tr.highlight { background: #f5efe9; }
```

## Pills and Ranks

```css
.pill { display: inline-block; padding: 1px 5px; border-radius: 4px; font-weight: 600; font-size: 9px; }
.pill-green { color: var(--green); background: var(--green-bg); }
.pill-red { color: var(--red); background: var(--red-bg); }
.pill-yellow { color: var(--yellow); background: var(--yellow-bg); }
.pill-neutral { color: var(--text-secondary); background: #ede7e0; }

.rank { display: inline-block; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; }
.rank-1 { color: #fff; background: var(--green); }
.rank-2 { color: var(--green); background: var(--green-bg); }
.rank-3 { color: var(--yellow); background: var(--yellow-bg); }
.rank-mid { color: var(--text-secondary); background: #ede7e0; }
.rank-last { color: var(--red); background: var(--red-bg); }
```

## AI Insight Callout

```css
.ai-callout {
  padding: 10px 14px; font-size: 9.5px; line-height: 1.55; color: var(--text-primary);
  background: linear-gradient(135deg, #edf7f6, #f4f0ec);
  border-top: 1px dashed var(--fuego-teal);
}
.ai-callout .ai-label {
  font-size: 8px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #5a9e9b; margin-bottom: 4px;
}
```

## Print / PDF

```css
@media print {
  body { background: var(--bg); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .report-container { max-width: 100%; padding: 4px; }
  .section { break-inside: avoid; }
  .kpi-row { break-inside: avoid; }
}
```

## HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Fuego System Weekly Flash – {week_range}</title>
<style>
@page { size: A4 portrait; margin: 0.3in; }
{ALL_CSS_ABOVE}
</style>
</head>
<body>
<div class="report-container">

  <!-- HEADER -->
  <div class="header header-b3 b3-v5">
    <div class="b3-bar-top"></div>
    <div class="header-b-inner">
      <div class="header-b3-tag">SYSTEM WEEKLY FLASH REPORT</div>
      <h1>Fuego Tortilla Grill</h1>
      <div class="header-b3-meta">
        <span class="header-b3-pill">All {n} Locations</span>
        <span class="header-b3-dot">&bull;</span>
        <span>{week_range}</span>
      </div>
    </div>
    <div class="b3-bar-bottom"></div>
  </div>

  <!-- KPI CARDS -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">System Sales</div>
      <div class="kpi-value">{sys_sales}</div>
      {kpi_badge_sss}
    </div>
    <!-- ... Orders, Avg Ticket, Labor %, Catering ... -->
  </div>

  <!-- SYSTEM SUMMARY -->
  <div class="gm-message">
    <div class="gm-label">System Summary</div>
    {narrative}
  </div>

  <!-- SYSTEM TRENDS TABLE -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-sales">&#128202;</div>
      <h2>System Performance Trends</h2>
      <div class="section-sub">Last 4 Weeks – All Locations Combined</div>
    </div>
    <table>
      <thead><tr>
        <th>Week</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th>
        <th>Avg Tkt</th><th>Guide Hrs</th><th>Actual Hrs</th><th>vs Guide #</th>
        <th>vs Guide %</th><th>Labor %</th><th>Catering</th>
      </tr></thead>
      <tbody>{trends_rows}</tbody>
    </table>
  </div>

  <!-- SALES RACK & STACK + AI Insight -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-sales">&#128176;</div>
      <h2>Sales Rack &amp; Stack</h2>
      <div class="section-sub">{week_range} – Ranked by Sales</div>
    </div>
    <table>
      <thead><tr>
        <th>Rank</th><th>Location</th><th>Sales</th><th>SSS %</th>
        <th>Orders</th><th>SST %</th><th>Avg Ticket</th><th>Tkt Chg</th>
        <th>Catering</th><th>Basis</th>
      </tr></thead>
      <tbody>{sales_rs_rows}</tbody>
    </table>
    <div class="ai-callout">
      <div class="ai-label">&#129302; AI Insight</div>
      {sales_callout}
    </div>
  </div>

  <!-- LABOR RACK & STACK + AI Insight -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-labor">&#128101;</div>
      <h2>Labor Rack &amp; Stack</h2>
      <div class="section-sub">{week_range} – Ranked by vs Guide %</div>
    </div>
    <table>
      <thead><tr>
        <th>Rank</th><th>Location</th><th>Sales</th><th>Guide Hrs</th>
        <th>Sch Hrs</th><th>Actual Hrs</th><th>vs Guide #</th>
        <th>vs Guide %</th><th>Labor %</th><th>SPLH</th>
      </tr></thead>
      <tbody>{labor_rs_rows}</tbody>
    </table>
    <div class="ai-callout">
      <div class="ai-label">&#129302; AI Insight</div>
      {labor_callout}
    </div>
  </div>

  <!-- REVIEWS RACK & STACK + AI Insight -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-reviews">&#11088;</div>
      <h2>Reviews Rack &amp; Stack</h2>
      <div class="section-sub">{week_range} – Ranked by Weighted Avg Rating</div>
    </div>
    <table>
      <thead><tr>
        <th>Rank</th><th>Location</th><th>Google</th><th>#</th>
        <th>Ovation</th><th>#</th><th>Yelp</th><th>#</th>
        <th>Wtd Avg</th><th>Total #</th>
      </tr></thead>
      <tbody>{reviews_rs_rows}</tbody>
    </table>
    <div class="ai-callout">
      <div class="ai-label">&#129302; AI Insight</div>
      {reviews_callout}
    </div>
  </div>

  <!-- CATERING RACK & STACK + AI Insight -->
  <div class="section">
    <div class="section-header">
      <div class="icon icon-catering">&#127919;</div>
      <h2>Catering Rack &amp; Stack</h2>
      <div class="section-sub">{week_range} – Ranked by Catering $</div>
    </div>
    <table>
      <thead><tr>
        <th>Rank</th><th>Location</th><th>Orders</th><th>Cat $</th>
        <th>Cat $ PY</th><th>vs PY</th>
      </tr></thead>
      <tbody>{cat_rs_rows}</tbody>
    </table>
    <div class="ai-callout">
      <div class="ai-label">&#129302; AI Insight</div>
      {catering_callout}
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Generated on {today} &middot; Fuego Tortilla Grill – System Report &middot; Data sourced from Chabi Analytics
  </div>

</div>
</body>
</html>
```
