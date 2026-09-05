#!/usr/bin/env python3
"""
Pull the core macro series from the FRED API and write data/latest.json
for the dashboard (index.html) to render.

Requires an API key from https://fred.stlouisfed.org/docs/api/api_key.html
passed via the FRED_API_KEY environment variable.

Usage:
    FRED_API_KEY=xxxxx python scripts/fetch_fred.py
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "latest.json")

# Each entry: FRED series id -> metadata used to build the dashboard.
# "keep" controls how many most-recent observations are kept in the
# output file (enough for the sparkline / history chart, not the full
# history FRED has on file).
SERIES = {
    "DFF":       {"name": "Effective Fed Funds Rate", "unit": "%",       "keep": 260, "group": "rates"},
    "DGS2":      {"name": "2-Year Treasury Yield",     "unit": "%",       "keep": 260, "group": "rates"},
    "DGS10":     {"name": "10-Year Treasury Yield",    "unit": "%",       "keep": 260, "group": "rates"},
    "T10Y2Y":    {"name": "10Y-2Y Treasury Spread",    "unit": "pp",      "keep": 260, "group": "rates"},
    "CPIAUCSL":  {"name": "CPI (YoY)",                 "unit": "%",       "keep": 36,  "group": "inflation", "transform": "yoy_pct"},
    "PCEPILFE":  {"name": "Core PCE (YoY)",            "unit": "%",       "keep": 36,  "group": "inflation", "transform": "yoy_pct"},
    "UNRATE":    {"name": "Unemployment Rate",         "unit": "%",       "keep": 36,  "group": "labor"},
    "PAYEMS":    {"name": "Nonfarm Payrolls (MoM)",    "unit": "K jobs",  "keep": 36,  "group": "labor", "transform": "mom_diff"},
    "ICSA":      {"name": "Initial Jobless Claims",    "unit": "claims",  "keep": 52,  "group": "labor"},
    "M2SL":      {"name": "M2 Money Supply (YoY)",     "unit": "%",       "keep": 36,  "group": "growth", "transform": "yoy_pct"},
    "A191RL1Q225SBEA": {"name": "Real GDP Growth (QoQ ann.)", "unit": "%", "keep": 24, "group": "growth"},
    "DTWEXBGS":  {"name": "US Dollar Index (Broad)",   "unit": "index",   "keep": 260, "group": "growth"},
    "VIXCLS":    {"name": "CBOE Volatility Index",     "unit": "index",   "keep": 260, "group": "growth"},
}


def fetch_series(series_id, api_key, retries=3):
    params = f"series_id={series_id}&api_key={api_key}&file_type=json&sort_order=asc"
    url = f"{FRED_BASE}?{params}"
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload.get("observations", [])
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {series_id}: {last_err}")


def clean(observations):
    """Drop FRED's '.' (missing value) placeholders, cast to float."""
    out = []
    for obs in observations:
        v = obs.get("value")
        if v in (None, ".", ""):
            continue
        try:
            out.append({"date": obs["date"], "value": float(v)})
        except ValueError:
            continue
    return out


def transform_yoy_pct(points):
    """Year-over-year % change for a monthly series (12-period lag)."""
    out = []
    for i in range(12, len(points)):
        prev, cur = points[i - 12], points[i]
        if prev["value"] == 0:
            continue
        pct = (cur["value"] / prev["value"] - 1.0) * 100.0
        out.append({"date": cur["date"], "value": round(pct, 2)})
    return out


def transform_mom_diff(points):
    """Month-over-month absolute change (e.g. payrolls, already in thousands)."""
    out = []
    for i in range(1, len(points)):
        prev, cur = points[i - 1], points[i]
        out.append({"date": cur["date"], "value": round(cur["value"] - prev["value"], 1)})
    return out


TRANSFORMS = {
    "yoy_pct": transform_yoy_pct,
    "mom_diff": transform_mom_diff,
}


def build():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("ERROR: FRED_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html", file=sys.stderr)
        sys.exit(1)

    result = {}
    for series_id, meta in SERIES.items():
        print(f"Fetching {series_id} ({meta['name']})...")
        raw = clean(fetch_series(series_id, api_key))
        transform = meta.get("transform")
        if transform:
            points = TRANSFORMS[transform](raw)
        else:
            points = raw

        keep = meta["keep"]
        trimmed = points[-keep:] if len(points) > keep else points
        if not trimmed:
            print(f"  WARNING: no usable observations for {series_id}", file=sys.stderr)
            continue

        latest = trimmed[-1]
        prev = trimmed[-2] if len(trimmed) > 1 else None

        result[series_id] = {
            "id": series_id,
            "name": meta["name"],
            "unit": meta["unit"],
            "group": meta["group"],
            "latest_date": latest["date"],
            "latest_value": latest["value"],
            "prev_value": prev["value"] if prev else None,
            "history": trimmed,
        }
        time.sleep(0.2)  # be polite to the API

    payload = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Federal Reserve Bank of St. Louis (FRED)",
        "series": result,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build()

