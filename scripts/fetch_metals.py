#!/usr/bin/env python3
"""
Pull gold and silver prices (USD/oz, COMEX front-month futures used as a
spot-price proxy) from Yahoo Finance's public chart endpoint and write
data/metals.json for the dashboard (index.html) to render alongside the
FRED macro series.

No API key required.

Background: this previously scraped Stooq's keyless CSV endpoint
(stooq.com/q/d/l/), but Stooq now gates that endpoint behind a
JavaScript proof-of-work challenge that a plain HTTP client can't solve,
so every fetch silently returned zero rows and data/metals.json ended up
with an empty "series". Yahoo's chart API returns JSON directly with no
such gate.

Yahoo Finance symbols used:
    GC=F  -> COMEX gold futures (front month), USD per troy ounce
    SI=F  -> COMEX silver futures (front month), USD per troy ounce
Stored in the output under the XAUUSD / XAGUSD keys the dashboard expects.

Usage:
    python scripts/fetch_metals.py
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"

METALS = {
    "XAUUSD": {"yahoo_symbol": "GC=F", "name": "Gold (COMEX front month)", "unit": "$/oz", "group": "metals", "keep": 260},
    "XAGUSD": {"yahoo_symbol": "SI=F", "name": "Silver (COMEX front month)", "unit": "$/oz", "group": "metals", "keep": 260},
}

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metals.json")

def fetch_chart(symbol, retries=3):
    url = CHART_URL.format(symbol=symbol)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {symbol}: {last_err}")

def parse_points(payload):
    result = payload.get("chart", {}).get("result") or []
    if not result:
        return []
    r = result[0]
    timestamps = r.get("timestamp") or []
    quotes = (r.get("indicators", {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    out = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        out.append({"date": d.strftime("%Y-%m-%d"), "value": round(float(close), 2)})
    return out

def build():
    result = {}
    for key, meta in METALS.items():
        symbol = meta["yahoo_symbol"]
        print(f"Fetching {symbol} ({meta['name']}) from Yahoo Finance...")
        try:
            payload = fetch_chart(symbol)
            points = parse_points(payload)
            if not points:
                print(f"  WARNING: no usable rows for {symbol}")
                continue

            keep = meta["keep"]
            trimmed = points[-keep:] if len(points) > keep else points
            latest = trimmed[-1]
            prev = trimmed[-2] if len(trimmed) > 1 else None

            result[key] = {
                "id": key,
                "name": meta["name"],
                "unit": meta["unit"],
                "group": meta["group"],
                "latest_date": latest["date"],
                "latest_value": latest["value"],
                "prev_value": prev["value"] if prev else None,
                "history": trimmed,
            }
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR fetching {symbol}: {e}")
            continue
        time.sleep(0.5)

    payload_out = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Yahoo Finance (COMEX front-month futures, GC=F / SI=F)",
        "series": result,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload_out, f, indent=2)
    print(f"Wrote {OUT_PATH}")

if __name__ == "__main__":
    build()
