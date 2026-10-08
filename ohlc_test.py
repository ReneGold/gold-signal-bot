import os
import requests

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    raise RuntimeError("TWELVE_DATA_API_KEY fehlt")

url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",
    "outputsize": 8,
    "apikey": API_KEY,
    "timezone": "UTC",
}

r = requests.get(url, params=params, timeout=20)
r.raise_for_status()

data = r.json()

if "values" not in data:
    raise RuntimeError(f"Twelve Data Fehler: {data}")

print("=== TWELVE DATA XAU/USD 15 MIN ===")

for candle in reversed(data["values"]):
    print(
        f"{candle['datetime']} | "
        f"O={float(candle['open']):.2f} | "
        f"H={float(candle['high']):.2f} | "
        f"L={float(candle['low']):.2f} | "
        f"C={float(candle['close']):.2f}"
    )
