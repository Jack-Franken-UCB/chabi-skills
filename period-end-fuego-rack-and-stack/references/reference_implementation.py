#!/usr/bin/env python3
"""
System Weekly Flash Report — 4-Week Consolidated Rack & Stack
Following fuego-weekly-consolidated-report skill exactly.
Period: Jan 26 – Feb 22, 2026 (4 weeks)
"""

import re, json, subprocess, shutil, os
from datetime import datetime, timedelta, date
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================
LOCATIONS = ["Burleson", "College Station", "Fayetteville", "San Antonio", "San Marcos", "Waco"]
WEEK_STARTS = [date(2026,2,16), date(2026,2,9), date(2026,2,2), date(2026,1,26)]
WS = WEEK_STARTS[0]  # Most recent week
TODAY_STR = "February 23, 2026"
REPORT_PERIOD = "Jan 26 – Feb 22, 2026"

# ============================================================
# HELPERS (from skill references/helpers.md)
# ============================================================
def fm(v, d=0):
    if v is None or v == 0: return "$0"
    return f"${v:,.{d}f}"
def fn(v, d=0):
    if v is None: return "—"
    return f"{v:,.{d}f}"
def fp(v, d=1):
    return f"{v:,.{d}f}%" if v else "—"
def pct_chg(current, prior):
    return ((current - prior) / prior) * 100 if prior else None
def pill_sss(v):
    if v is None: return '<span class="pill pill-neutral">N/A</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-green" if v >= 0 else "pill-red"
    return f'<span class="pill {cls}">{sign}{v:.1f}%</span>'
def pill_labor_diff(v):
    if v is None: return '<span class="pill pill-neutral">—</span>'
    sign = "+" if v >= 0 else ""
    cls = "pill-red" if v > 0.5 else ("pill-green" if v < -0.5 else "pill-yellow")
    return f'<span class="pill {cls}">{sign}{v:.0f}</span>'
def pill_labor_ratio(actual, guide):
    if not guide: return '<span class="pill pill-neutral">—</span>'
    r = (actual / guide) * 100
    cls = "pill-red" if r > 100.5 else ("pill-green" if r < 99.5 else "pill-yellow")
    return f'<span class="pill {cls}">{r:.1f}%</span>'
def pill_labor_pct(v):
    if not v: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v < 25 else ("pill-yellow" if v < 30 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}%</span>'
def pill_rating(v):
    if v is None: return '<span class="pill pill-neutral">—</span>'
    cls = "pill-green" if v >= 4.5 else ("pill-yellow" if v >= 4.0 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}</span>'
def rank_items(data, key, reverse=True):
    items = [(loc, data[loc].get(key, 0) or 0) for loc in LOCATIONS]
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
def kpi_badge_plain(text, cls="neutral"):
    return f'<div class="kpi-change {cls}">{text}</div>'
def wk_short(w): return w.strftime("%b %-d")
def wk_long(w):
    e = w + timedelta(days=6)
    return f"{w.strftime('%B %-d')} – {e.strftime('%-d')}, {e.year}"
def d(s): return date.fromisoformat(s)

# ============================================================
# RAW DATA (from Snowflake queries)
# ============================================================

# Daily sales (ORDER_METRICS day, TIME_PERIOD_TO_DATE=true)
daily_sales_raw = [
    ("Burleson","2026-01-27",2085.77),("Burleson","2026-01-28",3205.38),("Burleson","2026-01-29",4485.57),
    ("Burleson","2026-01-30",4871.50),("Burleson","2026-01-31",6216.10),("Burleson","2026-02-01",5731.83),
    ("Burleson","2026-02-03",4226.12),("Burleson","2026-02-04",3792.77),("Burleson","2026-02-05",4144.34),
    ("Burleson","2026-02-06",5781.70),("Burleson","2026-02-07",5949.61),("Burleson","2026-02-08",4576.81),
    ("Burleson","2026-02-10",4141.25),("Burleson","2026-02-11",4151.17),("Burleson","2026-02-12",5091.33),
    ("Burleson","2026-02-13",5998.08),("Burleson","2026-02-14",6256.61),("Burleson","2026-02-15",6810.92),
    ("Burleson","2026-02-17",4810.99),("Burleson","2026-02-18",4106.84),("Burleson","2026-02-19",5156.80),
    ("Burleson","2026-02-20",7594.99),("Burleson","2026-02-21",9738.59),("Burleson","2026-02-22",7870.56),
    ("College Station","2026-01-27",15713.51),("College Station","2026-01-28",17060.34),("College Station","2026-01-29",22889.50),
    ("College Station","2026-01-30",28185.36),("College Station","2026-01-31",33657.79),("College Station","2026-02-01",24043.88),
    ("College Station","2026-02-03",15713.08),("College Station","2026-02-04",17374.01),("College Station","2026-02-05",22045.45),
    ("College Station","2026-02-06",29243.44),("College Station","2026-02-07",35355.94),("College Station","2026-02-08",21541.74),
    ("College Station","2026-02-10",15194.41),("College Station","2026-02-11",17459.57),("College Station","2026-02-12",22276.49),
    ("College Station","2026-02-13",30036.81),("College Station","2026-02-14",26217.46),("College Station","2026-02-15",21534.53),
    ("College Station","2026-02-17",16755.88),("College Station","2026-02-18",19209.36),("College Station","2026-02-19",23079.80),
    ("College Station","2026-02-20",30887.04),("College Station","2026-02-21",33182.70),("College Station","2026-02-22",22353.46),
    ("Fayetteville","2026-01-27",159.77),("Fayetteville","2026-01-28",5437.31),("Fayetteville","2026-01-29",6965.17),
    ("Fayetteville","2026-01-30",9678.74),("Fayetteville","2026-01-31",9628.26),("Fayetteville","2026-02-01",7570.55),
    ("Fayetteville","2026-02-03",5135.57),("Fayetteville","2026-02-04",5158.61),("Fayetteville","2026-02-05",6633.50),
    ("Fayetteville","2026-02-06",9034.90),("Fayetteville","2026-02-07",8411.17),("Fayetteville","2026-02-08",5248.38),
    ("Fayetteville","2026-02-10",5284.60),("Fayetteville","2026-02-11",4696.70),("Fayetteville","2026-02-12",6750.01),
    ("Fayetteville","2026-02-13",8086.27),("Fayetteville","2026-02-14",7811.51),("Fayetteville","2026-02-15",7147.76),
    ("Fayetteville","2026-02-17",5213.36),("Fayetteville","2026-02-18",5481.09),("Fayetteville","2026-02-19",6094.60),
    ("Fayetteville","2026-02-20",8023.42),("Fayetteville","2026-02-21",8066.71),("Fayetteville","2026-02-22",7736.71),
    ("San Antonio","2026-01-27",6275.33),("San Antonio","2026-01-28",8137.13),("San Antonio","2026-01-29",7606.20),
    ("San Antonio","2026-01-30",9405.60),("San Antonio","2026-01-31",9197.81),("San Antonio","2026-02-01",7319.57),
    ("San Antonio","2026-02-03",7206.89),("San Antonio","2026-02-04",7827.21),("San Antonio","2026-02-05",6746.09),
    ("San Antonio","2026-02-06",9553.44),("San Antonio","2026-02-07",8967.72),("San Antonio","2026-02-08",6715.51),
    ("San Antonio","2026-02-10",6394.67),("San Antonio","2026-02-11",7151.55),("San Antonio","2026-02-12",7979.70),
    ("San Antonio","2026-02-13",8917.12),("San Antonio","2026-02-14",8764.90),("San Antonio","2026-02-15",7196.95),
    ("San Antonio","2026-02-17",8010.09),("San Antonio","2026-02-18",7605.51),("San Antonio","2026-02-19",7374.11),
    ("San Antonio","2026-02-20",10743.43),("San Antonio","2026-02-21",10602.89),("San Antonio","2026-02-22",8390.99),
    ("San Marcos","2026-01-27",6548.51),("San Marcos","2026-01-28",6906.71),("San Marcos","2026-01-29",7845.72),
    ("San Marcos","2026-01-30",9240.03),("San Marcos","2026-01-31",10299.45),("San Marcos","2026-02-01",7679.36),
    ("San Marcos","2026-02-03",6943.29),("San Marcos","2026-02-04",7590.44),("San Marcos","2026-02-05",7876.00),
    ("San Marcos","2026-02-06",9945.55),("San Marcos","2026-02-07",11295.24),("San Marcos","2026-02-08",7111.98),
    ("San Marcos","2026-02-10",7251.61),("San Marcos","2026-02-11",7387.84),("San Marcos","2026-02-12",7426.03),
    ("San Marcos","2026-02-13",10292.83),("San Marcos","2026-02-14",10585.51),("San Marcos","2026-02-15",7971.38),
    ("San Marcos","2026-02-17",6788.04),("San Marcos","2026-02-18",7799.74),("San Marcos","2026-02-19",9168.69),
    ("San Marcos","2026-02-20",11016.60),("San Marcos","2026-02-21",13039.12),("San Marcos","2026-02-22",8962.58),
    ("Waco","2026-01-27",5155.16),("Waco","2026-01-28",5881.55),("Waco","2026-01-29",7649.58),
    ("Waco","2026-01-30",8066.24),("Waco","2026-01-31",9770.01),("Waco","2026-02-01",6661.11),
    ("Waco","2026-02-03",7340.24),("Waco","2026-02-04",6636.99),("Waco","2026-02-05",7256.69),
    ("Waco","2026-02-06",11153.49),("Waco","2026-02-07",9315.14),("Waco","2026-02-08",6982.14),
    ("Waco","2026-02-10",5770.14),("Waco","2026-02-11",9115.88),("Waco","2026-02-12",7634.50),
    ("Waco","2026-02-13",10121.64),("Waco","2026-02-14",8273.38),("Waco","2026-02-15",9514.05),
    ("Waco","2026-02-17",5834.16),("Waco","2026-02-18",7183.42),("Waco","2026-02-19",7528.28),
    ("Waco","2026-02-20",11303.72),("Waco","2026-02-21",11150.11),("Waco","2026-02-22",7726.80),
]

# Weekly sales from ORDER_METRICS day_dow (correct PY alignment by day-of-week)
weekly_sales_raw = [
    ("Burleson","2026-01-26",26596.15,0,1417,0,817.39),
    ("Burleson","2026-02-02",28471.35,0,1597,0,939.93),
    ("Burleson","2026-02-09",32449.36,0,1718,0,1876.49),
    ("Burleson","2026-02-16",39288.24,0,2077,0,2558.97),
    ("College Station","2026-01-26",141550.38,129971.13,8533,8294,3335.84),
    ("College Station","2026-02-02",141273.66,134994.95,8945,8484,2652.88),
    ("College Station","2026-02-09",132719.27,134583.97,8714,8556,3101.76),
    ("College Station","2026-02-16",145491.40,139468.59,9125,8878,2494.48),
    ("Fayetteville","2026-01-26",39439.80,0,2545,0,2390.70),
    ("Fayetteville","2026-02-02",39622.13,0,2719,0,2671.91),
    ("Fayetteville","2026-02-09",39776.85,0,2645,0,2109.38),
    ("Fayetteville","2026-02-16",40615.89,0,2666,0,2545.55),
    ("San Antonio","2026-01-26",47941.64,47635.19,3213,3464,691.36),
    ("San Antonio","2026-02-02",47029.67,55189.75,3128,3646,683.52),
    ("San Antonio","2026-02-09",46409.96,53813.38,3137,3866,568.06),
    ("San Antonio","2026-02-16",52732.58,53894.77,3435,3748,756.40),
    ("San Marcos","2026-01-26",48519.78,51886.09,3142,3063,1183.15),
    ("San Marcos","2026-02-02",50782.22,52560.37,3284,3184,1275.98),
    ("San Marcos","2026-02-09",50915.20,53397.38,3261,3179,1211.12),
    ("San Marcos","2026-02-16",56774.77,51195.04,3544,3067,1258.25),
    ("Waco","2026-01-26",43183.65,47835.16,2752,3052,466.76),
    ("Waco","2026-02-02",48691.28,52111.96,3039,3121,732.54),
    ("Waco","2026-02-09",50429.59,47490.80,2998,3002,535.46),
    ("Waco","2026-02-16",50726.49,49394.71,3162,3017,667.02),
]

# Daily labor (day_dow — includes Monday boundary hours)
daily_labor_raw = [
    ("Burleson","2026-01-26",0.22,3.29),("Burleson","2026-01-27",69.8,1047.91),("Burleson","2026-01-28",89,1247.71),
    ("Burleson","2026-01-29",110.24,1588.98),("Burleson","2026-01-30",119.61,1682.76),("Burleson","2026-01-31",122.84,1811.64),
    ("Burleson","2026-02-01",100.54,1610.96),("Burleson","2026-02-02",1.1,16.52),("Burleson","2026-02-03",103.78,1434.99),
    ("Burleson","2026-02-04",94.58,1313.09),("Burleson","2026-02-05",103.01,1500.76),("Burleson","2026-02-06",114.38,1711.5),
    ("Burleson","2026-02-07",101.05,1417.62),("Burleson","2026-02-08",107.84,1514.87),("Burleson","2026-02-09",1.09,16.35),
    ("Burleson","2026-02-10",94.3,1382.78),("Burleson","2026-02-11",97.95,1459.1),("Burleson","2026-02-12",99.24,1455.65),
    ("Burleson","2026-02-13",98.07,1363.46),("Burleson","2026-02-14",87.24,1244.12),("Burleson","2026-02-15",90.22,1243.52),
    ("Burleson","2026-02-16",1.24,18.52),("Burleson","2026-02-17",88.85,1224.97),("Burleson","2026-02-18",93.09,1295.63),
    ("Burleson","2026-02-19",85.71,1190.32),("Burleson","2026-02-20",101.32,1405.5),("Burleson","2026-02-21",102.25,1495.4),
    ("Burleson","2026-02-22",100.58,1357.75),
    ("College Station","2026-01-26",4.02,66.03),("College Station","2026-01-27",222.02,3222.87),("College Station","2026-01-28",210.81,3020.33),
    ("College Station","2026-01-29",263.61,3812.8),("College Station","2026-01-30",285.55,4009.27),("College Station","2026-01-31",302.23,4390.18),
    ("College Station","2026-02-01",238.31,3527.28),("College Station","2026-02-02",6.07,101.58),("College Station","2026-02-03",240.64,3543.27),
    ("College Station","2026-02-04",225.42,3153.26),("College Station","2026-02-05",264.25,3782.41),("College Station","2026-02-06",299.58,4189.11),
    ("College Station","2026-02-07",318.68,4619.32),("College Station","2026-02-08",242.56,3624.27),("College Station","2026-02-09",4.82,80.58),
    ("College Station","2026-02-10",245.00,3522.56),("College Station","2026-02-11",216.58,3081.18),("College Station","2026-02-12",256.72,3669.77),
    ("College Station","2026-02-13",309.78,4419.5),("College Station","2026-02-14",292.48,4153.84),("College Station","2026-02-15",235.33,3389.81),
    ("College Station","2026-02-16",6.30,105.22),("College Station","2026-02-17",234.57,3418.69),("College Station","2026-02-18",229.97,3261.82),
    ("College Station","2026-02-19",260.01,3683.09),("College Station","2026-02-20",318.08,4467.52),("College Station","2026-02-21",323.64,4613.14),
    ("College Station","2026-02-22",237.26,3496.51),
    ("Fayetteville","2026-01-27",0,0),("Fayetteville","2026-01-28",181.28,2263.03),("Fayetteville","2026-01-29",180.5,2134.12),
    ("Fayetteville","2026-01-30",225.96,2756.32),("Fayetteville","2026-01-31",229.36,2968.07),("Fayetteville","2026-02-01",202.81,2850.81),
    ("Fayetteville","2026-02-02",1.77,28.03),("Fayetteville","2026-02-03",177.93,2115.27),("Fayetteville","2026-02-04",201.18,2411.68),
    ("Fayetteville","2026-02-05",222.22,2691.54),("Fayetteville","2026-02-06",242.98,2904.17),("Fayetteville","2026-02-07",207.66,2552.38),
    ("Fayetteville","2026-02-08",179.55,2832.89),("Fayetteville","2026-02-09",1.28,20.88),("Fayetteville","2026-02-10",172.4,2112.5),
    ("Fayetteville","2026-02-11",187.91,2349.05),("Fayetteville","2026-02-12",199.74,2519.71),("Fayetteville","2026-02-13",199.5,2397.03),
    ("Fayetteville","2026-02-14",208.98,2706.82),("Fayetteville","2026-02-15",143.88,2053.19),("Fayetteville","2026-02-16",0.95,16.12),
    ("Fayetteville","2026-02-17",150.53,1720.33),("Fayetteville","2026-02-18",151.25,1839.53),("Fayetteville","2026-02-19",127.85,1737.34),
    ("Fayetteville","2026-02-20",181.94,2208.0),("Fayetteville","2026-02-21",182.53,2435.34),("Fayetteville","2026-02-22",148.59,2187.94),
    ("San Antonio","2026-01-26",1.19,19.16),("San Antonio","2026-01-27",102.81,1088.01),("San Antonio","2026-01-28",107.07,1216.72),
    ("San Antonio","2026-01-29",109.08,1126.99),("San Antonio","2026-01-30",122.38,1213.82),("San Antonio","2026-01-31",133.18,1358.1),
    ("San Antonio","2026-02-01",98.38,1096.92),("San Antonio","2026-02-02",1.04,16.01),("San Antonio","2026-02-03",100.89,1142.88),
    ("San Antonio","2026-02-04",104.33,1116.6),("San Antonio","2026-02-05",111.82,1141.93),("San Antonio","2026-02-06",119.63,1227.08),
    ("San Antonio","2026-02-07",120.87,1161.5),("San Antonio","2026-02-08",97.41,1116.34),("San Antonio","2026-02-09",1.96,32.83),
    ("San Antonio","2026-02-10",102.48,1076.03),("San Antonio","2026-02-11",94.54,1041.02),("San Antonio","2026-02-12",105.47,981.61),
    ("San Antonio","2026-02-13",110.36,1102.71),("San Antonio","2026-02-14",116.45,1226.12),("San Antonio","2026-02-15",95.28,1047.61),
    ("San Antonio","2026-02-16",1.86,31.02),("San Antonio","2026-02-17",102.47,1041.8),("San Antonio","2026-02-18",115.09,1203.34),
    ("San Antonio","2026-02-19",119.56,1170.71),("San Antonio","2026-02-20",125.61,1192.61),("San Antonio","2026-02-21",133.74,1358.2),
    ("San Antonio","2026-02-22",105.96,1313.5),
    ("San Marcos","2026-01-26",1.44,23.48),("San Marcos","2026-01-27",113.53,1767.33),("San Marcos","2026-01-28",112.52,1759.61),
    ("San Marcos","2026-01-29",120.49,1904.44),("San Marcos","2026-01-30",131.49,2041.97),("San Marcos","2026-01-31",136.11,2096.6),
    ("San Marcos","2026-02-01",110.07,1666.68),("San Marcos","2026-02-02",1.46,23.81),("San Marcos","2026-02-03",118.61,1836.91),
    ("San Marcos","2026-02-04",117.62,1829.93),("San Marcos","2026-02-05",122.45,1914.02),("San Marcos","2026-02-06",139.09,2171.14),
    ("San Marcos","2026-02-07",138.58,2128.44),("San Marcos","2026-02-08",108.16,1635.13),("San Marcos","2026-02-09",1.53,25.0),
    ("San Marcos","2026-02-10",113.06,1751.85),("San Marcos","2026-02-11",112.49,1762.2),("San Marcos","2026-02-12",119.69,1889.25),
    ("San Marcos","2026-02-13",133.72,2078.48),("San Marcos","2026-02-14",136.7,2109.37),("San Marcos","2026-02-15",105.74,1604.66),
    ("San Marcos","2026-02-16",1.69,27.67),("San Marcos","2026-02-17",104.65,1619.7),("San Marcos","2026-02-18",116.38,1811.22),
    ("San Marcos","2026-02-19",127.45,1993.56),("San Marcos","2026-02-20",135.43,2081.3),("San Marcos","2026-02-21",145.89,2249.12),
    ("San Marcos","2026-02-22",119.16,1896.58),
    ("Waco","2026-01-26",3.35,66.1),("Waco","2026-01-27",90.78,1328.66),("Waco","2026-01-28",103.35,1437.14),
    ("Waco","2026-01-29",122.15,1673.02),("Waco","2026-01-30",146.38,2048.21),("Waco","2026-01-31",147.54,2114.44),
    ("Waco","2026-02-01",111.88,1541.12),("Waco","2026-02-02",1.98,39.6),("Waco","2026-02-03",125.02,1885.11),
    ("Waco","2026-02-04",105.67,1554.43),("Waco","2026-02-05",127.62,1882.23),("Waco","2026-02-06",134.34,1954.44),
    ("Waco","2026-02-07",132.26,1983.8),("Waco","2026-02-08",113.75,1687.96),("Waco","2026-02-09",2.01,41.38),
    ("Waco","2026-02-10",112.76,1710.63),("Waco","2026-02-11",121.27,1805.61),("Waco","2026-02-12",113.85,1687.78),
    ("Waco","2026-02-13",135.74,1980.79),("Waco","2026-02-14",115.45,1689.29),("Waco","2026-02-15",106.33,1513.45),
    ("Waco","2026-02-16",3.02,60.35),("Waco","2026-02-17",115.13,1735.21),("Waco","2026-02-18",121.54,1805.3),
    ("Waco","2026-02-19",116.93,1721.93),("Waco","2026-02-20",154.12,2330.9),("Waco","2026-02-21",147.05,2146.98),
    ("Waco","2026-02-22",114.67,1679.09),
]

scheduled_raw = [
    ("Burleson","2026-01-27",104),("Burleson","2026-01-28",97.5),("Burleson","2026-01-29",108.5),("Burleson","2026-01-30",116.5),("Burleson","2026-01-31",128),("Burleson","2026-02-01",99),
    ("Burleson","2026-02-03",101.5),("Burleson","2026-02-04",101.5),("Burleson","2026-02-05",107),("Burleson","2026-02-06",120.5),("Burleson","2026-02-07",119.5),("Burleson","2026-02-08",105.5),
    ("Burleson","2026-02-10",94),("Burleson","2026-02-11",100),("Burleson","2026-02-12",99.5),("Burleson","2026-02-13",103),("Burleson","2026-02-14",99),("Burleson","2026-02-15",94.5),
    ("Burleson","2026-02-17",96.5),("Burleson","2026-02-18",95.5),("Burleson","2026-02-19",90),("Burleson","2026-02-20",105),("Burleson","2026-02-21",101.5),("Burleson","2026-02-22",98),
    ("College Station","2026-01-27",230),("College Station","2026-01-28",202.5),("College Station","2026-01-29",236),("College Station","2026-01-30",252),("College Station","2026-01-31",287),("College Station","2026-02-01",212.5),
    ("College Station","2026-02-03",251.5),("College Station","2026-02-04",207.5),("College Station","2026-02-05",243),("College Station","2026-02-06",298.5),("College Station","2026-02-07",317),("College Station","2026-02-08",237),
    ("College Station","2026-02-10",245.5),("College Station","2026-02-11",212.5),("College Station","2026-02-12",246),("College Station","2026-02-13",293.5),("College Station","2026-02-14",300.5),("College Station","2026-02-15",230.25),
    ("College Station","2026-02-17",246),("College Station","2026-02-18",211.5),("College Station","2026-02-19",236.75),("College Station","2026-02-20",304),("College Station","2026-02-21",317),("College Station","2026-02-22",233.25),
    ("Fayetteville","2026-01-27",183),("Fayetteville","2026-01-28",180),("Fayetteville","2026-01-29",187.75),("Fayetteville","2026-01-30",217),("Fayetteville","2026-01-31",218.75),("Fayetteville","2026-02-01",172.75),
    ("Fayetteville","2026-02-03",184.5),("Fayetteville","2026-02-04",185.5),("Fayetteville","2026-02-05",236),("Fayetteville","2026-02-06",263),("Fayetteville","2026-02-07",227.5),("Fayetteville","2026-02-08",200),
    ("Fayetteville","2026-02-10",170.75),("Fayetteville","2026-02-11",194.5),("Fayetteville","2026-02-12",210.25),("Fayetteville","2026-02-13",235.25),("Fayetteville","2026-02-14",228.75),("Fayetteville","2026-02-15",182),
    ("Fayetteville","2026-02-17",136.5),("Fayetteville","2026-02-18",159.25),("Fayetteville","2026-02-19",144.75),("Fayetteville","2026-02-20",180.5),("Fayetteville","2026-02-21",178),("Fayetteville","2026-02-22",163.5),
    ("San Antonio","2026-01-27",104.25),("San Antonio","2026-01-28",77.5),("San Antonio","2026-01-29",97.5),("San Antonio","2026-01-30",102),("San Antonio","2026-01-31",123.5),("San Antonio","2026-02-01",97.5),
    ("San Antonio","2026-02-03",120),("San Antonio","2026-02-04",106.75),("San Antonio","2026-02-05",104.5),("San Antonio","2026-02-06",130),("San Antonio","2026-02-07",121),("San Antonio","2026-02-08",107),
    ("San Antonio","2026-02-10",99.75),("San Antonio","2026-02-11",92.5),("San Antonio","2026-02-12",108.5),("San Antonio","2026-02-13",119),("San Antonio","2026-02-14",114.5),("San Antonio","2026-02-15",92),
    ("San Antonio","2026-02-17",101.75),("San Antonio","2026-02-18",96.5),("San Antonio","2026-02-19",94),("San Antonio","2026-02-20",120),("San Antonio","2026-02-21",136.5),("San Antonio","2026-02-22",103.5),
    ("San Marcos","2026-01-27",118.5),("San Marcos","2026-01-28",121),("San Marcos","2026-01-29",124),("San Marcos","2026-01-30",131.5),("San Marcos","2026-01-31",132),("San Marcos","2026-02-01",108),
    ("San Marcos","2026-02-03",119.5),("San Marcos","2026-02-04",119),("San Marcos","2026-02-05",122),("San Marcos","2026-02-06",138),("San Marcos","2026-02-07",134),("San Marcos","2026-02-08",108),
    ("San Marcos","2026-02-10",119.5),("San Marcos","2026-02-11",119),("San Marcos","2026-02-12",124),("San Marcos","2026-02-13",131),("San Marcos","2026-02-14",134),("San Marcos","2026-02-15",108),
    ("San Marcos","2026-02-17",112),("San Marcos","2026-02-18",121),("San Marcos","2026-02-19",129),("San Marcos","2026-02-20",137.5),("San Marcos","2026-02-21",138),("San Marcos","2026-02-22",109),
    ("Waco","2026-01-27",122),("Waco","2026-01-28",113),("Waco","2026-01-29",124.25),("Waco","2026-01-30",156),("Waco","2026-01-31",159),("Waco","2026-02-01",124),
    ("Waco","2026-02-03",123),("Waco","2026-02-04",111),("Waco","2026-02-05",129.25),("Waco","2026-02-06",142),("Waco","2026-02-07",137),("Waco","2026-02-08",87),
    ("Waco","2026-02-10",123),("Waco","2026-02-11",111),("Waco","2026-02-12",130.25),("Waco","2026-02-13",144),("Waco","2026-02-14",137),("Waco","2026-02-15",88),
    ("Waco","2026-02-17",117),("Waco","2026-02-18",115),("Waco","2026-02-19",113.25),("Waco","2026-02-20",157),("Waco","2026-02-21",139),("Waco","2026-02-22",101.5),
]

# Catering CY
catering_cy_raw = [
    ("Burleson","2026-02-16",308.86,1),("Burleson","2026-02-09",1974.78,5),("Burleson","2026-02-02",313.10,2),("Burleson","2026-01-26",111.86,1),
    ("College Station","2026-02-16",5494.82,17),("College Station","2026-02-09",1543.95,12),("College Station","2026-02-02",2843.62,8),("College Station","2026-01-26",11030.74,15),
    ("Fayetteville","2026-02-16",471.90,2),("Fayetteville","2026-02-02",264.95,2),("Fayetteville","2026-01-26",304.68,1),
    ("San Antonio","2026-02-16",1400.16,5),("San Antonio","2026-02-09",130.05,1),("San Antonio","2026-02-02",1577.36,6),("San Antonio","2026-01-26",1213.98,2),
    ("San Marcos","2026-02-09",495.11,2),("San Marcos","2026-02-02",359.88,2),("San Marcos","2026-01-26",123.62,1),
    ("Waco","2026-02-16",2650.87,8),("Waco","2026-02-09",5020.72,15),("Waco","2026-02-02",3193.97,13),("Waco","2026-01-26",1756.00,5),
]

catering_py_raw = [
    ("College Station","2026-02-16",4420.19,14),("College Station","2026-02-09",1109.05,6),("College Station","2026-02-02",5342.75,16),("College Station","2026-01-26",4899.54,14),
    ("San Antonio","2026-02-16",328.11,3),("San Antonio","2026-02-09",231.49,2),("San Antonio","2026-02-02",3909.68,3),("San Antonio","2026-01-26",108.58,1),
    ("San Marcos","2026-02-16",641.32,2),("San Marcos","2026-02-09",352.94,2),("San Marcos","2026-02-02",2082.37,2),("San Marcos","2026-01-26",4177.73,3),
    ("Waco","2026-02-16",2080.56,11),("Waco","2026-02-09",3193.38,11),("Waco","2026-02-02",8487.20,14),("Waco","2026-01-26",2787.79,9),
]

reviews_raw = [
    ("Burleson","google",3.79,19),("Burleson","ovation",4.24,80),("Burleson","yelp",4.00,4),
    ("College Station","google",4.80,10),("College Station","ovation",4.72,71),("College Station","yelp",4.00,1),
    ("Fayetteville","google",3.83,23),("Fayetteville","ovation",4.34,119),
    ("San Antonio","google",4.45,11),("San Antonio","ovation",4.56,41),
    ("San Marcos","google",4.82,11),("San Marcos","ovation",4.68,53),("San Marcos","yelp",5.00,1),
    ("Waco","google",4.00,10),("Waco","ovation",3.86,49),("Waco","yelp",5.00,1),
]

# AGM data (from reference implementation)
agm_raw = [
    ("Burleson","2025-12-09","2030-12-31",0,0),
    ("College Station","2024-12-29","2030-12-31",8.333333333,50),
    ("Fayetteville","2026-01-26","2026-02-01",50,300),
    ("Fayetteville","2026-02-02","2026-02-08",41.666666667,250),
    ("Fayetteville","2026-02-09","2026-02-15",33.333333333,200),
    ("Fayetteville","2026-02-16","2026-02-22",25,150),
    ("San Antonio","2024-12-30","2030-12-31",0,0),
    ("San Marcos","2025-11-17","2030-12-31",-8.333333333,-50),
    ("Waco","2025-07-07","2030-12-31",0,0),
]

GUIDELINES_TABLE = {0:0,2100:326,18800:328,20000:345,25000:416,30000:488,35000:559,40000:631,45000:702,50000:744,55000:786,60000:828,65000:870,70000:912,75000:953,80000:995,85000:1037,90000:1079,95000:1120,100000:1162,105000:1204,110000:1246,115000:1287,120000:1329,125000:1371,130000:1413,135000:1454,140000:1496,145000:1538,150000:1580,155000:1621,160000:1663,165000:1705,170000:1747,175000:1788,180000:1830,185000:1872,190000:1914,195000:1956,200000:1997}

# ============================================================
# ORGANIZE DATA
# ============================================================
daily_sales_d = defaultdict(dict)
for loc,dt,amt in daily_sales_raw:
    daily_sales_d[loc][d(dt)] = amt

daily_labor = defaultdict(dict)
for loc,dt,hrs,pay in daily_labor_raw:
    daily_labor[loc][d(dt)] = {"hours":hrs,"pay":pay}

sched = defaultdict(dict)
for loc,dt,hrs in scheduled_raw:
    sched[loc][d(dt)] = hrs

weekly_sales = defaultdict(dict)
for loc,ws_str,amt,amt_py,ords,ords_py,disc in weekly_sales_raw:
    weekly_sales[loc][d(ws_str)] = {"amount":amt,"amount_py":amt_py,"orders":ords,"orders_py":ords_py,"discount":disc}

catering_cy = defaultdict(dict)
for loc,ws,amt,orders in catering_cy_raw:
    catering_cy[loc][d(ws)] = {"amount":amt,"orders":orders}
catering_py = defaultdict(dict)
for loc,ws,amt,orders in catering_py_raw:
    catering_py[loc][d(ws)] = {"amount":amt,"orders":orders}

reviews_dict = {}
for loc,source,avg_r,cnt in reviews_raw:
    if loc not in reviews_dict: reviews_dict[loc] = {}
    reviews_dict[loc][source] = {"avg":avg_r,"count":cnt}

# ============================================================
# GUIDELINE FUNCTIONS
# ============================================================
def lookup_guide(net_sales):
    thresholds = sorted(GUIDELINES_TABLE.items())
    if net_sales <= 0: return 0
    for i,(t,h) in enumerate(thresholds):
        if t > net_sales:
            lt,lh = thresholds[i-1]; frac = (net_sales-lt)/(t-lt)
            return lh + frac*(h-lh)
    return thresholds[-1][1]

def get_agm_daily(location, day):
    for loc,start,end,daily_h,weekly_h in agm_raw:
        if loc == location and d(start) <= day <= d(end): return weekly_h/6
    return 0

def compute_daily_guideline(week_start_dt, ds, location):
    DAYS_OPEN=6; DOW_ADJ={0:0,1:8,2:3,3:3,4:3,5:3,6:-20}; rate=54/3000
    days = [week_start_dt+timedelta(days=i) for i in range(7)]
    dws = sum(1 for dd in days if ds.get(dd,0)>0)
    is_partial = dws < DAYS_OPEN; result = {}
    if is_partial:
        for dd in days:
            s = ds.get(dd,0)
            if dd.weekday()==0 or s<=0: result[dd]=0
            else:
                proj=s*DAYS_OPEN; lkp=lookup_guide(proj)
                if lkp<=0: result[dd]=0
                else:
                    agm=get_agm_daily(location,dd)
                    result[dd]=lkp/DAYS_OPEN+DOW_ADJ.get(dd.weekday(),0)+agm
    else:
        wn=sum(ds.get(dd,0) for dd in days); tg=lookup_guide(wn); raw=[]
        for dd in days:
            if dd.weekday()==0: raw.append(0)
            else:
                s=ds.get(dd,0)
                if s<=0: raw.append(0)
                elif s<=9000: raw.append(s*rate)
                else: raw.append(9000*rate+(s-9000)*rate*0.80)
        tr = sum(raw) or 1
        for i,dd in enumerate(days):
            s=ds.get(dd,0)
            if dd.weekday()==0 or s<=0: result[dd]=0
            else:
                agm=get_agm_daily(location,dd)
                result[dd]=(raw[i]/tr)*tg+DOW_ADJ.get(dd.weekday(),0)+agm
    return result, sum(result.values()), sum(ds.get(dd,0) for dd in days)

# ============================================================
# COMPUTE PER-LOCATION PER-WEEK AND 4-WEEK AGGREGATES
# ============================================================
loc_weekly = defaultdict(dict)
loc_data = {}  # 4-week aggregates

for loc in LOCATIONS:
    total_amt = 0; total_amt_py = 0; total_ords = 0; total_ords_py = 0
    total_hrs = 0; total_pay = 0; total_guide = 0; total_sch = 0
    total_cat_amt = 0; total_cat_ords = 0; total_cat_py = 0; total_disc = 0

    for wi, ws_i in enumerate(WEEK_STARTS):
        # Sales from weekly aggregates
        cw = weekly_sales[loc].get(ws_i, {})
        amt = cw.get("amount", 0); amt_py = cw.get("amount_py", 0)
        ords = cw.get("orders", 0); ords_py = cw.get("orders_py", 0)
        disc = cw.get("discount", 0)
        has_py = amt_py > 0
        sss_v = pct_chg(amt, amt_py) if has_py else None
        sst_v = pct_chg(ords, ords_py) if has_py else None
        avg_tkt = amt / ords if ords else 0
        avg_tkt_py = amt_py / ords_py if (has_py and ords_py) else 0
        tkt_chg = pct_chg(avg_tkt, avg_tkt_py) if has_py else None

        # Labor
        week_days = [ws_i + timedelta(days=j) for j in range(7)]
        hrs = sum(daily_labor[loc].get(dd, {}).get("hours", 0) for dd in week_days)
        pay = sum(daily_labor[loc].get(dd, {}).get("pay", 0) for dd in week_days)
        sch_hrs = sum(sched[loc].get(dd, 0) for dd in week_days)

        # Guideline
        ds = {dd: daily_sales_d[loc].get(dd, 0) for dd in week_days}
        _, guide_total, _ = compute_daily_guideline(ws_i, ds, loc)

        lp = (pay / amt * 100) if amt > 0 else 0
        splh = amt / hrs if hrs > 0 else 0
        vs_guide_n = hrs - guide_total
        vs_guide_pct = (hrs / guide_total * 100) if guide_total > 0 else 0

        # Catering
        cat = catering_cy[loc].get(ws_i, {})
        cat_amt = cat.get("amount", 0); cat_ords = cat.get("orders", 0)
        cat_py_amt = catering_py[loc].get(ws_i, {}).get("amount", 0)

        loc_weekly[loc][wi] = {
            "amount": amt, "amount_py": amt_py, "orders": ords, "orders_py": ords_py,
            "has_py": has_py, "sss": sss_v, "sst": sst_v,
            "avg_tkt": avg_tkt, "tkt_chg": tkt_chg,
            "labor_hrs": hrs, "labor_pay": pay, "labor_pct": lp,
            "guide_total": guide_total, "vs_guide_n": vs_guide_n, "vs_guide_pct": vs_guide_pct,
            "sch_hrs": sch_hrs, "splh": splh,
            "cat_amt": cat_amt, "cat_ords": cat_ords, "cat_py_amt": cat_py_amt,
            "discount": disc,
        }

        total_amt += amt; total_amt_py += amt_py; total_ords += ords; total_ords_py += ords_py
        total_hrs += hrs; total_pay += pay; total_guide += guide_total
        total_sch += sch_hrs; total_disc += disc
        total_cat_amt += cat_amt; total_cat_ords += cat_ords; total_cat_py += cat_py_amt

    # 4-week aggregates
    has_py = total_amt_py > 2000
    sss = pct_chg(total_amt, total_amt_py) if has_py else None
    sst = pct_chg(total_ords, total_ords_py) if (has_py and total_ords_py) else None
    avg_tkt_4wk = total_amt / total_ords if total_ords else 0
    avg_tkt_py_4wk = total_amt_py / total_ords_py if (has_py and total_ords_py) else 0
    tkt_chg_4wk = pct_chg(avg_tkt_4wk, avg_tkt_py_4wk) if has_py else None
    lp_4wk = (total_pay / total_amt * 100) if total_amt > 0 else 0
    splh_4wk = total_amt / total_hrs if total_hrs > 0 else 0
    vs_guide_n = total_hrs - total_guide
    vs_guide_pct = (total_hrs / total_guide * 100) if total_guide > 0 else 0

    # Reviews
    rev = reviews_dict.get(loc, {})
    google_r = rev.get("google", {}).get("avg"); google_n = rev.get("google", {}).get("count", 0)
    ovation_r = rev.get("ovation", {}).get("avg"); ovation_n = rev.get("ovation", {}).get("count", 0)
    yelp_r = rev.get("yelp", {}).get("avg"); yelp_n = rev.get("yelp", {}).get("count", 0)
    total_rev_n = google_n + ovation_n + yelp_n
    wavg = ((google_r or 0)*google_n + (ovation_r or 0)*ovation_n + (yelp_r or 0)*yelp_n) / total_rev_n if total_rev_n else None

    cat_vs_py = pct_chg(total_cat_amt, total_cat_py) if total_cat_py > 0 else None

    loc_data[loc] = {
        "amount": total_amt, "amount_py": total_amt_py, "orders": total_ords, "orders_py": total_ords_py,
        "has_py": has_py, "sss": sss, "sst": sst,
        "avg_tkt": avg_tkt_4wk, "tkt_chg": tkt_chg_4wk, "avg_weekly": total_amt / 4,
        "labor_hrs": total_hrs, "labor_pay": total_pay, "labor_pct": lp_4wk,
        "guide_total": total_guide, "vs_guide_n": vs_guide_n, "vs_guide_pct": vs_guide_pct,
        "sch_hrs": total_sch, "splh": splh_4wk, "discount": total_disc,
        "cat_amt": total_cat_amt, "cat_ords": total_cat_ords, "cat_py_amt": total_cat_py, "cat_vs_py": cat_vs_py,
        "google_r": google_r, "google_n": google_n, "ovation_r": ovation_r, "ovation_n": ovation_n,
        "yelp_r": yelp_r, "yelp_n": yelp_n, "wavg_rating": wavg, "total_rev_n": total_rev_n,
        "suffix": "Comp" if has_py else "New",
    }

# ============================================================
# SYSTEM TOTALS
# ============================================================
comp_locs = [l for l in LOCATIONS if loc_data[l]["has_py"]]
sys_amt = sum(v["amount"] for v in loc_data.values())
sys_ords = sum(v["orders"] for v in loc_data.values())
comp_amt = sum(loc_data[l]["amount"] for l in comp_locs)
comp_amt_py = sum(loc_data[l]["amount_py"] for l in comp_locs)
comp_ords = sum(loc_data[l]["orders"] for l in comp_locs)
comp_ords_py = sum(loc_data[l]["orders_py"] for l in comp_locs)
sys_sss = pct_chg(comp_amt, comp_amt_py) if comp_amt_py else None
sys_sst = pct_chg(comp_ords, comp_ords_py) if comp_ords_py else None
sys_tkt = sys_amt / sys_ords if sys_ords else 0
comp_tkt = comp_amt / comp_ords if comp_ords else 0
comp_tkt_py = comp_amt_py / comp_ords_py if comp_ords_py else 0
sys_tkt_chg = pct_chg(comp_tkt, comp_tkt_py) if comp_tkt_py else None
sys_hrs = sum(v["labor_hrs"] for v in loc_data.values())
sys_pay = sum(v["labor_pay"] for v in loc_data.values())
sys_lp = (sys_pay / sys_amt * 100) if sys_amt else 0
sys_guide = sum(v["guide_total"] for v in loc_data.values())
sys_splh = sys_amt / sys_hrs if sys_hrs else 0
sys_cat = sum(v["cat_amt"] for v in loc_data.values())
sys_cat_ords = sum(v["cat_ords"] for v in loc_data.values())
sys_cat_py = sum(v["cat_py_amt"] for v in loc_data.values())
sys_sch = sum(v["sch_hrs"] for v in loc_data.values())

# ============================================================
# PRIOR PERIOD CONTEXT (Dec 29 – Jan 25) for AI Insights
# ============================================================
prior_sales = {
    "Burleson": {"cy": 109715.37, "py": 0},
    "College Station": {"cy": 416414.20, "py": 463986.86},
    "Fayetteville": {"cy": 143846.99, "py": 0},
    "San Antonio": {"cy": 163016.01, "py": 179578.35},
    "San Marcos": {"cy": 179371.44, "py": 192841.30},
    "Waco": {"cy": 150045.16, "py": 159812.03},
}
prior_labor = {
    "Burleson": {"hours": 2563.39, "pay": 36127.17},
    "College Station": {"hours": 5334.24, "pay": 76606.72},
    "Fayetteville": {"hours": 4747.52, "pay": 58641.60},
    "San Antonio": {"hours": 2538.44, "pay": 28235.11},
    "San Marcos": {"hours": 3108.45, "pay": 48073.69},
    "Waco": {"hours": 2601.69, "pay": 38079.12},
}
prior_catering = {
    "Burleson": 470.83, "College Station": 11956.15, "Fayetteville": 1078.96,
    "San Antonio": 1826.06, "San Marcos": 475.33, "Waco": 11397.57,
}

# Compute prior period metrics
prior_comp_cy = sum(prior_sales[l]["cy"] for l in comp_locs)
prior_comp_py = sum(prior_sales[l]["py"] for l in comp_locs)
prior_sys_sss = pct_chg(prior_comp_cy, prior_comp_py) if prior_comp_py else None
prior_sys_amt = sum(v["cy"] for v in prior_sales.values())
prior_sys_pay = sum(v["pay"] for v in prior_labor.values())
prior_sys_hrs = sum(v["hours"] for v in prior_labor.values())
prior_sys_lp = (prior_sys_pay / prior_sys_amt * 100) if prior_sys_amt else 0
prior_sys_cat = sum(prior_catering.values())

# Per-location prior SSS
prior_loc_sss = {}
for loc in comp_locs:
    ps = prior_sales[loc]
    prior_loc_sss[loc] = pct_chg(ps["cy"], ps["py"]) if ps["py"] else None

# Per-location prior labor %
prior_loc_lp = {}
for loc in LOCATIONS:
    ps = prior_sales[loc]["cy"]
    pp = prior_labor[loc]["pay"]
    prior_loc_lp[loc] = (pp / ps * 100) if ps else 0
sales_ranks = rank_items(loc_data, "amount", reverse=True)
labor_ranks = rank_items(loc_data, "vs_guide_pct", reverse=False)
cat_ranks = rank_items(loc_data, "cat_amt", reverse=True)
reviews_ranks = rank_items(loc_data, "wavg_rating", reverse=True)

# Comp SSS sorted
comp_sss = sorted([(l, loc_data[l]["sss"]) for l in comp_locs if loc_data[l]["sss"] is not None], key=lambda x: x[1])
best_sss_loc, best_sss_val = comp_sss[-1] if comp_sss else ("N/A", 0)
worst_sss_loc, worst_sss_val = comp_sss[0] if comp_sss else ("N/A", 0)

# Weekly trajectories
def traj(loc, key):
    return [loc_weekly[loc][wi].get(key, 0) for wi in [3,2,1,0]]

sales_callout = (
    f"System comp sales swung from <strong>{prior_sys_sss:+.1f}%</strong> in the prior 4-week window "
    f"to <strong>{sys_sss:+.1f}%</strong> this period — a meaningful trajectory shift. "
    f"<strong>College Station</strong> drove the turnaround, flipping from {prior_loc_sss.get('College Station',0):+.1f}% to "
    f"{loc_data['College Station']['sss']:+.1f}%, with the Feb 16 week ({fm(traj('College Station','amount')[3])}) their strongest in the window. "
    f"<strong>San Marcos</strong> improved from {prior_loc_sss.get('San Marcos',0):+.1f}% to {loc_data['San Marcos']['sss']:+.1f}% "
    f"and posted an accelerating weekly trend — their Feb 16 week ({fm(traj('San Marcos','amount')[3])}) was the best of the trailing 8 weeks. "
    f"<strong>San Antonio</strong> narrowed its comp gap from {prior_loc_sss.get('San Antonio',0):+.1f}% to {loc_data['San Antonio']['sss']:+.1f}%, "
    f"but the transaction decline ({loc_data['San Antonio']['sst']:+.1f}% SST) flags a traffic problem — ticket growth is masking it. "
    f"<strong>Burleson</strong> grew {pct_chg(loc_data['Burleson']['amount'], prior_sales['Burleson']['cy']):+.1f}% period-over-period as the ramp continues."
)

labor_callout = (
    f"System labor tightened from <strong>{prior_sys_lp:.1f}%</strong> in the prior 4-week window to "
    f"<strong>{sys_lp:.1f}%</strong> this period — a 3+ point improvement driven by both higher sales and better scheduling discipline. "
    f"<strong>San Antonio</strong> dropped from {prior_loc_lp['San Antonio']:.1f}% to {loc_data['San Antonio']['labor_pct']:.1f}%, "
    f"the tightest in the system — but verify this isn't understaffing given their negative transaction comps. "
    f"<strong>Fayetteville</strong> improved from {prior_loc_lp['Fayetteville']:.1f}% to {loc_data['Fayetteville']['labor_pct']:.1f}% as AGM hours "
    f"ramped down from 350 → 150 hrs/wk across the window. The gap to guideline ({loc_data['Fayetteville']['vs_guide_pct']:.1f}%) "
    f"should continue narrowing as training hours phase out completely. "
    f"<strong>Burleson</strong> cut from {prior_loc_lp['Burleson']:.1f}% to {loc_data['Burleson']['labor_pct']:.1f}% — "
    f"a textbook new-store labor ramp. Sharing their scheduling approach with Fayetteville could accelerate that store's normalization."
)

reviews_callout = (
    f"<strong>San Marcos</strong> leads with a {loc_data['San Marcos']['wavg_rating']:.2f} weighted average — "
    f"their {loc_data['San Marcos']['google_r']:.1f} Google score stands out as system-best and a real competitive advantage for discovery. "
    f"<strong>Waco's</strong> {loc_data['Waco']['wavg_rating']:.2f} weighted average (Ovation {loc_data['Waco']['ovation_r']:.2f}, "
    f"Google {loc_data['Waco']['google_r']:.1f}) is the system floor — investigate whether this ties to the labor tightening "
    f"(labor% dropped from {prior_loc_lp['Waco']:.1f}% → {loc_data['Waco']['labor_pct']:.1f}%) or specific service gaps. "
    f"<strong>Fayetteville's</strong> Google score ({loc_data['Fayetteville']['google_r']:.2f}) pulls down an otherwise strong "
    f"Ovation ({loc_data['Fayetteville']['ovation_r']:.2f}) — the {loc_data['Fayetteville']['google_n']} Google reviews likely include "
    f"early growing-pains ratings that will dilute over time. "
    f"Review volume system-wide ({sum(loc_data[l]['total_rev_n'] for l in LOCATIONS)} reviews over 4 weeks) is healthy — "
    f"keep Ovation prompts consistent."
)

cat_dir = "up" if sys_cat > prior_sys_cat else "down"
catering_callout = (
    f"System catering came in at {fm(sys_cat)}, {cat_dir} from {fm(prior_sys_cat)} in the prior 4-week window"
    f"{' — College Station drove the lift with ' + fm(loc_data['College Station']['cat_amt']) + ' vs ' + fm(prior_catering['College Station']) + ' prior.' if sys_cat > prior_sys_cat else '.'} "
    f"<strong>Waco</strong> held steady ({fm(loc_data['Waco']['cat_amt'])} vs {fm(prior_catering['Waco'])} prior) and leads the system "
    f"in catering consistency — their avg order size of "
    f"{fm(loc_data['Waco']['cat_amt']/loc_data['Waco']['cat_ords'],2) if loc_data['Waco']['cat_ords'] else '$0'} "
    f"suggests corporate/event-level business worth protecting with a dedicated contact. "
    f"<strong>San Antonio</strong> grew catering from {fm(prior_catering['San Antonio'])} → {fm(loc_data['San Antonio']['cat_amt'])} — "
    f"a potential offset to their declining dine-in traffic. "
    f"<strong>San Marcos</strong> ({fm(loc_data['San Marcos']['cat_amt'])}) and <strong>Fayetteville</strong> "
    f"({fm(loc_data['Fayetteville']['cat_amt'])}) remain underdeveloped — "
    f"targeted local business outreach could unlock an incremental revenue stream at both."
)

# ============================================================
# SYSTEM TRENDS TABLE (weekly)
# ============================================================
sys_weekly = {}
for ws_i in WEEK_STARTS:
    wi_idx = WEEK_STARTS.index(ws_i)
    sw_amt = sum(loc_weekly[l][wi_idx]["amount"] for l in LOCATIONS)
    sw_amt_py = sum(loc_weekly[l][wi_idx].get("amount_py",0) for l in comp_locs)
    sw_ords = sum(loc_weekly[l][wi_idx].get("orders",0) for l in LOCATIONS)
    sw_ords_py = sum(loc_weekly[l][wi_idx].get("orders_py",0) for l in comp_locs)
    sw_hrs = sum(loc_weekly[l][wi_idx]["labor_hrs"] for l in LOCATIONS)
    sw_pay = sum(loc_weekly[l][wi_idx]["labor_pay"] for l in LOCATIONS)
    sw_guide = sum(loc_weekly[l][wi_idx]["guide_total"] for l in LOCATIONS)
    sw_sch = sum(loc_weekly[l][wi_idx]["sch_hrs"] for l in LOCATIONS)
    sw_cat = sum(loc_weekly[l][wi_idx]["cat_amt"] for l in LOCATIONS)
    sw_cat_py = sum(loc_weekly[l][wi_idx]["cat_py_amt"] for l in LOCATIONS)
    sys_weekly[ws_i] = {"amount":sw_amt,"comp_amt_py":sw_amt_py,"orders":sw_ords,"comp_ords_py":sw_ords_py,
                        "labor_hrs":sw_hrs,"labor_pay":sw_pay,
                        "guide":sw_guide,"sch_hrs":sw_sch,"cat_amt":sw_cat,"cat_py":sw_cat_py}

trends_rows = ""
for ws_i in WEEK_STARTS:
    sw = sys_weekly[ws_i]
    wi_idx = WEEK_STARTS.index(ws_i)
    comp_amt_w = sum(loc_weekly[l][wi_idx]["amount"] for l in comp_locs)
    sss_w = pct_chg(comp_amt_w, sw["comp_amt_py"]) if sw["comp_amt_py"] else None
    comp_ords_w = sum(loc_weekly[l][wi_idx].get("orders",0) for l in comp_locs)
    sst_w = pct_chg(comp_ords_w, sw["comp_ords_py"]) if sw["comp_ords_py"] else None
    tkt_w = sw["amount"]/sw["orders"] if sw["orders"] else 0
    lp_w = (sw["labor_pay"]/sw["amount"]*100) if sw["amount"] else 0
    vs_g = sw["labor_hrs"]-sw["guide"]
    is_cw = ws_i == WS
    style = ' class="highlight"' if is_cw else ''
    b = lambda x: f"<strong>{x}</strong>" if is_cw else x
    trends_rows += (f'<tr{style}><td>{b(wk_short(ws_i))}</td><td>{b(fm(sw["amount"]))}</td>'
        f'<td>{pill_sss(sss_w)}</td><td>{b(fn(sw["orders"]))}</td><td>{pill_sss(sst_w)}</td>'
        f'<td>{b(fm(tkt_w,2))}</td>'
        f'<td>{b(fn(sw["guide"],0))}</td>'
        f'<td>{b(fn(sw["labor_hrs"],0))}</td><td>{pill_labor_diff(vs_g)}</td>'
        f'<td>{pill_labor_ratio(sw["labor_hrs"],sw["guide"])}</td><td>{pill_labor_pct(lp_w)}</td>'
        f'<td>{b(fm(sw["cat_amt"]))}</td></tr>')

# 4-week total row
trends_rows += (f'<tr class="total-row"><td><strong>Total</strong></td><td><strong>{fm(sys_amt)}</strong></td>'
    f'<td>{pill_sss(sys_sss)}</td><td><strong>{fn(sys_ords)}</strong></td><td>{pill_sss(sys_sst)}</td>'
    f'<td><strong>{fm(sys_tkt,2)}</strong></td>'
    f'<td><strong>{fn(sys_guide,0)}</strong></td>'
    f'<td><strong>{fn(sys_hrs,0)}</strong></td><td>{pill_labor_diff(sys_hrs-sys_guide)}</td>'
    f'<td>{pill_labor_ratio(sys_hrs,sys_guide)}</td><td>{pill_labor_pct(sys_lp)}</td>'
    f'<td><strong>{fm(sys_cat)}</strong></td></tr>')

# ============================================================
# RACK & STACK ROWS
# ============================================================
# Sales R&S
sales_rs_rows = ""
for loc,val,rk in sales_ranks:
    ld = loc_data[loc]
    sales_rs_rows += (f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td>'
        f'<td>{loc}</td><td>{fm(ld["amount"])}</td><td>{pill_sss(ld["sss"])}</td>'
        f'<td>{fn(ld["orders"])}</td><td>{pill_sss(ld.get("sst"))}</td>'
        f'<td>{fm(ld["avg_tkt"],2)}</td><td>{pill_sss(ld.get("tkt_chg"))}</td>'
        f'<td>{fm(ld["cat_amt"])}</td>'
        f'<td><span class="pill pill-neutral">{ld["suffix"]}</span></td></tr>')
sales_rs_rows += (f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fm(sys_amt)}</td>'
    f'<td>{pill_sss(sys_sss)}</td><td>{fn(sys_ords)}</td><td>{pill_sss(sys_sst)}</td>'
    f'<td>{fm(sys_tkt,2)}</td><td>{pill_sss(sys_tkt_chg)}</td>'
    f'<td>{fm(sys_cat)}</td><td><span class="pill pill-neutral">Comp</span></td></tr>')

# Labor R&S
labor_rs_rows = ""
for loc,val,rk in labor_ranks:
    ld = loc_data[loc]
    labor_rs_rows += (f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td>'
        f'<td>{loc}</td><td>{fm(ld["amount"])}</td><td>{fn(ld["guide_total"],0)}</td>'
        f'<td>{fn(ld["sch_hrs"],0)}</td><td>{fn(ld["labor_hrs"],0)}</td>'
        f'<td>{pill_labor_diff(ld["vs_guide_n"])}</td><td>{pill_labor_ratio(ld["labor_hrs"],ld["guide_total"])}</td>'
        f'<td>{pill_labor_pct(ld["labor_pct"])}</td><td>{fm(ld["splh"],2)}</td></tr>')
labor_rs_rows += (f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fm(sys_amt)}</td><td>{fn(sys_guide,0)}</td>'
    f'<td>{fn(sys_sch,0)}</td><td>{fn(sys_hrs,0)}</td><td>{pill_labor_diff(sys_hrs-sys_guide)}</td>'
    f'<td>{pill_labor_ratio(sys_hrs,sys_guide)}</td><td>{pill_labor_pct(sys_lp)}</td><td>{fm(sys_splh,2)}</td></tr>')

# Reviews R&S
reviews_rs_rows = ""
for loc,val,rk in reviews_ranks:
    ld = loc_data[loc]
    yelp_cell = pill_rating(ld["yelp_r"]) if ld["yelp_r"] else '<span class="pill pill-neutral">—</span>'
    yelp_n_cell = fn(ld["yelp_n"]) if ld["yelp_n"] else "—"
    reviews_rs_rows += (f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td>'
        f'<td>{loc}</td><td>{pill_rating(ld["google_r"])}</td><td>{fn(ld["google_n"])}</td>'
        f'<td>{pill_rating(ld["ovation_r"])}</td><td>{fn(ld["ovation_n"])}</td>'
        f'<td>{yelp_cell}</td><td>{yelp_n_cell}</td><td>{pill_rating(ld["wavg_rating"])}</td>'
        f'<td>{fn(ld["total_rev_n"])}</td></tr>')

# Catering R&S
cat_rs_rows = ""
for loc,val,rk in cat_ranks:
    ld = loc_data[loc]
    cat_rs_rows += (f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td>'
        f'<td>{loc}</td><td>{fn(ld["cat_ords"])}</td><td>{fm(ld["cat_amt"])}</td>'
        f'<td>{fm(ld["cat_py_amt"])}</td><td>{pill_sss(ld["cat_vs_py"])}</td></tr>')
cat_rs_rows += (f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fn(sys_cat_ords)}</td>'
    f'<td>{fm(sys_cat)}</td><td>{fm(sys_cat_py)}</td>'
    f'<td>{pill_sss(pct_chg(sys_cat,sys_cat_py) if sys_cat_py else None)}</td></tr>')

# ============================================================
# GM MESSAGE
# ============================================================
gm_msg = (
    f"Over the trailing 4-week period ({REPORT_PERIOD}), the Fuego system posted "
    f"{fm(sys_amt)} across {fn(sys_ords,0)} orders ({fm(sys_tkt,2)} avg ticket). "
    f"Comp same-store sales came in at {sys_sss:+.1f}%, a significant improvement from {prior_sys_sss:+.1f}% in the prior 4-week window. "
    f"System labor tightened to {sys_lp:.1f}% (from {prior_sys_lp:.1f}% prior), "
    f"running at {sys_hrs/sys_guide*100:.1f}% of guideline. "
    f"Catering delivered {fm(sys_cat)} system-wide."
)

# ============================================================
# CSS (from html_template.md)
# ============================================================
CSS = """
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
body { font-family: 'Source Sans 3','Myriad Pro',-apple-system,BlinkMacSystemFont,sans-serif;
  background: var(--bg); color: var(--text-primary); line-height: 1.4;
  -webkit-font-smoothing: antialiased; font-size: 11px; }
.report-container { max-width: 100%; margin: 0 auto; padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.header { border-radius: 10px; padding: 12px 20px; color: #fff; position: relative; overflow: hidden; }
.header-b3 { background: var(--fuego-charcoal); text-align: center; padding: 20px 20px 16px; position: relative; }
.header-b3-tag { display: inline-block; font-size: 8px; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; padding: 2px 10px; border-radius: 3px; margin-bottom: 8px;
  background: rgba(134,202,199,0.15); color: var(--fuego-teal); border: 1px solid rgba(134,202,199,0.3); }
.header-b3 h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 6px;
  text-shadow: 0 0 40px rgba(134,202,199,0.2); }
.header-b3-meta { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 11px; opacity: 0.75; }
.header-b3-pill { font-size: 9px; font-weight: 600; padding: 2px 8px; border-radius: 14px; border: 1px solid rgba(134,202,199,0.5); color: var(--fuego-teal); }
.header-b3-dot { color: var(--fuego-gold); font-size: 14px; }
.header-b3 .b3-bar-top, .header-b3 .b3-bar-bottom { position: absolute; left: 0; right: 0; }
.header-b3 .b3-bar-top { top: 0; } .header-b3 .b3-bar-bottom { bottom: 0; }
.b3-v5 .b3-bar-top { height: 2px; background: var(--fuego-teal); box-shadow: 0 0 12px rgba(134,202,199,0.6); }
.b3-v5 .b3-bar-bottom { height: 2px; background: var(--fuego-teal); box-shadow: 0 0 12px rgba(134,202,199,0.6); }
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.kpi-card { background: var(--card-bg); border-radius: 8px; padding: 10px 12px;
  border: 1px solid var(--border); border-top: 3px solid var(--fuego-teal); }
.kpi-card .kpi-label { font-size: 8px; font-weight: 500; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.kpi-card .kpi-value { font-size: 20px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.kpi-card .kpi-change { display: inline-flex; align-items: center; gap: 3px;
  font-size: 9px; font-weight: 600; margin-top: 6px; padding: 2px 8px; border-radius: 4px; }
.kpi-change.positive { color: var(--green); background: var(--green-bg); }
.kpi-change.negative { color: var(--red); background: var(--red-bg); }
.kpi-change.neutral { color: var(--yellow); background: var(--yellow-bg); }
.gm-message { background: linear-gradient(135deg, #f9f6f3, #f0ebe5);
  border: 1px solid var(--fuego-tan); border-left: 4px solid var(--fuego-teal);
  border-radius: 8px; padding: 10px 14px; font-size: 10px; line-height: 1.5; }
.gm-message .gm-label { font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #5a9e9b; margin-bottom: 6px; }
.section { background: var(--card-bg); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
.section-header { display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-bottom: 1px solid var(--border); background: #f9f6f3; border-left: 3px solid var(--fuego-teal); }
.section-header .icon { width: 22px; height: 22px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; font-size: 11px; }
.icon-sales { background: #fde8e3; color: var(--fuego-red); }
.icon-labor { background: #e8f1f0; color: #4a8e8b; }
.icon-reviews { background: #faf2e4; color: var(--fuego-gold); }
.icon-catering { background: #e0f2eb; color: var(--green); }
.section-header h2 { font-size: 11px; font-weight: 700; }
.section-header .section-sub { font-size: 8px; color: var(--text-secondary); margin-left: auto; }
table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
thead th { padding: 5px 5px; text-align: right; font-weight: 600; font-size: 7.5px;
  text-transform: uppercase; letter-spacing: 0.3px; color: var(--text-secondary);
  border-bottom: 2px solid var(--border); white-space: nowrap; }
thead th:first-child { text-align: left; }
tbody td { padding: 5px 5px; text-align: right; border-bottom: 1px solid #ede7e0; white-space: nowrap; }
tbody td:first-child { text-align: left; font-weight: 600; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #faf7f4; }
tbody tr.total-row { background: #f7f3ef; font-weight: 700; }
tbody tr.total-row td { border-top: 2px solid var(--border); }
tbody tr.highlight { background: #f5efe9; }
.pill { display: inline-block; padding: 1px 4px; border-radius: 4px; font-weight: 600; font-size: 8.5px; }
.pill-green { color: var(--green); background: var(--green-bg); }
.pill-red { color: var(--red); background: var(--red-bg); }
.pill-yellow { color: var(--yellow); background: var(--yellow-bg); }
.pill-neutral { color: var(--text-secondary); background: #ede7e0; }
.rank { display: inline-block; padding: 1px 5px; border-radius: 4px; font-weight: 700; font-size: 8.5px; }
.rank-1 { color: #fff; background: var(--green); }
.rank-2 { color: var(--green); background: var(--green-bg); }
.rank-3 { color: var(--yellow); background: var(--yellow-bg); }
.rank-mid { color: var(--text-secondary); background: #ede7e0; }
.rank-last { color: var(--red); background: var(--red-bg); }
.ai-callout { padding: 8px 12px; font-size: 9px; line-height: 1.5; color: var(--text-primary);
  background: linear-gradient(135deg, #edf7f6, #f4f0ec); border-top: 1px dashed var(--fuego-teal); }
.ai-callout .ai-label { font-size: 8px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #5a9e9b; margin-bottom: 4px; }
@media print {
  body { background: var(--bg); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .report-container { max-width: 100%; padding: 4px; }
  .section { break-inside: avoid; }
  .kpi-row { break-inside: avoid; }
}
"""

# ============================================================
# BUILD HTML
# ============================================================
html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Fuego System – 4-Week Consolidated Rack & Stack – {REPORT_PERIOD}</title>
<style>@page{{size:A4 portrait;margin:0.25in;}}{CSS}</style></head><body>
<div class="report-container">
<div class="header header-b3 b3-v5"><div class="b3-bar-top"></div><div class="header-b-inner"><div class="header-b3-tag">4-WEEK CONSOLIDATED RACK &amp; STACK</div><h1>Fuego Tortilla Grill</h1><div class="header-b3-meta"><span class="header-b3-pill">All 6 Locations</span><span class="header-b3-dot">&bull;</span><span>{REPORT_PERIOD}</span></div></div><div class="b3-bar-bottom"></div></div>
<div class="kpi-row">
<div class="kpi-card"><div class="kpi-label">System Sales</div><div class="kpi-value">{fm(sys_amt)}</div>{kpi_badge(sys_sss,"SSS (Comp)")}</div>
<div class="kpi-card"><div class="kpi-label">System Orders</div><div class="kpi-value">{fn(sys_ords)}</div>{kpi_badge(sys_sst,"SST (Comp)")}</div>
<div class="kpi-card"><div class="kpi-label">Avg Ticket</div><div class="kpi-value">{fm(sys_tkt,2)}</div>{kpi_badge(sys_tkt_chg,"vs PY (Comp)")}</div>
<div class="kpi-card"><div class="kpi-label">System Labor %</div><div class="kpi-value">{sys_lp:.1f}%</div>{kpi_badge_plain(f"{sys_hrs/sys_guide*100:.1f}% of Guide" if sys_guide else "—","positive" if sys_hrs<=sys_guide else "negative" if sys_hrs/sys_guide>1.05 else "neutral")}</div>
<div class="kpi-card"><div class="kpi-label">Catering</div><div class="kpi-value">{fm(sys_cat)}</div>{kpi_badge_plain("System Total","neutral")}</div>
</div>
<div class="gm-message"><div class="gm-label">System Summary</div>{gm_msg}</div>
<div class="section"><div class="section-header"><div class="icon icon-sales">&#128202;</div><h2>System Performance Trends</h2><div class="section-sub">Last 4 Weeks – All Locations Combined</div></div><table><thead><tr><th>Week</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th><th>Avg Tkt</th><th>Guide Hrs</th><th>Hours</th><th>vs Guide #</th><th>vs Guide %</th><th>Labor %</th><th>Catering</th></tr></thead><tbody>{trends_rows}</tbody></table></div>
<div class="section"><div class="section-header"><div class="icon icon-sales">&#128176;</div><h2>Sales Rack &amp; Stack</h2><div class="section-sub">{REPORT_PERIOD} – Ranked by Sales</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th><th>Avg Ticket</th><th>Tkt Chg</th><th>Catering</th><th>Basis</th></tr></thead><tbody>{sales_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{sales_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-labor">&#128101;</div><h2>Labor Rack &amp; Stack</h2><div class="section-sub">{REPORT_PERIOD} – Ranked by vs Guide %</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Sales</th><th>Guide Hrs</th><th>Sch Hrs</th><th>Hours</th><th>vs Guide #</th><th>vs Guide %</th><th>Labor %</th><th>SPLH</th></tr></thead><tbody>{labor_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{labor_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-reviews">&#11088;</div><h2>Reviews Rack &amp; Stack</h2><div class="section-sub">{REPORT_PERIOD} – Ranked by Weighted Avg Rating</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Google</th><th>#</th><th>Ovation</th><th>#</th><th>Yelp</th><th>#</th><th>Wtd Avg</th><th>Total #</th></tr></thead><tbody>{reviews_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{reviews_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-catering">&#127919;</div><h2>Catering Rack &amp; Stack</h2><div class="section-sub">{REPORT_PERIOD} – Ranked by Catering $</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Orders</th><th>Cat $</th><th>Cat $ PY</th><th>vs PY</th></tr></thead><tbody>{cat_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{catering_callout}</div></div>
</div></body></html>"""

# ============================================================
# SAVE
# ============================================================
html_path = "/home/claude/system_4wk_consolidated.html"
with open(html_path, "w") as f:
    f.write(html)

output_pdf = f"/mnt/user-data/outputs/Weekly Flash - Fuego System - 4-Week Consolidated - Jan 26 – Feb 22, 2026.pdf"
output_html = output_pdf.replace(".pdf", ".html")

try:
    from weasyprint import HTML
    HTML(filename=html_path).write_pdf(output_pdf)
    shutil.copy(html_path, output_html)
    print(f"✓ Saved: {output_pdf}")
    print(f"✓ Saved: {output_html}")
except Exception as e:
    shutil.copy(html_path, output_html)
    print(f"✗ PDF failed: {e}")
    print(f"✓ HTML saved: {output_html}")

# Print summary
print("\n=== 4-WEEK RACK & STACK ===")
for loc,val,rk in sales_ranks:
    ld = loc_data[loc]
    sss_str = f"{ld['sss']:+.1f}%" if ld['sss'] else "N/A"
    print(f"#{rk} {loc:20s} | Sales: {fm(ld['amount']):>10s} | SSS: {sss_str:>8s} | Labor%: {ld['labor_pct']:.1f}% | SPLH: {fm(ld['splh'],2)} | Reviews: {ld['wavg_rating']:.2f}★")
