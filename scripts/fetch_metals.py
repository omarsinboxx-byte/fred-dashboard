#!/usr/bin/env python3
"""
Pull spot gold and silver prices (USD/oz) from Stooq's free, keyless daily
CSV endpoint and write data/metals.json for the dashboard (index.html) to
render alongside the FRED macro series.

No API key required. Stooq symbols used:
    XAUUSD  -> spot gold, USD per troy ounce
    XAGUSD  -> spot silver, USD per troy ounce

Usage:
    python scripts/fetch_metals.py
"""
import csv
import io
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metals.json")

METALS = {
    "XAUUSD": {"name": "Gold Spot", "unit": "$/oz", "group": "metals", "keep": 260},
    "XAGUSD": {"name": "Silver Spot", "unit": "$/oz", "group": "metals", "keep": 260},
}


def fetch_csv(symbol, retries=3):
    url = STOOQ_URL.format(symbol=symbol.lower())
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {symbol}: {last_err}")


def parse_rows(raw_csv):
    """Stooq daily CSV: Date,Open,High,Low,Close,Volume"""
    out = []
    reader = csv.DictReader(io.StringIO(raw_csv))
    for row in reader:
        try:
            date = row["Date"]
            close = float(row["Close"])
        except (KeyError, ValueError, TypeError):
            continue
        out.append({"date": date, "value": round(close, 2)})
    return out


def build():
    result = {}
    for symbol, meta in METALS.items():
        print(f"Fetching {symbol} ({meta['name']}) from Stooq...")
        try:
            raw = fetch_csv(symbol)
            points = parse_rows(raw)
            if not points:
                print(f"  WARNING: no usable rows for {symbol}")
                continue

            keep = meta["keep"]
            trimmed = points[-keep:] if len(points) > keep else points
            latest = trimmed[-1]
            prev = trimmed[-2] if len(trimmed) > 1 else None

            result[symbol] = {
                "id": symbol,
                "name": meta["name"],
                "unit": meta["unit"],
                "group": meta["group"],
                "latest_date": latest["date"],
                "latest_value": latest["value"],
                "prev_value": prev["value"] if prev else None,
                "history": trimmed,
            }
        except Exception as e:  # noqa: BLE001
            # One symbol failing (Stooq hiccup, rate limit) shouldn't block
            # the other, and shouldn't crash the whole workflow step.
            print(f"  ERROR fetching {symbol}: {e}")
            continue
        time.sleep(0.5)  # be polite to Stooq

    payload = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Stooq (stooq.com)",
        "series": result,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
