#!/usr/bin/env python3
"""
Generate a plausible-looking data/latest.json so the dashboard has
something to render before the first real FRED pull. Not real data —
the output is flagged with "sample": true and the dashboard shows a
banner saying so.

Usage: python scripts/generate_sample_data.py
"""
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

random.seed(7)
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "latest.json")


def daterange_daily(n, end):
    return [(end - timedelta(days=i)) for i in range(n - 1, -1, -1)]


def daterange_monthly(n, end):
    dates = []
    y, m = end.year, end.month
    for i in range(n - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        dates.append(datetime(yy, mm, 1))
    return dates


def daterange_weekly(n, end):
    return [(end - timedelta(weeks=i)) for i in range(n - 1, -1, -1)]


def series_from(dates, gen_fn, keep):
    pts = [{"date": d.strftime("%Y-%m-%d"), "value": round(gen_fn(i, len(dates)), 2)} for i, d in enumerate(dates)]
    return pts[-keep:]


def noisy_walk(start, drift, vol, n, i):
    random.seed(hash((start, drift, n)) % (2**31))


def build():
    today = datetime.now(timezone.utc).replace(tzinfo=None)

    def make_walk(start, drift_per_step, vol, n_points, floor=None, ceil=None):
        vals = []
        v = start
        for i in range(n_points):
            v += drift_per_step + random.gauss(0, vol)
            if floor is not None:
                v = max(floor, v)
            if ceil is not None:
                v = min(ceil, v)
            vals.append(v)
        return vals

    def with_dates(dates, values):
        return [{"date": d.strftime("%Y-%m-%d"), "value": round(v, 2)} for d, v in zip(dates, values)]

    daily_dates = daterange_daily(260, today)
    monthly_dates = daterange_monthly(36, today)
    weekly_dates = daterange_weekly(52, today)
    gdp_dates = daterange_monthly(24, today)[::3][-24:]  # rough quarterly stand-in

    series = {}

    def add(sid, name, unit, group, dates, values):
        series[sid] = {
            "id": sid, "name": name, "unit": unit, "group": group,
            "latest_date": dates[-1].strftime("%Y-%m-%d"),
            "latest_value": round(values[-1], 2),
            "prev_value": round(values[-2], 2) if len(values) > 1 else None,
            "history": with_dates(dates, values),
        }

    add("DFF", "Effective Fed Funds Rate", "%", "rates", daily_dates,
        make_walk(5.33, -0.0005, 0.01, 260, floor=0))
    add("DGS2", "2-Year Treasury Yield", "%", "rates", daily_dates,
        make_walk(4.3, -0.001, 0.03, 260, floor=0))
    add("DGS10", "10-Year Treasury Yield", "%", "rates", daily_dates,
        make_walk(4.1, 0.0005, 0.03, 260, floor=0))
    dgs2_hist = series["DGS2"]["history"]
    dgs10_hist = series["DGS10"]["history"]
    spread_vals = [round(b["value"] - a["value"], 2) for a, b in zip(dgs2_hist, dgs10_hist)]
    add("T10Y2Y", "10Y-2Y Treasury Spread", "pp", "rates", daily_dates, spread_vals)

    add("CPIAUCSL", "CPI (YoY)", "%", "inflation", monthly_dates,
        [2.8 + 0.4 * math.sin(i / 6) + random.gauss(0, 0.05) for i in range(36)])
    add("PCEPILFE", "Core PCE (YoY)", "%", "inflation", monthly_dates,
        [2.6 + 0.3 * math.sin(i / 7 + 1) + random.gauss(0, 0.05) for i in range(36)])

    add("UNRATE", "Unemployment Rate", "%", "labor", monthly_dates,
        make_walk(4.1, 0.002, 0.03, 36, floor=3.0, ceil=6.0))
    add("PAYEMS", "Nonfarm Payrolls (MoM)", "K jobs", "labor", monthly_dates,
        [150 + 60 * math.sin(i / 5) + random.gauss(0, 25) for i in range(36)])
    add("ICSA", "Initial Jobless Claims", "claims", "labor", weekly_dates,
        [225000 + 15000 * math.sin(i / 8) + random.gauss(0, 5000) for i in range(52)])

    add("M2SL", "M2 Money Supply (YoY)", "%", "growth", monthly_dates,
        [1.5 + 2.0 * math.sin(i / 10) + random.gauss(0, 0.1) for i in range(36)])
    add("A191RL1Q225SBEA", "Real GDP Growth (QoQ ann.)", "%", "growth", gdp_dates,
        [2.2 + 1.2 * math.sin(i / 3) + random.gauss(0, 0.2) for i in range(len(gdp_dates))])
    add("DTWEXBGS", "US Dollar Index (Broad)", "index", "growth", daily_dates,
        make_walk(122, 0.0, 0.15, 260, floor=100))
    add("VIXCLS", "CBOE Volatility Index", "index", "growth", daily_dates,
        make_walk(15, 0.0, 0.6, 260, floor=9, ceil=45))

    payload = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Federal Reserve Bank of St. Louis (FRED)",
        "sample": True,
        "series": series,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote sample data to {OUT_PATH}")


if __name__ == "__main__":
    build()

