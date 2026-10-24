#!/usr/bin/env python3
"""Historical XAU/USD OHLC collection. Data only; no trading and no messages."""
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
SYMBOL = "XAU/USD"
START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 24, tzinfo=timezone.utc)
OUT = Path("gold_historical_data")
OUT.mkdir(exist_ok=True)
if not API_KEY:
    raise SystemExit("Missing TWELVE_DATA_API_KEY")

def fetch(interval, days):
    rows = {}
    cur = START
    segments = 0
    while cur < END:
        stop = min(cur + timedelta(days=days), END)
        params = {
            "symbol": SYMBOL, "interval": interval, "apikey": API_KEY,
            "start_date": cur.strftime("%Y-%m-%dT%H:%M:%S"),
            "end_date": stop.strftime("%Y-%m-%dT%H:%M:%S"),
            "outputsize": 5000, "timezone": "UTC", "format": "JSON",
        }
        response = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=40)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "error" or payload.get("code"):
            raise RuntimeError(f"{interval} {cur.date()}: provider error {payload.get('code')}: {payload.get('message')}")
        candles = payload.get("values", [])
        if not isinstance(candles, list):
            raise RuntimeError(f"Unexpected response structure for {interval}")
        for row in candles:
            if all(key in row for key in ("datetime", "open", "high", "low", "close")):
                t = datetime.fromisoformat(row["datetime"].replace(" ", "T")).replace(tzinfo=timezone.utc)
                if START <= t < END:
                    rows[t.isoformat()] = [t.isoformat()] + [float(row[k]) for k in ("open", "high", "low", "close")]
        segments += 1
        print(f"{interval}: segment {segments}, new candles={len(candles)}, total unique={len(rows)}", flush=True)
        cur = stop
        time.sleep(1.5)
    dest = OUT / f"xauusd_{interval}_20260801_20261024.csv"
    with dest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["datetime_utc", "open", "high", "low", "close"])
        writer.writerows(rows[key] for key in sorted(rows))
    if not rows:
        raise RuntimeError(f"No historical candles returned for {interval}")
    ordered = sorted(rows)
    print(f"{interval}: saved {len(rows)} unique candles, first={ordered[0]}, last={ordered[-1]}")
    return len(rows)

if __name__ == "__main__":
    try:
        count15 = fetch("15min", 7)
        count1h = fetch("1h", 14)
        print(f"DATA READY: 15min={count15}, 1h={count1h}. Data availability and gaps require review.")
    except Exception as exc:
        print(f"DATA FETCH FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
