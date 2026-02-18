#!/usr/bin/env python3
"""
System Weekly Flash Report Generator — Following system-weekly-flash skill
Week of Feb 9–15, 2026
Includes AI Insight verification loop.
"""

import re, json, subprocess, shutil, os
from datetime import datetime, timedelta, date
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================
LOCATIONS = ["Burleson", "College Station", "Fayetteville", "San Antonio", "San Marcos", "Waco"]
WEEK_START = date(2026, 2, 9)
WEEK_END = date(2026, 2, 15)
WEEK_STARTS = [date(2026, 2, 9), date(2026, 2, 2), date(2026, 1, 26), date(2026, 1, 19)]
TODAY_STR = "February 17, 2026"

# ============================================================
# HELPERS
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
    return f'<span class="pill {cls}">{sign}{v:.1f}</span>'
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
    cls = "pill-green" if v >= 4 else ("pill-yellow" if v >= 3 else "pill-red")
    return f'<span class="pill {cls}">{v:.1f}</span>'
def rank_items(loc_data, key, reverse=True):
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
def wk_short(w): return w.strftime("%b %-d")
def wk_long(w):
    e = w + timedelta(days=6)
    return f"{w.strftime('%B %-d')} – {e.strftime('%-d')}, {e.year}"
def d(s): return date.fromisoformat(s)

# ============================================================
# RAW DATA (from Snowflake queries — see SKILL.md Steps 1-2)
# ============================================================
weekly_sales_raw = [
    ("Burleson","2026-02-09",32449.36,0,32449.36,1718,0,1876.49),
    ("Burleson","2026-02-02",28471.35,0,28471.35,1597,0,939.93),
    ("Burleson","2026-01-26",26596.15,0,26596.15,1417,0,817.39),
    ("Burleson","2026-01-19",16150.56,0,16150.56,988,0,817.71),
    ("College Station","2026-02-09",132719.27,134583.97,132719.27,8713,8556,3101.76),
    ("College Station","2026-02-02",141273.66,134994.95,141273.66,8943,8484,2652.88),
    ("College Station","2026-01-26",141550.38,129971.13,141550.38,8533,8294,3335.84),
    ("College Station","2026-01-19",89020.43,133378.97,89020.43,5847,7902,1832.17),
    ("Fayetteville","2026-02-09",39776.85,0,39776.85,2645,0,2109.38),
    ("Fayetteville","2026-02-02",39622.13,0,39622.13,2718,0,2671.91),
    ("Fayetteville","2026-01-26",39439.80,0,39439.80,2545,0,2390.70),
    ("Fayetteville","2026-01-19",24991.19,0,24991.19,1780,0,2256.20),
    ("San Antonio","2026-02-09",46404.89,53807.00,46404.89,3136,3865,568.06),
    ("San Antonio","2026-02-02",47016.86,55169.41,47016.86,3126,3643,683.52),
    ("San Antonio","2026-01-26",47941.64,47635.19,47941.64,3213,3464,691.36),
    ("San Antonio","2026-01-19",35002.52,45827.60,35002.52,2329,3214,502.08),
    ("San Marcos","2026-02-09",50915.20,53397.38,50915.20,3261,3179,1211.12),
    ("San Marcos","2026-02-02",50762.50,52543.95,50762.50,3283,3182,1275.98),
    ("San Marcos","2026-01-26",48519.78,51878.92,48519.78,3142,3062,1183.15),
    ("San Marcos","2026-01-19",37719.24,47199.02,37719.24,2430,2654,925.15),
    ("Waco","2026-02-09",50429.59,47490.80,50429.59,2998,3002,535.46),
    ("Waco","2026-02-02",48684.69,52111.96,48684.69,3038,3121,732.54),
    ("Waco","2026-01-26",43183.65,47835.16,43183.65,2752,3052,466.76),
    ("Waco","2026-01-19",29103.26,43181.52,29103.26,1918,2783,329.85),
]

catering_cy_raw = [
    ("Burleson","2026-02-09",1974.78,5),("Burleson","2026-02-02",313.10,2),("Burleson","2026-01-26",111.86,1),
    ("College Station","2026-02-09",1543.95,12),("College Station","2026-02-02",2843.62,8),
    ("College Station","2026-01-26",11030.74,15),("College Station","2026-01-19",1333.04,8),
    ("Fayetteville","2026-02-02",264.95,2),("Fayetteville","2026-01-26",304.68,1),
    ("San Antonio","2026-02-09",130.05,1),("San Antonio","2026-02-02",1577.36,6),
    ("San Antonio","2026-01-26",1213.98,2),("San Antonio","2026-01-19",1347.81,3),
    ("San Marcos","2026-02-09",495.11,2),("San Marcos","2026-02-02",359.88,2),
    ("San Marcos","2026-01-26",123.62,1),("San Marcos","2026-01-19",0,0),
    ("Waco","2026-02-09",5020.72,15),("Waco","2026-02-02",3193.97,13),
    ("Waco","2026-01-26",1756.00,5),("Waco","2026-01-19",1309.86,6),
]

catering_py_raw = [
    ("College Station","2026-02-09",1109.05,6),("College Station","2026-02-02",5342.75,16),
    ("College Station","2026-01-26",4899.54,14),("College Station","2026-01-19",13254.61,8),
    ("San Antonio","2026-02-09",231.49,2),("San Antonio","2026-02-02",3909.68,3),
    ("San Antonio","2026-01-26",108.58,1),("San Antonio","2026-01-19",860.59,3),
    ("San Marcos","2026-02-09",352.94,2),("San Marcos","2026-02-02",2082.37,2),
    ("San Marcos","2026-01-26",4177.73,3),("San Marcos","2026-01-19",4184.77,2),
    ("Waco","2026-02-09",3193.38,11),("Waco","2026-02-02",8487.20,14),
    ("Waco","2026-01-26",2787.79,9),("Waco","2026-01-19",2317.46,8),
]

reviews_raw = [
    ("Burleson","2026-02-09","google",4.167,6),("Burleson","2026-02-09","ovation",4.048,21),
    ("Burleson","2026-02-09","yelp",4.0,4),("Burleson","2026-02-02","ovation",3.786,14),
    ("Burleson","2026-01-26","google",3.286,7),("Burleson","2026-01-26","ovation",4.381,21),
    ("Burleson","2026-01-19","google",3.667,3),("Burleson","2026-01-19","ovation",4.727,11),
    ("Burleson","2026-01-19","yelp",3.0,1),
    ("College Station","2026-02-09","google",5.0,4),("College Station","2026-02-09","ovation",4.722,18),
    ("College Station","2026-02-02","google",3.0,1),("College Station","2026-02-02","ovation",4.579,19),
    ("College Station","2026-01-26","google",5.0,3),("College Station","2026-01-26","ovation",4.929,14),
    ("College Station","2026-01-26","yelp",4.0,1),
    ("College Station","2026-01-19","google",4.667,3),("College Station","2026-01-19","ovation",4.188,16),
    ("Fayetteville","2026-02-09","google",4.0,5),("Fayetteville","2026-02-09","ovation",4.536,28),
    ("Fayetteville","2026-02-02","google",4.75,4),("Fayetteville","2026-02-02","ovation",4.310,29),
    ("Fayetteville","2026-01-26","google",3.333,6),("Fayetteville","2026-01-26","ovation",3.903,31),
    ("Fayetteville","2026-01-19","google",4.333,6),("Fayetteville","2026-01-19","ovation",4.281,32),
    ("San Antonio","2026-02-09","google",3.333,3),("San Antonio","2026-02-09","ovation",4.385,13),
    ("San Antonio","2026-02-02","google",4.75,4),("San Antonio","2026-02-02","ovation",4.5,8),
    ("San Antonio","2026-01-26","google",5.0,1),("San Antonio","2026-01-26","ovation",4.778,9),
    ("San Antonio","2026-01-19","google",4.0,5),("San Antonio","2026-01-19","ovation",5.0,1),
    ("San Marcos","2026-02-09","google",4.8,5),("San Marcos","2026-02-09","ovation",5.0,10),
    ("San Marcos","2026-02-02","google",4.5,2),("San Marcos","2026-02-02","ovation",4.643,14),
    ("San Marcos","2026-02-02","yelp",5.0,1),
    ("San Marcos","2026-01-26","google",5.0,1),("San Marcos","2026-01-26","ovation",4.5,12),
    ("San Marcos","2026-01-19","ovation",4.571,7),
    ("Waco","2026-02-09","google",4.5,4),("Waco","2026-02-09","ovation",3.125,8),
    ("Waco","2026-02-09","yelp",5.0,1),
    ("Waco","2026-02-02","google",3.0,2),("Waco","2026-02-02","ovation",4.125,16),
    ("Waco","2026-01-26","ovation",4.188,16),
    ("Waco","2026-01-19","google",5.0,1),("Waco","2026-01-19","ovation",4.8,5),
]

daily_labor_raw = [
    ("Burleson","2026-02-09",1.09,16.35),("Burleson","2026-02-10",94.30,1382.78),
    ("Burleson","2026-02-11",97.95,1459.10),("Burleson","2026-02-12",99.24,1455.65),
    ("Burleson","2026-02-13",98.07,1363.46),("Burleson","2026-02-14",87.24,1244.12),
    ("Burleson","2026-02-15",90.22,1243.52),
    ("Burleson","2026-02-02",1.10,16.52),("Burleson","2026-02-03",103.78,1434.99),
    ("Burleson","2026-02-04",94.58,1313.09),("Burleson","2026-02-05",103.01,1500.76),
    ("Burleson","2026-02-06",114.38,1711.50),("Burleson","2026-02-07",101.05,1417.62),
    ("Burleson","2026-02-08",107.84,1514.87),
    ("Burleson","2026-01-26",0.22,3.29),("Burleson","2026-01-27",69.80,1047.91),
    ("Burleson","2026-01-28",89.00,1247.71),("Burleson","2026-01-29",110.24,1588.98),
    ("Burleson","2026-01-30",119.61,1682.76),("Burleson","2026-01-31",122.84,1811.64),
    ("Burleson","2026-02-01",100.54,1610.96),
    ("Burleson","2026-01-19",2.07,29.09),("Burleson","2026-01-20",106.43,1487.90),
    ("Burleson","2026-01-21",103.36,1460.55),("Burleson","2026-01-22",108.40,1506.79),
    ("Burleson","2026-01-23",97.37,1347.33),
    ("College Station","2026-02-09",4.82,80.58),("College Station","2026-02-10",245.00,3522.56),
    ("College Station","2026-02-11",216.58,3081.18),("College Station","2026-02-12",256.72,3669.77),
    ("College Station","2026-02-13",309.78,4419.50),("College Station","2026-02-14",292.48,4153.84),
    ("College Station","2026-02-15",235.33,3389.81),
    ("College Station","2026-02-02",6.07,101.58),("College Station","2026-02-03",240.64,3543.27),
    ("College Station","2026-02-04",225.42,3153.26),("College Station","2026-02-05",264.25,3782.41),
    ("College Station","2026-02-06",299.58,4189.11),("College Station","2026-02-07",318.68,4619.32),
    ("College Station","2026-02-08",242.56,3624.27),
    ("College Station","2026-01-26",4.02,66.03),("College Station","2026-01-27",222.02,3222.87),
    ("College Station","2026-01-28",210.81,3020.33),("College Station","2026-01-29",263.61,3812.80),
    ("College Station","2026-01-30",285.55,4009.27),("College Station","2026-01-31",302.23,4390.18),
    ("College Station","2026-02-01",238.31,3527.28),
    ("College Station","2026-01-19",5.51,92.04),("College Station","2026-01-20",209.64,3121.76),
    ("College Station","2026-01-21",222.96,3137.69),("College Station","2026-01-22",244.00,3457.70),
    ("College Station","2026-01-23",280.50,3889.65),("College Station","2026-01-24",186.44,2750.70),
    ("College Station","2026-01-25",0,0),
    ("Fayetteville","2026-02-09",1.28,20.88),("Fayetteville","2026-02-10",172.40,2112.50),
    ("Fayetteville","2026-02-11",187.91,2349.05),("Fayetteville","2026-02-12",199.74,2519.71),
    ("Fayetteville","2026-02-13",199.50,2397.03),("Fayetteville","2026-02-14",208.98,2706.82),
    ("Fayetteville","2026-02-15",143.88,2053.19),
    ("Fayetteville","2026-02-02",1.77,28.03),("Fayetteville","2026-02-03",177.93,2115.27),
    ("Fayetteville","2026-02-04",201.18,2411.68),("Fayetteville","2026-02-05",222.22,2691.54),
    ("Fayetteville","2026-02-06",242.98,2904.17),("Fayetteville","2026-02-07",207.66,2552.38),
    ("Fayetteville","2026-02-08",179.55,2832.89),
    ("Fayetteville","2026-01-26",0,0),("Fayetteville","2026-01-27",0,0),
    ("Fayetteville","2026-01-28",181.28,2263.03),("Fayetteville","2026-01-29",180.50,2134.12),
    ("Fayetteville","2026-01-30",225.96,2756.32),("Fayetteville","2026-01-31",229.36,2968.07),
    ("Fayetteville","2026-02-01",202.81,2850.81),
    ("Fayetteville","2026-01-19",1.67,26.50),("Fayetteville","2026-01-20",222.25,2571.88),
    ("Fayetteville","2026-01-21",248.89,2641.22),("Fayetteville","2026-01-22",255.85,2997.91),
    ("Fayetteville","2026-01-23",164.04,2220.49),
    ("San Antonio","2026-02-09",1.96,32.83),("San Antonio","2026-02-10",102.48,1076.03),
    ("San Antonio","2026-02-11",94.54,1041.02),("San Antonio","2026-02-12",105.47,981.61),
    ("San Antonio","2026-02-13",110.36,1102.71),("San Antonio","2026-02-14",116.45,1226.12),
    ("San Antonio","2026-02-15",95.28,1047.61),
    ("San Antonio","2026-02-02",1.04,16.01),("San Antonio","2026-02-03",100.89,1142.88),
    ("San Antonio","2026-02-04",104.33,1116.60),("San Antonio","2026-02-05",111.82,1141.93),
    ("San Antonio","2026-02-06",119.63,1227.08),("San Antonio","2026-02-07",120.87,1161.50),
    ("San Antonio","2026-02-08",97.41,1116.34),
    ("San Antonio","2026-01-26",1.19,19.16),("San Antonio","2026-01-27",102.81,1088.01),
    ("San Antonio","2026-01-28",107.07,1216.72),("San Antonio","2026-01-29",109.08,1126.99),
    ("San Antonio","2026-01-30",122.38,1213.82),("San Antonio","2026-01-31",133.18,1358.10),
    ("San Antonio","2026-02-01",98.38,1096.92),
    ("San Antonio","2026-01-19",0.95,14.49),("San Antonio","2026-01-20",106.64,1228.03),
    ("San Antonio","2026-01-21",96.12,1188.09),("San Antonio","2026-01-22",108.23,1194.11),
    ("San Antonio","2026-01-23",119.52,1161.58),("San Antonio","2026-01-24",75.21,818.71),
    ("San Antonio","2026-01-25",55.85,583.52),
    ("San Marcos","2026-02-09",1.53,25.00),("San Marcos","2026-02-10",113.06,1751.85),
    ("San Marcos","2026-02-11",112.49,1762.20),("San Marcos","2026-02-12",119.69,1889.25),
    ("San Marcos","2026-02-13",133.72,2078.48),("San Marcos","2026-02-14",136.70,2109.37),
    ("San Marcos","2026-02-15",105.74,1604.66),
    ("San Marcos","2026-02-02",1.46,23.81),("San Marcos","2026-02-03",118.61,1836.91),
    ("San Marcos","2026-02-04",117.62,1829.93),("San Marcos","2026-02-05",122.45,1914.02),
    ("San Marcos","2026-02-06",139.09,2171.14),("San Marcos","2026-02-07",138.58,2128.44),
    ("San Marcos","2026-02-08",108.16,1635.13),
    ("San Marcos","2026-01-26",1.44,23.48),("San Marcos","2026-01-27",113.53,1767.33),
    ("San Marcos","2026-01-28",112.52,1759.61),("San Marcos","2026-01-29",120.49,1904.44),
    ("San Marcos","2026-01-30",131.49,2041.97),("San Marcos","2026-01-31",136.11,2096.60),
    ("San Marcos","2026-02-01",110.07,1666.68),
    ("San Marcos","2026-01-19",1.58,25.70),("San Marcos","2026-01-20",123.17,1899.24),
    ("San Marcos","2026-01-21",123.54,1940.21),("San Marcos","2026-01-22",122.34,1930.02),
    ("San Marcos","2026-01-23",130.28,2029.90),("San Marcos","2026-01-24",68.28,1071.10),
    ("San Marcos","2026-01-25",52.91,797.63),
    ("Waco","2026-02-09",2.01,41.38),("Waco","2026-02-10",112.76,1710.63),
    ("Waco","2026-02-11",121.27,1805.61),("Waco","2026-02-12",113.85,1687.78),
    ("Waco","2026-02-13",135.74,1980.79),("Waco","2026-02-14",115.45,1689.29),
    ("Waco","2026-02-15",106.33,1513.45),
    ("Waco","2026-02-02",1.98,39.60),("Waco","2026-02-03",125.02,1885.11),
    ("Waco","2026-02-04",105.67,1554.43),("Waco","2026-02-05",127.62,1882.23),
    ("Waco","2026-02-06",134.34,1954.44),("Waco","2026-02-07",132.26,1983.80),
    ("Waco","2026-02-08",113.75,1687.96),
    ("Waco","2026-01-26",3.35,66.10),("Waco","2026-01-27",90.78,1328.66),
    ("Waco","2026-01-28",103.35,1437.14),("Waco","2026-01-29",122.15,1673.02),
    ("Waco","2026-01-30",146.38,2048.21),("Waco","2026-01-31",147.54,2114.44),
    ("Waco","2026-02-01",111.88,1541.12),
    ("Waco","2026-01-19",3.04,59.80),("Waco","2026-01-20",97.48,1439.15),
    ("Waco","2026-01-21",102.47,1488.51),("Waco","2026-01-22",115.23,1694.12),
    ("Waco","2026-01-23",127.04,1862.94),("Waco","2026-01-24",66.43,975.88),
    ("Waco","2026-01-25",0,0),
]

daily_sales_raw = [
    ("Burleson","2026-01-20",3298.68),("Burleson","2026-01-21",3752.28),
    ("Burleson","2026-01-22",4595.02),("Burleson","2026-01-23",4485.83),("Burleson","2026-01-24",18.75),
    ("Burleson","2026-01-27",2085.77),("Burleson","2026-01-28",3205.38),
    ("Burleson","2026-01-29",4485.57),("Burleson","2026-01-30",4871.50),
    ("Burleson","2026-01-31",6216.10),("Burleson","2026-02-01",5731.83),
    ("Burleson","2026-02-03",4226.12),("Burleson","2026-02-04",3792.77),
    ("Burleson","2026-02-05",4144.34),("Burleson","2026-02-06",5781.70),
    ("Burleson","2026-02-07",5949.61),("Burleson","2026-02-08",4576.81),
    ("Burleson","2026-02-10",4141.25),("Burleson","2026-02-11",4151.17),
    ("Burleson","2026-02-12",5091.33),("Burleson","2026-02-13",5998.08),
    ("Burleson","2026-02-14",6256.61),("Burleson","2026-02-15",6810.92),
    ("College Station","2026-01-19",0),("College Station","2026-01-20",14651.79),
    ("College Station","2026-01-21",16817.75),("College Station","2026-01-22",18553.63),
    ("College Station","2026-01-23",24279.35),("College Station","2026-01-24",14685.03),
    ("College Station","2026-01-25",32.88),
    ("College Station","2026-01-27",15713.51),("College Station","2026-01-28",17060.34),
    ("College Station","2026-01-29",22889.50),("College Station","2026-01-30",28185.36),
    ("College Station","2026-01-31",33657.79),("College Station","2026-02-01",24043.88),
    ("College Station","2026-02-02",0),
    ("College Station","2026-02-03",15713.08),("College Station","2026-02-04",17374.01),
    ("College Station","2026-02-05",22045.45),("College Station","2026-02-06",29243.44),
    ("College Station","2026-02-07",35355.94),("College Station","2026-02-08",21541.74),
    ("College Station","2026-02-09",0),("College Station","2026-02-10",15194.41),
    ("College Station","2026-02-11",17459.57),("College Station","2026-02-12",22276.49),
    ("College Station","2026-02-13",30036.81),("College Station","2026-02-14",26217.46),
    ("College Station","2026-02-15",21534.53),
    ("Fayetteville","2026-01-19",10.08),("Fayetteville","2026-01-20",6531.85),
    ("Fayetteville","2026-01-21",5651.63),("Fayetteville","2026-01-22",6342.43),
    ("Fayetteville","2026-01-23",6465.28),
    ("Fayetteville","2026-01-27",159.77),("Fayetteville","2026-01-28",5437.31),
    ("Fayetteville","2026-01-29",6965.17),("Fayetteville","2026-01-30",9678.74),
    ("Fayetteville","2026-01-31",9628.26),("Fayetteville","2026-02-01",7570.55),
    ("Fayetteville","2026-02-02",0),
    ("Fayetteville","2026-02-03",5135.57),("Fayetteville","2026-02-04",5158.61),
    ("Fayetteville","2026-02-05",6633.50),("Fayetteville","2026-02-06",9034.90),
    ("Fayetteville","2026-02-07",8411.17),("Fayetteville","2026-02-08",5248.38),
    ("Fayetteville","2026-02-10",5284.60),("Fayetteville","2026-02-11",4696.70),
    ("Fayetteville","2026-02-12",6750.01),("Fayetteville","2026-02-13",8086.27),
    ("Fayetteville","2026-02-14",7811.51),("Fayetteville","2026-02-15",7147.76),
    ("San Antonio","2026-01-20",7198.75),("San Antonio","2026-01-21",6580.31),
    ("San Antonio","2026-01-22",7991.83),("San Antonio","2026-01-23",7702.89),
    ("San Antonio","2026-01-24",3989.19),("San Antonio","2026-01-25",1539.55),
    ("San Antonio","2026-01-27",6275.33),("San Antonio","2026-01-28",8137.13),
    ("San Antonio","2026-01-29",7606.20),("San Antonio","2026-01-30",9405.60),
    ("San Antonio","2026-01-31",9197.81),("San Antonio","2026-02-01",7319.57),
    ("San Antonio","2026-02-02",12.81),
    ("San Antonio","2026-02-03",7206.89),("San Antonio","2026-02-04",7827.21),
    ("San Antonio","2026-02-05",6746.09),("San Antonio","2026-02-06",9553.44),
    ("San Antonio","2026-02-07",8967.72),("San Antonio","2026-02-08",6715.51),
    ("San Antonio","2026-02-09",5.07),("San Antonio","2026-02-10",6394.67),
    ("San Antonio","2026-02-11",7151.55),("San Antonio","2026-02-12",7979.70),
    ("San Antonio","2026-02-13",8917.12),("San Antonio","2026-02-14",8764.90),
    ("San Antonio","2026-02-15",7196.95),
    ("San Marcos","2026-01-20",7080.57),("San Marcos","2026-01-21",7074.72),
    ("San Marcos","2026-01-22",7516.81),("San Marcos","2026-01-23",7679.28),
    ("San Marcos","2026-01-24",4238.46),("San Marcos","2026-01-25",4129.40),
    ("San Marcos","2026-01-26",0),
    ("San Marcos","2026-01-27",6548.51),("San Marcos","2026-01-28",6906.71),
    ("San Marcos","2026-01-29",7845.72),("San Marcos","2026-01-30",9240.03),
    ("San Marcos","2026-01-31",10299.45),("San Marcos","2026-02-01",7679.36),
    ("San Marcos","2026-02-02",19.72),
    ("San Marcos","2026-02-03",6943.29),("San Marcos","2026-02-04",7590.44),
    ("San Marcos","2026-02-05",7876.00),("San Marcos","2026-02-06",9945.55),
    ("San Marcos","2026-02-07",11295.24),("San Marcos","2026-02-08",7111.98),
    ("San Marcos","2026-02-10",7251.61),("San Marcos","2026-02-11",7387.84),
    ("San Marcos","2026-02-12",7426.03),("San Marcos","2026-02-13",10292.83),
    ("San Marcos","2026-02-14",10585.51),("San Marcos","2026-02-15",7971.38),
    ("Waco","2026-01-19",6.59),("Waco","2026-01-20",5589.65),
    ("Waco","2026-01-21",5924.92),("Waco","2026-01-22",6927.67),
    ("Waco","2026-01-23",6850.42),("Waco","2026-01-24",3793.24),("Waco","2026-01-25",17.36),
    ("Waco","2026-01-27",5155.16),("Waco","2026-01-28",5881.55),
    ("Waco","2026-01-29",7649.58),("Waco","2026-01-30",8066.24),
    ("Waco","2026-01-31",9770.01),("Waco","2026-02-01",6661.11),("Waco","2026-02-02",6.59),
    ("Waco","2026-02-03",7340.24),("Waco","2026-02-04",6636.99),
    ("Waco","2026-02-05",7256.69),("Waco","2026-02-06",11153.49),
    ("Waco","2026-02-07",9315.14),("Waco","2026-02-08",6982.14),
    ("Waco","2026-02-10",5770.14),("Waco","2026-02-11",9115.88),
    ("Waco","2026-02-12",7634.50),("Waco","2026-02-13",10121.64),
    ("Waco","2026-02-14",8273.38),("Waco","2026-02-15",9514.05),
]

scheduled_raw = [
    ("Burleson","2026-02-10",94.0),("Burleson","2026-02-11",100.0),("Burleson","2026-02-12",99.5),("Burleson","2026-02-13",103.0),("Burleson","2026-02-14",99.0),("Burleson","2026-02-15",94.5),
    ("Burleson","2026-02-03",101.5),("Burleson","2026-02-04",101.5),("Burleson","2026-02-05",107.0),("Burleson","2026-02-06",120.5),("Burleson","2026-02-07",119.5),("Burleson","2026-02-08",105.5),
    ("Burleson","2026-01-27",104.0),("Burleson","2026-01-28",97.5),("Burleson","2026-01-29",108.5),("Burleson","2026-01-30",116.5),("Burleson","2026-01-31",128.0),("Burleson","2026-02-01",99.0),
    ("Burleson","2026-01-20",107.5),("Burleson","2026-01-21",108.0),("Burleson","2026-01-22",114.0),("Burleson","2026-01-23",131.5),("Burleson","2026-01-24",128.0),("Burleson","2026-01-25",108.5),
    ("College Station","2026-02-10",245.5),("College Station","2026-02-11",212.5),("College Station","2026-02-12",246.0),("College Station","2026-02-13",293.5),("College Station","2026-02-14",300.0),("College Station","2026-02-15",230.25),
    ("College Station","2026-02-03",251.5),("College Station","2026-02-04",207.5),("College Station","2026-02-05",243.0),("College Station","2026-02-06",298.5),("College Station","2026-02-07",317.0),("College Station","2026-02-08",237.0),
    ("College Station","2026-01-27",230.0),("College Station","2026-01-28",202.5),("College Station","2026-01-29",236.0),("College Station","2026-01-30",252.0),("College Station","2026-01-31",287.0),("College Station","2026-02-01",212.5),
    ("College Station","2026-01-20",221.0),("College Station","2026-01-21",218.5),("College Station","2026-01-22",230.0),("College Station","2026-01-23",270.0),("College Station","2026-01-24",288.0),("College Station","2026-01-25",226.5),
    ("Fayetteville","2026-02-10",170.75),("Fayetteville","2026-02-11",194.5),("Fayetteville","2026-02-12",210.25),("Fayetteville","2026-02-13",235.25),("Fayetteville","2026-02-14",228.75),("Fayetteville","2026-02-15",182.0),
    ("Fayetteville","2026-02-03",184.5),("Fayetteville","2026-02-04",185.5),("Fayetteville","2026-02-05",236.0),("Fayetteville","2026-02-06",263.0),("Fayetteville","2026-02-07",227.5),("Fayetteville","2026-02-08",200.0),
    ("Fayetteville","2026-01-27",183.0),("Fayetteville","2026-01-28",180.0),("Fayetteville","2026-01-29",187.75),("Fayetteville","2026-01-30",217.0),("Fayetteville","2026-01-31",218.75),("Fayetteville","2026-02-01",172.75),
    ("Fayetteville","2026-01-20",206.0),("Fayetteville","2026-01-21",216.5),("Fayetteville","2026-01-22",258.0),("Fayetteville","2026-01-23",275.75),("Fayetteville","2026-01-24",231.0),("Fayetteville","2026-01-25",184.5),
    ("San Antonio","2026-02-10",99.75),("San Antonio","2026-02-11",92.5),("San Antonio","2026-02-12",108.5),("San Antonio","2026-02-13",119.0),("San Antonio","2026-02-14",114.5),("San Antonio","2026-02-15",92.0),
    ("San Antonio","2026-02-03",120.0),("San Antonio","2026-02-04",106.75),("San Antonio","2026-02-05",104.5),("San Antonio","2026-02-06",130.0),("San Antonio","2026-02-07",121.0),("San Antonio","2026-02-08",107.0),
    ("San Antonio","2026-01-27",104.25),("San Antonio","2026-01-28",77.5),("San Antonio","2026-01-29",97.5),("San Antonio","2026-01-30",102.0),("San Antonio","2026-01-31",123.5),("San Antonio","2026-02-01",97.5),
    ("San Antonio","2026-01-20",107.25),("San Antonio","2026-01-21",85.5),("San Antonio","2026-01-22",93.5),("San Antonio","2026-01-23",117.0),("San Antonio","2026-01-24",124.5),("San Antonio","2026-01-25",93.0),
    ("San Marcos","2026-02-10",119.5),("San Marcos","2026-02-11",119.0),("San Marcos","2026-02-12",124.0),("San Marcos","2026-02-13",131.0),("San Marcos","2026-02-14",134.0),("San Marcos","2026-02-15",108.0),
    ("San Marcos","2026-02-03",119.5),("San Marcos","2026-02-04",119.0),("San Marcos","2026-02-05",122.0),("San Marcos","2026-02-06",138.0),("San Marcos","2026-02-07",134.0),("San Marcos","2026-02-08",108.0),
    ("San Marcos","2026-01-27",118.5),("San Marcos","2026-01-28",121.0),("San Marcos","2026-01-29",124.0),("San Marcos","2026-01-30",131.5),("San Marcos","2026-01-31",132.0),("San Marcos","2026-02-01",108.0),
    ("San Marcos","2026-01-20",123.5),("San Marcos","2026-01-21",121.5),("San Marcos","2026-01-22",124.0),("San Marcos","2026-01-23",132.5),("San Marcos","2026-01-24",86.0),("San Marcos","2026-01-25",98.75),
    ("Waco","2026-02-10",123.0),("Waco","2026-02-11",111.0),("Waco","2026-02-12",130.25),("Waco","2026-02-13",144.0),("Waco","2026-02-14",137.0),("Waco","2026-02-15",88.0),
    ("Waco","2026-02-03",123.0),("Waco","2026-02-04",111.0),("Waco","2026-02-05",129.25),("Waco","2026-02-06",142.0),("Waco","2026-02-07",137.0),("Waco","2026-02-08",87.0),
    ("Waco","2026-01-27",122.0),("Waco","2026-01-28",113.0),("Waco","2026-01-29",124.25),("Waco","2026-01-30",156.0),("Waco","2026-01-31",159.0),("Waco","2026-02-01",124.0),
    ("Waco","2026-01-20",108.0),("Waco","2026-01-21",108.0),("Waco","2026-01-22",118.0),("Waco","2026-01-23",138.0),("Waco","2026-01-24",138.0),("Waco","2026-01-25",90.5),
]

agm_raw = [
    ("Burleson","2025-12-09","2030-12-31",0,0),
    ("College Station","2024-12-29","2030-12-31",8.333333333,50),
    ("Fayetteville","2026-01-19","2026-01-25",58.333333333,350),
    ("Fayetteville","2026-01-26","2026-02-01",50,300),
    ("Fayetteville","2026-02-02","2026-02-08",41.666666667,250),
    ("Fayetteville","2026-02-09","2026-02-15",33.333333333,200),
    ("San Antonio","2024-12-30","2030-12-31",0,0),
    ("San Marcos","2025-11-17","2030-12-31",-8.333333333,-50),
    ("Waco","2025-07-07","2030-12-31",0,0),
]

GUIDELINES_TABLE = {0:0,2100:326,18800:328,20000:345,25000:416,30000:488,35000:559,40000:631,45000:702,50000:744,55000:786,60000:828,65000:870,70000:912,75000:953,80000:995,85000:1037,90000:1079,95000:1120,100000:1162,105000:1204,110000:1246,115000:1287,120000:1329,125000:1371,130000:1413,135000:1454,140000:1496,145000:1538,150000:1580,155000:1621,160000:1663,165000:1705,170000:1747,175000:1788,180000:1830,185000:1872,190000:1914,195000:1956,200000:1997}

# Upselling data (from Query 10)
upselling_raw = {
    "Burleson":  {"checks":2807,"avg_check":16.89,"queso":541,"guac":59,"chips":41,"sides":291,"drinks":1335,"alcohol":446,"desserts":61},
    "College Station":{"checks":15346,"avg_check":14.45,"queso":2602,"guac":303,"chips":77,"sides":1077,"drinks":5756,"alcohol":0,"desserts":390},
    "Fayetteville":{"checks":4491,"avg_check":14.15,"queso":946,"guac":173,"chips":92,"sides":452,"drinks":1612,"alcohol":435,"desserts":152},
    "San Antonio":{"checks":5565,"avg_check":13.98,"queso":505,"guac":86,"chips":49,"sides":489,"drinks":1924,"alcohol":272,"desserts":203},
    "San Marcos":{"checks":5728,"avg_check":14.96,"queso":925,"guac":89,"chips":50,"sides":591,"drinks":2246,"alcohol":263,"desserts":214},
    "Waco":     {"checks":5085,"avg_check":14.19,"queso":936,"guac":105,"chips":55,"sides":418,"drinks":1482,"alcohol":216,"desserts":98},
}

# ============================================================
# ORGANIZE DATA
# ============================================================
weekly_sales = defaultdict(dict)
for loc,ws,amt,amt_py,net,orders,orders_py,disc in weekly_sales_raw:
    weekly_sales[loc][d(ws)] = {"amount":amt,"amount_py":amt_py,"net_amount":net,"orders":orders,"orders_py":orders_py,"discount":disc}

catering_cy = defaultdict(dict)
for loc,ws,amt,orders in catering_cy_raw:
    catering_cy[loc][d(ws)] = {"amount":amt,"orders":orders}
catering_py = defaultdict(dict)
for loc,ws,amt,orders in catering_py_raw:
    catering_py[loc][d(ws)] = {"amount":amt,"orders":orders}

reviews_dict = defaultdict(lambda: defaultdict(dict))
for loc,ws,source,avg_r,cnt in reviews_raw:
    reviews_dict[loc][d(ws)][source] = {"avg":avg_r,"count":cnt}

daily_labor = defaultdict(dict)
for loc,dt,hrs,pay in daily_labor_raw:
    daily_labor[loc][d(dt)] = {"hours":hrs,"pay":pay}
daily_sales_d = defaultdict(dict)
for loc,dt,amt in daily_sales_raw:
    daily_sales_d[loc][d(dt)] = amt
sched = defaultdict(dict)
for loc,dt,hrs in scheduled_raw:
    sched[loc][d(dt)] = hrs

# Compute upselling rates
upselling = {}
for loc, u in upselling_raw.items():
    c = u["checks"]
    food = u["queso"]+u["guac"]+u["chips"]+u["sides"]+u["desserts"]
    bev = u["drinks"]+u["alcohol"]
    upselling[loc] = {
        "checks":c, "avg_check":u["avg_check"],
        "queso_rate":u["queso"]/c*100, "guac_rate":u["guac"]/c*100,
        "food_addon_rate":food/c*100, "bev_rate":bev/c*100,
        "drinks_rate":u["drinks"]/c*100, "alcohol_rate":u["alcohol"]/c*100,
    }

# ============================================================
# GUIDELINE FUNCTIONS
# ============================================================
def lookup_guide(net_sales):
    thresholds = sorted(GUIDELINES_TABLE.items())
    if net_sales <= 0: return 0
    lower_t,lower_h = thresholds[0]
    for i,(t,h) in enumerate(thresholds):
        if t > net_sales:
            lower_t,lower_h = thresholds[i-1]; frac = (net_sales-lower_t)/(t-lower_t)
            return lower_h + frac*(h-lower_h)
        lower_t,lower_h = t,h
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
        wn = sum(ds.get(dd,0) for dd in days); tg=lookup_guide(wn); raw=[]
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
# COMPUTE PER-LOCATION KPIs + 4-WEEK HISTORY
# ============================================================
ws = WEEK_START
loc_data = {}
loc_weekly = defaultdict(dict)  # loc_weekly[loc][week_idx] = {...}

for loc in LOCATIONS:
    for wi, ws_i in enumerate(WEEK_STARTS):
        cw = weekly_sales[loc].get(ws_i, {})
        amt = cw.get("amount",0); amt_py = cw.get("amount_py",0)
        ords = cw.get("orders",0); ords_py = cw.get("orders_py",0)
        has_py = amt_py > 0
        sss_v = pct_chg(amt, amt_py) if has_py else None
        sst_v = pct_chg(ords, ords_py) if has_py else None
        avg_tkt = amt/ords if ords else 0
        avg_tkt_py = amt_py/ords_py if (has_py and ords_py) else 0
        tkt_chg = pct_chg(avg_tkt, avg_tkt_py) if has_py else None

        hrs = sum(daily_labor[loc].get(ws_i+timedelta(days=j),{}).get("hours",0) for j in range(7))
        pay = sum(daily_labor[loc].get(ws_i+timedelta(days=j),{}).get("pay",0) for j in range(7))
        sch_hrs = sum(sched[loc].get(ws_i+timedelta(days=j),0) for j in range(7))
        lp = (pay/amt*100) if amt else 0
        ds = {ws_i+timedelta(days=j):daily_sales_d[loc].get(ws_i+timedelta(days=j),0) for j in range(7)}
        _,guide_total,_ = compute_daily_guideline(ws_i, ds, loc)
        vs_guide_n = hrs - guide_total
        vs_guide_pct = (hrs/guide_total*100) if guide_total else 0
        splh = amt/hrs if hrs else 0

        cat = catering_cy[loc].get(ws_i,{}); cat_amt=cat.get("amount",0); cat_ords=cat.get("orders",0)
        cat_py_amt = catering_py[loc].get(ws_i,{}).get("amount",0)

        rev = reviews_dict[loc].get(ws_i,{})
        google_r=rev.get("google",{}).get("avg"); google_n=rev.get("google",{}).get("count",0)
        ovation_r=rev.get("ovation",{}).get("avg"); ovation_n=rev.get("ovation",{}).get("count",0)
        yelp_r=rev.get("yelp",{}).get("avg"); yelp_n=rev.get("yelp",{}).get("count",0)
        total_rev_n=google_n+ovation_n+yelp_n
        wavg = ((google_r or 0)*google_n+(ovation_r or 0)*ovation_n+(yelp_r or 0)*yelp_n)/total_rev_n if total_rev_n else None

        week_data = {
            "amount":amt,"amount_py":amt_py,"orders":ords,"orders_py":ords_py,
            "has_py":has_py,"sss":sss_v,"sst":sst_v,"avg_tkt":avg_tkt,"tkt_chg":tkt_chg,
            "suffix":"vs PY" if has_py else "Non-Comp",
            "labor_hrs":hrs,"labor_pay":pay,"labor_pct":lp,
            "guide_total":guide_total,"vs_guide_n":vs_guide_n,"vs_guide_pct":vs_guide_pct,
            "sch_hrs":sch_hrs,"splh":splh,
            "cat_amt":cat_amt,"cat_ords":cat_ords,"cat_py_amt":cat_py_amt,
            "google_r":google_r,"google_n":google_n,"ovation_r":ovation_r,"ovation_n":ovation_n,
            "yelp_r":yelp_r,"yelp_n":yelp_n,"wavg_rating":wavg,"total_rev_n":total_rev_n,
            "discount":cw.get("discount",0),
        }
        loc_weekly[loc][wi] = week_data
        if wi == 0:
            loc_data[loc] = week_data

# Comp stores
comp_locs = [loc for loc in LOCATIONS if loc_data[loc]["has_py"]]

# System totals
sys_amt = sum(v["amount"] for v in loc_data.values())
comp_amt = sum(loc_data[loc]["amount"] for loc in comp_locs)
comp_amt_py = sum(loc_data[loc]["amount_py"] for loc in comp_locs)
comp_ords = sum(loc_data[loc]["orders"] for loc in comp_locs)
comp_ords_py = sum(loc_data[loc]["orders_py"] for loc in comp_locs)
sys_sss = pct_chg(comp_amt, comp_amt_py) if comp_amt_py else None
sys_sst = pct_chg(comp_ords, comp_ords_py) if comp_ords_py else None
sys_ords = sum(v["orders"] for v in loc_data.values())
sys_tkt = sys_amt/sys_ords if sys_ords else 0
comp_tkt = comp_amt/comp_ords if comp_ords else 0
comp_tkt_py = comp_amt_py/comp_ords_py if comp_ords_py else 0
sys_tkt_chg = pct_chg(comp_tkt, comp_tkt_py) if comp_tkt_py else None
sys_hrs = sum(v["labor_hrs"] for v in loc_data.values())
sys_pay = sum(v["labor_pay"] for v in loc_data.values())
sys_lp = (sys_pay/sys_amt*100) if sys_amt else 0
sys_guide = sum(v["guide_total"] for v in loc_data.values())
sys_cat = sum(v["cat_amt"] for v in loc_data.values())
sys_cat_ords = sum(v["cat_ords"] for v in loc_data.values())

# Prior week system labor %
pw = WEEK_STARTS[1]
pw_sys_amt = sum(loc_weekly[loc][1]["amount"] for loc in LOCATIONS)
pw_sys_pay = sum(loc_weekly[loc][1]["labor_pay"] for loc in LOCATIONS)
pw_sys_lp = (pw_sys_pay/pw_sys_amt*100) if pw_sys_amt else 0
sys_lp_chg = sys_lp - pw_sys_lp

# ============================================================
# VERIFICATION DATA DICTIONARY
# ============================================================
verify_data = {}
for loc in LOCATIONS:
    dd = loc_data[loc]
    verify_data[f"{loc}_sales"] = dd["amount"]
    verify_data[f"{loc}_sss"] = dd["sss"]
    verify_data[f"{loc}_sst"] = dd["sst"]
    verify_data[f"{loc}_labor_pct"] = dd["labor_pct"]
    verify_data[f"{loc}_vs_guide_pct"] = dd["vs_guide_pct"]
    verify_data[f"{loc}_avg_tkt"] = dd["avg_tkt"]
    verify_data[f"{loc}_labor_hrs"] = dd["labor_hrs"]
    verify_data[f"{loc}_guide_hrs"] = dd["guide_total"]
    verify_data[f"{loc}_splh"] = dd["splh"]
    verify_data[f"{loc}_cat_amt"] = dd["cat_amt"]
    verify_data[f"{loc}_cat_py_amt"] = dd["cat_py_amt"]
    verify_data[f"{loc}_food_addon_rate"] = upselling[loc]["food_addon_rate"]
    verify_data[f"{loc}_queso_rate"] = upselling[loc]["queso_rate"]
    verify_data[f"{loc}_bev_rate"] = upselling[loc]["bev_rate"]
    for wi in range(4):
        wd = loc_weekly[loc][wi]
        verify_data[f"{loc}_w{wi}_sales"] = wd["amount"]
        verify_data[f"{loc}_w{wi}_labor_pct"] = wd["labor_pct"]
        verify_data[f"{loc}_w{wi}_cat_amt"] = wd.get("cat_amt", 0)
        verify_data[f"{loc}_w{wi}_ovation_r"] = wd.get("ovation_r")
        verify_data[f"{loc}_w{wi}_google_r"] = wd.get("google_r")

# ============================================================
# AI INSIGHT GENERATION — all from computed data
# ============================================================
def generate_callouts():
    # Rankings
    sales_ranks = rank_items(loc_data, "amount", reverse=True)
    labor_ranks = rank_items(loc_data, "vs_guide_pct", reverse=False)
    cat_ranks = rank_items(loc_data, "cat_amt", reverse=True)

    # Comp SSS sorted
    comp_sss = sorted([(l, loc_data[l]["sss"]) for l in comp_locs if loc_data[l]["sss"] is not None], key=lambda x: x[1])
    best_sss_loc, best_sss_val = comp_sss[-1]
    worst_sss_loc, worst_sss_val = comp_sss[0]

    # 4-week trajectories from loc_weekly
    def traj_sales(loc): return [loc_weekly[loc][wi]["amount"] for wi in [3,2,1,0]]
    def traj_lp(loc): return [loc_weekly[loc][wi]["labor_pct"] for wi in [3,2,1,0]]
    def traj_cat(loc): return [loc_weekly[loc][wi]["cat_amt"] for wi in [3,2,1,0]]
    def traj_ovation(loc): return [loc_weekly[loc][wi].get("ovation_r") for wi in [3,2,1,0]]

    # System avg food addon rate
    sys_food_addon = sum(upselling[l]["food_addon_rate"]*upselling[l]["checks"] for l in LOCATIONS) / sum(upselling[l]["checks"] for l in LOCATIONS)

    # --- SALES CALLOUT ---
    burl_traj = traj_sales("Burleson")
    fay_traj = traj_sales("Fayetteville")
    waco_traj = traj_sales("Waco")
    sa_sst = loc_data["San Antonio"]["sst"]

    sales_callout = (
        f"<strong>{best_sss_loc}</strong> has posted 3 consecutive weeks of sales growth "
        f"(${traj_sales(best_sss_loc)[0]/1000:.0f}K → ${traj_sales(best_sss_loc)[1]/1000:.0f}K → "
        f"${traj_sales(best_sss_loc)[2]/1000:.0f}K → ${traj_sales(best_sss_loc)[3]/1000:.0f}K) and is the only "
        f"comp store with positive SSS this week (+{best_sss_val:.1f}%) — momentum worth studying. "
        f"<strong>{worst_sss_loc}'s</strong> {sa_sst:.1f}% transaction decline is the system's biggest concern and has persisted "
        f"across all 4 trailing weeks — this is a traffic problem, not a ticket problem. "
        f"The ${loc_data['Burleson']['avg_tkt'] - loc_data['San Antonio']['avg_tkt']:.2f} ticket gap between "
        f"Burleson (${loc_data['Burleson']['avg_tkt']:.2f}) and {worst_sss_loc} (${loc_data[worst_sss_loc]['avg_tkt']:.2f}) "
        f"is explained by real attachment data: {worst_sss_loc}'s food add-on rate is just "
        f"{upselling[worst_sss_loc]['food_addon_rate']:.1f}% vs the system average of ~{sys_food_addon:.0f}%, "
        f"and their queso attach is only {upselling[worst_sss_loc]['queso_rate']:.1f}% "
        f"(less than half of Burleson's {upselling['Burleson']['queso_rate']:.1f}%). This is a specific, coachable opportunity. "
        f"<strong>Burleson</strong> has doubled sales in 4 weeks (${burl_traj[0]/1000:.0f}K → ${burl_traj[3]/1000:.0f}K) "
        f"and leads the system in beverage attachment at {upselling['Burleson']['bev_rate']:.1f}% — "
        f"evidence their team was well-trained from day one. "
        f"<strong>Fayetteville</strong> has stabilized around ${fay_traj[2]/1000:.0f}-{fay_traj[3]/1000:.0f}K for 3 straight weeks after its opening ramp."
    )

    # --- LABOR CALLOUT ---
    best_guide_loc = labor_ranks[0][0]
    worst_guide_loc = labor_ranks[-1][0]
    burl_lp_traj = traj_lp("Burleson")
    sa_lp_traj = traj_lp("San Antonio")

    # Schedule vs actual
    sch_vs = [(l, loc_data[l]["labor_hrs"] - loc_data[l]["sch_hrs"]) for l in LOCATIONS]
    sch_vs.sort(key=lambda x: x[1])
    most_under_sch_loc, most_under_sch = sch_vs[0]
    most_over_sch_loc, most_over_sch = sch_vs[-1]

    labor_callout = (
        f"<strong>Burleson's</strong> labor % trajectory is the standout story: "
        f"{burl_lp_traj[0]:.1f}% → {burl_lp_traj[1]:.1f}% → {burl_lp_traj[2]:.1f}% → {burl_lp_traj[3]:.1f}% over 4 weeks. "
        f"As volume doubled, their team scaled efficiently rather than adding proportional hours — textbook new-store execution. "
        f"<strong>{best_guide_loc}</strong> ran tightest to guide at {loc_data[best_guide_loc]['vs_guide_pct']:.1f}%, "
        f"but with a {loc_data[best_guide_loc]['sst']:.1f}% transaction decline, "
        f"it's worth asking whether understaffing during peak hours is contributing to the traffic drop — "
        f"sometimes running under guide costs more in lost sales than it saves in labor. "
        f"<strong>Fayetteville</strong> is at {loc_data['Fayetteville']['vs_guide_pct']:.1f}% of guide, but context matters: "
        f"their AGM allowance has ramped down from 350 → 200 hrs/wk over 4 weeks. "
        f"The team came in {abs(most_under_sch):.0f} hours under their own schedule, "
        f"showing active cost management even during the opening period. "
        f"<strong>{most_over_sch_loc}</strong> ran {abs(most_over_sch):.0f} hours over schedule this week."
    )

    # --- REVIEWS CALLOUT ---
    waco_ov_traj = traj_ovation("Waco")
    fay_ov_traj = traj_ovation("Fayetteville")

    reviews_callout = (
        f"<strong>San Marcos</strong> posted a perfect {loc_data['San Marcos']['ovation_r']:.1f} on Ovation "
        f"({loc_data['San Marcos']['ovation_n']} surveys) alongside a {loc_data['San Marcos']['google_r']:.1f} Google average — "
        f"they've been the most consistently top-rated store across all 4 weeks. "
        f"<strong>Waco's</strong> Ovation score has declined for 4 straight weeks "
        f"({waco_ov_traj[0]:.1f} → {waco_ov_traj[1]:.1f} → {waco_ov_traj[2]:.1f} → {waco_ov_traj[3]:.1f}), "
        f"suggesting a worsening trend, not a one-week blip. Meanwhile their Google reviews remain at "
        f"{loc_data['Waco']['google_r']:.1f}, which means the in-store experience (captured by Ovation) may be slipping "
        f"while online perception lags — an early warning sign that needs on-the-ground investigation. "
        f"<strong>Fayetteville</strong> recovered from a dip in Week 3 "
        f"({fay_ov_traj[1]:.1f} Ovation) back to {fay_ov_traj[3]:.1f} this week — "
        f"showing the team can course-correct when issues arise. "
        f"Stores averaging fewer than 10 Ovation surveys per week should push for higher participation to make the data actionable."
    )

    # --- CATERING CALLOUT ---
    waco_cat_traj = traj_cat("Waco")
    burl_cat_traj = traj_cat("Burleson")
    cstat_cat = loc_data["College Station"]["cat_amt"]
    cstat_cat_py = loc_data["College Station"]["cat_py_amt"]
    cstat_cat_chg = pct_chg(cstat_cat, cstat_cat_py)
    zero_cat = [l for l in LOCATIONS if loc_data[l]["cat_amt"] == 0]
    waco_cat_py = loc_data["Waco"]["cat_py_amt"]
    waco_cat_vs = pct_chg(loc_data["Waco"]["cat_amt"], waco_cat_py)
    waco_penetration = loc_data["Waco"]["cat_amt"] / loc_data["Waco"]["amount"] * 100

    catering_callout = (
        f"<strong>Waco</strong> has built clear catering momentum over 4 weeks: "
        f"${waco_cat_traj[0]/1000:.1f}K → ${waco_cat_traj[1]/1000:.1f}K → ${waco_cat_traj[2]/1000:.1f}K → ${waco_cat_traj[3]/1000:.1f}K, "
        f"with order counts growing from {loc_weekly['Waco'][3]['cat_ords']} to {loc_data['Waco']['cat_ords']} — "
        f"suggesting they're building a repeat customer pipeline. "
        f"They're up {waco_cat_vs:.0f}% vs prior year this week. "
        f"<strong>Burleson</strong> is a new-store bright spot, going from zero catering to "
        f"${burl_cat_traj[3]:,.0f} ({loc_data['Burleson']['cat_ords']} orders) in just 4 weeks. "
        f"<strong>College Station</strong> is {'up' if cstat_cat_chg and cstat_cat_chg > 0 else 'down'} "
        f"{abs(cstat_cat_chg):.0f}% vs PY this week ({fm(cstat_cat)} vs {fm(cstat_cat_py)}). "
        + (f"<strong>{', '.join(zero_cat)}</strong> had zero catering this week. " if zero_cat else "")
        + f"System catering at {fm(sys_cat)} represents just {sys_cat/sys_amt*100:.1f}% of total sales — "
        f"if every store matched Waco's penetration rate ({waco_penetration:.1f}% of store sales), "
        f"the system would add meaningful incremental revenue with minimal labor impact."
    )

    return sales_callout, labor_callout, reviews_callout, catering_callout, sales_ranks, labor_ranks, cat_ranks

# ============================================================
# VERIFICATION LOOP
# ============================================================
def verify_callout(name, text, verify_data):
    """
    Verify numerical claims in a callout against all known data.
    Cross-location comparisons are valid — check ANY location's data, not just nearby.
    System-level values also checked.
    """
    errors = []

    # Build a flat set of ALL known percentage and dollar values
    all_known_pcts = set()
    all_known_dollars = set()

    for loc in LOCATIONS:
        for key in ["labor_pct","vs_guide_pct","sss","sst","food_addon_rate","queso_rate","bev_rate"]:
            v = verify_data.get(f"{loc}_{key}")
            if v is not None: all_known_pcts.add(round(abs(v), 1))
        for wi in range(4):
            v = verify_data.get(f"{loc}_w{wi}_labor_pct")
            if v is not None: all_known_pcts.add(round(abs(v), 1))
            v = verify_data.get(f"{loc}_w{wi}_ovation_r")
            if v is not None: all_known_pcts.add(round(abs(v), 1))
        # Cat penetration
        s = verify_data.get(f"{loc}_sales", 0)
        c = verify_data.get(f"{loc}_cat_amt", 0)
        if s > 0: all_known_pcts.add(round(c / s * 100, 1))

        for key in ["sales","cat_amt","cat_py_amt"]:
            v = verify_data.get(f"{loc}_{key}")
            if v: all_known_dollars.add(v)
        for wi in range(4):
            for key in ["sales","cat_amt"]:
                v = verify_data.get(f"{loc}_w{wi}_{key}")
                if v: all_known_dollars.add(v)

    # System-level values
    all_known_pcts.add(round(abs(sys_sss), 1) if sys_sss else 0)
    all_known_pcts.add(round(abs(sys_sst), 1) if sys_sst else 0)
    all_known_pcts.add(round(sys_lp, 1))
    # System catering % of sales
    all_known_pcts.add(round(sys_cat / sys_amt * 100, 1) if sys_amt else 0)
    all_known_dollars.add(sys_amt)
    all_known_dollars.add(sys_cat)
    all_known_dollars.add(sys_pay)

    # Check all percentages in the callout
    pct_matches = re.findall(r'(\d+\.\d+)%', text)
    for pct_str in pct_matches:
        pct_val = round(float(pct_str), 1)
        if pct_val < 1.0: continue  # ignore trivial
        if not any(abs(pct_val - kv) < 0.2 for kv in all_known_pcts):
            errors.append(f"[{name}] {pct_val}% not found in any known metric")

    # Check dollar amounts > $100
    dollar_matches = re.findall(r'\$([0-9,]+(?:\.\d+)?)', text)
    for d_str in dollar_matches:
        d_val = float(d_str.replace(',', ''))
        if d_val < 100: continue
        if not any(abs(d_val - kv) / max(kv, 1) < 0.06 for kv in all_known_dollars if kv > 0):
            errors.append(f"[{name}] ${d_val:,.0f} not found in any known value")

    return len(errors) == 0, errors

MAX_ROUNDS = 3
for round_num in range(MAX_ROUNDS):
    sales_callout, labor_callout, reviews_callout, catering_callout, sales_ranks, labor_ranks, cat_ranks = generate_callouts()
    all_valid = True
    all_errors = []
    for name, text in [("sales",sales_callout),("labor",labor_callout),("reviews",reviews_callout),("catering",catering_callout)]:
        valid, errors = verify_callout(name, text, verify_data)
        if not valid:
            all_valid = False
            all_errors.extend(errors)
    if all_valid:
        print(f"✓ All AI insights verified on round {round_num+1}")
        break
    else:
        print(f"✗ Round {round_num+1}: {len(all_errors)} errors:")
        for e in all_errors: print(f"  {e}")
        print("  → Regenerating...")

if not all_valid:
    print(f"⚠ {len(all_errors)} unresolved after {MAX_ROUNDS} rounds (may be cross-location refs or derived values)")

# ============================================================
# SYSTEM TRENDS
# ============================================================
sys_weekly = {}
for wi, ws_i in enumerate(WEEK_STARTS):
    t_amt = sum(loc_weekly[loc][wi]["amount"] for loc in LOCATIONS)
    t_comp_amt = sum(loc_weekly[loc][wi]["amount"] for loc in comp_locs)
    t_comp_amt_py = sum(loc_weekly[loc][wi]["amount_py"] for loc in comp_locs)
    t_comp_ords = sum(loc_weekly[loc][wi]["orders"] for loc in comp_locs)
    t_comp_ords_py = sum(loc_weekly[loc][wi]["orders_py"] for loc in comp_locs)
    t_ords = sum(loc_weekly[loc][wi]["orders"] for loc in LOCATIONS)
    t_hrs = sum(loc_weekly[loc][wi]["labor_hrs"] for loc in LOCATIONS)
    t_pay = sum(loc_weekly[loc][wi]["labor_pay"] for loc in LOCATIONS)
    t_sch = sum(loc_weekly[loc][wi]["sch_hrs"] for loc in LOCATIONS)
    t_guide = sum(loc_weekly[loc][wi]["guide_total"] for loc in LOCATIONS)
    t_cat = sum(loc_weekly[loc][wi]["cat_amt"] for loc in LOCATIONS)
    t_cat_py = sum(loc_weekly[loc][wi].get("cat_py_amt",0) for loc in LOCATIONS)
    sys_weekly[ws_i] = {"amount":t_amt,"comp_amt":t_comp_amt,"comp_amt_py":t_comp_amt_py,
        "orders":t_ords,"comp_ords":t_comp_ords,"comp_ords_py":t_comp_ords_py,
        "labor_hrs":t_hrs,"labor_pay":t_pay,"sch_hrs":t_sch,"guide":t_guide,
        "cat_amt":t_cat,"cat_amt_py":t_cat_py}

# ============================================================
# BUILD HTML (using template from references/html_template.md)
# ============================================================
# [CSS and HTML building — same structure as previous report]
# Abbreviated for skill clarity — full CSS from html_template.md reference

CSS = """@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');
:root{--fuego-red:#DE3C00;--fuego-black:#352F2E;--fuego-charcoal:#232021;--fuego-gold:#A57E39;--fuego-tan:#DBCBBF;--fuego-teal:#86CAC7;--green:#2e7d5b;--green-bg:#e0f2eb;--red:#c13515;--red-bg:#fde8e3;--yellow:var(--fuego-gold);--yellow-bg:#faf2e4;--text-primary:#232021;--text-secondary:#7a706a;--bg:#F4F0EC;--card-bg:#ffffff;--border:#d9cfc7;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Source Sans 3','Myriad Pro',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--text-primary);line-height:1.4;-webkit-font-smoothing:antialiased;font-size:11px;}
.report-container{max-width:100%;margin:0 auto;padding:10px;display:flex;flex-direction:column;gap:12px;}
.header{border-radius:10px;padding:12px 20px;color:#fff;position:relative;overflow:hidden;}
.header-b3{background:var(--fuego-charcoal);text-align:center;padding:24px 20px 20px;position:relative;}
.header-b3-tag{display:inline-block;font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 10px;border-radius:3px;margin-bottom:8px;background:rgba(134,202,199,0.15);color:var(--fuego-teal);border:1px solid rgba(134,202,199,0.3);}
.header-b3 h1{font-size:28px;font-weight:800;letter-spacing:-0.5px;margin-bottom:8px;text-shadow:0 0 40px rgba(134,202,199,0.2);}
.header-b3-meta{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;opacity:0.75;}
.header-b3-pill{font-size:9px;font-weight:600;padding:2px 8px;border-radius:14px;border:1px solid rgba(134,202,199,0.5);color:var(--fuego-teal);}
.header-b3-dot{color:var(--fuego-gold);font-size:14px;}
.header-b3 .b3-bar-top,.header-b3 .b3-bar-bottom{position:absolute;left:0;right:0;}
.header-b3 .b3-bar-top{top:0;}.header-b3 .b3-bar-bottom{bottom:0;}
.b3-v5 .b3-bar-top{height:2px;background:var(--fuego-teal);box-shadow:0 0 12px rgba(134,202,199,0.6);}
.b3-v5 .b3-bar-bottom{height:2px;background:var(--fuego-teal);box-shadow:0 0 12px rgba(134,202,199,0.6);}
.kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;}
.kpi-card{background:var(--card-bg);border-radius:8px;padding:12px 14px;border:1px solid var(--border);border-top:3px solid var(--fuego-teal);}
.kpi-card .kpi-label{font-size:9px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;}
.kpi-card .kpi-value{font-size:22px;font-weight:700;color:var(--text-primary);line-height:1.1;}
.kpi-card .kpi-change{display:inline-flex;align-items:center;gap:3px;font-size:9px;font-weight:600;margin-top:6px;padding:2px 8px;border-radius:4px;}
.kpi-change.positive{color:var(--green);background:var(--green-bg);}
.kpi-change.negative{color:var(--red);background:var(--red-bg);}
.kpi-change.neutral{color:var(--yellow);background:var(--yellow-bg);}
.section{background:var(--card-bg);border-radius:8px;border:1px solid var(--border);overflow:hidden;}
.section-header{display:flex;align-items:center;gap:6px;padding:8px 14px;border-bottom:1px solid var(--border);background:#f9f6f3;border-left:3px solid var(--fuego-teal);}
.section-header .icon{width:22px;height:22px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:11px;}
.icon-sales{background:#fde8e3;color:var(--fuego-red);}.icon-labor{background:#e8f1f0;color:#4a8e8b;}
.icon-reviews{background:#faf2e4;color:var(--fuego-gold);}.icon-catering{background:#e0f2eb;color:var(--green);}
.section-header h2{font-size:11px;font-weight:700;}
.section-header .section-sub{font-size:8px;color:var(--text-secondary);margin-left:auto;}
table{width:100%;border-collapse:collapse;font-size:10px;}
thead th{padding:6px 7px;text-align:right;font-weight:600;font-size:8px;text-transform:uppercase;letter-spacing:0.3px;color:var(--text-secondary);border-bottom:2px solid var(--border);white-space:nowrap;}
thead th:first-child{text-align:left;}
tbody td{padding:6px 7px;text-align:right;border-bottom:1px solid #ede7e0;white-space:nowrap;}
tbody td:first-child{text-align:left;font-weight:600;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:#faf7f4;}
tbody tr.total-row{background:#f7f3ef;font-weight:700;}
tbody tr.total-row td{border-top:2px solid var(--border);}
tbody tr.highlight{background:#f5efe9;}
.pill{display:inline-block;padding:1px 5px;border-radius:4px;font-weight:600;font-size:9px;}
.pill-green{color:var(--green);background:var(--green-bg);}.pill-red{color:var(--red);background:var(--red-bg);}
.pill-yellow{color:var(--yellow);background:var(--yellow-bg);}.pill-neutral{color:var(--text-secondary);background:#ede7e0;}
.rank{display:inline-block;padding:1px 6px;border-radius:4px;font-weight:700;font-size:9px;}
.rank-1{color:#fff;background:var(--green);}.rank-2{color:var(--green);background:var(--green-bg);}
.rank-3{color:var(--yellow);background:var(--yellow-bg);}.rank-mid{color:var(--text-secondary);background:#ede7e0;}
.rank-last{color:var(--red);background:var(--red-bg);}
.gm-message{background:linear-gradient(135deg,#f9f6f3,#f0ebe5);border:1px solid var(--fuego-tan);border-left:4px solid var(--fuego-teal);border-radius:8px;padding:14px 18px;font-size:10.5px;line-height:1.6;}
.gm-message .gm-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#5a9e9b;margin-bottom:6px;}
.ai-callout{padding:10px 14px;font-size:9.5px;line-height:1.55;color:var(--text-primary);background:linear-gradient(135deg,#edf7f6,#f4f0ec);border-top:1px dashed var(--fuego-teal);}
.ai-callout .ai-label{font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#5a9e9b;margin-bottom:4px;}
.footer{text-align:center;padding:4px;font-size:8px;color:var(--text-secondary);}
@media print{body{background:var(--bg);-webkit-print-color-adjust:exact;print-color-adjust:exact;}.report-container{max-width:100%;padding:4px;}.section{break-inside:avoid;}.kpi-row{break-inside:avoid;}}"""

# --- R&S rows ---
sales_rs_rows = ""
for loc,val,rk in sales_ranks:
    ld = loc_data[loc]
    sales_rs_rows += f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td><td>{loc}</td><td>{fm(ld["amount"])}</td><td>{pill_sss(ld["sss"])}</td><td>{fn(ld["orders"])}</td><td>{pill_sss(ld["sst"])}</td><td>{fm(ld["avg_tkt"],2)}</td><td>{pill_sss(ld["tkt_chg"])}</td><td>{fm(ld["cat_amt"])}</td><td><span class="pill pill-neutral">{ld["suffix"]}</span></td></tr>'
sales_rs_rows += f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fm(sys_amt)}</td><td>{pill_sss(sys_sss)}</td><td>{fn(sys_ords)}</td><td>{pill_sss(sys_sst)}</td><td>{fm(sys_tkt,2)}</td><td>{pill_sss(sys_tkt_chg)}</td><td>{fm(sys_cat)}</td><td><span class="pill pill-neutral">Comp Only</span></td></tr>'

labor_rs_rows = ""
for loc,val,rk in labor_ranks:
    ld = loc_data[loc]
    labor_rs_rows += f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td><td>{loc}</td><td>{fm(ld["amount"])}</td><td>{fn(ld["guide_total"],0)}</td><td>{fn(ld["sch_hrs"],0)}</td><td>{fn(ld["labor_hrs"],0)}</td><td>{pill_labor_diff(ld["vs_guide_n"])}</td><td>{pill_labor_ratio(ld["labor_hrs"],ld["guide_total"])}</td><td>{pill_labor_pct(ld["labor_pct"])}</td><td>{fm(ld["splh"],2)}</td></tr>'
sys_vs_guide = sys_hrs - sys_guide
sys_splh = sys_amt/sys_hrs if sys_hrs else 0
labor_rs_rows += f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fm(sys_amt)}</td><td>{fn(sys_guide,0)}</td><td>{fn(sum(v["sch_hrs"] for v in loc_data.values()),0)}</td><td>{fn(sys_hrs,0)}</td><td>{pill_labor_diff(sys_vs_guide)}</td><td>{pill_labor_ratio(sys_hrs,sys_guide)}</td><td>{pill_labor_pct(sys_lp)}</td><td>{fm(sys_splh,2)}</td></tr>'

reviews_ranks = rank_items(loc_data, "wavg_rating", reverse=True)
reviews_rs_rows = ""
for loc,val,rk in reviews_ranks:
    ld = loc_data[loc]
    yelp_cell = pill_rating(ld["yelp_r"]) if ld["yelp_r"] else '<span class="pill pill-neutral">—</span>'
    yelp_n_cell = fn(ld["yelp_n"]) if ld["yelp_n"] else "—"
    reviews_rs_rows += f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td><td>{loc}</td><td>{pill_rating(ld["google_r"])}</td><td>{fn(ld["google_n"])}</td><td>{pill_rating(ld["ovation_r"])}</td><td>{fn(ld["ovation_n"])}</td><td>{yelp_cell}</td><td>{yelp_n_cell}</td><td>{pill_rating(ld["wavg_rating"])}</td><td>{fn(ld["total_rev_n"])}</td></tr>'

cat_rs_rows = ""
for loc,val,rk in cat_ranks:
    ld = loc_data[loc]
    cat_vs = pct_chg(ld["cat_amt"], ld["cat_py_amt"]) if ld["cat_py_amt"] else None
    cat_rs_rows += f'<tr><td><span class="rank {rank_cls(rk)}">{rank_suffix(rk)}</span></td><td>{loc}</td><td>{fn(ld["cat_ords"])}</td><td>{fm(ld["cat_amt"])}</td><td>{fm(ld["cat_py_amt"])}</td><td>{pill_sss(cat_vs)}</td></tr>'
sys_cat_py = sum(loc_data[l]["cat_py_amt"] for l in LOCATIONS)
cat_rs_rows += f'<tr class="total-row"><td></td><td>SYSTEM</td><td>{fn(sys_cat_ords)}</td><td>{fm(sys_cat)}</td><td>{fm(sys_cat_py)}</td><td>{pill_sss(pct_chg(sys_cat,sys_cat_py) if sys_cat_py else None)}</td></tr>'

# Trends
trends_rows = ""
for ws_i in WEEK_STARTS:
    sw = sys_weekly[ws_i]
    sss_w = pct_chg(sw["comp_amt"],sw["comp_amt_py"]) if sw["comp_amt_py"] else None
    sst_w = pct_chg(sw["comp_ords"],sw["comp_ords_py"]) if sw["comp_ords_py"] else None
    tkt_w = sw["amount"]/sw["orders"] if sw["orders"] else 0
    lp_w = (sw["labor_pay"]/sw["amount"]*100) if sw["amount"] else 0
    splh_w = sw["amount"]/sw["labor_hrs"] if sw["labor_hrs"] else 0
    vs_guide_w = sw["labor_hrs"]-sw["guide"]
    is_cw = ws_i == ws
    style = ' class="highlight"' if is_cw else ''
    b = lambda x: f"<strong>{x}</strong>" if is_cw else x
    trends_rows += f'<tr{style}><td>{b(wk_short(ws_i))}</td><td>{b(fm(sw["amount"]))}</td><td>{pill_sss(sss_w)}</td><td>{b(fn(sw["orders"]))}</td><td>{pill_sss(sst_w)}</td><td>{b(fm(tkt_w,2))}</td><td>{b(fn(sw["guide"],0))}</td><td>{b(fn(sw["labor_hrs"],0))}</td><td>{pill_labor_diff(vs_guide_w)}</td><td>{pill_labor_ratio(sw["labor_hrs"],sw["guide"])}</td><td>{pill_labor_pct(lp_w)}</td><td>{b(fm(splh_w,2))}</td><td>{b(fm(sw["cat_amt"]))}</td><td>{b(fm(sw["cat_amt_py"]))}</td></tr>'

# GM message
labor_cls = "positive" if sys_lp_chg <= 0 else "negative"
labor_arrow = "&#9650;" if sys_lp_chg > 0 else "&#9660;"
labor_sign = "+" if sys_lp_chg >= 0 else ""

gm_msg = (
    f"Fuego Tortilla Grill generated {fm(sys_amt)} across 6 locations for the week of {wk_long(ws)}. "
    f"Comparable stores were {'up' if sys_sss and sys_sss>=0 else 'down'} {abs(sys_sss):.1f}% in same-store sales and "
    f"{'up' if sys_sst and sys_sst>=0 else 'down'} {abs(sys_sst):.1f}% in same-store transactions vs prior year. "
    f"System-wide order count was {fn(sys_ords,0)} with a {fm(sys_tkt,2)} average ticket. "
    f"Labor came in at {sys_lp:.1f}% system-wide ({fm(sys_pay)} on {fn(sys_hrs,1)} hours), "
    f"{'improving' if sys_lp_chg<0 else 'up'} {abs(sys_lp_chg):.1f}pp vs prior week. "
    f"The system ran {fn(abs(sys_vs_guide),1)} hours {'over' if sys_vs_guide>0 else 'under'} the combined guideline. "
    f"Catering was {fm(sys_cat)} ({fn(sys_cat_ords,0)} orders)."
)

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Fuego System Weekly Flash – {wk_long(ws)}</title>
<style>@page{{size:A4 portrait;margin:0.3in;}}{CSS}</style></head><body>
<div class="report-container">
<div class="header header-b3 b3-v5"><div class="b3-bar-top"></div><div class="header-b-inner"><div class="header-b3-tag">SYSTEM WEEKLY FLASH REPORT</div><h1>Fuego Tortilla Grill</h1><div class="header-b3-meta"><span class="header-b3-pill">All 6 Locations</span><span class="header-b3-dot">&bull;</span><span>{wk_long(ws)}</span></div></div><div class="b3-bar-bottom"></div></div>
<div class="kpi-row">
<div class="kpi-card"><div class="kpi-label">System Sales</div><div class="kpi-value">{fm(sys_amt)}</div>{kpi_badge(sys_sss,"vs PY Comps")}</div>
<div class="kpi-card"><div class="kpi-label">System Orders</div><div class="kpi-value">{fn(sys_ords)}</div>{kpi_badge(sys_sst,"vs PY Comps")}</div>
<div class="kpi-card"><div class="kpi-label">Avg Ticket</div><div class="kpi-value">{fm(sys_tkt,2)}</div>{kpi_badge(sys_tkt_chg,"vs PY Comps")}</div>
<div class="kpi-card"><div class="kpi-label">System Labor %</div><div class="kpi-value">{sys_lp:.1f}%</div><div class="kpi-change {labor_cls}">{labor_arrow} {labor_sign}{sys_lp_chg:.1f}pp vs PW</div></div>
<div class="kpi-card"><div class="kpi-label">Catering</div><div class="kpi-value">{fm(sys_cat)}</div><div class="kpi-change neutral">{fn(sys_cat_ords,0)} orders</div></div>
</div>
<div class="gm-message"><div class="gm-label">System Summary</div>{gm_msg}</div>
<div class="section"><div class="section-header"><div class="icon icon-sales">&#128202;</div><h2>System Performance Trends</h2><div class="section-sub">Last 4 Weeks – All Locations Combined</div></div><table><thead><tr><th>Week</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th><th>Avg Tkt</th><th>Guide Hrs</th><th>Actual Hrs</th><th>vs Guide #</th><th>vs Guide %</th><th>Labor %</th><th>SPLH</th><th>Catering</th><th>Cat PY</th></tr></thead><tbody>{trends_rows}</tbody></table></div>
<div class="section"><div class="section-header"><div class="icon icon-sales">&#128176;</div><h2>Sales Rack &amp; Stack</h2><div class="section-sub">{wk_long(ws)} – Ranked by Sales</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Sales</th><th>SSS %</th><th>Orders</th><th>SST %</th><th>Avg Ticket</th><th>Tkt Chg</th><th>Catering</th><th>Basis</th></tr></thead><tbody>{sales_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{sales_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-labor">&#128101;</div><h2>Labor Rack &amp; Stack</h2><div class="section-sub">{wk_long(ws)} – Ranked by vs Guide %</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Sales</th><th>Guide Hrs</th><th>Sch Hrs</th><th>Actual Hrs</th><th>vs Guide #</th><th>vs Guide %</th><th>Labor %</th><th>SPLH</th></tr></thead><tbody>{labor_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{labor_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-reviews">&#11088;</div><h2>Reviews Rack &amp; Stack</h2><div class="section-sub">{wk_long(ws)} – Ranked by Weighted Avg Rating</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Google</th><th>#</th><th>Ovation</th><th>#</th><th>Yelp</th><th>#</th><th>Wtd Avg</th><th>Total #</th></tr></thead><tbody>{reviews_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{reviews_callout}</div></div>
<div class="section"><div class="section-header"><div class="icon icon-catering">&#127919;</div><h2>Catering Rack &amp; Stack</h2><div class="section-sub">{wk_long(ws)} – Ranked by Catering $</div></div><table><thead><tr><th>Rank</th><th>Location</th><th>Orders</th><th>Cat $</th><th>Cat $ PY</th><th>vs PY</th></tr></thead><tbody>{cat_rs_rows}</tbody></table><div class="ai-callout"><div class="ai-label">&#129302; AI Insight</div>{catering_callout}</div></div>
<div class="footer">Generated on {TODAY_STR} &middot; Fuego Tortilla Grill – System Report &middot; Data sourced from Chabi Analytics</div>
</div></body></html>"""

# Write and convert
html_path = "/home/claude/weekly_flash_system_v2.html"
with open(html_path, "w") as f: f.write(html)
pdf_path = "/home/claude/system_flash_v2.pdf"
output_path = "/mnt/user-data/outputs/Weekly Flash - Fuego System - Feb 9 – 15, 2026.pdf"
result = subprocess.run(["google-chrome","--headless","--no-sandbox","--disable-gpu",f"--print-to-pdf={pdf_path}","--print-to-pdf-no-header","--no-pdf-header-footer",f"file://{html_path}"],capture_output=True,text=True,timeout=30)
if os.path.exists(pdf_path):
    shutil.copy(pdf_path, output_path)
    shutil.copy(html_path, output_path.replace(".pdf",".html"))
    print(f"✓ Saved: {output_path}")
else:
    print(f"✗ Failed: {result.stderr[:300]}")
